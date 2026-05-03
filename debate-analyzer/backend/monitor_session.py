import sys
import os
import time

# Add the backend dir to path so we can import app
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.workers.tasks import process_audio, analyze_session, build_graph
from app.services.nlp_service import extract_topics
from app.models.db_models import Segment, Session

session_id = "27a663b8-9a44-44ab-8f5c-2ed405da3f27"
wav_path = "/audio_files/27a663b8-9a44-44ab-8f5c-2ed405da3f27.m4a"

def monitor():
    print(f"Starting manual processing for {session_id}...")
    
    # 1. Process Audio
    print("Step 1: process_audio (Transcription & Diarization)...")
    try:
        process_audio(session_id, wav_path)
        print("process_audio finished.")
    except Exception as e:
        print(f"Error in process_audio: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Analyze Session
    print("Step 2: analyze_session (Summarization)...")
    try:
        analyze_session(session_id)
        print("analyze_session finished.")
    except Exception as e:
        print(f"Error in analyze_session: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Build Graph
    print("Step 3: build_graph (Graph Generation & Explanation)...")
    try:
        from app.config import settings
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        sync_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url)
        SyncSessionLocal = sessionmaker(bind=engine)
        
        db = SyncSessionLocal()
        segments = db.query(Segment).filter(Segment.session_id == session_id).all()
        full_text = " ".join([s.text for s in segments])
        topics = extract_topics(full_text)
        db.close()
        
        print(f"Topics: {topics}")
        build_graph(session_id, topics)
        print("build_graph finished.")
    except Exception as e:
        print(f"Error in build_graph: {e}")
        import traceback
        traceback.print_exc()
        return

    print("ALL STEPS COMPLETE SUCCESSFULLY.")

if __name__ == "__main__":
    monitor()
