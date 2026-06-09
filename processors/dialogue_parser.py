"""
Dialogue Parser — converts raw text into structured ScriptLine turns.

Supports three input formats:
  1. Screenplay format:   CHARACTER: Dialogue text
  2. Narrative quotes:    —Dialogue —said Character—, more text.
                          "Dialogue", said Character.
  3. Explicit tags:       [voice_id]Dialogue text[/voice_id]

Output: List[ScriptLine] ready for DramaMixer.
"""

import re
from typing import List, Optional

from core.media_package import ScriptLine


class DialogueParser:
    """Parse various text formats into structured dialogue turns."""

    # Pattern for explicit tags: [voice_id]text[/voice_id]
    EXPLICIT_TAG_RE = re.compile(
        r"\[(?P<voice_id>[a-zA-Z0-9_]+)\](?P<text>.*?)\[/\1\]",
        re.DOTALL
    )

    # Pattern for screenplay: CHARACTER: text
    # Allows uppercase, lowercase, spaces, accents, underscores
    SCREENPLAY_RE = re.compile(
        r"^\s*(?P<character>[A-ZÁÉÍÓÚÑa-záéíóúñ_][A-ZÁÉÍÓÚÑa-záéíóúñ0-9_\s]*?):\s*(?P<text>.+)$",
        re.MULTILINE
    )

    # Pattern for narrative with em-dash quotes:
    # —Dialogue —said Character—, more text.
    # —Dialogue —respondió Character.
    NARRATIVE_RAYA_RE = re.compile(
        r"[—\"“](?P<text>.+?)[\"”]?\s*[—-]?\s*(?:dijo|respondió|exclamó|preguntó|gritó|murmuró|pensó|susurró)\s+(?P<character>[A-ZÁÉÍÓÚÑa-záéíóúñ][a-záéíóúñ0-9_\s]*)(?=[.,;!]?\s*[—-]?|$)",
        re.UNICODE
    )

    # Pattern for simple quotes: "text", said Character.
    SIMPLE_QUOTE_RE = re.compile(
        r'["""](?P<text>.+?)["""]\s*,?\s*(?:dijo|respondió|exclamó|preguntó|gritó|murmuró|pensó|susurró)\s+(?P<character>[A-ZÁÉÍÓÚÑa-záéíóúñ][a-záéíóúñ0-9_\s]*)(?=[.,;!]|$)',
        re.UNICODE
    )

    def __init__(self, default_voice_id: str = "narrador"):
        self.default_voice_id = default_voice_id

    def parse(self, text: str, voice_id: Optional[str] = None) -> List[ScriptLine]:
        """
        Auto-detect format and parse into ScriptLine list.
        Order of detection: explicit tags → screenplay → narrative quotes.
        """
        text = text.strip()
        if not text:
            return []

        # 1. Check for explicit tags first
        if "[" in text and "[/" in text:
            lines = self.parse_explicit_tags(text)
            if lines:
                return lines

        # 2. Check for screenplay format
        lines = self.parse_screenplay(text)
        if len(lines) >= 2:
            return lines

        # 3. Check for narrative quotes
        lines = self.parse_narrative(text)
        if len(lines) >= 1:
            return lines

        # 4. Fallback: treat entire text as a single narration line
        return [ScriptLine(
            character="Narrador",
            text=text,
            voice_id=voice_id or self.default_voice_id
        )]

    def parse_explicit_tags(self, text: str) -> List[ScriptLine]:
        """Parse [voice_id]text[/voice_id] format."""
        lines = []
        for match in self.EXPLICIT_TAG_RE.finditer(text):
            voice_id = match.group("voice_id")
            line_text = match.group("text").strip()
            if line_text:
                lines.append(ScriptLine(
                    character=voice_id.capitalize(),
                    text=line_text,
                    voice_id=voice_id
                ))
        return lines

    def parse_screenplay(self, text: str) -> List[ScriptLine]:
        """Parse CHARACTER: text format."""
        lines = []
        for match in self.SCREENPLAY_RE.finditer(text):
            character = match.group("character").strip()
            line_text = match.group("text").strip()
            # Clean up any trailing parentheticals like (sad) or [angry]
            emotion = None
            emotion_match = re.search(r"\s*\((\w+)\)\s*\.?$", line_text)
            if emotion_match:
                emotion = emotion_match.group(1)
                line_text = line_text[:emotion_match.start()].strip()
            if line_text:
                lines.append(ScriptLine(
                    character=character,
                    text=line_text,
                    voice_id=character.lower().replace(" ", "_"),
                    emotion=emotion
                ))
        return lines

    def parse_narrative(self, text: str) -> List[ScriptLine]:
        """Parse narrative text with dialogue quotes."""
        lines = []

        # Try em-dash / raya format first (more common in Spanish)
        matches = list(self.NARRATIVE_RAYA_RE.finditer(text))
        if not matches:
            matches = list(self.SIMPLE_QUOTE_RE.finditer(text))

        last_end = 0
        for match in matches:
            # Check if there's narration before this dialogue
            if match.start() > last_end:
                narration = text[last_end:match.start()].strip()
                if narration:
                    lines.append(ScriptLine(
                        character="Narrador",
                        text=narration,
                        voice_id=self.default_voice_id
                    ))

            character = match.group("character").strip()
            line_text = match.group("text").strip()
            lines.append(ScriptLine(
                character=character,
                text=line_text,
                voice_id=character.lower().replace(" ", "_"),
                pause_before_ms=300,
                pause_after_ms=300
            ))
            last_end = match.end()

        # Trailing narration
        if last_end < len(text):
            narration = text[last_end:].strip()
            if narration:
                lines.append(ScriptLine(
                    character="Narrador",
                    text=narration,
                    voice_id=self.default_voice_id
                ))

        return lines

    def parse_with_character_map(
        self,
        text: str,
        character_voice_map: dict,
        default_voice_id: Optional[str] = None
    ) -> List[ScriptLine]:
        """
        Parse text and then map characters to specific voice IDs.
        character_voice_map: {"Don Quijote": "homer", "Sancho": "jorge"}
        Matching is case-insensitive.
        """
        # Build case-insensitive lookup
        lookup = {k.lower(): v for k, v in character_voice_map.items()}
        lines = self.parse(text, voice_id=default_voice_id or self.default_voice_id)
        for line in lines:
            key = line.character.lower()
            if key in lookup:
                line.voice_id = lookup[key]
        return lines
