"""Tests for DramaMixer."""

import os
import tempfile
import unittest
from pathlib import Path

from core.media_package import MediaPackage, Manifest, ScriptLine
from audio.drama_mixer import DramaMixer


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


if __name__ == "__main__":
    unittest.main()
