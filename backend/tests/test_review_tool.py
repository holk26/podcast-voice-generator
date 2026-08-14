"""
Tests for ReviewTool.
"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest

from core.episode_queue import EpisodeQueue
from core.review_tool import ReviewTool
from core.media_package import MediaPackage, Manifest


class TestReviewTool:
    @pytest.fixture
    def setup(self):
        tmpdir = tempfile.mkdtemp()
        qf = Path(tmpdir) / "queue.json"
        queue = EpisodeQueue(queue_file=str(qf))
        review = ReviewTool(queue)

        # Create a fake episode with package
        ep = queue.enqueue(config={"title": "Test Ep"})
        pkg_dir = Path(tmpdir) / ep.episode_id
        pkg_dir.mkdir()
        pkg = MediaPackage(package_id=ep.episode_id, manifest=Manifest(title="Original"))
        pkg.save(str(pkg_dir))
        audio_path = pkg_dir / "final.mp3"
        audio_path.write_text("fake")

        queue.update_status(
            ep.episode_id,
            "review",
            media_package_path=str(pkg_dir),
            final_audio_path=str(audio_path)
        )

        yield {"tmpdir": tmpdir, "queue": queue, "review": review, "ep_id": ep.episode_id}
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def test_preview_audio(self, setup):
        path = setup["review"].preview_audio(setup["ep_id"])
        assert path is not None
        assert os.path.exists(path)

    def test_preview_audio_missing_episode(self, setup):
        with pytest.raises(KeyError):
            setup["review"].preview_audio("nonexistent")

    def test_preview_audio_not_ready(self, setup):
        ep = setup["queue"].enqueue(config={})
        # No final_audio_path set
        setup["queue"].update_status(ep.episode_id, "review")
        assert setup["review"].preview_audio(ep.episode_id) is None

    def test_get_package(self, setup):
        pkg = setup["review"].get_package(setup["ep_id"])
        assert pkg is not None
        assert pkg.package_id == setup["ep_id"]

    def test_get_package_missing(self, setup):
        ep = setup["queue"].enqueue(config={})
        setup["queue"].update_status(ep.episode_id, "review")
        assert setup["review"].get_package(ep.episode_id) is None

    # ------------------------------------------------------------------
    # Review actions
    # ------------------------------------------------------------------

    def test_approve(self, setup):
        ep = setup["review"].approve(setup["ep_id"], notes="Great")
        assert ep.status == "approved"
        assert ep.review_notes == "Great"
        assert setup["queue"].get(setup["ep_id"]).status == "approved"

    def test_reject(self, setup):
        ep = setup["review"].reject(setup["ep_id"], reason="Bad audio")
        assert ep.status == "rejected"
        assert ep.review_notes == "Bad audio"

    def test_request_revision(self, setup):
        ep = setup["review"].request_revision(setup["ep_id"], instructions="Fix intro")
        assert ep.status == "pending"
        assert "Fix intro" in ep.review_notes

    # ------------------------------------------------------------------
    # Metadata editing
    # ------------------------------------------------------------------

    def test_edit_metadata(self, setup):
        pkg = setup["review"].edit_metadata(
            setup["ep_id"],
            title="New Title",
            description="New Desc"
        )
        assert pkg.manifest.title == "New Title"
        assert pkg.manifest.description == "New Desc"

        # Verify persisted
        reloaded = setup["review"].get_package(setup["ep_id"])
        assert reloaded.manifest.title == "New Title"

    def test_edit_metadata_unknown_field_raises(self, setup):
        with pytest.raises(ValueError, match="Unknown manifest field"):
            setup["review"].edit_metadata(setup["ep_id"], bogus_field="x")

    def test_edit_metadata_no_package_raises(self, setup):
        ep = setup["queue"].enqueue(config={})
        setup["queue"].update_status(ep.episode_id, "review")
        with pytest.raises(ValueError, match="no MediaPackage path"):
            setup["review"].edit_metadata(ep.episode_id, title="X")

    # ------------------------------------------------------------------
    # Lists & stats
    # ------------------------------------------------------------------

    def test_list_pending_review(self, setup):
        pending = setup["review"].list_pending_review()
        assert len(pending) == 1
        assert pending[0].episode_id == setup["ep_id"]

    def test_list_approved(self, setup):
        setup["review"].approve(setup["ep_id"])
        approved = setup["review"].list_approved()
        assert len(approved) == 1

    def test_list_rejected(self, setup):
        setup["review"].reject(setup["ep_id"])
        rejected = setup["review"].list_rejected()
        assert len(rejected) == 1

    def test_get_stats(self, setup):
        setup["review"].approve(setup["ep_id"])
        stats = setup["review"].get_stats()
        assert stats["total"] == 1
        assert stats["approved_count"] == 1
        assert stats["pending_review_count"] == 0
        assert stats["next_to_publish"] == setup["ep_id"]
        assert stats["next_for_review"] is None
