from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.db_models import Session, Speaker, Segment, GraphData
import os

router = APIRouter()

@router.get("/session/{session_id}/export/pdf")
async def export_pdf(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        from weasyprint import HTML
        import jinja2
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF export dependencies not installed")

    # Fetch session
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch speakers
    spk_result = await db.execute(select(Speaker).where(Speaker.session_id == session_id))
    speakers = spk_result.scalars().all()
    spk_map = {s.speaker_label: {"display_name": s.display_name, "color": s.color} for s in speakers}

    # Fetch segments
    seg_result = await db.execute(select(Segment).where(Segment.session_id == session_id).order_by(Segment.start_time))
    segments = seg_result.scalars().all()

    # Fetch graph
    graph_result = await db.execute(select(GraphData).where(GraphData.session_id == session_id))
    graph_data = graph_result.scalar_one_or_none()

    template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = env.get_template("pdf_report.html")

    explanation_html = ""
    conclusion_html = ""
    if graph_data:
        import markdown
        explanation_html = markdown.markdown(graph_data.explanation or "")
        conclusion_html = markdown.markdown(graph_data.conclusion or "")

    html_out = template.render(
        session=session,
        speakers=speakers,
        segments=segments,
        spk_map=spk_map,
        explanation_html=explanation_html,
        conclusion_html=conclusion_html
    )

    pdf_bytes = HTML(string=html_out).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="session_{session_id}.pdf"'}
    )
