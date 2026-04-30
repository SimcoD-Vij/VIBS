from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.db_models import Session, Segment, Speaker, GraphData, TopicShift

router = APIRouter()

@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "status": session.status,
        "progress_percent": session.progress_percent,
        "speaker_count": session.speaker_count,
        "duration_seconds": session.duration_seconds
    }

@router.get("/session/{session_id}/result")
async def get_session_result(session_id: str, db: AsyncSession = Depends(get_db)):
    import json
    
    # Check session
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.status != "complete":
        return {"status": "processing"}, 202
        
    # Fetch speakers
    speakers_result = await db.execute(select(Speaker).where(Speaker.session_id == session_id))
    speakers = [
        {
            "id": s.id,
            "speaker_label": s.speaker_label,
            "display_name": s.display_name,
            "summary": s.summary,
            "total_seconds": s.total_seconds,
            "talk_share": s.talk_share,
            "color": s.color
        } for s in speakers_result.scalars().all()
    ]
    
    # Fetch segments
    segments_result = await db.execute(select(Segment).where(Segment.session_id == session_id).order_by(Segment.start_time))
    segments = [
        {
            "id": s.id,
            "speaker_label": s.speaker_label,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "text": s.text,
            "is_overlap": s.is_overlap
        } for s in segments_result.scalars().all()
    ]
    
    # Fetch graph
    graph_result = await db.execute(select(GraphData).where(GraphData.session_id == session_id))
    graph_data = graph_result.scalar_one_or_none()
    graph = {"nodes": [], "edges": []}
    if graph_data:
        graph = {
            "nodes": json.loads(graph_data.nodes_json),
            "edges": json.loads(graph_data.edges_json),
            "explanation": graph_data.explanation,
            "conclusion": graph_data.conclusion
        }
        
    # Fetch topic shifts
    shifts_result = await db.execute(select(TopicShift).where(TopicShift.session_id == session_id).order_by(TopicShift.time_seconds))
    topic_shifts = [
        {
            "time_seconds": s.time_seconds,
            "from_topic": s.from_topic,
            "to_topic": s.to_topic,
            "speaker_label": s.speaker_label
        } for s in shifts_result.scalars().all()
    ]
    
    return {
        "session": {
            "id": session.id,
            "duration_seconds": session.duration_seconds,
            "speaker_count": session.speaker_count,
            "created_at": session.created_at.isoformat()
        },
        "speakers": speakers,
        "segments": segments,
        "graph": graph,
        "topic_shifts": topic_shifts
    }

@router.patch("/session/{session_id}/speaker/{speaker_label}")
async def rename_speaker(session_id: str, speaker_label: str, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Speaker).where(Speaker.session_id == session_id, Speaker.speaker_label == speaker_label))
    speaker = result.scalar_one_or_none()
    if not speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
        
    speaker.display_name = data.get("display_name", speaker.display_name)
    await db.commit()
    return {"status": "ok"}
