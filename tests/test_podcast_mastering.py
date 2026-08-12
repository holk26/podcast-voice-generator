import pytest
from audio.podcast_mastering import MasteringConfig, _db_to_linear, _linear_to_db


def test_db_to_linear():
    assert _db_to_linear(-6.0) == pytest.approx(0.501, abs=0.01)


def test_linear_to_db():
    assert _linear_to_db(0.5) == pytest.approx(-6.02, abs=0.1)


def test_mastering_config_defaults():
    cfg = MasteringConfig()
    assert cfg.enabled is True
    assert cfg.crossfade_ms == 80
    assert cfg.target_lufs == -16.0
