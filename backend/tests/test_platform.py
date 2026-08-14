"""
Tests for MediaAutomationPlatform (end-to-end integration).
"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest

from core.platform import MediaAutomationPlatform
from core.pipeline_orchestrator import EpisodeConfig
from publishers.file_publisher import FilePublisher
from agents.llm_provider import MockProvider


class TestMediaAutomationPlatform:
    @pytest.fixture
    def setup(self):
        tmpdir = tempfile.mkdtemp()
        pub_dir = Path(tmpdir) / "published"
        platform = MediaAutomationPlatform(
            data_dir=str(Path(tmpdir) / "data"),
            publishers=[FilePublisher(output_dir=str(pub_dir))],
            provider=MockProvider()
        )
        yield {"tmpdir": tmpdir, "platform": platform, "pub_dir": pub_dir}
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def test_submit(self, setup):
        ep = setup["platform"].submit(EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "hello"}]
        ))
        assert ep.status == "pending"
        assert ep.config["episode_type"] == "raw"

    def test_submit_raw_convenience(self, setup):
        ep = setup["platform"].submit_raw("My Title", "My content")
        assert ep.config["title"] == "My Title"
        assert ep.config["sources"][0]["content"] == "My content"

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def test_run_pipeline_success(self, setup):
        platform = setup["platform"]
        ep = platform.submit(EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "test content"}],
            branding_enabled=False
        ))
        result = platform.run_pipeline(ep.episode_id)
        assert result.success is True
        assert result.final_audio_path is not None

        # Episode should be in review status
        updated = platform.queue.get(ep.episode_id)
        assert updated.status == "review"
        assert updated.final_audio_path is not None

    def test_run_pipeline_not_found(self, setup):
        result = setup["platform"].run_pipeline("missing")
        assert result.success is False
        assert "not found" in result.error

    def test_run_pipeline_wrong_status(self, setup):
        platform = setup["platform"]
        ep = platform.submit(EpisodeConfig(episode_type="raw", sources=[{"content": "x"}]))
        platform.run_pipeline(ep.episode_id)  # Moves to review
        result = platform.run_pipeline(ep.episode_id)  # Try again
        assert result.success is False
        assert "expected 'pending'" in result.error

    def test_run_next_pending(self, setup):
        platform = setup["platform"]
        ep = platform.submit(EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "test"}],
            branding_enabled=False
        ))
        result = platform.run_next_pending()
        assert result is not None
        assert result.success is True

    def test_run_next_pending_empty(self, setup):
        result = setup["platform"].run_next_pending()
        assert result is None

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    def test_approve_reject_revision(self, setup):
        platform = setup["platform"]
        ep = platform.submit_raw("Title", "Content", branding_enabled=False)
        platform.run_pipeline(ep.episode_id)

        approved = platform.approve(ep.episode_id, notes="Good")
        assert approved.status == "approved"
        assert approved.review_notes == "Good"

        platform.request_revision(ep.episode_id, instructions="Fix intro")
        revised = platform.queue.get(ep.episode_id)
        assert revised.status == "pending"
        assert "Fix intro" in revised.review_notes

    def test_edit_metadata(self, setup):
        platform = setup["platform"]
        ep = platform.submit_raw("Old", "Content", branding_enabled=False)
        platform.run_pipeline(ep.episode_id)

        pkg = platform.edit_metadata(ep.episode_id, title="New Title")
        assert pkg.manifest.title == "New Title"

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def test_publish_single(self, setup):
        platform = setup["platform"]
        ep = platform.submit_raw("Pub Test", "Content", branding_enabled=False)
        platform.run_pipeline(ep.episode_id)
        platform.approve(ep.episode_id)

        results = platform.publish(ep.episode_id)
        assert len(results) == 1
        assert results[0].success is True

        published = platform.queue.list_by_status("published")
        assert len(published) == 1

    def test_auto_publish(self, setup):
        platform = setup["platform"]
        for i in range(2):
            ep = platform.submit_raw(f"Auto {i}", "Content", branding_enabled=False)
            platform.run_pipeline(ep.episode_id)
            platform.approve(ep.episode_id)

        results = platform.auto_publish()
        assert len(results) == 2
        assert all(r.success for r in results)

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def test_schedule_and_cancel(self, setup):
        platform = setup["platform"]
        from datetime import datetime, timedelta
        future = (datetime.now() + timedelta(days=1)).isoformat()

        job = platform.schedule(
            EpisodeConfig(episode_type="raw", sources=[{"content": "x"}]),
            when=future,
            recurrence="daily"
        )
        assert job.recurrence == "daily"

        assert platform.cancel_schedule(job.schedule_id) is True
        assert platform.cancel_schedule(job.schedule_id) is False

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def test_tick(self, setup):
        platform = setup["platform"]
        # Schedule a past job
        from datetime import datetime, timedelta
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        platform.schedule(
            EpisodeConfig(episode_type="raw", sources=[{"content": "tick"}]),
            when=past
        )

        result = platform.tick()
        assert "scheduled_enqueued" in result
        assert "pipeline_result" in result
        assert "published" in result

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def test_dashboard(self, setup):
        platform = setup["platform"]
        platform.submit_raw("Dash", "Content")

        dash = platform.get_dashboard()
        assert dash.total_episodes == 1
        assert dash.by_status["pending"] == 1
        assert dash.pending_review == 0

    def test_list_episodes(self, setup):
        platform = setup["platform"]
        ep1 = platform.submit_raw("A", "Content")
        ep2 = platform.submit_raw("B", "Content")
        platform.run_pipeline(ep1.episode_id)  # Moves to review

        all_eps = platform.list_episodes()
        assert len(all_eps) == 2

        pending = platform.list_episodes("pending")
        assert len(pending) == 1
        assert pending[0].episode_id == ep2.episode_id
