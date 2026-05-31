import pytest
import numpy as np
from audio.effects import fade_in, fade_out, add_silence


def test_fade_in_shape():
    audio = np.ones(24000, dtype=np.float32)
    faded = fade_in(audio, sample_rate=24000, duration_ms=500)
    assert faded.shape == audio.shape
    assert faded[0] < faded[-1]


def test_fade_out_shape():
    audio = np.ones(24000, dtype=np.float32)
    faded = fade_out(audio, sample_rate=24000, duration_ms=500)
    assert faded.shape == audio.shape
    assert faded[-1] < faded[0]


def test_add_silence():
    audio = np.ones(24000, dtype=np.float32)
    result = add_silence(audio, sample_rate=24000, duration_ms=1000)
    assert len(result) == 24000 + 24000
