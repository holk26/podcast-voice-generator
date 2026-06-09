"""
Publisher base class — abstraction for distributing episodes.

All publishers must implement:
  publish(episode) -> PublishResult
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.episode_queue import QueuedEpisode


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    published_url: Optional[str] = None
    published_path: Optional[str] = None
    error: Optional[str] = None


class Publisher(ABC):
    """Abstract base for all episode publishers."""

    @abstractmethod
    def publish(self, episode: QueuedEpisode) -> PublishResult:
        """
        Publish a single episode.

        Args:
            episode: A QueuedEpisode in 'approved' status with final_audio_path set.

        Returns:
            PublishResult with success flag, URL/path, and optional error.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable publisher name."""
        ...
