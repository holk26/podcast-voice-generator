from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False, default="podcast")
    source_text = Column(Text, nullable=True)
    voice_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    audio_url = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    target_duration_minutes = Column(Float, nullable=True)
    published_at = Column(DateTime, nullable=True)  # marca manual de publicación


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    niche = Column(String, nullable=True)
    format = Column(String, nullable=False, default="podcast")
    default_voice_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    brief = Column(Text, nullable=True)  # brief de producción generado por IA
    autopilot = Column(Boolean, default=False, nullable=False)
    episodes_per_week = Column(Integer, default=2, nullable=False)
    target_minutes = Column(Integer, default=10, nullable=False)
    num_speakers = Column(Integer, default=1, nullable=False)  # 1 = monólogo, 2 = diálogo
    speaker_voices = Column(JSON, nullable=True)  # {"SpeakerName": "voice_id"}
    published_at = Column(DateTime, nullable=True)  # marca manual de publicación
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    entries = relationship("ContentPlanEntry", back_populates="channel", cascade="all, delete-orphan")


class ContentPlanEntry(Base):
    __tablename__ = "content_plan_entries"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    scheduled_date = Column(DateTime, nullable=True)
    season = Column(Integer, default=1, nullable=False)
    status = Column(String, nullable=False, default="draft")
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    channel = relationship("Channel", back_populates="entries")
    episode = relationship("Episode")


class DiagnosticLog(Base):
    __tablename__ = "diagnostic_logs"

    id = Column(Integer, primary_key=True, index=True)
    component = Column(String, nullable=False)
    status = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
