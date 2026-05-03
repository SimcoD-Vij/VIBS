"""
WebSocket endpoint that:
1. Accepts connection at /ws/session/{session_id}
2. Receives binary audio chunks from browser
3. Appends each chunk to a temporary .webm accumulation buffer
4. On connection close, converts the accumulated audio to 16kHz mono WAV
   using ffmpeg subprocess
5. Enqueues a Celery task to process the WAV file
6. Sends JSON text frames back to browser as acknowledgements

Audio format coming in: audio/webm;codecs=opus (browser MediaRecorder default)
Audio format saved: 16kHz mono WAV (required by WhisperX)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings
from app.workers.tasks import process_audio
from app.services.vad_service import SilenceTracker, score_chunk
from app.database import AsyncSessionLocal
from app.models.db_models import Session
import uuid, json, subprocess, os, aiofiles, io, tempfile
import numpy as np
from pathlib import Path

router = APIRouter()

@router.websocket("/ws/session/{session_id}")
async def audio_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # DB Session to create initial session row
    async with AsyncSessionLocal() as db:
        new_session = Session(id=session_id, status="pending", progress_percent=0)
        db.add(new_session)
        await db.commit()

    # Create AUDIO_DIR if it doesn't exist
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)
    
    webm_path = settings.AUDIO_DIR / f"{session_id}_raw.webm"
    wav_path  = settings.AUDIO_DIR / f"{session_id}.wav"
    chunk_index = 0
    tracker = SilenceTracker()

    try:
        async with aiofiles.open(webm_path, 'wb') as f:
            while True:
                data = await websocket.receive()

                if 'bytes' in data:
                    await f.write(data['bytes'])
                    chunk_index += 1
                    
                    # Decode the webm chunk to raw PCM for VAD scoring
                    try:
                        with tempfile.NamedTemporaryFile(suffix='.webm', delete=True) as tmp_in:
                            tmp_in.write(data['bytes'])
                            tmp_in.flush()
                            # Convert to raw f32le mono 16kHz for silero
                            cmd = [
                                'ffmpeg', '-y', '-i', tmp_in.name,
                                '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'
                            ]
                            proc = subprocess.run(cmd, capture_output=True)
                            if proc.returncode == 0 and len(proc.stdout) >= 512 * 4:
                                score = score_chunk(proc.stdout)
                            else:
                                score = 1.0  # Can't decode, assume speech
                    except Exception:
                        score = 1.0

                    # Approximate duration from raw PCM bytes if successful, else estimate
                    if 'proc' in locals() and proc.returncode == 0:
                        chunk_duration = len(proc.stdout) / (16000 * 4) # f32 is 4 bytes
                    else:
                        chunk_duration = 5.0 # Fallback estimate
                    
                    tracker.update(score, chunk_duration)
                    
                    if tracker.is_silent:
                        await websocket.send_text(json.dumps({"type": "vad_silence"}))
                        break
                    
                    await websocket.send_text(json.dumps({
                        "type": "ack",
                        "chunk_index": chunk_index
                    }))

                elif 'text' in data:
                    msg = json.loads(data['text'])
                    if msg.get('type') == 'stop':
                        break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        return
    finally:
        try:
            await websocket.close()
        except:
            pass

    # Convert webm to 16kHz mono WAV using ffmpeg
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(webm_path),
        "-ar", "16000",     # 16kHz sample rate (required by Whisper)
        "-ac", "1",          # mono channel
        "-c:a", "pcm_s16le", # 16-bit PCM
        str(wav_path)
    ]
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Log ffmpeg error
        print(f"ffmpeg error for session {session_id}: {result.stderr}")
        return

    # Clean up the raw webm
    if os.path.exists(webm_path):
        os.remove(webm_path)

    # Enqueue the Celery processing task (non-blocking)
    process_audio.delay(session_id, str(wav_path))
