from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.database import Base

class SessionStatus(str, enum.Enum):
    pending = "pending"
    transcribing = "transcribing"
    analyzing = "analyzing"
    complete = "complete"
    failed = "failed"

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(SessionStatus), default=SessionStatus.pending)
    progress_percent = Column(Integer, default=0)
    wav_path = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    speaker_count = Column(Integer, default=0)

    segments = relationship("Segment", back_populates="session")
    speakers = relationship("Speaker", back_populates="session")
    graph_data = relationship("GraphData", back_populates="session", uselist=False)
    topic_shifts = relationship("TopicShift", back_populates="session")

class Segment(Base):
    __tablename__ = "segments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"))
    speaker_label = Column(String)
    start_time = Column(Float)
    end_time = Column(Float)
    text = Column(Text)
    is_overlap = Column(Boolean, default=False)

    session = relationship("Session", back_populates="segments")

class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"))
    speaker_label = Column(String)
    display_name = Column(String)
    summary = Column(Text, nullable=True)
    total_seconds = Column(Float, default=0.0)
    talk_share = Column(Float, default=0.0)
    color = Column(String)

    session = relationship("Session", back_populates="speakers")

class GraphData(Base):
    __tablename__ = "graph_data"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), unique=True)
    nodes_json = Column(Text)
    edges_json = Column(Text)
    prompt_version = Column(String)
    explanation = Column(Text, nullable=True)
    conclusion = Column(Text, nullable=True)
    eval_score = Column(Float, nullable=True)

    session = relationship("Session", back_populates="graph_data")

class TopicShift(Base):
    __tablename__ = "topic_shifts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"))
    time_seconds = Column(Float)
    from_topic = Column(String)
    to_topic = Column(String)
    speaker_label = Column(String)

    session = relationship("Session", back_populates="topic_shifts")
