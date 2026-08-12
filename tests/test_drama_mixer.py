"""Tests for DramaMixer."""

import math
import os
import struct
import tempfile
import unittest
from pathlib import Path

from pydub import AudioSegment

from core.media_package import MediaPackage, Manifest, ScriptLine
from audio.drama_mixer import DramaMixer


def _sine_segment(duration_ms: int, freq: float = 440.0, frame_rate: int = 24000) -> AudioSegment:
    """Generate a mono sine-wave AudioSegment for testing."""
    sample_width = 2
    num_samples = int(frame_rate * duration_ms / 1000)
    max_val = (2 ** (sample_width * 8 - 1)) - 1
    data = b"".join(
        struct.pack("<h", int(max_val * 0.5 * math.sin(2 * math.pi * freq * i / frame_rate)))
        for i in range(num_samples)
    )
    return AudioSegment(
        data=data,
        sample_width=sample_width,
        frame_rate=frame_rate,
        channels=1,
    )


class TestDramaMixer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mixer = DramaMixer()

    def tearDown(self):
        import shutil
        self.mixer.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_render_edge_tts_only(self):
        """Render a two-line script using Edge-TTS voices only."""
        pkg = MediaPackage(package_id="test_drama_001")
        pkg.set_manifest(Manifest(title="Test Drama"))
        pkg.add_line(ScriptLine(
            character="Jorge",
            text="Hola, este es un mensaje de prueba.",
            voice_id="jorge",
            pause_after_ms=500
        ))
        pkg.add_line(ScriptLine(
            character="Dalia",
            text="Y este es otro mensaje de prueba.",
            voice_id="dalia",
            pause_after_ms=300
        ))

        output_path = os.path.join(self.temp_dir, "test_mix.wav")
        result = self.mixer.mix_package(pkg, output_path)

        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 1000)

    def test_render_with_explicit_tags_parsed(self):
        """Parse explicit tags and render."""
        from processors.dialogue_parser import DialogueParser

        parser = DialogueParser()
        text = "[jorge]Primer mensaje.[/jorge][dalia]Segundo mensaje.[/dalia]"
        lines = parser.parse(text)

        pkg = MediaPackage(package_id="test_drama_002")
        pkg.set_manifest(Manifest(title="Tag Drama"))
        pkg.add_lines(lines)

        output_path = os.path.join(self.temp_dir, "tag_mix.wav")
        result = self.mixer.mix_package(pkg, output_path)

        self.assertTrue(os.path.exists(result))

    def test_accepts_crossfade_config(self):
        """DramaMixer stores crossfade and trim configuration."""
        mixer = DramaMixer(crossfade_ms=80, trim_silence_threshold_db=-50)
        self.assertEqual(mixer.crossfade_ms, 80)
        self.assertEqual(mixer.trim_silence_threshold_db, -50)

    def test_trim_segment_keeps_padding(self):
        """_trim_segment removes leading/trailing silence and keeps ~50 ms padding."""
        sample_rate = 24000
        leading_silence = AudioSegment.silent(duration=300, frame_rate=sample_rate)
        trailing_silence = AudioSegment.silent(duration=400, frame_rate=sample_rate)
        voice = _sine_segment(duration_ms=1000, freq=440.0, frame_rate=sample_rate)

        segment = leading_silence + voice + trailing_silence
        trimmed = self.mixer._trim_segment(segment)

        # The result should be shorter than the original (silence trimmed).
        self.assertLess(len(trimmed), len(segment))
        # Expected duration: voice + ~50 ms padding on each side.
        expected_duration = 1000 + 50 + 50
        self.assertAlmostEqual(len(trimmed), expected_duration, delta=30)

    def test_crossfade_segments_reduces_duration(self):
        """_crossfade_segments produces output shorter than the sum of segments."""
        sample_rate = 24000
        seg1 = _sine_segment(duration_ms=500, freq=440.0, frame_rate=sample_rate)
        seg2 = _sine_segment(duration_ms=500, freq=880.0, frame_rate=sample_rate)

        mixed = self.mixer._crossfade_segments([seg1, seg2])

        total = len(seg1) + len(seg2)
        self.assertLess(len(mixed), total)
        # Duration reduction should not exceed the configured crossfade.
        reduction = total - len(mixed)
        self.assertLessEqual(reduction, self.mixer.crossfade_ms)

    def test_crossfade_segments_duration_with_three_segments(self):
        """_crossfade_segments total reduction equals one crossfade per boundary."""
        sample_rate = 24000
        seg1 = _sine_segment(duration_ms=500, freq=440.0, frame_rate=sample_rate)
        seg2 = _sine_segment(duration_ms=500, freq=880.0, frame_rate=sample_rate)
        seg3 = _sine_segment(duration_ms=500, freq=660.0, frame_rate=sample_rate)

        mixed = self.mixer._crossfade_segments([seg1, seg2, seg3])

        total = len(seg1) + len(seg2) + len(seg3)
        reduction = total - len(mixed)
        # Two boundaries, each reducing by up to crossfade_ms.
        self.assertGreater(reduction, 0)
        self.assertLessEqual(reduction, 2 * self.mixer.crossfade_ms)


if __name__ == "__main__":
    unittest.main()
