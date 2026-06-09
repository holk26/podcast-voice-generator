"""
MediaPackage — Core data structures for the Media Automation Platform.

A MediaPackage is an episode-agnostic container that holds:
  - script.json: structured script with voice turns, SFX cues, scene marks
  - manifest.yaml: episode metadata (title, description, tags, cover art)
  - assets/: generated audio, images, music files

This architecture is intentionally output-format agnostic so that in the future
an ImageRenderer or VideoRenderer (Remotion) can consume the same package.
"""

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class ScriptLine:
    """A single line/turn in the script."""
    character: str           # Display name: "Homer", "Narrador", "Don Quijote"
    text: str                # Text to speak
    voice_id: str            # ID from VoiceCast: "homer", "dalia", "narrador"
    emotion: Optional[str] = None       # "happy", "sad", "angry", "calm", etc.
    sfx_cue: Optional[str] = None       # Sound effect or ambience to play
    sfx_volume: float = 0.2             # 0.0 to 1.0
    pause_before_ms: int = 300          # Silence before this line
    pause_after_ms: int = 500           # Silence after this line
    scene_mark: Optional[str] = None    # e.g. "Scene: Bosque"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScriptLine":
        return cls(**data)


@dataclass
class Manifest:
    """Episode metadata — used for RSS, publishing, and future video descriptions."""
    title: str
    description: str = ""
    summary: str = ""                    # Short summary for RSS <itunes:summary>
    author: str = "Media Automation Platform"
    category: str = "Technology"         # RSS category
    explicit: bool = False
    language: str = "es-ES"
    tags: List[str] = field(default_factory=list)
    cover_art: Optional[str] = None      # Path to cover image
    duration_seconds: Optional[int] = None
    publish_date: Optional[str] = None
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    content_type: str = "podcast"        # podcast, audiobook, meditation, motivation
    source_url: Optional[str] = None     # Original RSS URL, Gutenberg link, etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Manifest":
        return cls(**data)


@dataclass
class MediaPackage:
    """Container for a single episode's production assets."""
    package_id: str                      # e.g. "techpulse_2026-06-05_ep42"
    script: List[ScriptLine] = field(default_factory=list)
    manifest: Manifest = field(default_factory=lambda: Manifest(title="Untitled"))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Runtime paths (set when load/save is called)
    _base_path: Optional[Path] = field(default=None, repr=False)

    @property
    def assets_path(self) -> Path:
        if self._base_path is None:
            raise ValueError("MediaPackage has no base path. Call save() first.")
        return self._base_path / "assets"

    @property
    def script_path(self) -> Path:
        if self._base_path is None:
            raise ValueError("MediaPackage has no base path. Call save() first.")
        return self._base_path / "script.json"

    @property
    def manifest_path(self) -> Path:
        if self._base_path is None:
            raise ValueError("MediaPackage has no base path. Call save() first.")
        return self._base_path / "manifest.yaml"

    def add_line(self, line: ScriptLine) -> None:
        self.script.append(line)
        self._touch()

    def add_lines(self, lines: List[ScriptLine]) -> None:
        self.script.extend(lines)
        self._touch()

    def set_manifest(self, manifest: Manifest) -> None:
        self.manifest = manifest
        self._touch()

    def _touch(self) -> None:
        self.modified_at = datetime.now().isoformat()

    def save(self, base_dir: str) -> Path:
        """Save the full package to disk. Returns the package directory path."""
        base = Path(base_dir) / self.package_id
        base.mkdir(parents=True, exist_ok=True)
        self._base_path = base

        # Save script.json
        script_data = {
            "package_id": self.package_id,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "lines": [line.to_dict() for line in self.script]
        }
        with open(base / "script.json", "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        # Save manifest.yaml
        import yaml
        with open(base / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump(self.manifest.to_dict(), f, allow_unicode=True, sort_keys=False)

        # Ensure assets dir exists
        (base / "assets").mkdir(exist_ok=True)

        return base

    @classmethod
    def load(cls, package_dir: str) -> "MediaPackage":
        """Load a MediaPackage from a directory."""
        base = Path(package_dir)
        if not base.exists():
            raise FileNotFoundError(f"Package directory not found: {base}")

        # Load script.json
        script_path = base / "script.json"
        script = []
        if script_path.exists():
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            for line_data in script_data.get("lines", []):
                script.append(ScriptLine.from_dict(line_data))
            package_id = script_data.get("package_id", base.name)
            created_at = script_data.get("created_at", datetime.now().isoformat())
            modified_at = script_data.get("modified_at", datetime.now().isoformat())
        else:
            package_id = base.name
            created_at = modified_at = datetime.now().isoformat()

        # Load manifest.yaml
        manifest_path = base / "manifest.yaml"
        if manifest_path.exists():
            import yaml
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = yaml.safe_load(f)
            manifest = Manifest.from_dict(manifest_data or {})
        else:
            manifest = Manifest(title=base.name)

        pkg = cls(
            package_id=package_id,
            script=script,
            manifest=manifest,
            created_at=created_at,
            modified_at=modified_at
        )
        pkg._base_path = base
        return pkg

    def copy_asset(self, source_path: str, asset_name: Optional[str] = None) -> Path:
        """Copy an external file into the package assets folder."""
        self.assets_path.mkdir(parents=True, exist_ok=True)
        src = Path(source_path)
        name = asset_name or src.name
        dest = self.assets_path / name
        shutil.copy2(src, dest)
        return dest

    def list_assets(self) -> List[Path]:
        """List all files in the assets folder."""
        if not self.assets_path.exists():
            return []
        return sorted(self.assets_path.iterdir())

    def get_asset(self, name: str) -> Optional[Path]:
        """Get path to a specific asset."""
        path = self.assets_path / name
        return path if path.exists() else None
