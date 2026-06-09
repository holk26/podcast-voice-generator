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


if __name__ == "__main__":
    unittest.main()
