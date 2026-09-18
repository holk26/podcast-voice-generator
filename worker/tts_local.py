"""TTS local en el worker para voces clonadas.

El backend remoto NO ejecuta modelos pesados ni almacena muestras de voz.
El worker carga Higgs o Qwen3 en la GPU local y genera el audio a partir de
las muestras que viven en voices/clones/.
"""

import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
    if not paths:
        raise ValueError("No audio parts to concatenate")
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
    sf.write(
        str(output_path),
        np.concatenate(samples),
        rate or 24000,
        format="WAV",
        subtype="PCM_16",
    )
    return output_path


def release_engine(engine_name: str | None = None) -> None:
    """Libera un motor TTS (o todos) de la GPU.

    Los motores quedan residentes como singletones para reutilizarlos, pero
    pasos posteriores de postproducción (p. ej. VoiceFixer) necesitan VRAM;
    descargar el motor libera esa memoria. El motor se recarga bajo demanda
    en la siguiente síntesis.
    """
    import gc

    names = [engine_name.lower()] if engine_name else list(_engines)
    for name in names:
        engine = _engines.pop(name, None)
        if engine is None:
            continue
        unload = getattr(engine, "unload", None)
        if callable(unload):
            try:
                unload()
            except Exception as e:
                logger.warning(f"[TTS] No se pudo descargar el motor '{name}': {e}")
    try:
        import torch

        torch.cuda.empty_cache()
    except Exception:
        pass
    gc.collect()


def validator_prev_pitch(validator) -> float:
    """Pitch de referencia vigente del validador (chunk anterior o referencia)."""
    prev = getattr(validator, "_prev", None)
    if prev is not None and prev.pitch_median > 0:
        return prev.pitch_median
    return getattr(validator, "_ref_pitch", 0.0) or 0.0


def synthesize_clone(text: str, voice_id: str, output_path: str) -> str:
    """Genera audio para una voz clonada usando el motor local, troceando textos largos."""
    voice = _parse_clone_voice_id(voice_id)
    engine = _get_engine(voice.engine)

    # Saneado de tokens <|...|>: higgs recibe normalizados (bare -> emotion:x)
    # y filtrados a los que soporta; el resto de motores pierden todos los
    # tokens (los pronunciarían literalmente).
    from core.emotion_tags import normalize_emotion_tags, sanitize_emotion_tags

    clean_text = text.strip()
    if voice.engine == "higgs":
        clean_text = sanitize_emotion_tags(normalize_emotion_tags(clean_text), "higgs")
    else:
        clean_text = sanitize_emotion_tags(clean_text, voice.engine)
    chunks = _split_text(clean_text)
    total_chunks = len(chunks)

    logger.info(
        f"[TTS] Iniciando síntesis para '{voice.name}' (motor: {voice.engine}) -> {total_chunks} fragmentos"
    )

    if total_chunks <= 1:
        logger.info("[TTS] Sintetizando texto único en 1 sola pasada...")
        start_t = time.time()
        res = engine.synthesize(clean_text, voice, output_path)
        logger.info(f"[TTS] Síntesis completada en {time.time() - start_t:.1f}s")
        return res

    out_p = Path(output_path)
    tmp_dir = out_p.parent / f"_chunks_{out_p.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    validator = None
    if os.getenv("TTS_QUALITY_ENABLED", "1").lower() in ("1", "true", "yes"):
        from worker.tts_quality import ChunkValidator

        try:
            validator = ChunkValidator(voice.reference_path)
            logger.info(
                "[TTS] Validación de consistencia activada "
                f"(umbral sim={validator.config.sim_threshold}, "
                f"máx intentos={validator.config.max_attempts})"
            )
        except Exception as e:
            logger.warning(
                f"[TTS] No se pudo iniciar el validador ({e}); "
                "continuando sin validación"
            )

    part_paths: list[Path] = []
    total_start = time.time()
    try:
        for i, chunk in enumerate(chunks):
            pct = int(((i + 1) / total_chunks) * 100)
            preview = chunk[:40].replace("\n", " ")
            logger.info(
                f"[TTS] [{pct}%] Fragmento {i + 1}/{total_chunks} sintetizando: '{preview}...'"
            )
            part_start = time.time()
            part = tmp_dir / f"chunk_{i:04d}.wav"
            max_attempts = validator.config.max_attempts if validator else 1
            best: tuple | None = None
            for attempt in range(1, max_attempts + 1):
                engine.synthesize(chunk, voice, str(part))
                if validator is None:
                    best = (part, None)
                    break
                try:
                    score = validator.validate(str(part), chunk)
                except Exception as e:
                    logger.warning(
                        f"[TTS] Validador falló en chunk {i + 1} ({e}); "
                        "se acepta el chunk (fail-open)"
                    )
                    best = (part, None)
                    break
                pitch_ref = validator_prev_pitch(validator)
                delta_pitch = ""
                if pitch_ref > 0 and score.pitch_median > 0:
                    rel = (score.pitch_median - pitch_ref) / pitch_ref
                    delta_pitch = f" Δpitch={rel:+.0%}"
                logger.info(
                    f"[TTS] chunk {i + 1}/{total_chunks} intento {attempt}: "
                    f"sim={score.similarity:.2f} speed={score.speed_wps:.1f} pal/seg"
                    f"{delta_pitch} {'✓' if score.passed else '✗'}"
                )
                if best is None or (score.passed, score.similarity) > (
                    best[1].passed, best[1].similarity
                ):
                    best_part = tmp_dir / f"chunk_{i:04d}_best.wav"
                    shutil.copy2(part, best_part)
                    best = (best_part, score)
                if score.passed:
                    break

            best_part, best_score = best
            if validator is not None and best_score is not None:
                if not best_score.passed:
                    logger.warning(
                        f"[TTS] chunk {i + 1}/{total_chunks}: mejor intento "
                        f"sim={best_score.similarity:.2f} < umbral; "
                        "se acepta igual (best-of-N)"
                    )
                from worker.tts_quality import extract_emotion

                validator.accept(best_score, extract_emotion(chunk))
                shutil.copy2(best_part, part)
                best_part.unlink(missing_ok=True)
            part_paths.append(part)
            logger.info(
                f"[TTS] Fragmento {i + 1}/{total_chunks} generado en {time.time() - part_start:.1f}s"
            )

        if validator is not None:
            logger.info(f"[TTS] Resumen consistencia: {validator.summary()}")
        logger.info(f"[TTS] Concatenando {total_chunks} fragmentos de audio...")
        _concat_wavs(part_paths, out_p)
        logger.info(
            f"[TTS] Síntesis de voz clonada completada con éxito en {time.time() - total_start:.1f}s -> {out_p.name}"
        )
        return str(out_p)
    finally:
        for p in part_paths:
            p.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except Exception:
            pass



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
