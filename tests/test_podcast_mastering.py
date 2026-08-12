import pytest
from audio.podcast_mastering import (
    MasteringConfig,
    _db_to_linear,
    _ffmpeg_available,
    _linear_to_db,
)


def test_db_to_linear():
    assert _db_to_linear(-6.0) == pytest.approx(0.501, abs=0.01)


def test_db_to_linear_zero():
    assert _db_to_linear(0) == pytest.approx(1.0, abs=0.01)


def test_linear_to_db():
    assert _linear_to_db(0.5) == pytest.approx(-6.02, abs=0.01)


def test_linear_to_db_zero():
    assert _linear_to_db(0) <= -99.0


def test_mastering_config_defaults():
    cfg = MasteringConfig()
    assert cfg.enabled is True
    assert cfg.crossfade_ms == 80
    assert cfg.target_lufs == -16.0


def test_mastering_config_custom_values_isolated():
    cfg = MasteringConfig(target_lufs=-14.0, crossfade_ms=120)
    assert cfg.target_lufs == -14.0
    assert cfg.crossfade_ms == 120
    assert cfg.enabled is True
    assert cfg.branding_crossfade_ms == 300


def test_ffmpeg_available():
    assert _ffmpeg_available() is True
