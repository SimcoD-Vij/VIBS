from celery import Celery
from app.config import settings
from app.database import engine, Base
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy import create_engine
from app.models.db_models import Session, Segment, Speaker
from app.services.audio_service import get_audio_duration, detect_overlaps, assign_speaker_colors
import traceback
import sys

celery_app = Celery(
    "debate_analyzer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Create a synchronous engine for celery tasks since celery is sync
sync_engine = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''))

@celery_app.task(bind=True, max_retries=1)
def process_audio(self, session_id: str, wav_path: str):
    import whisperx
    import torch
    
    with SyncSession(sync_engine) as db:
        session_record = db.query(Session).filter(Session.id == session_id).first()
        if not session_record:
            return
            
        try:
            # 0. Convert to standard wav if needed
            final_wav_path = wav_path
            if not wav_path.lower().endswith('.wav'):
                print(f"Converting {wav_path} to standard WAV...")
                temp_wav = wav_path.rsplit('.', 1)[0] + "_standard.wav"
                import subprocess
                try:
                    subprocess.run([
                        'ffmpeg', '-y', '-i', wav_path,
                        '-ar', '16000', '-ac', '1',
                        temp_wav
                    ], check=True, capture_output=True)
                    final_wav_path = temp_wav
                    print(f"Conversion successful: {final_wav_path}")
                    
                    # Update DB with the new path
                    session_record.wav_path = final_wav_path
                    db.commit()
                except subprocess.CalledProcessError as e:
                    print(f"FFmpeg conversion failed: {e.stderr.decode()}")
                    # Fallback to original path and hope for the best
            
            wav_path = final_wav_path # Use the converted path for subsequent steps

            session_record.status = "transcribing"
            session_record.progress_percent = 5
            db.commit()

            duration = get_audio_duration(wav_path)
            if duration < 10.0:
                raise ValueError("Audio too short")
                
            session_record.duration_seconds = duration
            db.commit()

            device = settings.WHISPER_DEVICE
            compute_type = "float16" if device == "cuda" else "int8"

            # HOTFIX for WhisperX 301 Redirect bug via monkey-patching urllib
            import urllib.request
            import requests
            from io import BytesIO

            class MockResponse(BytesIO):
                def __init__(self, content, headers):
                    super().__init__(content)
                    self._headers = headers
                def info(self):
                    # tqdm expects an object with a .get() method (like HTTPMessage)
                    class HeaderDict(dict):
                        def get(self, key, default=None):
                            val = super().get(key.lower(), default)
                            return val if val is not None else default
                    
                    headers = {k.lower(): str(v) for k, v in self._headers.items()}
                    if 'content-length' not in headers:
                        headers['content-length'] = str(len(self.getvalue()))
                    return HeaderDict(headers)

            original_urlopen = urllib.request.urlopen

            def custom_urlopen(url, *args, **kwargs):
                url_str = str(url)
                if "whisperx" in url_str and "pytorch_model.bin" in url_str:
                    # Fix for S3 301 Redirect: move to the new official GitHub location
                    url_str = "https://github.com/m-bain/whisperX/raw/main/whisperx/assets/pytorch_model.bin"
                    print(f"Intercepted and redirected VAD model download to GitHub: {url_str}")
                    res = requests.get(url_str, allow_redirects=True)
                    res.raise_for_status()
                    return MockResponse(res.content, res.headers)
                return original_urlopen(url, *args, **kwargs)

            urllib.request.urlopen = custom_urlopen

            try:
                # 5-A: Load model
                model = whisperx.load_model(settings.WHISPER_MODEL, device, compute_type=compute_type)
            finally:
                # Restore original urlopen
                urllib.request.urlopen = original_urlopen
            audio = whisperx.load_audio(wav_path)
            
            session_record.progress_percent = 20
            db.commit()

            # 5-B: Transcribe
            result = model.transcribe(audio, batch_size=16)

            session_record.progress_percent = 40
            db.commit()

            # 5-C: Align
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

            session_record.progress_percent = 60
            db.commit()

            # 5-D: Diarize
            from whisperx.diarize import DiarizationPipeline
            diarize_segments = None
            try:
                print(f"Starting diarization for {session_id}...")
                
                # Try 1: Official gated model
                try:
                    print("Attempting to load official pyannote/speaker-diarization-3.1...")
                    diarize_model = DiarizationPipeline(
                        model_name="pyannote/speaker-diarization-3.1",
                        use_auth_token=settings.HF_TOKEN, 
                        device=device
                    )
                    # Check if model loaded (whisperx wrapper might hide failure)
                    if hasattr(diarize_model, 'model') and diarize_model.model is None:
                        raise ValueError("Official model failed to load (likely gated).")
                    
                    diarize_segments = diarize_model(wav_path)
                except Exception as e1:
                    print(f"Official model failed: {e1}. Trying non-gated community model...")
                    # Try 2: Non-gated community model
                    diarize_model = DiarizationPipeline(
                        model_name="fatymatariq/speaker-diarization-3.1",
                        use_auth_token=settings.HF_TOKEN, 
                        device=device
                    )
                    print("Diarization model loaded. Running inference...")
                    # Remove hardcoded speaker counts to prevent hangs on ambiguous audio
                    diarize_segments = diarize_model(wav_path)
                    if diarize_segments is None:
                        raise ValueError("Diarization returned None.")
                    print(f"Diarization complete for {session_id}. Found {len(diarize_segments)} segments.")
            except Exception as de:
                print(f"All diarization attempts failed for {session_id}: {de}. Falling back to single speaker.")
                print("TIP: Make sure you have accepted the terms at https://hf.co/pyannote/speaker-diarization-3.1")

            session_record.progress_percent = 75
            db.commit()

            # 5-E: Assign speakers
            if diarize_segments is not None:
                result = whisperx.assign_word_speakers(diarize_segments, result)
            else:
                # Fallback: assign all to Speaker 00
                for seg in result["segments"]:
                    seg["speaker"] = "SPEAKER_00"

            # 5-F: Detect overlap
            detect_overlaps(result["segments"])

            session_record.progress_percent = 80
            db.commit()

            # 5-G: Store in DB
            all_speakers = []
            for seg in result["segments"]:
                spk = seg.get("speaker", "SPEAKER_00")
                all_speakers.append(spk)
                db_seg = Segment(
                    session_id=session_id,
                    speaker_label=spk,
                    start_time=seg.get("start", 0.0),
                    end_time=seg.get("end", 0.0),
                    text=seg.get("text", "").strip(),
                    is_overlap=seg.get("is_overlap", False)
                )
                db.add(db_seg)
            
            colors = assign_speaker_colors(all_speakers)
            
            # Compute stats
            unique_speakers = set(all_speakers)
            session_record.speaker_count = len(unique_speakers)
            
            for spk in unique_speakers:
                spk_segments = [s for s in result["segments"] if s.get("speaker", "SPEAKER_00") == spk]
                total_secs = sum([s.get("end", 0.0) - s.get("start", 0.0) for s in spk_segments])
                share = total_secs / duration if duration > 0 else 0
                
                db_speaker = Speaker(
                    session_id=session_id,
                    speaker_label=spk,
                    display_name=f"Speaker {spk.split('_')[-1]}",
                    total_seconds=total_secs,
                    talk_share=share,
                    color=colors.get(spk, "#888780")
                )
                db.add(db_speaker)

            session_record.progress_percent = 90
            db.commit()

            # 5-H: Enqueue analyze
            analyze_session.delay(session_id)
            
            session_record.progress_percent = 95
            db.commit()
            
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            session_record.status = "failed"
            session_record.progress_percent = 0
            db.commit()

