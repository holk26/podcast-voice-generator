import pytest
import numpy as np
from audio.normalizer import normalize_peak, normalize_lufs


def test_normalize_peak():
    audio = np.array([0.5, 1.0, 0.5], dtype=np.float32)
    normalized = normalize_peak(audio, target_db=-6.0)
    peak = np.max(np.abs(normalized))
    assert abs(peak - 0.5) < 0.01


def test_normalize_peak_empty():
    audio = np.array([], dtype=np.float32)
    result = normalize_peak(audio, target_db=-6.0)
    assert len(result) == 0
