import asyncio
import edge_tts
import uuid
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


def handle_podcast_episode(episode: Episode, db: Session) -> Path:
    output_dir = OUTPUT_DIR / str(episode.id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "final.mp3"

    voice = VOICE_MAP.get(episode.voice_id, DEFAULT_VOICE)

    async def _run():
        communicate = edge_tts.Communicate(
            episode.source_text or "",
            voice=voice
        )
        await communicate.save(str(output_path))

    asyncio.run(_run())

    episode.audio_url = f"/outputs/{episode.id}/final.mp3"
    episode.status = "completed"
    db.commit()
    return output_path
