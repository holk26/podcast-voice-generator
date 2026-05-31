import pytest
import numpy as np
import tempfile
import os
from audio.exporter import export_audio


def test_export_wav():
    audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 24000)).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.wav")
        export_audio(audio, path, sample_rate=24000)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
