"""Tests for BrandingEngine."""

import tempfile
import unittest
from pathlib import Path

from core.media_package import MediaPackage, Manifest
from audio.branding_engine import BrandingEngine


class TestBrandingEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = BrandingEngine()

    def tearDown(self):
        import shutil
        self.engine.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_intro_voice_only(self):
        """Generate intro without music (if no jingle exists)."""
        manifest = Manifest(title="Test Show", episode_number=1)
        intro = self.engine.generate_intro(manifest, music_name="nonexistent_jingle")
        self.assertIsNotNone(intro)
        self.assertGreater(len(intro), 0)

    def test_generate_outro_voice_only(self):
        """Generate outro without music."""
        manifest = Manifest(title="Test Show")
        outro = self.engine.generate_outro(manifest, music_name="nonexistent_theme")
        self.assertIsNotNone(outro)
        self.assertGreater(len(outro), 0)

    def test_apply_to_package_with_music(self):
        """Apply intro/outro to a synthetic silent audio file."""
        from pydub import AudioSegment

        pkg = MediaPackage(package_id="test_branding_001")
        pkg.set_manifest(Manifest(title="Branded Test", episode_number=1))

        # Create a fake main audio file
        main_path = Path(self.temp_dir) / "main.wav"
        main = AudioSegment.silent(duration=3000, frame_rate=24000)
        main.export(str(main_path), format="wav")

        output_path = Path(self.temp_dir) / "branded.wav"
        result = self.engine.apply_to_package(pkg, str(main_path), str(output_path))

        self.assertTrue(Path(result).exists())
        self.assertGreater(Path(result).stat().st_size, 1000)

    def test_apply_to_package_with_target_lufs(self):
        """Apply intro/outro and normalize segments to a target LUFS."""
        from pydub import AudioSegment

        pkg = MediaPackage(package_id="test_branding_002")
        pkg.set_manifest(Manifest(title="Branded LUFS Test", episode_number=2))

        main_path = Path(self.temp_dir) / "main_lufs.wav"
        main = AudioSegment.silent(duration=3000, frame_rate=24000)
        main.export(str(main_path), format="wav")

        output_path = Path(self.temp_dir) / "branded_lufs.wav"
        result = self.engine.apply_to_package(
            pkg,
            str(main_path),
            str(output_path),
            target_lufs=-16.0,
        )

        self.assertTrue(Path(result).exists())
        self.assertGreater(Path(result).stat().st_size, 1000)

    def test_branding_engine_crossfade_ms_clamping(self):
        """BrandingEngine clamps branding_crossfade_ms and accepts custom values."""
        engine = BrandingEngine()
        try:
            self.assertEqual(engine.branding_crossfade_ms, 300)
        finally:
            engine.close()

        engine_custom = BrandingEngine(branding_crossfade_ms=500)
        try:
            self.assertEqual(engine_custom.branding_crossfade_ms, 500)
        finally:
            engine_custom.close()

        engine_negative = BrandingEngine(branding_crossfade_ms=-100)
        try:
            self.assertEqual(engine_negative.branding_crossfade_ms, 0)
        finally:
            engine_negative.close()

        engine_large = BrandingEngine(branding_crossfade_ms=2000)
        try:
            self.assertEqual(engine_large.branding_crossfade_ms, 1000)
        finally:
            engine_large.close()


if __name__ == "__main__":
    unittest.main()
