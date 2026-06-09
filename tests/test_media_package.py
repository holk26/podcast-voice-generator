"""Tests for MediaPackage core data structures."""

import os
import tempfile
import unittest
from pathlib import Path

from core.media_package import MediaPackage, Manifest, ScriptLine


class TestScriptLine(unittest.TestCase):
    def test_to_from_dict(self):
        line = ScriptLine(
            character="Homero",
            text="Bienvenidos al podcast.",
            voice_id="homer",
            emotion="happy",
            sfx_cue="applause",
            sfx_volume=0.3,
            pause_before_ms=200,
            pause_after_ms=400,
            scene_mark="Intro"
        )
        d = line.to_dict()
        restored = ScriptLine.from_dict(d)
        self.assertEqual(restored.character, "Homero")
        self.assertEqual(restored.text, "Bienvenidos al podcast.")
        self.assertEqual(restored.voice_id, "homer")
        self.assertEqual(restored.emotion, "happy")
        self.assertEqual(restored.sfx_cue, "applause")
        self.assertEqual(restored.sfx_volume, 0.3)


class TestManifest(unittest.TestCase):
    def test_defaults(self):
        m = Manifest(title="Episodio 1")
        self.assertEqual(m.title, "Episodio 1")
        self.assertEqual(m.category, "Technology")
        self.assertFalse(m.explicit)

    def test_to_from_dict(self):
        m = Manifest(
            title="Test",
            description="Desc",
            tags=["tech", "news"],
            episode_number=42
        )
        d = m.to_dict()
        restored = Manifest.from_dict(d)
        self.assertEqual(restored.title, "Test")
        self.assertEqual(restored.tags, ["tech", "news"])
        self.assertEqual(restored.episode_number, 42)


class TestMediaPackage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_save(self):
        pkg = MediaPackage(package_id="test_ep_001")
        pkg.set_manifest(Manifest(title="Episodio de Prueba"))
        pkg.add_line(ScriptLine(character="Homero", text="Hola mundo", voice_id="homer"))
        pkg.add_line(ScriptLine(character="Dalia", text="¿Qué tal?", voice_id="dalia"))

        base = pkg.save(self.temp_dir)
        self.assertTrue(base.exists())
        self.assertTrue((base / "script.json").exists())
        self.assertTrue((base / "manifest.yaml").exists())
        self.assertTrue((base / "assets").exists())

    def test_load_roundtrip(self):
        pkg = MediaPackage(package_id="test_ep_002")
        pkg.set_manifest(Manifest(title="Roundtrip Test", description="Testing save/load"))
        pkg.add_line(ScriptLine(character="Narrador", text="Era una noche oscura.", voice_id="narrador"))

        base = pkg.save(self.temp_dir)
        loaded = MediaPackage.load(base)

        self.assertEqual(loaded.package_id, "test_ep_002")
        self.assertEqual(loaded.manifest.title, "Roundtrip Test")
        self.assertEqual(len(loaded.script), 1)
        self.assertEqual(loaded.script[0].character, "Narrador")
        self.assertEqual(loaded.script[0].text, "Era una noche oscura.")

    def test_copy_asset(self):
        pkg = MediaPackage(package_id="test_ep_003")
        pkg.save(self.temp_dir)

        # Create a dummy file to copy
        dummy = Path(self.temp_dir) / "dummy.txt"
        dummy.write_text("hello")

        copied = pkg.copy_asset(str(dummy))
        self.assertTrue(copied.exists())
        self.assertEqual(copied.name, "dummy.txt")
        self.assertIn(copied, pkg.list_assets())


if __name__ == "__main__":
    unittest.main()
