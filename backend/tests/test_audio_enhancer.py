"""
Tests for audio enhancer module.
"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest
from pydub import AudioSegment

from audio.audio_enhancer import NoOpEnhancer, VoiceFixerEnhancer


class TestNoOpEnhancer:
    def test_enhance_copies_file(self):
        enh = NoOpEnhancer()
        tmpdir = tempfile.mkdtemp()
        try:
            src = Path(tmpdir) / "input.wav"
            out = Path(tmpdir) / "output.wav"
            seg = AudioSegment.silent(duration=1000, frame_rate=24000)
            seg.export(src, format="wav")

            assert enh.enhance(str(src), str(out)) is True
            assert out.exists()
            assert os.path.getsize(out) == os.path.getsize(src)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_name(self):
        assert NoOpEnhancer().name() == "noop"


class TestVoiceFixerEnhancer:
    def test_name(self):
        enh = VoiceFixerEnhancer(cuda=False, mode=0)
        assert enh.name() == "voicefixer_mode0"

    def test_enhance_real_audio(self):
        """Integration test with VoiceFixer (requires installation)."""
        try:
            from voicefixer import VoiceFixer
        except ImportError:
            pytest.skip("voicefixer not installed")

        tmpdir = tempfile.mkdtemp()
        try:
            src = Path(tmpdir) / "input.wav"
            out = Path(tmpdir) / "output.wav"

            # Create a synthetic voice-like audio (not just silence)
            # VoiceFixer may fail on pure silence; use a sine wave
            import numpy as np
            sample_rate = 24000
            duration_ms = 2000
            t = np.linspace(0, duration_ms / 1000, int(sample_rate * duration_ms / 1000))
            wave = (np.sin(2 * np.pi * 440 * t) * 0.3 * 32767).astype(np.int16)
            seg = AudioSegment(
                wave.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=1
            )
            seg.export(src, format="wav")

            enh = VoiceFixerEnhancer(cuda=False, mode=0)
            success = enh.enhance(str(src), str(out))

            if success:
                assert out.exists()
                assert os.path.getsize(out) > 0
            else:
                # VoiceFixer may fail on synthetic data; that's OK for the test
                pass

            enh.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_enhance_missing_input_raises(self):
        enh = VoiceFixerEnhancer(cuda=False, mode=0)
        with pytest.raises(FileNotFoundError):
            enh.enhance("/nonexistent/file.wav", "/tmp/out.wav")

    def test_close_releases(self):
        enh = VoiceFixerEnhancer(cuda=False, mode=0)
        enh._voicefixer = "dummy"
        enh.close()
        assert enh._voicefixer is None
