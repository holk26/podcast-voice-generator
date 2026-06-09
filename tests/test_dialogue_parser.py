"""Tests for DialogueParser."""

import unittest

from processors.dialogue_parser import DialogueParser


class TestDialogueParser(unittest.TestCase):
    def setUp(self):
        self.parser = DialogueParser(default_voice_id="narrador")

    def test_explicit_tags(self):
        text = """
[homer]Buenos días, bienvenidos al podcast.[/homer]
[dalia]Y yo soy Dalia.[/dalia]
"""
        lines = self.parser.parse_explicit_tags(text)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].voice_id, "homer")
        self.assertEqual(lines[0].text, "Buenos días, bienvenidos al podcast.")
        self.assertEqual(lines[1].voice_id, "dalia")
        self.assertEqual(lines[1].text, "Y yo soy Dalia.")

    def test_screenplay_format(self):
        text = """HOMERO: Buenos días, bienvenidos al podcast.
DALIA: Y yo soy Dalia.
NARRADOR: Hoy tenemos noticias interesantes."""
        lines = self.parser.parse_screenplay(text)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].character, "HOMERO")
        self.assertEqual(lines[0].voice_id, "homero")
        self.assertEqual(lines[1].character, "DALIA")
        self.assertEqual(lines[2].text, "Hoy tenemos noticias interesantes.")

    def test_screenplay_with_emotion(self):
        text = "HOMERO: Estoy muy triste (sad)."
        lines = self.parser.parse_screenplay(text)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].emotion, "sad")
        self.assertEqual(lines[0].text, "Estoy muy triste")

    def test_narrative_raya(self):
        text = "—Buenos días —dijo Homero—, bienvenidos. —Gracias —respondió Dalia."
        lines = self.parser.parse_narrative(text)
        # Should have 2 dialogue lines + possible narration
        dialogues = [l for l in lines if l.character != "Narrador"]
        self.assertEqual(len(dialogues), 2)
        self.assertEqual(dialogues[0].character.lower(), "homero")
        self.assertEqual(dialogues[1].character.lower(), "dalia")

    def test_simple_quotes(self):
        text = '\"Hola\", dijo Pedro. \"¿Cómo estás?\", preguntó María.'
        lines = self.parser.parse_narrative(text)
        dialogues = [l for l in lines if l.character != "Narrador"]
        self.assertEqual(len(dialogues), 2)
        self.assertEqual(dialogues[0].character.lower(), "pedro")
        self.assertEqual(dialogues[1].character.lower(), "maría")

    def test_auto_detect_explicit(self):
        text = "[homer]Hola[/homer][dalia]Adiós[/dalia]"
        lines = self.parser.parse(text)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].voice_id, "homer")
        self.assertEqual(lines[1].voice_id, "dalia")

    def test_auto_detect_screenplay(self):
        text = "A: Hola.\nB: ¿Qué tal?"
        lines = self.parser.parse(text)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].character, "A")

    def test_fallback_single_line(self):
        text = "Este es un texto simple sin diálogos."
        lines = self.parser.parse(text, voice_id="narrador")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].character, "Narrador")
        self.assertEqual(lines[0].text, text)

    def test_character_map(self):
        text = "DON QUIJOTE: En un lugar de la Mancha.\nSANCHO: Señor, ¿adónde vamos?"
        lines = self.parser.parse_with_character_map(
            text,
            character_voice_map={"Don Quijote": "homer", "Sancho": "jorge"}
        )
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].voice_id, "homer")  # Mapped
        self.assertEqual(lines[1].voice_id, "jorge")  # Mapped


if __name__ == "__main__":
    unittest.main()
