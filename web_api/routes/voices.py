from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()


class VoiceResponse(BaseModel):
    id: str
    name: str
    engine: str
    language: str
    gender: str


DEFAULT_VOICES: List[VoiceResponse] = [
    VoiceResponse(id="jorge", name="Jorge", engine="edge", language="es", gender="male"),
    VoiceResponse(id="dalia", name="Dalia", engine="edge", language="es", gender="female"),
    VoiceResponse(id="elvira", name="Elvira", engine="edge", language="es", gender="female"),
]


@router.get("", response_model=List[VoiceResponse])
def list_voices():
    return DEFAULT_VOICES


@router.get("/{voice_id}", response_model=VoiceResponse)
def get_voice(voice_id: str):
    for voice in DEFAULT_VOICES:
        if voice.id == voice_id:
            return voice
    raise HTTPException(status_code=404, detail="Voice not found")
