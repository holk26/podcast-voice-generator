"""
Review Tool — manual review and approval workflow for generated episodes.

Integrates with EpisodeQueue to provide:
  - Audio preview path retrieval
  - Approve / reject / request revision
  - Metadata editing (title, description, tags, etc.)
  - Review statistics

Designed to be consumed by a CLI or web UI layer.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.episode_queue import EpisodeQueue, QueuedEpisode
from core.media_package import MediaPackage


class ReviewTool:
    """Review and approval workflow for episode production."""

    def __init__(self, queue: EpisodeQueue):
        self.queue = queue

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview_audio(self, episode_id: str) -> Optional[str]:
        """
        Return the path to the final audio file for preview.
        Returns None if the episode hasn't finished rendering yet.
        Raises KeyError if episode_id doesn't exist.
        """
        episode = self.queue.get(episode_id)
        if episode is None:
            raise KeyError(f"Episode not found: {episode_id}")

        if episode.final_audio_path and os.path.exists(episode.final_audio_path):
            return episode.final_audio_path

        return None

    def get_package(self, episode_id: str) -> Optional[MediaPackage]:
        """Load the MediaPackage for an episode if available."""
        episode = self.queue.get(episode_id)
        if episode is None:
            raise KeyError(f"Episode not found: {episode_id}")

        if episode.media_package_path and os.path.exists(episode.media_package_path):
            return MediaPackage.load(episode.media_package_path)

        return None

    # ------------------------------------------------------------------
    # Review actions
    # ------------------------------------------------------------------

    def approve(self, episode_id: str, notes: str = "") -> QueuedEpisode:
        """Mark an episode as approved for publishing."""
        return self.queue.update_status(
            episode_id,
            status="approved",
            review_notes=notes
        )

    def reject(self, episode_id: str, reason: str = "") -> QueuedEpisode:
        """Mark an episode as rejected."""
        return self.queue.update_status(
            episode_id,
            status="rejected",
            review_notes=reason
        )

    def request_revision(self, episode_id: str, instructions: str = "") -> QueuedEpisode:
        """
        Send an episode back to pending status for revision.
        The instructions are stored in review_notes.
        """
        return self.queue.update_status(
            episode_id,
            status="pending",
            review_notes=instructions
        )

    # ------------------------------------------------------------------
    # Metadata editing
    # ------------------------------------------------------------------

    def edit_metadata(self, episode_id: str, **kwargs) -> MediaPackage:
        """
        Edit manifest metadata for an episode.

        Usage:
            tool.edit_metadata(
                "ep_abc123",
                title="Nuevo título",
                description="Nueva descripción",
                tags=["tech", "ai"]
            )
        """
        episode = self.queue.get(episode_id)
        if episode is None:
            raise KeyError(f"Episode not found: {episode_id}")

        if not episode.media_package_path:
            raise ValueError(f"Episode {episode_id} has no MediaPackage path.")

        package = MediaPackage.load(episode.media_package_path)

        manifest_fields = {
            f for f in dir(package.manifest)
            if not f.startswith("_") and not callable(getattr(package.manifest, f, None))
        }

        updated = []
        for key, value in kwargs.items():
            if key in manifest_fields:
                setattr(package.manifest, key, value)
                updated.append(key)
            else:
                raise ValueError(f"Unknown manifest field: {key}")

        # Save back
        base_dir = os.path.dirname(episode.media_package_path)
        package.save(base_dir)

        # Update review notes to reflect the edit
        if updated:
            note = f"Metadata updated: {', '.join(updated)}"
            current_notes = episode.review_notes or ""
            new_notes = f"{current_notes}\n{note}".strip() if current_notes else note
            self.queue.update_status(episode_id, episode.status, review_notes=new_notes)

        return package

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def list_pending_review(self) -> List[QueuedEpisode]:
        """Return all episodes waiting for review."""
        return self.queue.list_by_status("review")

    def list_approved(self) -> List[QueuedEpisode]:
        """Return all approved episodes ready for publishing."""
        return self.queue.list_by_status("approved")

    def list_rejected(self) -> List[QueuedEpisode]:
        """Return all rejected episodes."""
        return self.queue.list_by_status("rejected")

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return review dashboard statistics."""
        counts = self.queue.count_by_status()
        pending_review = self.list_pending_review()
        approved = self.list_approved()

        return {
            "counts": counts,
            "pending_review_count": len(pending_review),
            "approved_count": len(approved),
            "total": sum(counts.values()),
            "next_for_review": pending_review[0].episode_id if pending_review else None,
            "next_to_publish": approved[0].episode_id if approved else None,
        }
