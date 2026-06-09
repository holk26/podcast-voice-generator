"""
Voice Cast Manager — manages the pool of available voices and character-to-voice mapping.

Provides a central registry for all voices (cloned XTTS, Edge-TTS pretrained, etc.)
and maps fictional characters to specific voices for dramatized productions.
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path

import yaml

from core.project import Voice


class VoiceProfile:
    """Static configuration for a voice."""

    def __init__(
        self,
        voice_id: str,
        name: str,
        engine: str,           # "xtts", "edge_tts", "bark", "zonos", etc.
        language: str,
        speed: float = 1.0,
        speaker_id: Optional[str] = None,      # For pretrained models (Edge-TTS speaker)
        reference_path: Optional[str] = None,   # For cloned models (XTTS reference WAV)
        description: str = "",
        gender: str = "",
        locale: str = ""
    ):
        self.voice_id = voice_id
        self.name = name
        self.engine = engine
        self.language = language
        self.speed = speed
        self.speaker_id = speaker_id
        self.reference_path = reference_path
        self.description = description
        self.gender = gender
        self.locale = locale

    def to_voice(self) -> Voice:
        """Convert to a core.project.Voice ready for TTS engines."""
        voice_type = "cloned" if self.reference_path else "pretrained"
        return Voice(
            id=self.voice_id,
            name=self.name,
            type=voice_type,
            engine=self.engine,
            language=self.language,
            speed=self.speed,
            reference_path=self.reference_path,
            speaker_id=self.speaker_id
        )

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceProfile":
        return cls(**data)

    def to_dict(self) -> dict:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "engine": self.engine,
            "language": self.language,
            "speed": self.speed,
            "speaker_id": self.speaker_id,
            "reference_path": self.reference_path,
            "description": self.description,
            "gender": self.gender,
            "locale": self.locale,
        }


class VoiceCastManager:
    """Registry of all available voices and character assignments."""

    def __init__(
        self,
        profiles_dir: str = "cast/voice_profiles",
        character_map_path: str = "cast/character_voice_map.json"
    ):
        self.profiles_dir = Path(profiles_dir)
        self.character_map_path = Path(character_map_path)
        self._profiles: Dict[str, VoiceProfile] = {}
        self._character_map: Dict[str, str] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load voice profiles and character map from disk."""
        self._load_profiles()
        self._load_character_map()

    def _load_profiles(self) -> None:
        if not self.profiles_dir.exists():
            return
        for yaml_file in sorted(self.profiles_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data:
                    profile = VoiceProfile.from_dict(data)
                    self._profiles[profile.voice_id] = profile
            except Exception as e:
                print(f"[VoiceCast] Warning: failed to load {yaml_file}: {e}")

    def _load_character_map(self) -> None:
        if self.character_map_path.exists():
            try:
                with open(self.character_map_path, "r", encoding="utf-8") as f:
                    self._character_map = json.load(f)
            except Exception as e:
                print(f"[VoiceCast] Warning: failed to load character map: {e}")
                self._character_map = {}

    def _save_character_map(self) -> None:
        self.character_map_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.character_map_path, "w", encoding="utf-8") as f:
            json.dump(self._character_map, f, indent=2, ensure_ascii=False)

    # ── Voice Registry ────────────────────────────────────────────────

    def register_profile(self, profile: VoiceProfile) -> None:
        """Register a new voice profile and save its YAML file."""
        self._profiles[profile.voice_id] = profile
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = self.profiles_dir / f"{profile.voice_id}.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(profile.to_dict(), f, allow_unicode=True, sort_keys=False)

    def unregister_profile(self, voice_id: str) -> bool:
        """Remove a voice profile."""
        if voice_id not in self._profiles:
            return False
        del self._profiles[voice_id]
        yaml_path = self.profiles_dir / f"{voice_id}.yaml"
        if yaml_path.exists():
            yaml_path.unlink()
        return True

    def get_profile(self, voice_id: str) -> Optional[VoiceProfile]:
        return self._profiles.get(voice_id)

    def get_voice(self, voice_id: str) -> Optional[Voice]:
        """Get a core.project.Voice ready for TTS engines."""
        profile = self._profiles.get(voice_id)
        return profile.to_voice() if profile else None

    def list_profiles(self) -> List[VoiceProfile]:
        return list(self._profiles.values())

    def list_voice_ids(self) -> List[str]:
        return sorted(self._profiles.keys())

    # ── Character Mapping ─────────────────────────────────────────────

    def assign_character(self, character_name: str, voice_id: str) -> None:
        """Map a character name to a voice ID."""
        if voice_id not in self._profiles:
            raise ValueError(f"Voice ID '{voice_id}' is not registered.")
        self._character_map[character_name] = voice_id
        self._save_character_map()

    def unassign_character(self, character_name: str) -> bool:
        if character_name in self._character_map:
            del self._character_map[character_name]
            self._save_character_map()
            return True
        return False

    def get_character_voice(self, character_name: str) -> Optional[VoiceProfile]:
        """Get the voice profile assigned to a character."""
        voice_id = self._character_map.get(character_name)
        return self._profiles.get(voice_id) if voice_id else None

    def get_character_voice_id(self, character_name: str) -> Optional[str]:
        return self._character_map.get(character_name)

    def list_characters(self) -> Dict[str, str]:
        """Return all character → voice_id mappings."""
        return dict(self._character_map)

    def resolve_voice_for_line(self, character: str, fallback_voice_id: str = "homer") -> VoiceProfile:
        """Given a character name, return their assigned voice or fallback."""
        profile = self.get_character_voice(character)
        if profile:
            return profile
        # Try direct voice_id lookup (character might already BE a voice_id)
        profile = self._profiles.get(character)
        if profile:
            return profile
        # Fallback
        return self._profiles.get(fallback_voice_id) or list(self._profiles.values())[0]

    # ── Batch Operations ──────────────────────────────────────────────

    def save_all(self) -> None:
        """Re-save all profiles and character map to disk."""
        for profile in self._profiles.values():
            yaml_path = self.profiles_dir / f"{profile.voice_id}.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(profile.to_dict(), f, allow_unicode=True, sort_keys=False)
        self._save_character_map()
