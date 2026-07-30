import asyncio
import edge_tts
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from sqlalchemy.orm import Session
from web_api.models import Episode
from web_api.config import OUTPUT_DIR, BASE_DIR

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}
DEFAULT_VOICE = "es-ES-AlvaroNeural"

API_BASE = f"http://localhost:{os.getenv('API_PORT', '8000')}"

MUSIC_INTRO = BASE_DIR / "sfx_library" / "music" / "intro_jingle.wav"
MUSIC_OUTRO = BASE_DIR / "sfx_library" / "music" / "outro_theme.wav"


def _handle_cloned_episode(episode: Episode, output_dir: Path) -> Path:
    """Voces clonadas: delega en la API, que mantiene el motor Higgs cargado
    en GPU (el worker no tiene VRAM para una segunda instancia)."""
    output_path = output_dir / "final.wav"
    req = urllib.request.Request(
        f"{API_BASE}/api/tts/synthesize",
        data=json.dumps({
            "voice_id": episode.voice_id,
            "text": episode.source_text or "",
            "label": f"Episodio #{episode.id}: {episode.title}",
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3600) as resp:
        audio_url = json.load(resp)["audio_url"]
    with urllib.request.urlopen(f"{API_BASE}{audio_url}", timeout=300) as resp:
        output_path.write_bytes(resp.read())
    return output_path


def _add_branding_music(path: Path) -> None:
    """Añade la música de intro y outro alrededor del contenido."""
    if not MUSIC_INTRO.exists() and not MUSIC_OUTRO.exists():
        return
    from pydub import AudioSegment

    main = AudioSegment.from_file(path)
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


def postprocess_episode_audio(path: Path) -> None:
    """Cadena de postproducción del episodio: música + volumen uniforme."""
    try:
        _add_branding_music(path)
    except Exception:
        pass  # la música nunca debe romper el episodio
    try:
        _normalize_loudness(path)
    except Exception:
        pass


def handle_podcast_episode(episode: Episode, db: Session) -> Path:
    output_dir = OUTPUT_DIR / str(episode.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    if (episode.voice_id or "").startswith("clone:"):
        output_path = _handle_cloned_episode(episode, output_dir)
    else:
        output_path = output_dir / "final.mp3"
        voice = VOICE_MAP.get(episode.voice_id, DEFAULT_VOICE)

        async def _run():
            from core.emotion_tags import sanitize_emotion_tags
            communicate = edge_tts.Communicate(
                sanitize_emotion_tags(episode.source_text or "", "edge"),
                voice=voice
            )
            await communicate.save(str(output_path))

        asyncio.run(_run())

    postprocess_episode_audio(output_path)

    episode.audio_url = f"/outputs/{episode.id}/{output_path.name}"
    episode.status = "completed"
    db.commit()
    return output_path
