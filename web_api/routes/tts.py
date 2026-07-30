import os
import re
import uuid
import edge_tts
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from web_api.schemas import PreviewRequest, PreviewResponse
from web_api.config import PREVIEW_DIR
from web_api.routes.voices import list_voices, VoiceResponse
from web_api.services.job_service import registry
from core.emotion_tags import sanitize_emotion_tags

router = APIRouter()

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}

DEFAULT_VOICE = "es-ES-AlvaroNeural"

_higgs_engine = None
_qwen_engine = None


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


def _get_qwen_engine():
    """Motor Qwen3-TTS-12Hz-1.7B-Base (lazy singleton).
    Clonación de voz por referencia de 3 s. Ver docs/QWEN3_TTS_SETUP.md."""
    global _qwen_engine
    if _qwen_engine is None:
        from core.qwen_tts_engine import Qwen3TTSEngine, DEFAULT_MODEL
        model_name = os.getenv("QWEN3_TTS_MODEL", DEFAULT_MODEL)
        device = os.getenv("QWEN3_TTS_DEVICE", "cuda")
        dtype = os.getenv("QWEN3_TTS_DTYPE") or None
        _qwen_engine = Qwen3TTSEngine(
            model_name=model_name, device=device, dtype=dtype
        )
    return _qwen_engine


def _get_clone_engine(voice: VoiceResponse):
    """Devuelve el singleton del motor correspondiente al campo `engine`."""
    if voice.engine == "qwen3":
        return _get_qwen_engine()
    return _get_higgs_engine()


def _find_voice(voice_id: str) -> VoiceResponse | None:
    for v in list_voices():
        if v.id == voice_id:
            return v
    return None


def _synthesize_clone(text: str, voice: VoiceResponse, output_path: Path) -> Path:
    """Sintetiza texto con voz clonada vía el motor correspondiente
    al campo `engine` de la voz (higgs | qwen3)."""
    import traceback as tb_mod
    from core.project import Voice as CoreVoice

    core_voice = CoreVoice(
        id=voice.id,
        name=voice.name,
        type="cloned",
        engine=voice.engine,
        language=voice.language,
        reference_path=voice.reference_path,
    )
    engine = _get_clone_engine(voice)
    try:
        engine.synthesize(text, core_voice, str(output_path))
    except Exception:
        tb = tb_mod.format_exc()
        print(f"[tts] ERROR en síntesis {voice.engine} para '{voice.name}':\n{tb}", flush=True)
        raise
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
    Emite un job "tts" con el progreso por partes (visible en /api/jobs).
    """
    voice = _find_voice(request.voice_id)
    if voice is None or voice.type != "cloned" or not voice.reference_path:
        raise HTTPException(status_code=400, detail="Solo voces clonadas (clone:*)")
    engine_kind = voice.engine if voice.engine in ("higgs", "qwen3") else "higgs"
    clean_text = sanitize_emotion_tags(request.text, engine_kind)

    job = uuid.uuid4().hex
    job_id = registry.create("tts", detail=request.label or f"Síntesis con {voice.name}")
    try:
        chunks = _split_text(clean_text)
        registry.emit(job_id, "start", f"Motor {voice.engine}: {len(chunks)} partes a sintetizar")
        part_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            registry.emit(job_id, "synth", f"Sintetizando parte {i + 1}/{len(chunks)}…")
            part = PREVIEW_DIR / f"{job}_{i:03d}.wav"
            await run_in_threadpool(_synthesize_clone, chunk, voice, part)
            part_paths.append(part)
        registry.emit(job_id, "concat", "Uniendo el audio final…")
        final = PREVIEW_DIR / f"{job}_full.wav"
        if len(part_paths) == 1:
            part_paths[0].rename(final)
        else:
            await run_in_threadpool(_concat_wavs, part_paths, final)
            for p in part_paths:
                p.unlink(missing_ok=True)
        registry.emit(job_id, "done", "Audio listo")
        registry.finish(job_id, {"audio_url": f"/outputs/previews/{final.name}"})
        return PreviewResponse(audio_url=f"/outputs/previews/{final.name}")
    except Exception as e:
        registry.fail(job_id, str(e))
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Synthesize failed: {e}\n{tb}")


@router.post("/preview", response_model=PreviewResponse)
async def preview(request: PreviewRequest):
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = PREVIEW_DIR / filename
    voice = _find_voice(request.voice_id)

    if voice is not None and voice.type == "cloned" and voice.reference_path:
        try:
            wav_path = output_path.with_suffix(".wav")
            text = sanitize_emotion_tags(
                request.text,
                voice.engine if voice.engine in ("higgs", "qwen3") else "higgs"
            )
            # La síntesis es bloqueante (~1-4 s tras la carga inicial del motor)
            await run_in_threadpool(_synthesize_clone, text, voice, wav_path)
            return PreviewResponse(audio_url=f"/outputs/previews/{wav_path.name}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            raise HTTPException(status_code=500, detail=f"Preview failed ({voice.engine}): {e}\n{tb}")

    edge_voice = VOICE_MAP.get(request.voice_id, DEFAULT_VOICE)
    communicate = edge_tts.Communicate(sanitize_emotion_tags(request.text, "edge"), voice=edge_voice)
    await communicate.save(str(output_path))
    return PreviewResponse(audio_url=f"/outputs/previews/{filename}")
