import re
from dataclasses import dataclass
from typing import Dict, List

from core.media_package import ScriptLine


@dataclass
class DialogueSegment:
    speaker: str
    text: str


SPEAKER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_\s]*?):\s*(.+)$", re.MULTILINE)
TAG_RE = re.compile(r"\[(\w+)\](.*?)\[/\1\]", re.DOTALL)


def parse_dialogue(script: str) -> List[DialogueSegment]:
    """Split a script into segments when lines start with a speaker prefix."""
    segments: List[DialogueSegment] = []
    current_speaker: str | None = None
    current_lines: List[str] = []

    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        m = SPEAKER_RE.match(line)
        if m:
            if current_speaker and current_lines:
                segments.append(DialogueSegment(current_speaker, " ".join(current_lines)))
            current_speaker = m.group(1).strip().capitalize()
            current_lines = [m.group(2).strip()]
        elif current_speaker:
            current_lines.append(line)

    if current_speaker and current_lines:
        segments.append(DialogueSegment(current_speaker, " ".join(current_lines)))

    return segments


class DialogueParser:
    """Parse dramatized scripts into ScriptLine objects."""

    def parse(self, text: str) -> List[ScriptLine]:
        """Parse BBCode-style [speaker]text[/speaker] tags."""
        lines: List[ScriptLine] = []
        for match in TAG_RE.finditer(text):
            character = match.group(1).strip().capitalize()
            content = match.group(2).strip()
            if not content:
                continue
            lines.append(ScriptLine(character=character, text=content, voice_id=character.lower()))
        return lines

    def parse_with_character_map(
        self, script: str, casting_map: Dict[str, str]
    ) -> List[ScriptLine]:
        """Parse speaker-prefixed lines and assign voice IDs from a casting map."""
        segments = parse_dialogue(script)
        lines: List[ScriptLine] = []
        for segment in segments:
            character = segment.speaker
            voice_id = casting_map.get(character) or casting_map.get(character.lower()) or character.lower()
            lines.append(ScriptLine(character=character, text=segment.text, voice_id=voice_id))
        return lines
