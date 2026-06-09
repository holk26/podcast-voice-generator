"""
Audio Enhancer — post-processing stage for TTS-generated voice fragments.

Applies local AI models to clean, restore, and upscale audio quality
before final mixing. Currently supports VoiceFixer for speech restoration.

Usage:
    from audio.audio_enhancer import VoiceFixerEnhancer
    enhancer = VoiceFixerEnhancer(cuda=True, mode=0)
    enhancer.enhance("input.wav", "output.wav")
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class AudioEnhancer(ABC):
    """Abstract base for audio enhancement processors."""

    @abstractmethod
    def enhance(self, input_path: str, output_path: str) -> bool:
        """
        Process an audio file and write enhanced output.

        Args:
            input_path: Path to input audio file (wav recommended).
            output_path: Path to write enhanced audio.

        Returns:
            True on success, False on failure.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable enhancer name."""
        ...


class NoOpEnhancer(AudioEnhancer):
    """Pass-through enhancer that copies input to output unchanged."""

    def enhance(self, input_path: str, output_path: str) -> bool:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        shutil.copy2(input_path, output_path)
        return True

    def name(self) -> str:
        return "noop"


class VoiceFixerEnhancer(AudioEnhancer):
    """
    Speech restoration using VoiceFixer local AI model.

    Two-stage pipeline:
      1. Analysis module extracts clean features from degraded audio
      2. Neural vocoder reconstructs high-fidelity 44.1kHz waveform

    Modes:
      0 = Original model (recommended default)
      1 = Add preprocessing (remove higher frequencies)
      2 = Train mode (sometimes better on heavily degraded speech)
    """

    def __init__(
        self,
        cuda: bool = True,
        mode: int = 0,
        weight_prepare: bool = False
    ):
        self.cuda = cuda
        self.mode = mode
        self._voicefixer = None

        if weight_prepare:
            self._prepare_weights()

    def name(self) -> str:
        return f"voicefixer_mode{self.mode}"

    def _get_voicefixer(self):
        """Lazy initialization of VoiceFixer (downloads models on first use)."""
        if self._voicefixer is None:
            try:
                from voicefixer import VoiceFixer
            except ImportError as exc:
                raise RuntimeError(
                    "voicefixer not installed. Run: pip install voicefixer"
                ) from exc
            self._voicefixer = VoiceFixer()
        return self._voicefixer

    def _prepare_weights(self) -> None:
        """Pre-download model weights without processing audio."""
        vf = self._get_voicefixer()
        # VoiceFixer downloads weights lazily on first restore call;
        # no explicit pre-download API is exposed.
        # We call restore on a dummy silent file to trigger download.
        from pydub import AudioSegment
        dummy = AudioSegment.silent(duration=1000, frame_rate=24000)
        tmp_in = "/tmp/vf_dummy_in.wav"
        tmp_out = "/tmp/vf_dummy_out.wav"
        dummy.export(tmp_in, format="wav")
        try:
            vf.restore(tmp_in, tmp_out, cuda=self.cuda, mode=self.mode)
        except Exception:
            pass
        finally:
            for p in (tmp_in, tmp_out):
                if os.path.exists(p):
                    os.remove(p)

    def enhance(self, input_path: str, output_path: str) -> bool:
        """Restore speech quality using VoiceFixer."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input not found: {input_path}")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        try:
            vf = self._get_voicefixer()
            vf.restore(input_path, output_path, cuda=self.cuda, mode=self.mode)
            return os.path.exists(output_path)
        except Exception as exc:
            # Log error but don't crash the pipeline
            print(f"[VoiceFixerEnhancer] ERROR: {exc}")
            return False

    def close(self) -> None:
        """Release model resources."""
        self._voicefixer = None
