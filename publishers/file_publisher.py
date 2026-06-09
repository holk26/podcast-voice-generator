"""
File Publisher — copies final audio to a destination directory.

Simplest publisher: just organizes approved episodes into a clean output folder.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from publishers.base import Publisher, PublishResult
from core.episode_queue import QueuedEpisode


class FilePublisher(Publisher):
    """
    Copies episode audio files to a destination directory with sanitized filenames.
    """

    def __init__(self, output_dir: str = "published", organize_by_date: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.organize_by_date = organize_by_date

    def name(self) -> str:
        return "file"

    def publish(self, episode: QueuedEpisode) -> PublishResult:
        if not episode.final_audio_path:
            return PublishResult(
                success=False,
                error="Episode has no final_audio_path."
            )

        src = Path(episode.final_audio_path)
        if not src.exists():
            return PublishResult(
                success=False,
                error=f"Audio file not found: {src}"
            )

        # Build destination path
        dest_dir = self._build_dest_dir(episode)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_title = self._sanitize(episode.config.get("title", episode.episode_id))
        ext = src.suffix or ".mp3"
        dest_name = f"{safe_title}{ext}"
        dest = dest_dir / dest_name

        # Handle collision
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{safe_title}_{counter}{ext}"
            counter += 1

        try:
            shutil.copy2(src, dest)
        except Exception as exc:
            return PublishResult(success=False, error=str(exc))

        return PublishResult(
            success=True,
            published_path=str(dest),
            published_url=f"file://{dest.resolve()}"
        )

    def _build_dest_dir(self, episode: QueuedEpisode) -> Path:
        if self.organize_by_date:
            from datetime import datetime
            now = datetime.now()
            return self.output_dir / f"{now.year}" / f"{now.month:02d}"
        return self.output_dir

    @staticmethod
    def _sanitize(name: str) -> str:
        """Sanitize a string for use as a filename."""
        import re
        safe = re.sub(r'[^\w\s-]', '', name)
        safe = re.sub(r'[-\s]+', '_', safe)
        return safe.strip('_') or "episode"
