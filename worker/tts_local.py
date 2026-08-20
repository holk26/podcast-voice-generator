"""TTS local en el worker para voces clonadas.

El backend remoto NO ejecuta modelos pesados ni almacena muestras de voz.
El worker carga Higgs o Qwen3 en la GPU local y genera el audio a partir de
las muestras que viven en voices/clones/.
"""

import os
import re
from pathlib import Path
from typing import Optional

from core.project import Voice
from shared.config import BASE_DIR

_CLONES_DIR = BASE_DIR / "voices" / "clones"

# Motores lazy-load (singletons por motor)
_engines: dict[str, object] = {}


def _resolve_model_path(model_name: str) -> str:
    """Devuelve la ruta local si existe, o el hub ID para descarga."""
    local_candidates = [
        BASE_DIR / model_name,
        BASE_DIR / "models" / model_name,
        BASE_DIR / "models" / Path(model_name).name,
        BASE_DIR / model_name.replace("/", "_"),
    ]
    for candidate in local_candidates:
        if candidate.is_dir():
            return str(candidate)
    return model_name


def _get_engine(engine_name: str):
    """Obtiene o crea el motor TTS local solicitado."""
    engine_name = engine_name.lower()
    if engine_name in _engines:
        return _engines[engine_name]

    if engine_name == "higgs":
        from core.higgs_engine import HiggsAudioEngine

        model_path = _resolve_model_path("bosonai/higgs-audio-v3-tts-4b")
        engine = HiggsAudioEngine(
            model_name=model_path,
            device=os.getenv("HIGGS_DEVICE", "cuda"),
            quantization=os.getenv("HIGGS_QUANTIZATION", "fp8"),
            max_model_len=int(os.getenv("HIGGS_MAX_MODEL_LEN", "1536")),
            enforce_eager=os.getenv("HIGGS_ENFORCE_EAGER", "false").lower() == "true",
        )
    elif engine_name == "qwen3":
        from core.qwen_tts_engine import Qwen3TTSEngine

        model_path = _resolve_model_path("Qwen/Qwen3-TTS-12Hz-1.7B-Base")
        engine = Qwen3TTSEngine(
            model_name=model_path,
            device=os.getenv("QWEN3_TTS_DEVICE", "cuda"),
            dtype=os.getenv("QWEN3_TTS_DTYPE", "bfloat16"),
            language="es",
        )
    else:
        raise ValueError(f"Unknown local TTS engine: {engine_name}")

    _engines[engine_name] = engine
    return engine


def _parse_clone_voice_id(voice_id: str) -> Voice:
    """Parsea IDs como 'clone:alejandra' o 'clone:alejandra:qwen3'."""
    if not voice_id.startswith("clone:"):
        raise ValueError(f"Not a cloned voice id: {voice_id}")

    parts = voice_id.split(":")
    name = parts[1]
    engine = parts[2] if len(parts) > 2 else "higgs"

    # Buscar archivo de referencia; admite .wav, .mp3, etc.
    ref_path: Optional[Path] = None
    for ext in (".wav", ".mp3", ".m4a", ".flac", ".ogg"):
        candidate = _CLONES_DIR / f"{name}{ext}"
        if candidate.exists():
            ref_path = candidate
            break

    if ref_path is None:
        raise FileNotFoundError(
            f"No reference audio found for voice '{name}' in {_CLONES_DIR}"
        )

    return Voice(
        id=voice_id,
        name=name,
        type="cloned",
        engine=engine,
        language="es",
        reference_path=str(ref_path),
    )


def synthesize_clone(text: str, voice_id: str, output_path: str) -> str:
    """Genera audio para una voz clonada usando el motor local."""
    voice = _parse_clone_voice_id(voice_id)
    engine = _get_engine(voice.engine)
    return engine.synthesize(text, voice, output_path)


def list_local_clones() -> list[dict]:
    """Lista las voces clonadas disponibles localmente en voices/clones/."""
    if not _CLONES_DIR.is_dir():
        return []

    voices = []
    for ext in (".wav", ".mp3", ".m4a", ".flac", ".ogg"):
        for path in sorted(_CLONES_DIR.glob(f"*{ext}")):
            stem = path.stem
            voices.append({
                "id": f"clone:{stem}",
                "name": stem,
                "engine": "higgs",
                "reference_path": str(path),
            })
            voices.append({
                "id": f"clone:{stem}:qwen3",
                "name": f"{stem} (qwen3)",
                "engine": "qwen3",
                "reference_path": str(path),
            })
    return voices
