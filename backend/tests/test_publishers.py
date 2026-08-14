"""
Tests for publishers.
"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest

from core.episode_queue import EpisodeQueue
from publishers.file_publisher import FilePublisher
from publishers.rss_publisher import RSSPublisher, RSSFeedConfig


class TestFilePublisher:
    @pytest.fixture
    def tmp_pub(self):
        tmpdir = tempfile.mkdtemp()
        pub = FilePublisher(output_dir=tmpdir, organize_by_date=False)
        yield {"pub": pub, "tmpdir": tmpdir}
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.fixture
    def fake_episode(self):
        tmpdir = tempfile.mkdtemp()
        audio = Path(tmpdir) / "test.mp3"
        audio.write_text("fake audio")

        qf = Path(tmpdir) / "queue.json"
        queue = EpisodeQueue(queue_file=str(qf))
        ep = queue.enqueue(config={"title": "Test Episode"})
        queue.update_status(ep.episode_id, "approved", final_audio_path=str(audio))
        ep = queue.get(ep.episode_id)

        yield ep
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_publish_success(self, tmp_pub, fake_episode):
        result = tmp_pub["pub"].publish(fake_episode)
        assert result.success is True
        assert result.published_path is not None
        assert os.path.exists(result.published_path)

    def test_publish_no_audio_path(self, tmp_pub):
        from core.episode_queue import EpisodeQueue
        qf = Path(tmp_pub["tmpdir"]) / "empty_queue.json"
        queue = EpisodeQueue(queue_file=str(qf))
        ep = queue.enqueue(config={})
        result = tmp_pub["pub"].publish(ep)
        assert result.success is False
        assert "final_audio_path" in result.error

    def test_publish_missing_file(self, tmp_pub):
        from core.episode_queue import EpisodeQueue
        qf = Path(tmp_pub["tmpdir"]) / "empty_queue2.json"
        queue = EpisodeQueue(queue_file=str(qf))
        ep = queue.enqueue(config={})
        queue.update_status(ep.episode_id, "approved", final_audio_path="/nonexistent/file.mp3")
        ep = queue.get(ep.episode_id)
        result = tmp_pub["pub"].publish(ep)
        assert result.success is False
        assert "not found" in result.error

    def test_sanitize_filename(self, tmp_pub):
        pub = tmp_pub["pub"]
        assert pub._sanitize("Hello World!") == "Hello_World"
        # Unicode letters are preserved (valid in modern filesystems)
        assert pub._sanitize("¿Qué tal?") == "Qué_tal"
        assert pub._sanitize("") == "episode"


class TestRSSPublisher:
    @pytest.fixture
    def tmp_pub(self):
        tmpdir = tempfile.mkdtemp()
        pub = RSSPublisher(
            output_dir=tmpdir,
            feed_config=RSSFeedConfig(title="Test Feed"),
            base_url="https://test.example.com"
        )
        yield {"pub": pub, "tmpdir": tmpdir}
        shutil.rmtree(tmpdir, ignore_errors=True)

    @pytest.fixture
    def fake_episode(self):
        tmpdir = tempfile.mkdtemp()
        audio = Path(tmpdir) / "test.mp3"
        audio.write_text("fake audio")

        qf = Path(tmpdir) / "queue.json"
        queue = EpisodeQueue(queue_file=str(qf))
        ep = queue.enqueue(config={"title": "RSS Episode", "episode_type": "news"})
        queue.update_status(ep.episode_id, "approved", final_audio_path=str(audio))
        ep = queue.get(ep.episode_id)

        yield ep
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_publish_success(self, tmp_pub, fake_episode):
        result = tmp_pub["pub"].publish(fake_episode)
        assert result.success is True
        assert os.path.exists(result.published_path)

    def test_feed_contains_episode(self, tmp_pub, fake_episode):
        pub = tmp_pub["pub"]
        pub.publish(fake_episode)

        feed_path = Path(tmp_pub["tmpdir"]) / "feed.xml"
        assert feed_path.exists()
        content = feed_path.read_text()
        assert "RSS Episode" in content
        assert "<enclosure" in content
        assert "audio/mpeg" in content

    def test_regenerate_feed(self, tmp_pub, fake_episode):
        pub = tmp_pub["pub"]
        pub.publish(fake_episode)

        qf = Path(tmp_pub["tmpdir"]) / "queue.json"
        queue = EpisodeQueue(queue_file=str(qf))
        # Manually add the episode to queue for regeneration
        ep2 = queue.enqueue(config={"title": "Episode 2"})
        audio2 = Path(tmp_pub["tmpdir"]) / "ep2.mp3"
        audio2.write_text("fake")
        queue.update_status(ep2.episode_id, "published", final_audio_path=str(audio2))

        feed_path = pub.regenerate_feed(queue)
        assert os.path.exists(feed_path)
        content = Path(feed_path).read_text()
        assert "Episode 2" in content

    def test_mime_type(self, tmp_pub):
        assert tmp_pub["pub"]._mime_type(".mp3") == "audio/mpeg"
        assert tmp_pub["pub"]._mime_type(".wav") == "audio/wav"
        assert tmp_pub["pub"]._mime_type(".unknown") == "audio/mpeg"
