import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Voice:
    id: str
    name: str
    type: str  # "cloned" or "pretrained"
    engine: str
    language: str
    speed: float = 1.0
    reference_path: Optional[str] = None
    speaker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Voice":
        return cls(**data)


@dataclass
class Section:
    id: str
    title: str
    text: str
    voice_id: str
    speed: float = 1.0
    pause_after_ms: int = 0
    music: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Section":
        return cls(**data)


@dataclass
class ProjectSettings:
    output_format: str = "mp3"
    sample_rate: int = 24000
    bitrate: str = "192k"
    normalize_audio: bool = True
    fade_in_ms: int = 500
    fade_out_ms: int = 1000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectSettings":
        return cls(**data)


@dataclass
class Project:
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    voices: List[Voice] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    generation_state: Dict[str, Any] = field(default_factory=lambda: {
        "status": "none",
        "completed_sections": [],
        "output_files": {}
    })

    _section_counter: int = field(default=0, repr=False)

    def add_section(self, title: str, text: str, voice_id: str, speed: float = 1.0, pause_after_ms: int = 0, music: Optional[Dict] = None) -> Section:
        self._section_counter += 1
        section = Section(
            id=f"sec_{self._section_counter:03d}",
            title=title,
            text=text,
            voice_id=voice_id,
            speed=speed,
            pause_after_ms=pause_after_ms,
            music=music
        )
        self.sections.append(section)
        self._update_modified()
        return section

    def add_voice(self, voice: Voice) -> None:
        self.voices.append(voice)
        self._update_modified()

    def get_voice(self, voice_id: str) -> Optional[Voice]:
        for v in self.voices:
            if v.id == voice_id:
                return v
        return None

    def remove_section(self, section_id: str) -> bool:
        for i, s in enumerate(self.sections):
            if s.id == section_id:
                self.sections.pop(i)
                self._update_modified()
                return True
        return False

    def _update_modified(self) -> None:
        self.modified_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": {
                "name": self.name,
                "created_at": self.created_at,
                "modified_at": self.modified_at,
                "settings": self.settings.to_dict()
            },
            "voices": [v.to_dict() for v in self.voices],
            "sections": [s.to_dict() for s in self.sections],
            "generation_state": self.generation_state
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        self._update_modified()

    @classmethod
    def load(cls, path: str) -> "Project":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        proj_data = data.get("project", {})
        project = cls(
            name=proj_data.get("name", "Untitled"),
            created_at=proj_data.get("created_at", datetime.now().isoformat()),
            modified_at=proj_data.get("modified_at", datetime.now().isoformat()),
            settings=ProjectSettings.from_dict(proj_data.get("settings", {})),
            generation_state=data.get("generation_state", {})
        )
        for v_data in data.get("voices", []):
            project.voices.append(Voice.from_dict(v_data))
        max_counter = 0
        for s_data in data.get("sections", []):
            section = Section.from_dict(s_data)
            project.sections.append(section)
            try:
                num = int(section.id.replace("sec_", ""))
                max_counter = max(max_counter, num)
            except ValueError:
                pass
        project._section_counter = max_counter
        return project
