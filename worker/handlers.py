import asyncio
import edge_tts
import json
import logging
import os
import subprocess
from pathlib import Path

from shared.config import BASE_DIR, OUTPUT_DIR
from shared.schemas import WorkerJob
from worker.tts_local import synthesize_clone

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}
DEFAULT_VOICE = "es-ES-AlvaroNeural"

MUSIC_DIR = BASE_DIR / "sfx_library" / "music"
MUSIC_INTRO = MUSIC_DIR / "intro_jingle.wav"
MUSIC_OUTRO = MUSIC_DIR / "outro_theme.wav"


def _handle_cloned_episode(job: WorkerJob, output_dir: Path) -> Path:
    """Voces clonadas: genera audio localmente con Higgs/Qwen3 en el worker.

    El backend remoto NO ejecuta modelos pesados ni almacena muestras de voz.
    """
    output_path = output_dir / "final.mp3"
    synthesize_clone(job.source_text or "", job.voice_id, str(output_path))
    return output_path


MUSIC_TRACK_MAP = {
    "crime": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "crimen": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "misterio": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "suspenso": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "garavito": "arctsound-mysterious-suspense-background-no-copyright-music-252023.mp3",
    "motivation": "rockot-powerful-emotional-epic-174136.mp3",
    "motivacion": "rockot-powerful-emotional-epic-174136.mp3",
    "mindfulness": "daynigthmorning-aura-273351.mp3",
    "aura": "daynigthmorning-aura-273351.mp3",
    "relax": "daynigthmorning-aura-273351.mp3",
}


def _resolve_background_music(job: WorkerJob | None) -> Path | None:
    if not MUSIC_DIR.is_dir():
        return None

    if job:
        title = (job.title or "").lower()
        job_type = (job.type or "").lower()
        for key, filename in MUSIC_TRACK_MAP.items():
            if key in job_type or key in title:
                cand = MUSIC_DIR / filename
                if cand.exists():
                    return cand

    # Default fallback a la primera pista mp3 disponible en sfx_library/music
    for candidate in sorted(MUSIC_DIR.glob("*.mp3")):
        if candidate.name not in ("intro_jingle.wav", "outro_theme.wav"):
            return candidate
    return None


def _add_branding_music(path: Path, job: WorkerJob | None = None) -> None:
    """Mezcla la música de fondo del canal y jingles de intro/outro."""
    bg_path = _resolve_background_music(job)
    has_intro_outro = MUSIC_INTRO.exists() or MUSIC_OUTRO.exists()

    if not bg_path and not has_intro_outro:
        return

    from pydub import AudioSegment

    main = AudioSegment.from_file(path)

    # 1. Mezclar música de fondo del canal (gain -18 dB para mantener la voz clara)
    if bg_path and bg_path.exists():
        logger.info(f"[Audio] Aplicando música de fondo del canal: {bg_path.name}")
        bg = AudioSegment.from_file(bg_path).apply_gain(-18)
        if len(bg) < len(main):
            loops = (len(main) // len(bg)) + 1
            bg = bg * loops
        bg = bg[:len(main)].fade_in(2000).fade_out(3000)
        main = main.overlay(bg)

    # 2. Añadir intro y outro jingles si existen
    parts: list[AudioSegment] = []
    if MUSIC_INTRO.exists():
        intro = AudioSegment.from_file(MUSIC_INTRO).apply_gain(-5)
        parts.append(intro.fade_out(1500))
    parts.append(main)
    if MUSIC_OUTRO.exists():
        outro = AudioSegment.from_file(MUSIC_OUTRO).apply_gain(-5)
        parts.append(outro.fade_in(2000))

    mixed = parts[0]
    for part in parts[1:]:
        mixed = mixed.append(part, crossfade=300)

    fmt = "mp3" if path.suffix.lower() == ".mp3" else "wav"
    mixed.export(path, format=fmt)


def _normalize_loudness(path: Path, target_i: float = -16.0) -> None:
    """Volumen uniforme de principio a fin: loudnorm a dos pasadas
    (mide y aplica una ganancia constante; -16 LUFS = estándar podcast)."""
    measure = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path),
         "-af", f"loudnorm=I={target_i}:TP=-1.5:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=300,
    )
    try:
        tail = measure.stderr[measure.stderr.rfind("{"):]
        stats = json.loads(tail)
        loudness = (
            f"loudnorm=I={target_i}:TP=-1.5:LRA=11:"
            f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
            f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
            "linear=true"
        )
    except (json.JSONDecodeError, KeyError):
        loudness = f"loudnorm=I={target_i}:TP=-1.5:LRA=11"

    tmp = path.with_suffix(".norm" + path.suffix)
    fmt_args = ["-codec:a", "libmp3lame", "-b:a", "192k"] if path.suffix.lower() == ".mp3" else []
    result = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(path), "-af", loudness, "-ar", "48000", *fmt_args, str(tmp)],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode == 0 and tmp.exists():
        tmp.replace(path)


USE_VOICEFIXER = os.getenv("USE_VOICEFIXER", "1").lower() in ("1", "true", "yes")


def _apply_voicefixer_enhancer(path: Path) -> None:
    """Restaura y mejora la calidad de la voz sintética con VoiceFixer AI."""
    if not USE_VOICEFIXER:
        return
    try:
        logger.info("[Audio] Aplicando mejorador de voz neural VoiceFixer...")
        from audio.audio_enhancer import VoiceFixerEnhancer
        enhancer = VoiceFixerEnhancer(cuda=True, mode=0)
        tmp_out = path.with_suffix(".enhanced" + path.suffix)
        success = enhancer.enhance(str(path), str(tmp_out))
        if success and tmp_out.exists():
            tmp_out.replace(path)
            logger.info("[Audio] Restauración VoiceFixer completada con éxito.")
        enhancer.close()
    except Exception as e:
        logger.warning(f"[Audio] No se pudo aplicar VoiceFixer: {e}")


def postprocess_episode_audio(path: Path, job: WorkerJob | None = None) -> None:
    """Cadena de postproducción del episodio: VoiceFixer + música + volumen uniforme."""
    logger.info("[Audio] Iniciando postproducción de audio (VoiceFixer + música + normalización LUFS)...")
    _apply_voicefixer_enhancer(path)
    try:
        _add_branding_music(path, job)
    except Exception as e:
        logger.warning(f"[Audio] No se pudo aplicar música de fondo: {e}")
    try:
        logger.info("[Audio] Normalizando volumen con ffmpeg loudnorm (-16 LUFS)...")
        _normalize_loudness(path)
        logger.info("[Audio] Normalización de volumen completada con éxito.")
    except Exception as e:
        logger.warning(f"[Audio] No se pudo normalizar volumen: {e}")


def handle_podcast_episode(job: WorkerJob) -> Path:
    output_dir = OUTPUT_DIR / str(job.episode_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    if (job.voice_id or "").startswith("clone:"):
        output_path = _handle_cloned_episode(job, output_dir)
    else:
        output_path = output_dir / "final.mp3"
        voice = VOICE_MAP.get(job.voice_id, DEFAULT_VOICE)

        async def _run():
            from core.emotion_tags import sanitize_emotion_tags
            communicate = edge_tts.Communicate(
                sanitize_emotion_tags(job.source_text or "", "edge"),
                voice=voice
            )
            await communicate.save(str(output_path))

        asyncio.run(_run())

    postprocess_episode_audio(output_path, job)
    return output_path

