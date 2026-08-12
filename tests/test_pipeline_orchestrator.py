"""
Tests for PipelineOrchestrator.

Uses MockProvider and mocked fetchers to avoid network calls and heavy TTS loading.
"""

import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest
from pydub import AudioSegment

from core.pipeline_orchestrator import PipelineOrchestrator, EpisodeConfig, PipelineResult
from agents.llm_provider import MockProvider
from audio.podcast_mastering import MasteringConfig
from core.media_package import MediaPackage, ScriptLine, Manifest


class TestPipelineOrchestrator:
    """Unit tests for the PipelineOrchestrator."""

    @pytest.fixture
    def temp_output(self):
        tmp = tempfile.mkdtemp()
        yield tmp
        shutil.rmtree(tmp, ignore_errors=True)

    @pytest.fixture
    def mock_provider(self):
        return MockProvider()

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    def test_config_defaults(self):
        cfg = EpisodeConfig(episode_type="news")
        assert cfg.target_duration_minutes == 8.0
        assert cfg.branding_enabled is True
        assert cfg.host_voice_id == "homer"
        assert cfg.output_dir == "media_packages"

    def test_episode_config_has_mastering_defaults(self):
        cfg = EpisodeConfig(episode_type="raw")
        assert cfg.podcast_mastering is not None
        assert cfg.podcast_mastering.enabled is True
        assert cfg.podcast_mastering.target_lufs == -16.0

    def test_background_music_ducking_uses_sidechain_config(self, temp_output):
        tmp_path = Path(temp_output)
        cfg = EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "Hola", "title": "Test"}],
            background_music="test_music",
            bg_music_volume=-18.0,
            podcast_mastering=MasteringConfig(enabled=True),
            output_dir=str(temp_output),
        )
        orch = PipelineOrchestrator(cfg)

        # Create dummy voice audio
        voice_path = str(tmp_path / "voice.mp3")
        AudioSegment.silent(duration=500, frame_rate=24000).export(voice_path, format="mp3")

        # Create dummy music file
        music_dir = Path("sfx_library") / "music"
        music_dir.mkdir(parents=True, exist_ok=True)
        music_path = music_dir / "test_music.wav"
        AudioSegment.silent(duration=1000, frame_rate=24000).export(str(music_path), format="wav")

        try:
            with patch("core.pipeline_orchestrator._ffmpeg_available", return_value=True):
                with patch("core.pipeline_orchestrator.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    # Make AudioSegment.from_file on the ffmpeg output return a silent segment
                    with patch.object(AudioSegment, "from_file", return_value=AudioSegment.silent(duration=500, frame_rate=24000)):
                        orch._apply_background_music(voice_path)

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            filter_str = cmd[cmd.index("-filter_complex") + 1]
            assert "sidechaincompress" in filter_str
            assert "attack=20" in filter_str
            assert "release=250" in filter_str
            assert "ratio=5" in filter_str
            assert "threshold=-24.0dB" in filter_str  # -20 - 8/2
            assert orch.config.podcast_mastering.ducking_ratio == 5.0
        finally:
            if music_path.exists():
                music_path.unlink()

    def test_pipeline_result_repr(self):
        r = PipelineResult(success=True)
        assert r.success is True
        assert r.media_package is None

    # ------------------------------------------------------------------
    # Raw content pipeline (no fetchers)
    # ------------------------------------------------------------------

    def test_raw_pipeline_success(self, temp_output, mock_provider):
        """A raw episode should run the full pipeline end-to-end."""
        cfg = EpisodeConfig(
            episode_type="raw",
            title="Test Raw",
            sources=[{"content": "Hola mundo. Este es un test."}],
            target_duration_minutes=1.0,
            branding_enabled=False,
            output_dir=temp_output
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)

        # Mock DramaMixer to avoid heavy TTS
        mock_segment = AudioSegment.silent(duration=1000, frame_rate=24000)
        with patch("audio.drama_mixer.DramaMixer") as MockMixer:
            instance = MockMixer.return_value
            instance.mix_package = MagicMock(return_value="/fake/main.mp3")
            instance.close = MagicMock()
            # Make mixer write a dummy file so branding can read it
            def side_effect(pkg, path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                mock_segment.export(path, format="mp3")
                return path
            instance.mix_package.side_effect = side_effect

            result = pipeline.run()

        assert result.success is True
        assert result.media_package is not None
        assert result.final_audio_path is not None
        assert os.path.exists(result.final_audio_path)

    def test_raw_pipeline_no_source_raises(self, temp_output, mock_provider):
        """Raw episode without sources should fail gracefully."""
        cfg = EpisodeConfig(
            episode_type="raw",
            title="Test",
            sources=[],
            output_dir=temp_output
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)
        result = pipeline.run()
        assert result.success is False
        assert "Raw episodes require" in result.error

    # ------------------------------------------------------------------
    # Content acquisition routing
    # ------------------------------------------------------------------

    def test_unsupported_episode_type_raises(self, temp_output, mock_provider):
        cfg = EpisodeConfig(
            episode_type="unsupported_xyz",
            output_dir=temp_output
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)
        result = pipeline.run()
        assert result.success is False
        assert "Unsupported episode_type" in result.error

    @patch("content.rss_fetcher.RSSFetcher.fetch")
    def test_news_acquisition_routing(self, mock_fetch, temp_output, mock_provider):
        mock_fetch.return_value = [
            {"title": "T1", "content": "C1", "source_url": "http://a"},
            {"title": "T2", "content": "C2", "source_url": "http://b"}
        ]
        cfg = EpisodeConfig(
            episode_type="news",
            sources=[{"type": "rss", "url": "http://fake", "max_articles": 2}],
            output_dir=temp_output,
            branding_enabled=False
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)

        mock_segment = AudioSegment.silent(duration=500, frame_rate=24000)
        with patch("audio.drama_mixer.DramaMixer") as MockMixer:
            instance = MockMixer.return_value
            instance.close = MagicMock()
            def side_effect(pkg, path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                mock_segment.export(path, format="mp3")
                return path
            instance.mix_package.side_effect = side_effect

            result = pipeline.run()

        assert result.success is True
        mock_fetch.assert_called_once()

    # ------------------------------------------------------------------
    # Template generation (meditation/motivation)
    # ------------------------------------------------------------------

    def test_meditation_pipeline(self, temp_output, mock_provider):
        cfg = EpisodeConfig(
            episode_type="meditation",
            target_duration_minutes=2.0,
            branding_enabled=False,
            output_dir=temp_output,
            processor_options={"topic": "gratitud", "seed": 123}
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)

        mock_segment = AudioSegment.silent(duration=500, frame_rate=24000)
        with patch("audio.drama_mixer.DramaMixer") as MockMixer:
            instance = MockMixer.return_value
            instance.close = MagicMock()
            def side_effect(pkg, path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                mock_segment.export(path, format="mp3")
                return path
            instance.mix_package.side_effect = side_effect

            result = pipeline.run()

        assert result.success is True
        assert "gratitud" in result.media_package.manifest.title.lower() or \
               "meditación" in result.media_package.manifest.title.lower()

    # ------------------------------------------------------------------
    # Branding on/off
    # ------------------------------------------------------------------

    def test_branding_disabled_copies_main(self, temp_output, mock_provider):
        cfg = EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "Hello world"}],
            branding_enabled=False,
            output_dir=temp_output
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)

        mock_segment = AudioSegment.silent(duration=500, frame_rate=24000)
        with patch("audio.drama_mixer.DramaMixer") as MockMixer:
            instance = MockMixer.return_value
            instance.close = MagicMock()
            def side_effect(pkg, path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                mock_segment.export(path, format="mp3")
                return path
            instance.mix_package.side_effect = side_effect

            result = pipeline.run()

        assert result.success is True
        # Should be named final.mp3 when branding is off
        assert "final.mp3" in result.final_audio_path

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def test_logs_populated_on_success(self, temp_output, mock_provider):
        cfg = EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "Test"}],
            branding_enabled=False,
            output_dir=temp_output
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)

        mock_segment = AudioSegment.silent(duration=500, frame_rate=24000)
        with patch("audio.drama_mixer.DramaMixer") as MockMixer:
            instance = MockMixer.return_value
            instance.close = MagicMock()
            def side_effect(pkg, path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                mock_segment.export(path, format="mp3")
                return path
            instance.mix_package.side_effect = side_effect

            result = pipeline.run()

        steps = [log["step"] for log in result.logs]
        assert "acquire" in steps
        assert "process" in steps
        assert "render" in steps
        assert "brand" in steps

    def test_logs_populated_on_failure(self, temp_output, mock_provider):
        cfg = EpisodeConfig(
            episode_type="raw",
            sources=[],
            output_dir=temp_output
        )
        pipeline = PipelineOrchestrator(cfg, provider=mock_provider)
        result = pipeline.run()

        assert result.success is False
        assert any(log["step"] == "pipeline" for log in result.logs)

    # ------------------------------------------------------------------
    # Voice mastering / loudness
    # ------------------------------------------------------------------

    def test_pipeline_applies_voice_processing_after_render(self, temp_output):
        cfg = EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "Hola mundo", "title": "Test"}],
            output_dir=str(temp_output),
            podcast_mastering=MasteringConfig(enabled=True),
            branding_enabled=False,
        )
        orch = PipelineOrchestrator(cfg)

        package = MediaPackage(package_id="test_mastering")
        package.script = [
            ScriptLine(character="Narrador", text="Hola mundo.", voice_id="homer")
        ]
        package.manifest = Manifest(title="Test")
        package._base_path = Path(temp_output) / "test_mastering"
        package._base_path.mkdir(parents=True, exist_ok=True)
        (package._base_path / "assets").mkdir(exist_ok=True)

        fake_rendered = str(package._base_path / "assets" / "main_mix.mp3")

        call_order = []

        def master_side_effect(pkg, path):
            call_order.append("master")
            return fake_rendered, True

        def finalize_side_effect(path):
            call_order.append("finalize")
            return fake_rendered, True

        with (
            patch.object(orch, "_acquire_content", return_value=("Hola mundo.", {"title": "Test"})),
            patch.object(orch, "_process_content", return_value=package),
            patch.object(orch, "_master_voice_mix", side_effect=master_side_effect) as mock_master,
            patch.object(orch, "_finalize_loudness", side_effect=finalize_side_effect) as mock_finalize,
            patch.object(orch, "_update_manifest"),
            patch("audio.drama_mixer.DramaMixer") as MockMixer,
        ):
            instance = MockMixer.return_value
            instance.close = MagicMock()

            def mix_side_effect(pkg, path):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text("fake audio")
                return path

            instance.mix_package.side_effect = mix_side_effect

            package.save = MagicMock()
            result = orch.run()

            assert result.success is True
            mock_master.assert_called_once()
            mock_finalize.assert_called_once()
            assert mock_master.call_args_list[0][0][1] == fake_rendered
            assert call_order == ["master", "finalize"]
