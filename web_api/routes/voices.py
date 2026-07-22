import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from web_api.config import BASE_DIR

router = APIRouter()

CLONES_DIR = BASE_DIR / "voices" / "clones"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus"}


class VoiceResponse(BaseModel):
    id: str
    name: str
    engine: str
    language: str
    gender: str
    type: str = "pretrained"
    reference_path: Optional[str] = None


DEFAULT_VOICES: List[VoiceResponse] = [
    VoiceResponse(id="jorge", name="Jorge", engine="edge", language="es", gender="male"),
    VoiceResponse(id="dalia", name="Dalia", engine="edge", language="es", gender="female"),
    VoiceResponse(id="elvira", name="Elvira", engine="edge", language="es", gender="female"),
]


def _scan_cloned_voices() -> List[VoiceResponse]:
    cloned: List[VoiceResponse] = []
    if not CLONES_DIR.is_dir():
        return cloned
    for entry in sorted(CLONES_DIR.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        stem = entry.stem
        cloned.append(
            VoiceResponse(
                id=f"clone:{stem}",
                name=stem,
                engine="higgs",
                language="es",
                gender="unknown",
                type="cloned",
                reference_path=str(entry),
            )
        )
    return cloned


@router.get("", response_model=List[VoiceResponse])
def list_voices():
    return DEFAULT_VOICES + _scan_cloned_voices()


@router.get("/{voice_id}", response_model=VoiceResponse)
def get_voice(voice_id: str):
    for voice in DEFAULT_VOICES + _scan_cloned_voices():
        if voice.id == voice_id:
            return voice
    raise HTTPException(status_code=404, detail="Voice not found")
