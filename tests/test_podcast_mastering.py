import os
import tempfile

import numpy as np
import pytest
from audio.podcast_mastering import (
    MasteringConfig,
    process_voice_mix,
    _db_to_linear,
    _ffmpeg_available,
    _linear_to_db,
)
from pydub import AudioSegment


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


def _make_test_wav(path: str, duration_ms: int = 1000, freq: int = 440):
    sample_rate = 24000
    t = np.linspace(0, duration_ms / 1000.0, int(sample_rate * duration_ms / 1000.0))
    samples = (0.5 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    audio = AudioSegment(
        samples.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1,
    )
    audio.export(path, format="wav")


def test_process_voice_mix_disabled_copies_input():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input.wav")
        dst = os.path.join(tmp, "output.wav")
        _make_test_wav(src)
        cfg = MasteringConfig(enabled=False)
        result = process_voice_mix(src, dst, cfg)
        assert result == dst
        assert os.path.exists(dst)


def test_process_voice_mix_outputs_valid_audio():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input.wav")
        dst = os.path.join(tmp, "output.wav")
        _make_test_wav(src)
        cfg = MasteringConfig(enabled=True)
        result = process_voice_mix(src, dst, cfg)
        assert result == dst
        seg = AudioSegment.from_wav(result)
        assert seg.frame_rate == 24000
        assert seg.channels == 1
