"""Tests for VoiceCastManager."""

import os
import tempfile
import unittest
from pathlib import Path

from cast.voice_cast_manager import VoiceCastManager, VoiceProfile


class TestVoiceCastManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.profiles_dir = Path(self.temp_dir) / "profiles"
        self.map_path = Path(self.temp_dir) / "character_map.json"
        self.vcm = VoiceCastManager(
            profiles_dir=str(self.profiles_dir),
            character_map_path=str(self.map_path)
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_and_get_profile(self):
        profile = VoiceProfile(
            voice_id="test_voz",
            name="Test Voz",
            engine="edge_tts",
            language="es",
            speaker_id="es-ES-AlvaroNeural"
        )
        self.vcm.register_profile(profile)
        retrieved = self.vcm.get_profile("test_voz")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test Voz")
        self.assertEqual(retrieved.engine, "edge_tts")

    def test_profile_to_voice(self):
        profile = VoiceProfile(
            voice_id="test_voz",
            name="Test Voz",
            engine="edge_tts",
            language="es",
            speaker_id="es-ES-AlvaroNeural"
        )
        voice = profile.to_voice()
        self.assertEqual(voice.id, "test_voz")
        self.assertEqual(voice.type, "pretrained")
        self.assertEqual(voice.speaker_id, "es-ES-AlvaroNeural")

    def test_cloned_profile_to_voice(self):
        profile = VoiceProfile(
            voice_id="clone_test",
            name="Clone Test",
            engine="xtts",
            language="es",
            reference_path="voices/clones/test.wav"
        )
        voice = profile.to_voice()
        self.assertEqual(voice.type, "cloned")
        self.assertEqual(voice.reference_path, "voices/clones/test.wav")

    def test_character_assignment(self):
        profile = VoiceProfile(
            voice_id="v1",
            name="Voz 1",
            engine="edge_tts",
            language="es",
            speaker_id="es-ES-AlvaroNeural"
        )
        self.vcm.register_profile(profile)
        self.vcm.assign_character("Don Quijote", "v1")
        self.assertEqual(self.vcm.get_character_voice_id("Don Quijote"), "v1")

    def test_resolve_voice_for_line(self):
        p1 = VoiceProfile(voice_id="h", name="H", engine="edge_tts", language="es", speaker_id="es-ES-AlvaroNeural")
        p2 = VoiceProfile(voice_id="d", name="D", engine="edge_tts", language="es", speaker_id="es-MX-DaliaNeural")
        self.vcm.register_profile(p1)
        self.vcm.register_profile(p2)
        self.vcm.assign_character("Sancho", "d")

        resolved = self.vcm.resolve_voice_for_line("Sancho", fallback_voice_id="h")
        self.assertEqual(resolved.voice_id, "d")

        resolved2 = self.vcm.resolve_voice_for_line("Unknown", fallback_voice_id="h")
        self.assertEqual(resolved2.voice_id, "h")

    def test_default_cast_loads(self):
        """Test that the default cast in the repo loads correctly."""
        vcm = VoiceCastManager()
        self.assertIn("homer", vcm.list_voice_ids())
        self.assertIn("dalia", vcm.list_voice_ids())
        self.assertIn("narrador", vcm.list_voice_ids())
        self.assertIn("elvira", vcm.list_voice_ids())
        self.assertIn("jorge", vcm.list_voice_ids())

        homer = vcm.get_profile("homer")
        self.assertEqual(homer.engine, "xtts")
        self.assertEqual(homer.reference_path, "voices/clones/voz_homer_compat.wav")


if __name__ == "__main__":
    unittest.main()
