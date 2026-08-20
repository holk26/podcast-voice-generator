import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from typing import List, Optional

import soundfile as sf

from backend.app.config import BASE_DIR
from backend.app.dependencies import get_current_user
from backend.app.models import User

router = APIRouter()

CLONES_DIR = BASE_DIR / "voices" / "clones"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus"}

# Motores disponibles para voces clonadas. Cada wav se expone dos veces,
# una por motor, para que el usuario elija en el dropdown de la UI.
CLONE_ENGINES = ("higgs", "qwen3")


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
        try:
            info = sf.info(entry)
            if info.samplerate != 24000 or info.channels != 1:
                print(
                    f"[voices] WARNING {entry.name}: expected 24000 Hz mono, "
                    f"got {info.samplerate} Hz {info.channels}ch"
                )
        except Exception as e:
            print(f"[voices] WARNING could not inspect {entry.name}: {e}")
        stem = entry.stem
        for engine in CLONE_ENGINES:
            suffix = "" if engine == "higgs" else f":{engine}"
            cloned.append(
                VoiceResponse(
                    id=f"clone:{stem}{suffix}",
                    name=f"{stem} ({engine})",
                    engine=engine,
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


@router.post("/upload", response_model=VoiceResponse)
def upload_cloned_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Sube una muestra de voz clonada al directorio voices/clones.

    El archivo debe ser de audio mono a 24000 Hz para los motores de clonación.
    """
    CLONES_DIR.mkdir(parents=True, exist_ok=True)

    filename = audio.filename or "voice.wav"
    suffix = Path(filename).suffix.lower()
    if suffix not in AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {suffix}. Use one of {AUDIO_EXTENSIONS}",
        )

    dest_path = CLONES_DIR / filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    stem = dest_path.stem
    return VoiceResponse(
        id=f"clone:{stem}",
        name=stem,
        engine="higgs",
        language="es",
        gender="unknown",
        type="cloned",
        reference_path=str(dest_path),
    )


@router.get("/{voice_id}", response_model=VoiceResponse)
def get_voice(voice_id: str):
    for voice in DEFAULT_VOICES + _scan_cloned_voices():
        if voice.id == voice_id:
            return voice
    raise HTTPException(status_code=404, detail="Voice not found")
