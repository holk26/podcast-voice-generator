"""
Episode Scheduler — schedules automatic episode generation and publishing.

Combines:
  - EpisodeScheduler: schedules future episode generation jobs
  - AutoPublisher: periodically publishes approved episodes

Both are designed to be called from a cron job or daemon loop.
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.episode_queue import EpisodeQueue, QueuedEpisode
from publishers.base import Publisher, PublishResult


# ------------------------------------------------------------------
# ScheduledEpisode
# ------------------------------------------------------------------

@dataclass
class ScheduledEpisode:
    """A scheduled generation job."""

    schedule_id: str
    config: Dict[str, Any]
    next_run: str  # ISO datetime
    recurrence: Optional[str] = None  # "daily", "weekly", "none"
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledEpisode":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ------------------------------------------------------------------
# EpisodeScheduler
# ------------------------------------------------------------------

class EpisodeScheduler:
    """
    Manages a schedule of automatic episode generation jobs.
    """

    VALID_RECURRENCE = {"none", "daily", "weekly"}

    def __init__(
        self,
        queue: EpisodeQueue,
        schedule_file: str = "data/schedule.json"
    ):
        self.queue = queue
        self.schedule_file = Path(schedule_file)
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
        self._schedules: Dict[str, ScheduledEpisode] = {}
        self._load()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def schedule(
        self,
        config: Dict[str, Any],
        when: Optional[str] = None,
        recurrence: Optional[str] = None,
        schedule_id: Optional[str] = None
    ) -> ScheduledEpisode:
        """
        Schedule a new episode generation job.

        Args:
            config: EpisodeConfig dict
            when: ISO datetime string (default: now)
            recurrence: "daily", "weekly", or None
        """
        if recurrence and recurrence not in self.VALID_RECURRENCE:
            raise ValueError(f"Invalid recurrence '{recurrence}'. Valid: {self.VALID_RECURRENCE}")

        sid = schedule_id or self._generate_id()
        next_run = when or datetime.now().isoformat()

        job = ScheduledEpisode(
            schedule_id=sid,
            config=config,
            next_run=next_run,
            recurrence=recurrence or "none"
        )
        self._schedules[sid] = job
        self._save()
        return job

    def cancel(self, schedule_id: str) -> bool:
        """Cancel a scheduled job."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            self._save()
            return True
        return False

    def get(self, schedule_id: str) -> Optional[ScheduledEpisode]:
        return self._schedules.get(schedule_id)

    def enable(self, schedule_id: str) -> Optional[ScheduledEpisode]:
        job = self._schedules.get(schedule_id)
        if job:
            job.enabled = True
            self._save()
        return job

    def disable(self, schedule_id: str) -> Optional[ScheduledEpisode]:
        job = self._schedules.get(schedule_id)
        if job:
            job.enabled = False
            self._save()
        return job

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> List[ScheduledEpisode]:
        return sorted(self._schedules.values(), key=lambda s: s.next_run)

    def list_upcoming(self, limit: int = 10) -> List[ScheduledEpisode]:
        now = datetime.now().isoformat()
        upcoming = [
            s for s in self._schedules.values()
            if s.enabled and s.next_run >= now
        ]
        upcoming.sort(key=lambda s: s.next_run)
        return upcoming[:limit]

    def list_overdue(self) -> List[ScheduledEpisode]:
        now = datetime.now().isoformat()
        return [
            s for s in self._schedules.values()
            if s.enabled and s.next_run < now
        ]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def tick(self) -> List[QueuedEpisode]:
        """
        Check for due scheduled jobs, enqueue them, and update recurrence.
        Call this periodically (e.g., every minute from a cron/loop).
        """
        now = datetime.now()
        enqueued = []

        for job in list(self._schedules.values()):
            if not job.enabled:
                continue

            run_at = datetime.fromisoformat(job.next_run)
            if run_at > now:
                continue

            # Enqueue episode
            episode = self.queue.enqueue(
                config=job.config,
                episode_id=f"scheduled_{job.schedule_id}_{now.strftime('%Y%m%d_%H%M%S')}"
            )
            enqueued.append(episode)

            # Update job
            job.last_run = now.isoformat()
            job.run_count += 1

            if job.recurrence == "daily":
                next_run = run_at + timedelta(days=1)
                job.next_run = next_run.isoformat()
            elif job.recurrence == "weekly":
                next_run = run_at + timedelta(weeks=1)
                job.next_run = next_run.isoformat()
            else:
                job.enabled = False  # One-shot completed

        if enqueued:
            self._save()
        return enqueued

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.schedule_file.exists():
            self._schedules = {}
            return
        try:
            with open(self.schedule_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._schedules = {}
            return

        if isinstance(data, dict):
            self._schedules = {
                k: ScheduledEpisode.from_dict(v)
                for k, v in data.items()
            }
        else:
            self._schedules = {}

    def _save(self) -> None:
        data = {k: v.to_dict() for k, v in self._schedules.items()}
        tmp = self.schedule_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(self.schedule_file)

    @staticmethod
    def _generate_id() -> str:
        return f"sched_{uuid.uuid4().hex[:12]}"


# ------------------------------------------------------------------
# AutoPublisher
# ------------------------------------------------------------------

class AutoPublisher:
    """
    Automatically publishes approved episodes through configured publishers.
    """

    def __init__(
        self,
        queue: EpisodeQueue,
        publishers: List[Publisher]
    ):
        self.queue = queue
        self.publishers = publishers

    def run(self) -> List[PublishResult]:
        """
        Publish all approved episodes that haven't been published yet.
        Updates episode status to 'published' on success.
        """
        approved = self.queue.list_by_status("approved")
        results = []

        for episode in approved:
            episode_results = []
            all_success = True

            for publisher in self.publishers:
                result = publisher.publish(episode)
                episode_results.append(result)
                if not result.success:
                    all_success = False

            if all_success and episode_results:
                self.queue.update_status(
                    episode.episode_id,
                    "published",
                    review_notes=(episode.review_notes or "") + "\nAuto-published."
                )

            # Return first result as representative
            results.append(episode_results[0] if episode_results else PublishResult(success=False))

        return results

    def run_single(self, episode_id: str) -> List[PublishResult]:
        """Publish a single episode by ID."""
        episode = self.queue.get(episode_id)
        if episode is None:
            return [PublishResult(success=False, error=f"Episode not found: {episode_id}")]

        if episode.status != "approved":
            return [PublishResult(
                success=False,
                error=f"Episode status is '{episode.status}', expected 'approved'."
            )]

        results = []
        all_success = True

        for publisher in self.publishers:
            result = publisher.publish(episode)
            results.append(result)
            if not result.success:
                all_success = False

        if all_success and results:
            self.queue.update_status(
                episode_id,
                "published",
                review_notes=(episode.review_notes or "") + "\nAuto-published."
            )

        return results
