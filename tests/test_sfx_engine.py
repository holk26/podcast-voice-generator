"""Tests for SFXEngine."""

import tempfile
import unittest
from pathlib import Path

from pydub import AudioSegment

from audio.sfx_engine import SFXLibrary, SFXMixer, AutoAmbience


class TestSFXLibrary(unittest.TestCase):
    def test_ensure_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = SFXLibrary(library_base_dir=tmp)
            self.assertTrue((Path(tmp) / "ambience").exists())
            self.assertTrue((Path(tmp) / "impacts").exists())
            self.assertTrue((Path(tmp) / "music").exists())

    def test_get_sound_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = SFXLibrary(library_base_dir=tmp)
            sound_path = Path(tmp) / "ambience" / "forest.wav"
            sound_path.write_bytes(b"fake")  # Just for existence check
            found = lib.get_sound_path("ambience", "forest")
            self.assertEqual(found, sound_path)

    def test_suggest_ambience(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = SFXLibrary(library_base_dir=tmp)
            # Create a fake forest sound
            (Path(tmp) / "ambience" / "forest.wav").write_bytes(b"fake")
            suggestions = lib.suggest_ambience("Caminamos por el bosque.")
            self.assertTrue(any(s[1] == "forest" for s in suggestions))


class TestSFXMixer(unittest.TestCase):
    def test_apply_ambience_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = SFXLibrary(library_base_dir=tmp)
            mixer = SFXMixer(library=lib, sample_rate=24000)
            main = AudioSegment.silent(duration=2000, frame_rate=24000)
            result = mixer.apply_ambience(main, "nonexistent")
            self.assertEqual(len(result), len(main))

    def test_apply_background_music_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = SFXLibrary(library_base_dir=tmp)
            mixer = SFXMixer(library=lib, sample_rate=24000)
            main = AudioSegment.silent(duration=2000, frame_rate=24000)
            result = mixer.apply_background_music(main, "nonexistent")
            self.assertEqual(len(result), len(main))


class TestAutoAmbience(unittest.TestCase):
    def test_suggest_for_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            ambience_dir = Path(tmp) / "ambience"
            ambience_dir.mkdir(exist_ok=True)
            (ambience_dir / "rain.wav").write_bytes(b"fake")
            aa = AutoAmbience(sfx_library=SFXLibrary(library_base_dir=tmp))
            suggestions = aa.suggest_for_text("Está lloviendo mucho hoy.")
            self.assertTrue(any(s[1] == "rain" for s in suggestions))


if __name__ == "__main__":
    unittest.main()
