from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EpisodeCreate(BaseModel):
    title: str
    type: str = "podcast"
    source_text: Optional[str] = None
    voice_id: str
    target_duration_minutes: Optional[float] = None


class EpisodeResponse(BaseModel):
    id: int
    title: str
    type: str
    source_text: Optional[str] = None
    voice_id: str
    status: str
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    target_duration_minutes: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PreviewRequest(BaseModel):
    text: str
    voice_id: str


class PreviewResponse(BaseModel):
    audio_url: str
