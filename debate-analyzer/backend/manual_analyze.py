from app.workers.tasks import analyze_session, build_graph
from app.services.nlp_service import extract_topics
from app.models.db_models import Segment
from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

# Convert asyncpg URL to psycopg2 for sync usage
sync_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(sync_url)
SessionLocal = sessionmaker(bind=engine)

session_id = "1122c12a-14a9-44f9-91b6-b085d831a0ec"
print(f"Manually triggering analyze_session for {session_id}...")
analyze_session(session_id)

print("Analysis complete! Extracting topics for build_graph...")
db = SessionLocal()
segments = db.query(Segment).filter(Segment.session_id == session_id).all()
full_text = " ".join([s.text for s in segments])
topics = extract_topics(full_text)
db.close()

print(f"Topics found: {topics}")
print("Now triggering build_graph...")
build_graph(session_id, topics)
print("Manual build_graph complete!")