@celery_app.task(bind=True, max_retries=1)
def analyze_session(self, session_id: str):
    from app.services.nlp_service import get_llm_client, summarize_speaker, extract_topics
    
    with SyncSession(sync_engine) as db:
        session_record = db.query(Session).filter(Session.id == session_id).first()
        if not session_record:
            return
            
        try:
            session_record.status = "analyzing"
            db.commit()

            # 6-A: Load segments
            segments = db.query(Segment).filter(Segment.session_id == session_id).order_by(Segment.start_time).all()
            
            speaker_texts = {}
            full_text_parts = []
            for seg in segments:
                text = seg.text.strip()
                if not text:
                    continue
                full_text_parts.append(text)
                
                spk = seg.speaker_label
                if spk not in speaker_texts:
                    speaker_texts[spk] = []
                speaker_texts[spk].append(text)
                
            full_text = " ".join(full_text_parts)
            
            # 6-B: Summarize per speaker
            llm_client = get_llm_client()
            speakers = db.query(Speaker).filter(Speaker.session_id == session_id).all()
            for spk in speakers:
                text_to_summarize = " ".join(speaker_texts.get(spk.speaker_label, []))
                if text_to_summarize:
                    summary = summarize_speaker(text_to_summarize, llm_client)
                else:
                    summary = "No speech detected."
                spk.summary = summary
            
            db.commit()
            
            # 6-C: Extract topics
            topics = extract_topics(full_text)
            
            # 6-D: Enqueue graph task
            build_graph.delay(session_id, topics)
            
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            session_record.status = "failed"
            db.commit()

@celery_app.task(bind=True, max_retries=1)
def build_graph(self, session_id: str, topics: list):
    from app.services.graph_service import (
        load_prompt_version, call_graph_llm, detect_topic_shifts,
        evaluate_graph, save_graph_to_db, explain_graph
    )
    from app.services.nlp_service import get_llm_client
    import json
    
    with SyncSession(sync_engine) as db:
        session_record = db.query(Session).filter(Session.id == session_id).first()
        if not session_record:
            return
            
        try:
            speakers = db.query(Speaker).filter(Speaker.session_id == session_id).all()
            speakers_json = json.dumps([{"id": s.speaker_label, "name": s.display_name, "summary": s.summary} for s in speakers])
            
            prompt_template = load_prompt_version(settings.PROMPT_VERSION)
            prompt = prompt_template.format(
                max_nodes=settings.MAX_NODES_IN_GRAPH,
                speakers_json=speakers_json,
                topics_list=json.dumps(topics)
            )
            
            llm_client = get_llm_client()
            
            # 7-B: Call LLM
            graph_json = call_graph_llm(prompt, llm_client)
            
            # 7-D: Detect shifts
            segments = db.query(Segment).filter(Segment.session_id == session_id).all()
            segments_data = [{"text": s.text, "start": s.start_time, "speaker_label": s.speaker_label} 
                             for s in segments]
            shifts = detect_topic_shifts(graph_json, segments_data)
            
            # 7-E: Evaluate
            eval_score = evaluate_graph(graph_json, llm_client)
            
            # 7-G: Explain
            analysis = explain_graph(graph_json, llm_client)
            
            # 7-F: Save
            save_graph_to_db(
                session_id, 
                graph_json, 
                shifts, 
                eval_score, 
                analysis["explanation"], 
                analysis["conclusion"], 
                db
            )
            
            session_record.status = "complete"
            session_record.progress_percent = 100
            db.commit()
            
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            session_record.status = "failed"
            db.commit()
