import re
import uuid
import edge_tts
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from web_api.schemas import PreviewRequest, PreviewResponse
from web_api.config import PREVIEW_DIR
from web_api.routes.voices import list_voices, VoiceResponse

router = APIRouter()

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}

DEFAULT_VOICE = "es-ES-AlvaroNeural"

_higgs_engine = None


def _get_higgs_engine():
    """Motor Higgs v3 (lazy singleton). Las voces clonadas se sintetizan con
    Higgs, no con XTTS (calidad metálica). Config ajustada a 8GB VRAM;
    ver docs/HIGGS_SETUP.md."""
    global _higgs_engine
    if _higgs_engine is None:
        from core.higgs_engine import HiggsAudioEngine
        from web_api.config import BASE_DIR
        _higgs_engine = HiggsAudioEngine(
            model_name=str(BASE_DIR / "models" / "higgs-audio-v3-tts-4b")
        )
    return _higgs_engine


def _find_voice(voice_id: str) -> VoiceResponse | None:
    for v in list_voices():
        if v.id == voice_id:
            return v
    return None


def _synthesize_clone(text: str, voice: VoiceResponse, output_path: Path) -> Path:
    """Sintetiza texto con voz clonada vía Higgs (bloqueante)."""
    from core.project import Voice as CoreVoice
    core_voice = CoreVoice(
        id=voice.id,
        name=voice.name,
        type="cloned",
        engine="higgs",
        language=voice.language,
        reference_path=voice.reference_path,
    )
    engine = _get_higgs_engine()
    engine.synthesize(text, core_voice, str(output_path))
    return output_path


def _split_text(text: str, max_chars: int = 400) -> list[str]:
    """Divide en frases y las agrupa en chunks cortos (el motor tiene
    max_model_len limitado; textos largos deben trocearse)."""
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?…])\s+|[\r\n]+", text)
        if s.strip()
    ]
    chunks: list[str] = []
    current = ""
    for s in sentences:
        if current and len(current) + len(s) + 1 > max_chars:
            chunks.append(current)
            current = s
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks or [text]


def _concat_wavs(paths: list[Path], output_path: Path) -> Path:
    import numpy as np
    import soundfile as sf
    samples = []
    rate = None
    for p in paths:
        data, sr = sf.read(str(p), always_2d=False)
        if data.ndim == 2:
            data = data.mean(axis=1)
        rate = sr
        samples.append(data.astype(np.float32))
    sf.write(str(output_path), np.concatenate(samples), rate or 24000,
             format="WAV", subtype="PCM_16")
    return output_path


@router.post("/synthesize", response_model=PreviewResponse)
async def synthesize(request: PreviewRequest):
    """Síntesis de texto largo con voz clonada (para episodios del worker).

    Trocea el texto, sintetiza cada chunk con Higgs y concatena el resultado.
    """
    voice = _find_voice(request.voice_id)
    if voice is None or voice.type != "cloned" or not voice.reference_path:
        raise HTTPException(status_code=400, detail="Solo voces clonadas (clone:*)")

    job = uuid.uuid4().hex
    try:
        chunks = _split_text(request.text)
        part_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            part = PREVIEW_DIR / f"{job}_{i:03d}.wav"
            await run_in_threadpool(_synthesize_clone, chunk, voice, part)
            part_paths.append(part)
        final = PREVIEW_DIR / f"{job}_full.wav"
        if len(part_paths) == 1:
            part_paths[0].rename(final)
        else:
            await run_in_threadpool(_concat_wavs, part_paths, final)
            for p in part_paths:
                p.unlink(missing_ok=True)
        return PreviewResponse(audio_url=f"/outputs/previews/{final.name}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Higgs synthesize failed: {e}\n{tb}")


@router.post("/preview", response_model=PreviewResponse)
async def preview(request: PreviewRequest):
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = PREVIEW_DIR / filename
    voice = _find_voice(request.voice_id)

    if voice is not None and voice.type == "cloned" and voice.reference_path:
        try:
            wav_path = output_path.with_suffix(".wav")
            # La síntesis es bloqueante (~1-4 s tras la carga inicial del motor)
            await run_in_threadpool(_synthesize_clone, request.text, voice, wav_path)
            return PreviewResponse(audio_url=f"/outputs/previews/{wav_path.name}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            raise HTTPException(status_code=500, detail=f"Higgs preview failed: {e}\n{tb}")

    edge_voice = VOICE_MAP.get(request.voice_id, DEFAULT_VOICE)
    communicate = edge_tts.Communicate(request.text, voice=edge_voice)
    await communicate.save(str(output_path))
    return PreviewResponse(audio_url=f"/outputs/previews/{filename}")
