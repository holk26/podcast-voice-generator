"""
Media Automation Platform — unified interface for the entire system.

Combines all phases into a single orchestration layer:
  - EpisodeQueue (job tracking)
  - PipelineOrchestrator (content → audio)
  - ReviewTool (approval workflow)
  - EpisodeScheduler (automatic scheduling)
  - AutoPublisher (distribution)

Usage:
    platform = MediaAutomationPlatform()
    ep = platform.submit(EpisodeConfig(episode_type="news", ...))
    result = platform.run_pipeline(ep.episode_id)
    platform.approve(ep.episode_id)
    platform.publish(ep.episode_id)
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.episode_queue import EpisodeQueue, QueuedEpisode
from core.pipeline_orchestrator import PipelineOrchestrator, EpisodeConfig, PipelineResult
from core.review_tool import ReviewTool
from core.scheduler import EpisodeScheduler, AutoPublisher
from publishers.base import Publisher, PublishResult


@dataclass
class Dashboard:
    """Platform overview statistics."""

    total_episodes: int = 0
    by_status: Dict[str, int] = field(default_factory=dict)
    pending_review: int = 0
    approved: int = 0
    published: int = 0
    scheduled_jobs: int = 0
    upcoming_jobs: int = 0
    last_tick: Optional[str] = None


class MediaAutomationPlatform:
    """
    Single entry point for the Media Automation Platform.
    """

    def __init__(
        self,
        data_dir: str = "data",
        publishers: Optional[List[Publisher]] = None,
        provider=None,
        voice_cast=None
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.provider = provider
        self.voice_cast = voice_cast
        self.publishers = publishers or []

        # Subsystems
        self.queue = EpisodeQueue(queue_file=str(self.data_dir / "episode_queue.json"))
        self.review = ReviewTool(self.queue)
        self.scheduler = EpisodeScheduler(
            self.queue,
            schedule_file=str(self.data_dir / "schedule.json")
        )
        self.auto_publisher = AutoPublisher(self.queue, self.publishers)

        self._last_tick: Optional[str] = None

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit(self, config: EpisodeConfig, priority: int = 0) -> QueuedEpisode:
        """
        Submit a new episode for production.
        Returns the queued episode entry.
        """
        return self.queue.enqueue(
            config=config.__dict__,
            priority=priority
        )

    def submit_raw(
        self,
        title: str,
        content: str,
        episode_type: str = "raw",
        **kwargs
    ) -> QueuedEpisode:
        """Convenience method to submit raw content."""
        cfg = EpisodeConfig(
            episode_type=episode_type,
            title=title,
            sources=[{"content": content}],
            **kwargs
        )
        return self.submit(cfg)

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def run_pipeline(self, episode_id: str) -> PipelineResult:
        """
        Run the full production pipeline for a pending episode.
        Updates the episode status through rendering → review.
        """
        episode = self.queue.get(episode_id)
        if episode is None:
            return PipelineResult(
                success=False,
                error=f"Episode not found: {episode_id}"
            )

        if episode.status != "pending":
            return PipelineResult(
                success=False,
                error=f"Episode status is '{episode.status}', expected 'pending'."
            )

        # Mark as rendering
        self.queue.update_status(episode_id, "rendering")

        # Build EpisodeConfig from stored dict
        cfg_dict = episode.config
        try:
            config = EpisodeConfig(**cfg_dict)
        except Exception as exc:
            self.queue.update_status(
                episode_id,
                "pending",
                error_message=f"Invalid config: {exc}"
            )
            return PipelineResult(success=False, error=str(exc))

        # Run pipeline
        orchestrator = PipelineOrchestrator(
            config=config,
            provider=self.provider,
            voice_cast=self.voice_cast
        )
        result = orchestrator.run()

        if result.success:
            self.queue.update_status(
                episode_id,
                "review",
                media_package_path=str(result.media_package._base_path),
                final_audio_path=result.final_audio_path
            )
        else:
            self.queue.update_status(
                episode_id,
                "pending",
                error_message=result.error
            )

        return result

    def run_next_pending(self) -> Optional[PipelineResult]:
        """Run pipeline for the highest-priority pending episode."""
        next_ep = self.queue.get_next_pending()
        if next_ep is None:
            return None
        return self.run_pipeline(next_ep.episode_id)

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    def approve(self, episode_id: str, notes: str = "") -> QueuedEpisode:
        """Approve an episode for publishing."""
        return self.review.approve(episode_id, notes=notes)

    def reject(self, episode_id: str, reason: str = "") -> QueuedEpisode:
        """Reject an episode."""
        return self.review.reject(episode_id, reason=reason)

    def request_revision(self, episode_id: str, instructions: str = "") -> QueuedEpisode:
        """Send an episode back for revision."""
        return self.review.request_revision(episode_id, instructions=instructions)

    def edit_metadata(self, episode_id: str, **kwargs) -> Any:
        """Edit episode metadata."""
        return self.review.edit_metadata(episode_id, **kwargs)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish(self, episode_id: str) -> List[PublishResult]:
        """Publish a single approved episode through all configured publishers."""
        return self.auto_publisher.run_single(episode_id)

    def auto_publish(self) -> List[PublishResult]:
        """Publish all approved episodes."""
        return self.auto_publisher.run()

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule(
        self,
        config: EpisodeConfig,
        when: Optional[str] = None,
        recurrence: Optional[str] = None
    ) -> Any:
        """Schedule an automatic episode generation job."""
        return self.scheduler.schedule(
            config=config.__dict__,
            when=when,
            recurrence=recurrence
        )

    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a scheduled job."""
        return self.scheduler.cancel(schedule_id)

    # ------------------------------------------------------------------
    # Cycle / daemon tick
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        """
        Run one full automation cycle:
          1. Execute due scheduled jobs (enqueue them)
          2. Run pipeline for next pending episode
          3. Auto-publish approved episodes
        """
        self._last_tick = datetime.now().isoformat()
        results = {
            "scheduled_enqueued": [],
            "pipeline_result": None,
            "published": []
        }

        # 1. Scheduler tick
        enqueued = self.scheduler.tick()
        results["scheduled_enqueued"] = [ep.episode_id for ep in enqueued]

        # 2. Run next pending pipeline
        pipe_result = self.run_next_pending()
        if pipe_result is not None:
            results["pipeline_result"] = {
                "success": pipe_result.success,
                "episode_id": pipe_result.media_package.package_id if pipe_result.media_package else None,
                "error": pipe_result.error
            }

        # 3. Auto-publish approved
        pub_results = self.auto_publish()
        results["published"] = [
            {"success": r.success, "path": r.published_path, "error": r.error}
            for r in pub_results
        ]

        return results

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_dashboard(self) -> Dashboard:
        """Get platform overview statistics."""
        counts = self.queue.count_by_status()
        review_stats = self.review.get_stats()
        upcoming = self.scheduler.list_upcoming()

        return Dashboard(
            total_episodes=sum(counts.values()),
            by_status=counts,
            pending_review=review_stats["pending_review_count"],
            approved=review_stats["approved_count"],
            published=counts.get("published", 0),
            scheduled_jobs=len(self.scheduler.list_all()),
            upcoming_jobs=len(upcoming),
            last_tick=self._last_tick
        )

    def list_episodes(self, status: Optional[str] = None) -> List[QueuedEpisode]:
        """List episodes, optionally filtered by status."""
        if status:
            return self.queue.list_by_status(status)
        return self.queue.list_all()
