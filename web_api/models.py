from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from web_api.database import Base


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
