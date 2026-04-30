from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import os
import shutil
import uuid
from app.database import get_db
from app.models.db_models import Session, SessionStatus
from app.workers.tasks import process_audio
from app.config import settings

router = APIRouter()

@router.post("/upload")
async def upload_audio(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    # 1. Validate file extension
    if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.flac', '.ogg')):
        raise HTTPException(status_code=400, detail="Invalid file format. Supported: .wav, .mp3, .m4a, .flac, .ogg")

    # 2. Generate unique session ID and filename
    session_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{session_id}{ext}"
    
    # 3. Ensure audio directory exists
    audio_dir = str(settings.AUDIO_DIR)
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir, exist_ok=True)
        
    file_path = os.path.join(audio_dir, filename)

    # 4. Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 5. Create session in database
    new_session = Session(
        id=session_id,
        status=SessionStatus.pending,
        wav_path=file_path,
        progress_percent=0
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    # 6. Trigger background task
    # The worker container also has /audio_files mounted at the same path
    process_audio.delay(session_id, file_path)

    return {
        "session_id": session_id,
        "filename": filename,
        "status": "pending",
        "message": "File uploaded successfully. Processing started."
    }
