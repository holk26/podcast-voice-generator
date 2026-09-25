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


def _looks_like_speaker_name(prefix: str) -> bool:
    """Heurística para prefijos que no están en el mapa de voces del canal:
    nombres de hablante reales son cortos (1-3 palabras, <=25 chars) y o van
    en MAYÚSCULAS ('EDUARDO:') o son una única palabra capitalizada. Una
    frase narrativa seguida de dos puntos ('Hoy vamos a responder una
    pregunta que casi nadie se hace: ...') no cumple ninguna de las dos."""
    words = prefix.split()
    if not 1 <= len(words) <= 3 or len(prefix) > 25:
        return False
    letters = [c for c in prefix if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return True
    return len(words) == 1 and prefix[0].isupper()


def parse_dialogue(script: str, valid_speakers: set[str] | None = None) -> List[DialogueSegment]:
    """Split a script into segments when lines start with a speaker prefix.

    ``valid_speakers`` (título-case) lista los hablantes conocidos del canal:
    siempre abren turno. Los prefijos desconocidos solo abren turno cuando
    parecen un nombre de hablante (ver ``_looks_like_speaker_name``); sin
    esta comprobación, cualquier frase seguida de dos puntos se confunde con
    un turno y el texto narrativo previo se pierde.
    """
    segments: List[DialogueSegment] = []
    current_speaker: str | None = None
    current_lines: List[str] = []

    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        m = SPEAKER_RE.match(line)
        speaker = m.group(1).strip().title() if m else None
        is_turn = m and (
            valid_speakers is None
            or speaker in valid_speakers
            or _looks_like_speaker_name(m.group(1).strip())
        )
        if m and is_turn:
            if current_speaker and current_lines:
                segments.append(DialogueSegment(current_speaker, " ".join(current_lines)))
            current_speaker = speaker
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
            character = match.group(1).strip().title()
            content = match.group(2).strip()
            if not content:
                continue
            lines.append(ScriptLine(character=character, text=content, voice_id=character.lower()))
        return lines

    def parse_with_character_map(
        self, script: str, casting_map: Dict[str, str]
    ) -> List[ScriptLine]:
        """Parse speaker-prefixed lines and assign voice IDs from a casting map."""
        segments = parse_dialogue(
            script,
            valid_speakers={k.strip().title() for k in casting_map},
        )
        lines: List[ScriptLine] = []
        for segment in segments:
            character = segment.speaker
            voice_id = casting_map.get(character) or casting_map.get(character.lower()) or character.lower()
            lines.append(ScriptLine(character=character, text=segment.text, voice_id=voice_id))
        return lines
