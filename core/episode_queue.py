"""
Episode Queue — persistent job queue for episode production.

Manages the lifecycle of episodes from creation to publishing:
  pending → rendering → review → approved → published
                      └→ rejected

Stores queue in a JSON file for durability across restarts.
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class QueuedEpisode:
    """A single entry in the production queue."""

    episode_id: str
    config: Dict[str, Any]
    status: str = "pending"  # pending | rendering | review | approved | rejected | published
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    media_package_path: Optional[str] = None
    final_audio_path: Optional[str] = None
    review_notes: str = ""
    priority: int = 0  # Higher = processed first
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueuedEpisode":
        # Filter unknown keys for forward compatibility
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ------------------------------------------------------------------
# Queue manager
# ------------------------------------------------------------------

class EpisodeQueue:
    """
    Persistent FIFO queue with priority support for episode production jobs.
    """

    VALID_STATUSES = {"pending", "rendering", "review", "approved", "rejected", "published"}

    def __init__(self, queue_file: str = "data/episode_queue.json"):
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self._episodes: Dict[str, QueuedEpisode] = {}
        self._load()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def enqueue(
        self,
        config: Dict[str, Any],
        priority: int = 0,
        episode_id: Optional[str] = None
    ) -> QueuedEpisode:
        """Add a new episode to the queue."""
        eid = episode_id or self._generate_id()
        episode = QueuedEpisode(
            episode_id=eid,
            config=config,
            status="pending",
            priority=priority
        )
        self._episodes[eid] = episode
        self._save()
        return episode

    def get(self, episode_id: str) -> Optional[QueuedEpisode]:
        """Retrieve a single episode by ID."""
        return self._episodes.get(episode_id)

    def get_next_pending(self) -> Optional[QueuedEpisode]:
        """
        Return the highest-priority pending episode.
        Ties broken by creation time (oldest first).
        """
        pending = [
            ep for ep in self._episodes.values()
            if ep.status == "pending"
        ]
        if not pending:
            return None
        # Sort by priority desc, then created_at asc
        pending.sort(key=lambda ep: (-ep.priority, ep.created_at))
        return pending[0]

    def update_status(
        self,
        episode_id: str,
        status: str,
        media_package_path: Optional[str] = None,
        final_audio_path: Optional[str] = None,
        review_notes: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> QueuedEpisode:
        """Update episode status and optional fields."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Valid: {self.VALID_STATUSES}")

        episode = self._episodes.get(episode_id)
        if episode is None:
            raise KeyError(f"Episode not found: {episode_id}")

        episode.status = status
        episode.updated_at = datetime.now().isoformat()

        if media_package_path is not None:
            episode.media_package_path = media_package_path
        if final_audio_path is not None:
            episode.final_audio_path = final_audio_path
        if review_notes is not None:
            episode.review_notes = review_notes
        if error_message is not None:
            episode.error_message = error_message

        self._save()
        return episode

    def delete(self, episode_id: str) -> bool:
        """Remove an episode from the queue."""
        if episode_id in self._episodes:
            del self._episodes[episode_id]
            self._save()
            return True
        return False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_by_status(self, status: str) -> List[QueuedEpisode]:
        """Return all episodes with the given status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'.")
        return [ep for ep in self._episodes.values() if ep.status == status]

    def list_all(self) -> List[QueuedEpisode]:
        """Return all episodes, sorted by updated_at desc."""
        return sorted(self._episodes.values(), key=lambda ep: ep.updated_at, reverse=True)

    def count_by_status(self) -> Dict[str, int]:
        """Return a count map of statuses."""
        counts = {s: 0 for s in self.VALID_STATUSES}
        for ep in self._episodes.values():
            counts[ep.status] = counts.get(ep.status, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.queue_file.exists():
            self._episodes = {}
            return

        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._episodes = {}
            return

        if isinstance(data, dict):
            self._episodes = {
                k: QueuedEpisode.from_dict(v)
                for k, v in data.items()
            }
        else:
            self._episodes = {}

    def _save(self) -> None:
        data = {k: v.to_dict() for k, v in self._episodes.items()}
        tmp = self.queue_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(self.queue_file)

    @staticmethod
    def _generate_id() -> str:
        return f"ep_{uuid.uuid4().hex[:12]}"
