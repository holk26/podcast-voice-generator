"""
SFX Engine — manages sound effects, ambience, and audio layering.

Features:
  - Categorized sound library (ambience, impacts, music)
  - Automatic ambience suggestion based on text keywords
  - Layer mixing with volume control and voice ducking
  - Per-line SFX cues from ScriptLine
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import numpy as np
from pydub import AudioSegment


class SFXLibrary:
    """Manages paths to sound effect files organized by category."""

    DEFAULT_CATEGORIES = {
        "ambience": [
            ("forest", ["bosque", "árbol", "árboles", "naturaleza", "campo"]),
            ("rain", ["lluvia", "lloviendo", "tormenta"]),
            ("city", ["ciudad", "calle", "tráfico", "urbano", "metro"]),
            ("office", ["oficina", "trabajo", "escritorio"]),
            ("cafe", ["cafetería", "café", "restaurante"]),
            ("beach", ["playa", "mar", "océano", "olas"]),
            ("wind", ["viento", "ventisca", "tormenta"]),
        ],
        "impacts": [
            ("applause", ["aplauso", "aplausos", "bravo"]),
            ("door", ["puerta", "golpe"]),
            ("phone", ["teléfono", "llamada", "móvil"]),
            ("notification", ["notificación", "mensaje", "alerta"]),
        ],
        "music": [
            ("intro_jingle", []),
            ("outro_theme", []),
            ("calm_ambient", ["meditación", "relax", "calma"]),
            ("motivational", ["motivación", "éxito", "logro"]),
        ]
    }

    def __init__(self, library_base_dir: str = "sfx_library"):
        self.base_dir = Path(library_base_dir)
        self._ensure_default_structure()

    def _ensure_default_structure(self) -> None:
        for category in ["ambience", "impacts", "music"]:
            (self.base_dir / category).mkdir(parents=True, exist_ok=True)

    def get_sound_path(self, category: str, name: str) -> Optional[Path]:
        """Return path to a sound file if it exists."""
        for ext in [".mp3", ".wav", ".flac", ".ogg"]:
            candidate = self.base_dir / category / f"{name}{ext}"
            if candidate.exists():
                return candidate
        return None

    def list_sounds(self, category: Optional[str] = None) -> List[str]:
        """List available sound names (without extension)."""
        names = []
        dirs = [self.base_dir / category] if category else [self.base_dir / c for c in ["ambience", "impacts", "music"]]
        for d in dirs:
            if d.exists():
                names.extend(p.stem for p in d.iterdir() if p.is_file())
        return sorted(set(names))

    def suggest_ambience(self, text: str) -> List[Tuple[str, str]]:
        """Suggest (category, sound_name) pairs based on keywords in text."""
        text_lower = text.lower()
        suggestions = []
        for category, sounds in self.DEFAULT_CATEGORIES.items():
            for sound_name, keywords in sounds:
                if category == "impacts":
                    continue  # Impacts are cue-based, not ambience
                if any(kw in text_lower for kw in keywords):
                    if self.get_sound_path(category, sound_name):
                        suggestions.append((category, sound_name))
        return suggestions


class SFXMixer:
    """Layer sound effects onto a main audio track using pydub."""

    def __init__(self, library: Optional[SFXLibrary] = None, sample_rate: int = 24000):
        self.library = library or SFXLibrary()
        self.sample_rate = sample_rate

    def load_sound(self, category: str, name: str) -> Optional[AudioSegment]:
        path = self.library.get_sound_path(category, name)
        if not path:
            return None
        try:
            seg = AudioSegment.from_file(path)
            return seg.set_frame_rate(self.sample_rate).set_channels(1)
        except Exception as e:
            print(f"[SFXMixer] Failed to load {path}: {e}")
            return None

    def apply_ambience(
        self,
        main_audio: AudioSegment,
        ambience_name: str,
        volume_db: float = -20.0
    ) -> AudioSegment:
        """Loop an ambience sound to match main_audio length and mix it."""
        ambience = self.load_sound("ambience", ambience_name)
        if ambience is None:
            print(f"[SFXMixer] Ambience '{ambience_name}' not found, skipping.")
            return main_audio

        # Loop ambience to cover main audio duration
        loops = []
        total_ms = 0
        while total_ms < len(main_audio):
            loops.append(ambience)
            total_ms += len(ambience)

        ambience_track = sum(loops[1:], loops[0])
        ambience_track = ambience_track[:len(main_audio)]

        # Adjust volume
        ambience_track = ambience_track + volume_db

        return main_audio.overlay(ambience_track)

    def apply_background_music(
        self,
        main_audio: AudioSegment,
        music_name: str,
        volume_db: float = -18.0,
        fade_in_ms: int = 2000,
        fade_out_ms: int = 3000
    ) -> AudioSegment:
        """Mix background music (looped if needed) with optional ducking."""
        music = self.load_sound("music", music_name)
        if music is None:
            print(f"[SFXMixer] Music '{music_name}' not found, skipping.")
            return main_audio

        # Loop music to cover main audio
        loops = []
        total_ms = 0
        while total_ms < len(main_audio):
            loops.append(music)
            total_ms += len(music)

        music_track = sum(loops[1:], loops[0])
        music_track = music_track[:len(main_audio)]

        # Fade in/out
        music_track = music_track.fade_in(fade_in_ms).fade_out(fade_out_ms)

        # Volume adjust
        music_track = music_track + volume_db

        return main_audio.overlay(music_track)

    def apply_impact(
        self,
        main_audio: AudioSegment,
        impact_name: str,
        position_ms: int = 0,
        volume_db: float = -6.0
    ) -> AudioSegment:
        """Place a one-shot impact sound at a specific position."""
        impact = self.load_sound("impacts", impact_name)
        if impact is None:
            return main_audio
        impact = impact + volume_db
        return main_audio.overlay(impact, position=position_ms)


class AutoAmbience:
    """Automatically suggest and apply ambience to a script or audio."""

    def __init__(self, sfx_library: Optional[SFXLibrary] = None):
        self.library = sfx_library or SFXLibrary()

    def suggest_for_text(self, text: str) -> List[Tuple[str, str]]:
        return self.library.suggest_ambience(text)

    def suggest_for_script(self, script_lines: list) -> Dict[str, List[str]]:
        """
        Return a dict of recommended ambience layers per scene/line.
        { "forest": [line_indices], "rain": [line_indices] }
        """
        result: Dict[str, List[int]] = {}
        for i, line in enumerate(script_lines):
            text = f"{line.text} {line.scene_mark or ''}"
            for category, sound_name in self.library.suggest_ambience(text):
                if category == "ambience":
                    result.setdefault(sound_name, []).append(i)
        return result
