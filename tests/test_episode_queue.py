"""
Tests for EpisodeQueue.
"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest

from core.episode_queue import EpisodeQueue, QueuedEpisode


class TestEpisodeQueue:
    @pytest.fixture
    def tmp_queue(self):
        tmpdir = tempfile.mkdtemp()
        qf = Path(tmpdir) / "queue.json"
        queue = EpisodeQueue(queue_file=str(qf))
        yield queue
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Basic CRUD
    # ------------------------------------------------------------------

    def test_enqueue_creates_episode(self, tmp_queue):
        ep = tmp_queue.enqueue(config={"type": "test"})
        assert ep.episode_id.startswith("ep_")
        assert ep.status == "pending"
        assert ep.config["type"] == "test"

    def test_enqueue_with_custom_id(self, tmp_queue):
        ep = tmp_queue.enqueue(config={}, episode_id="my_custom_id")
        assert ep.episode_id == "my_custom_id"

    def test_get_existing(self, tmp_queue):
        ep = tmp_queue.enqueue(config={})
        fetched = tmp_queue.get(ep.episode_id)
        assert fetched is not None
        assert fetched.episode_id == ep.episode_id

    def test_get_missing_returns_none(self, tmp_queue):
        assert tmp_queue.get("nonexistent") is None

    def test_delete_removes_episode(self, tmp_queue):
        ep = tmp_queue.enqueue(config={})
        assert tmp_queue.delete(ep.episode_id) is True
        assert tmp_queue.get(ep.episode_id) is None
        assert tmp_queue.delete(ep.episode_id) is False

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def test_update_status(self, tmp_queue):
        ep = tmp_queue.enqueue(config={})
        updated = tmp_queue.update_status(ep.episode_id, "rendering")
        assert updated.status == "rendering"
        assert tmp_queue.get(ep.episode_id).status == "rendering"

    def test_update_status_invalid_raises(self, tmp_queue):
        ep = tmp_queue.enqueue(config={})
        with pytest.raises(ValueError, match="Invalid status"):
            tmp_queue.update_status(ep.episode_id, "bogus")

    def test_update_status_missing_episode_raises(self, tmp_queue):
        with pytest.raises(KeyError):
            tmp_queue.update_status("missing", "approved")

    def test_update_status_with_paths(self, tmp_queue):
        ep = tmp_queue.enqueue(config={})
        updated = tmp_queue.update_status(
            ep.episode_id,
            "review",
            media_package_path="/pkg",
            final_audio_path="/audio.mp3",
            review_notes="check this"
        )
        assert updated.media_package_path == "/pkg"
        assert updated.final_audio_path == "/audio.mp3"
        assert updated.review_notes == "check this"

    # ------------------------------------------------------------------
    # Priority & ordering
    # ------------------------------------------------------------------

    def test_get_next_pending_priority_order(self, tmp_queue):
        low = tmp_queue.enqueue(config={}, priority=1)
        high = tmp_queue.enqueue(config={}, priority=10)
        mid = tmp_queue.enqueue(config={}, priority=5)

        next_ep = tmp_queue.get_next_pending()
        assert next_ep.episode_id == high.episode_id

    def test_get_next_pending_tie_breaker(self, tmp_queue):
        # Same priority: oldest first
        first = tmp_queue.enqueue(config={}, priority=5)
        second = tmp_queue.enqueue(config={}, priority=5)
        assert tmp_queue.get_next_pending().episode_id == first.episode_id

    def test_get_next_pending_no_pending(self, tmp_queue):
        assert tmp_queue.get_next_pending() is None

    def test_get_next_pending_skips_non_pending(self, tmp_queue):
        pending = tmp_queue.enqueue(config={}, priority=5)
        tmp_queue.enqueue(config={}, priority=5)
        tmp_queue.update_status(pending.episode_id, "rendering")
        # The second one should be returned
        next_ep = tmp_queue.get_next_pending()
        assert next_ep is not None
        assert next_ep.status == "pending"

    # ------------------------------------------------------------------
    # Listing & stats
    # ------------------------------------------------------------------

    def test_list_by_status(self, tmp_queue):
        e1 = tmp_queue.enqueue(config={})
        e2 = tmp_queue.enqueue(config={})
        tmp_queue.update_status(e1.episode_id, "approved")
        approved = tmp_queue.list_by_status("approved")
        assert len(approved) == 1
        assert approved[0].episode_id == e1.episode_id

    def test_list_by_status_invalid_raises(self, tmp_queue):
        with pytest.raises(ValueError):
            tmp_queue.list_by_status("bogus")

    def test_list_all_sorted_by_updated(self, tmp_queue):
        e1 = tmp_queue.enqueue(config={})
        e2 = tmp_queue.enqueue(config={})
        tmp_queue.update_status(e1.episode_id, "rendering")
        all_eps = tmp_queue.list_all()
        assert all_eps[0].episode_id == e1.episode_id  # Most recently updated

    def test_count_by_status(self, tmp_queue):
        tmp_queue.enqueue(config={})
        tmp_queue.enqueue(config={})
        counts = tmp_queue.count_by_status()
        assert counts["pending"] == 2
        assert counts["approved"] == 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def test_persistence_across_instances(self, tmp_queue):
        ep = tmp_queue.enqueue(config={"title": "Persist"})
        tmp_queue.update_status(ep.episode_id, "review")

        # New instance, same file
        q2 = EpisodeQueue(queue_file=tmp_queue.queue_file)
        fetched = q2.get(ep.episode_id)
        assert fetched is not None
        assert fetched.config["title"] == "Persist"
        assert fetched.status == "review"

    def test_corrupt_file_loads_empty(self, tmp_queue):
        with open(tmp_queue.queue_file, "w") as f:
            f.write("not json{{{")
        q2 = EpisodeQueue(queue_file=tmp_queue.queue_file)
        assert q2.list_all() == []

    def test_missing_file_starts_empty(self, tmp_queue):
        # Use a completely new path that never existed
        missing_path = tmp_queue.queue_file.parent / "never_created.json"
        q2 = EpisodeQueue(queue_file=str(missing_path))
        assert q2.list_all() == []

    # ------------------------------------------------------------------
    # QueuedEpisode serialization
    # ------------------------------------------------------------------

    def test_episode_roundtrip(self):
        ep = QueuedEpisode(
            episode_id="ep_123",
            config={"a": 1},
            status="pending",
            media_package_path="/pkg",
            final_audio_path="/audio.mp3",
            review_notes="note",
            priority=5,
            error_message="err"
        )
        data = ep.to_dict()
        restored = QueuedEpisode.from_dict(data)
        assert restored.episode_id == ep.episode_id
        assert restored.config == ep.config
        assert restored.status == ep.status
        assert restored.priority == ep.priority
        assert restored.error_message == ep.error_message

    def test_episode_from_dict_ignores_unknown_keys(self):
        restored = QueuedEpisode.from_dict({
            "episode_id": "x",
            "config": {},
            "status": "pending",
            "future_field": "should be ignored"
        })
        assert restored.episode_id == "x"
