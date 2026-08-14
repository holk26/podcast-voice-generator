import pytest
import numpy as np
from audio.mixer import mix_with_background, apply_ducking


def test_mix_with_background():
    voice = np.ones(24000, dtype=np.float32) * 0.5
    bg = np.ones(24000, dtype=np.float32) * 0.3
    mixed = mix_with_background(voice, bg, bg_volume_db=-10)
    assert len(mixed) == len(voice)
    assert np.max(np.abs(mixed)) <= 1.0


def test_apply_ducking():
    bg = np.ones(24000, dtype=np.float32) * 0.5
    ducked = apply_ducking(bg, duck_db=12)
    assert np.max(np.abs(ducked)) < 0.5
