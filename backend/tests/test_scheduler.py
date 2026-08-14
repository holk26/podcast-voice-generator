"""
Tests for EpisodeScheduler and AutoPublisher.
"""

import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core.episode_queue import EpisodeQueue
from core.scheduler import EpisodeScheduler, AutoPublisher, ScheduledEpisode
from publishers.file_publisher import FilePublisher


class TestEpisodeScheduler:
    @pytest.fixture
    def setup(self):
        tmpdir = tempfile.mkdtemp()
        qf = Path(tmpdir) / "queue.json"
        sf = Path(tmpdir) / "schedule.json"
        queue = EpisodeQueue(queue_file=str(qf))
        scheduler = EpisodeScheduler(queue, schedule_file=str(sf))
        yield {"tmpdir": tmpdir, "queue": queue, "scheduler": scheduler}
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_schedule_one_shot(self, setup):
        when = (datetime.now() + timedelta(hours=1)).isoformat()
        job = setup["scheduler"].schedule(config={"type": "test"}, when=when)
        assert job.schedule_id.startswith("sched_")
        assert job.next_run == when
        assert job.recurrence == "none"

    def test_schedule_recurring(self, setup):
        when = (datetime.now() + timedelta(hours=1)).isoformat()
        job = setup["scheduler"].schedule(
            config={"type": "test"},
            when=when,
            recurrence="daily"
        )
        assert job.recurrence == "daily"

    def test_schedule_invalid_recurrence_raises(self, setup):
        with pytest.raises(ValueError):
            setup["scheduler"].schedule(config={}, recurrence="hourly")

    def test_cancel(self, setup):
        job = setup["scheduler"].schedule(config={})
        assert setup["scheduler"].cancel(job.schedule_id) is True
        assert setup["scheduler"].get(job.schedule_id) is None
        assert setup["scheduler"].cancel("missing") is False

    def test_enable_disable(self, setup):
        job = setup["scheduler"].schedule(config={})
        setup["scheduler"].disable(job.schedule_id)
        assert setup["scheduler"].get(job.schedule_id).enabled is False
        setup["scheduler"].enable(job.schedule_id)
        assert setup["scheduler"].get(job.schedule_id).enabled is True

    def test_list_upcoming(self, setup):
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        setup["scheduler"].schedule(config={}, when=past)
        setup["scheduler"].schedule(config={}, when=future)

        upcoming = setup["scheduler"].list_upcoming()
        assert len(upcoming) == 1
        assert upcoming[0].next_run == future

    def test_list_overdue(self, setup):
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        setup["scheduler"].schedule(config={}, when=past)
        setup["scheduler"].schedule(config={}, when=future)

        overdue = setup["scheduler"].list_overdue()
        assert len(overdue) == 1
        assert overdue[0].next_run == past

    def test_tick_enqueues_past_job(self, setup):
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        setup["scheduler"].schedule(config={"title": "Past Job"}, when=past)

        before = len(setup["queue"].list_by_status("pending"))
        enqueued = setup["scheduler"].tick()
        after = len(setup["queue"].list_by_status("pending"))

        assert len(enqueued) == 1
        assert after == before + 1
        assert enqueued[0].config["title"] == "Past Job"

    def test_tick_does_not_enqueue_future_job(self, setup):
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        setup["scheduler"].schedule(config={}, when=future)

        enqueued = setup["scheduler"].tick()
        assert len(enqueued) == 0

    def test_tick_daily_recurrence_updates_next_run(self, setup):
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        job = setup["scheduler"].schedule(
            config={},
            when=past,
            recurrence="daily"
        )

        setup["scheduler"].tick()
        updated = setup["scheduler"].get(job.schedule_id)
        assert updated.last_run is not None
        assert updated.run_count == 1

        # Next run should be ~24h after the original run time
        original = datetime.fromisoformat(past)
        next_run = datetime.fromisoformat(updated.next_run)
        delta = next_run - original
        assert 23 <= delta.total_seconds() / 3600 <= 25

    def test_tick_one_shot_disabled_after_run(self, setup):
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        job = setup["scheduler"].schedule(config={}, when=past, recurrence="none")
        setup["scheduler"].tick()
        updated = setup["scheduler"].get(job.schedule_id)
        assert updated.enabled is False

    def test_persistence(self, setup):
        job = setup["scheduler"].schedule(config={"type": "persist"})
        # New instance same file
        scheduler2 = EpisodeScheduler(setup["queue"], schedule_file=str(setup["scheduler"].schedule_file))
        loaded = scheduler2.get(job.schedule_id)
        assert loaded is not None
        assert loaded.config["type"] == "persist"


class TestAutoPublisher:
    @pytest.fixture
    def setup(self):
        tmpdir = tempfile.mkdtemp()
        qf = Path(tmpdir) / "queue.json"
        pub_dir = Path(tmpdir) / "published"
        queue = EpisodeQueue(queue_file=str(qf))
        publisher = FilePublisher(output_dir=str(pub_dir))
        auto = AutoPublisher(queue, publishers=[publisher])
        yield {"tmpdir": tmpdir, "queue": queue, "auto": auto, "pub_dir": pub_dir}
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_run_publishes_approved(self, setup):
        # Create approved episode with audio
        audio = Path(setup["tmpdir"]) / "test.mp3"
        audio.write_text("fake")
        ep = setup["queue"].enqueue(config={"title": "Auto Pub"})
        setup["queue"].update_status(ep.episode_id, "approved", final_audio_path=str(audio))

        results = setup["auto"].run()
        assert len(results) == 1
        assert results[0].success is True

        # Should be published now
        published = setup["queue"].list_by_status("published")
        assert len(published) == 1
        assert published[0].episode_id == ep.episode_id

    def test_run_skips_non_approved(self, setup):
        ep = setup["queue"].enqueue(config={"title": "Pending"})
        # Leave as pending
        results = setup["auto"].run()
        assert len(results) == 0

    def test_run_single(self, setup):
        audio = Path(setup["tmpdir"]) / "test.mp3"
        audio.write_text("fake")
        ep = setup["queue"].enqueue(config={"title": "Single"})
        setup["queue"].update_status(ep.episode_id, "approved", final_audio_path=str(audio))

        results = setup["auto"].run_single(ep.episode_id)
        assert len(results) == 1
        assert results[0].success is True

    def test_run_single_not_found(self, setup):
        results = setup["auto"].run_single("missing")
        assert len(results) == 1
        assert results[0].success is False
        assert "not found" in results[0].error

    def test_run_single_not_approved(self, setup):
        ep = setup["queue"].enqueue(config={})
        results = setup["auto"].run_single(ep.episode_id)
        assert results[0].success is False
        assert "approved" in results[0].error
