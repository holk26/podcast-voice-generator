import asyncio
import edge_tts
import json
import os
import urllib.request
from pathlib import Path
from sqlalchemy.orm import Session
from web_api.models import Episode
from web_api.config import OUTPUT_DIR

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}
DEFAULT_VOICE = "es-ES-AlvaroNeural"

API_BASE = f"http://localhost:{os.getenv('API_PORT', '8000')}"


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


def handle_podcast_episode(episode: Episode, db: Session) -> Path:
    output_dir = OUTPUT_DIR / str(episode.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    if (episode.voice_id or "").startswith("clone:"):
        output_path = _handle_cloned_episode(episode, output_dir)
    else:
        output_path = output_dir / "final.mp3"
        voice = VOICE_MAP.get(episode.voice_id, DEFAULT_VOICE)

        async def _run():
            communicate = edge_tts.Communicate(
                episode.source_text or "",
                voice=voice
            )
            await communicate.save(str(output_path))

        asyncio.run(_run())

    episode.audio_url = f"/outputs/{episode.id}/{output_path.name}"
    episode.status = "completed"
    db.commit()
    return output_path
