from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DiagnosticCheckResult(BaseModel):
    component: str
    status: str  # ok | warning | error
    detail: str
    checked_at: datetime

    class Config:
        from_attributes = True


class DiagnosticsReport(BaseModel):
    checks: list[DiagnosticCheckResult]
    overall: str
    generated_at: datetime


class EpisodeCreate(BaseModel):
    title: str
    type: str = "podcast"
    source_text: Optional[str] = None
    voice_id: str
    target_duration_minutes: Optional[float] = None
    channel_id: Optional[int] = None


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
    channel_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PreviewRequest(BaseModel):
    text: str
    voice_id: str
    label: str | None = None


class PreviewResponse(BaseModel):
    audio_url: str


class ChannelBase(BaseModel):
    name: str
    description: Optional[str] = None
    niche: Optional[str] = None
    format: str = "podcast"
    default_voice_id: str
    is_active: bool = True
    brief: Optional[str] = None
    autopilot: bool = False
    episodes_per_week: int = 2
    target_minutes: int = 10
    num_speakers: int = 1
    speaker_voices: Optional[dict[str, str]] = None


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    niche: Optional[str] = None
    format: Optional[str] = None
    default_voice_id: Optional[str] = None
    is_active: Optional[bool] = None
    brief: Optional[str] = None
    autopilot: Optional[bool] = None
    episodes_per_week: Optional[int] = None
    target_minutes: Optional[int] = None
    num_speakers: Optional[int] = None
    speaker_voices: Optional[dict[str, str]] = None
    published_at: Optional[datetime] = None


class ChannelResponse(ChannelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    entries_total: int = 0
    entries_generated: int = 0

    class Config:
        from_attributes = True


class PlanEntryBase(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_date: Optional[datetime] = None


class PlanEntryCreate(PlanEntryBase):
    pass


class PlanEntryResponse(PlanEntryBase):
    id: int
    channel_id: int
    status: str
    season: int = 1
    episode_id: Optional[int] = None
    audio_url: Optional[str] = None
    episode_published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChannelWithPlanResponse(ChannelResponse):
    entries: List[PlanEntryResponse] = []


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    is_admin: bool


class LoginRequest(BaseModel):
    username: str
    password: str


class WorkerJob(BaseModel):
    episode_id: int
    title: str
    type: str
    source_text: Optional[str] = None
    voice_id: str
    target_duration_minutes: Optional[float] = None


class WorkerJobCompleteRequest(BaseModel):
    audio_url: str


class WorkerJobFailRequest(BaseModel):
    error: str
