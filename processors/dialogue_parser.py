import re
from dataclasses import dataclass
from typing import List


@dataclass
class DialogueSegment:
    speaker: str
    text: str


SPEAKER_RE = re.compile(r"^(Alejandra|Homero):\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def parse_dialogue(script: str) -> List[DialogueSegment]:
    """Split a script into segments when lines start with 'Alejandra:' or 'Homero:'."""
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
            current_speaker = m.group(1).capitalize()
            current_lines = [m.group(2)]
        elif current_speaker:
            current_lines.append(line)

    if current_speaker and current_lines:
        segments.append(DialogueSegment(current_speaker, " ".join(current_lines)))

    return segments
