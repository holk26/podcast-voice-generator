# Podcast Voice Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular desktop PyQt6 application that generates podcast/meditation/story audio using XTTS v2 and Bark TTS engines with full GPU optimization.

**Architecture:** Four-layer modular design: `gui` (PyQt6 widgets), `core` (TTS engines, project model, batch generation), `audio` (mixing, normalization, export), `utils` (GPU detection, config, file helpers). Each layer only depends on layers below it.

**Tech Stack:** Python 3.10+, PyQt6, Coqui TTS (XTTS v2), Bark, torch/torchaudio, pydub, soundfile, pynvml, pytest

---

## File Structure

```
podcast-voice-generator/
├── main.py
├── config.yaml
├── requirements.txt
├── gui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── project_panel.py
│   ├── script_editor.py
│   ├── voice_manager.py
│   ├── generation_panel.py
│   └── audio_player.py
├── core/
│   ├── __init__.py
│   ├── tts_engine.py
│   ├── xtts_engine.py
│   ├── bark_engine.py
│   ├── project.py
│   ├── audio_pipeline.py
│   └── batch_generator.py
├── audio/
│   ├── __init__.py
│   ├── mixer.py
│   ├── normalizer.py
│   ├── exporter.py
│   └── effects.py
├── utils/
│   ├── __init__.py
│   ├── gpu_utils.py
│   ├── config_manager.py
│   └── file_utils.py
└── tests/
    ├── __init__.py
    ├── test_gpu_utils.py
    ├── test_xtts_engine.py
    ├── test_project.py
    ├── test_audio_pipeline.py
    └── test_batch_generator.py
```

---

## Phase 1: Foundation (Config, Utils, Data Model)

### Task 1: Project Dependencies and Config

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `utils/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```txt
PyQt6>=6.5.0
TTS>=0.22.0
torch>=2.0.0
torchaudio>=2.0.0
pydub>=0.25.1
soundfile>=0.12.1
pynvml>=11.5.0
pytest>=7.4.0
pyyaml>=6.0
```

- [ ] **Step 2: Create config.yaml**

```yaml
app:
  name: "Podcast Voice Generator"
  version: "1.0.0"

gpu:
  device: "auto"
  use_fp16: true
  max_vram_gb: 22
  keep_model_loaded: true

xtts:
  model: "tts_models/multilingual/multi-dataset/xtts_v2"
  gpu_layers: "all"
  languages:
    - "es"
    - "en"
    - "fr"
    - "de"
    - "it"
    - "pt"
    - "pl"
    - "tr"
    - "ru"
    - "nl"
    - "cs"
    - "ar"
    - "zh"
    - "ja"
    - "hu"
    - "ko"

bark:
  enabled: true
  model_size: "large"
  fallback_if_oom: "xtts"

paths:
  voices_dir: "voices"
  clones_dir: "voices/clones"
  pretrained_dir: "voices/pretrained"
  output_dir: "output"
  projects_dir: "projects"
  music_dir: "music"

audio:
  default_format: "mp3"
  default_sample_rate: 24000
  default_bitrate: "192k"
  normalize_default: true
  default_fade_in_ms: 500
  default_fade_out_ms: 1000
```

- [ ] **Step 3: Create empty __init__.py files**

```bash
touch utils/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt config.yaml utils/__init__.py
git commit -m "chore: add dependencies and config"
```

---

### Task 2: Config Manager

**Files:**
- Create: `utils/config_manager.py`
- Create: `tests/test_config_manager.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import os
import tempfile
import yaml
from utils.config_manager import ConfigManager


def test_load_default_config():
    cm = ConfigManager("config.yaml")
    assert cm.get("app.name") == "Podcast Voice Generator"
    assert cm.get("gpu.use_fp16") is True


def test_load_missing_file_uses_defaults():
    cm = ConfigManager("nonexistent.yaml")
    assert cm.get("app.name") == "Podcast Voice Generator"


def test_nested_get():
    cm = ConfigManager("config.yaml")
    assert cm.get("xtts.model") == "tts_models/multilingual/multi-dataset/xtts_v2"


def test_get_with_default():
    cm = ConfigManager("config.yaml")
    assert cm.get("nonexistent.key", "default") == "default"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_config_manager.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement ConfigManager**

```python
import os
from typing import Any, Optional
import yaml


DEFAULT_CONFIG = {
    "app": {
        "name": "Podcast Voice Generator",
        "version": "1.0.0"
    },
    "gpu": {
        "device": "auto",
        "use_fp16": True,
        "max_vram_gb": 22,
        "keep_model_loaded": True
    },
    "xtts": {
        "model": "tts_models/multilingual/multi-dataset/xtts_v2",
        "gpu_layers": "all",
        "languages": ["es", "en", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hu", "ko"]
    },
    "bark": {
        "enabled": True,
        "model_size": "large",
        "fallback_if_oom": "xtts"
    },
    "paths": {
        "voices_dir": "voices",
        "clones_dir": "voices/clones",
        "pretrained_dir": "voices/pretrained",
        "output_dir": "output",
        "projects_dir": "projects",
        "music_dir": "music"
    },
    "audio": {
        "default_format": "mp3",
        "default_sample_rate": 24000,
        "default_bitrate": "192k",
        "normalize_default": True,
        "default_fade_in_ms": 500,
        "default_fade_out_ms": 1000
    }
}


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self._config = DEFAULT_CONFIG.copy()
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self._merge(self._config, file_config)

    def _merge(self, base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge(base[key], value)
            else:
                base[key] = value

    def get(self, key_path: str, default: Optional[Any] = None) -> Any:
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_all(self) -> dict:
        return self._config.copy()
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_config_manager.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add utils/config_manager.py tests/test_config_manager.py
git commit -m "feat: add ConfigManager with nested key access"
```

---

### Task 3: File Utils

**Files:**
- Create: `utils/file_utils.py`
- Create: `tests/test_file_utils.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import os
import tempfile
from utils.file_utils import ensure_dir, get_project_path, sanitize_filename


def test_ensure_dir_creates_directory():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "nested", "dir")
        ensure_dir(path)
        assert os.path.isdir(path)


def test_sanitize_filename():
    assert sanitize_filename("Hello World!") == "Hello_World"
    assert sanitize_filename("file/name\\test") == "file_name_test"
    assert sanitize_filename("a" * 300) == "a" * 100


def test_get_project_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = get_project_path(tmp, "My Podcast #1")
        assert path.startswith(tmp)
        assert "My_Podcast_1" in path
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_file_utils.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement file_utils.py**

```python
import os
import re


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def sanitize_filename(name: str, max_length: int = 100) -> str:
    sanitized = re.sub(r'[^\w\s-]', '_', name).strip()
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    return sanitized[:max_length]


def get_project_path(base_dir: str, project_name: str) -> str:
    safe_name = sanitize_filename(project_name)
    return os.path.join(base_dir, safe_name)


def validate_audio_file(path: str) -> bool:
    if not os.path.exists(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def get_file_size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 * 1024)
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_file_utils.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add utils/file_utils.py tests/test_file_utils.py
git commit -m "feat: add file utils for directory creation and filename sanitization"
```

---

### Task 4: GPU Utils

**Files:**
- Create: `utils/gpu_utils.py`
- Create: `tests/test_gpu_utils.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
from unittest.mock import patch, MagicMock
from utils.gpu_utils import estimate_vram_needed, format_vram


def test_estimate_vram_xtts():
    assert estimate_vram_needed("xtts", "default") == 4.0


def test_estimate_vram_bark_small():
    assert estimate_vram_needed("bark", "small") == 4.0


def test_estimate_vram_bark_large():
    assert estimate_vram_needed("bark", "large") == 10.0


def test_format_vram():
    assert format_vram(4.0) == "4.00 GB"
    assert format_vram(0.5) == "512.00 MB"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_gpu_utils.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement gpu_utils.py**

```python
import torch
from typing import Optional, Dict, List


def get_gpu_info() -> List[Dict]:
    gpus = []
    if not torch.cuda.is_available():
        return gpus
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        gpus.append({
            "id": i,
            "name": props.name,
            "total_memory_gb": props.total_memory / (1024 ** 3),
            "compute_capability": f"{props.major}.{props.minor}"
        })
    return gpus


def get_vram_info(device_id: int = 0) -> Dict:
    if not torch.cuda.is_available():
        return {"available": False}
    try:
        torch.cuda.set_device(device_id)
        total = torch.cuda.get_device_properties(device_id).total_memory / (1024 ** 3)
        reserved = torch.cuda.memory_reserved(device_id) / (1024 ** 3)
        allocated = torch.cuda.memory_allocated(device_id) / (1024 ** 3)
        free = total - allocated
        return {
            "available": True,
            "device_id": device_id,
            "total_gb": total,
            "allocated_gb": allocated,
            "reserved_gb": reserved,
            "free_gb": free,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def estimate_vram_needed(engine: str, model_size: str = "default") -> float:
    estimates = {
        ("xtts", "default"): 4.0,
        ("bark", "small"): 4.0,
        ("bark", "medium"): 7.0,
        ("bark", "large"): 10.0,
    }
    return estimates.get((engine, model_size), 4.0)


def can_fit_model(device_id: int, engine: str, model_size: str = "default", safety_margin_gb: float = 2.0) -> bool:
    vram = get_vram_info(device_id)
    if not vram.get("available"):
        return False
    needed = estimate_vram_needed(engine, model_size) + safety_margin_gb
    return vram["free_gb"] >= needed


def select_best_device() -> str:
    if not torch.cuda.is_available():
        return "cpu"
    best_id = 0
    best_free = -1
    for i in range(torch.cuda.device_count()):
        vram = get_vram_info(i)
        if vram.get("available") and vram["free_gb"] > best_free:
            best_free = vram["free_gb"]
            best_id = i
    return f"cuda:{best_id}"


def clear_gpu_cache() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def format_vram(gb: float) -> str:
    if gb >= 1.0:
        return f"{gb:.2f} GB"
    return f"{gb * 1024:.2f} MB"
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_gpu_utils.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add utils/gpu_utils.py tests/test_gpu_utils.py
git commit -m "feat: add GPU detection and VRAM estimation utilities"
```

---

### Task 5: Project Data Model

**Files:**
- Create: `core/__init__.py`
- Create: `core/project.py`
- Create: `tests/test_project.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import json
import tempfile
import os
from core.project import Project, ProjectSettings, Section, Voice


def test_create_project():
    p = Project(name="Test Podcast")
    assert p.name == "Test Podcast"
    assert len(p.sections) == 0
    assert len(p.voices) == 0


def test_add_section():
    p = Project(name="Test")
    p.add_section("Intro", "Hello world", "voz1")
    assert len(p.sections) == 1
    assert p.sections[0].text == "Hello world"


def test_add_voice():
    p = Project(name="Test")
    v = Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es")
    p.add_voice(v)
    assert len(p.voices) == 1


def test_save_and_load_project():
    with tempfile.TemporaryDirectory() as tmp:
        p = Project(name="Save Test")
        p.add_section("Intro", "Hello", "v1")
        v = Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es")
        p.add_voice(v)
        path = os.path.join(tmp, "project.json")
        p.save(path)
        assert os.path.exists(path)
        loaded = Project.load(path)
        assert loaded.name == "Save Test"
        assert len(loaded.sections) == 1
        assert loaded.sections[0].text == "Hello"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_project.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement project.py**

```python
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
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_project.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add core/__init__.py core/project.py tests/test_project.py
git commit -m "feat: add Project data model with save/load"
```

---

## Phase 2: TTS Engines

### Task 6: TTS Base Interface

**Files:**
- Create: `core/tts_engine.py`
- Create: `tests/test_tts_engine.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
from core.tts_engine import TTSBase
from core.project import Voice


def test_tts_base_is_abstract():
    with pytest.raises(TypeError):
        TTSBase()


def test_dummy_engine_implements_interface():
    class DummyEngine(TTSBase):
        def synthesize(self, text, voice, output_path):
            return output_path
        def clone_voice(self, reference_path, name):
            return "voice_id"
        def get_speakers(self):
            return ["speaker1"]
        def is_loaded(self):
            return True
        def load(self):
            pass
        def unload(self):
            pass

    engine = DummyEngine()
    assert engine.is_loaded() is True
    assert engine.get_speakers() == ["speaker1"]
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_tts_engine.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement tts_engine.py**

```python
from abc import ABC, abstractmethod
from typing import List
from core.project import Voice


class TTSBase(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        pass

    @abstractmethod
    def clone_voice(self, reference_path: str, name: str) -> str:
        pass

    @abstractmethod
    def get_speakers(self) -> List[str]:
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        pass

    @abstractmethod
    def load(self) -> None:
        pass

    @abstractmethod
    def unload(self) -> None:
        pass
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_tts_engine.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/tts_engine.py tests/test_tts_engine.py
git commit -m "feat: add abstract TTSBase interface"
```

---

### Task 7: XTTS Engine

**Files:**
- Create: `core/xtts_engine.py`
- Create: `tests/test_xtts_engine.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
from unittest.mock import patch, MagicMock
from core.xtts_engine import XTTSEngine
from core.project import Voice


def test_xtts_engine_properties():
    with patch("core.xtts_engine.TTS") as mock_tts_class:
        mock_tts = MagicMock()
        mock_tts_class.return_value = mock_tts
        engine = XTTSEngine(device="cpu")
        assert engine.name == "xtts"
        assert engine.is_loaded() is False


def test_xtts_get_speakers_before_load():
    with patch("core.xtts_engine.TTS") as mock_tts_class:
        mock_tts = MagicMock()
        mock_tts_class.return_value = mock_tts
        engine = XTTSEngine(device="cpu")
        assert engine.get_speakers() == []
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_xtts_engine.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement xtts_engine.py**

```python
import os
import torch
from typing import List
from TTS.api import TTS
from core.tts_engine import TTSBase
from core.project import Voice
from utils.gpu_utils import select_best_device, clear_gpu_cache


class XTTSEngine(TTSBase):
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2", device: str = "auto"):
        self.model_name = model_name
        self.device = device if device != "auto" else select_best_device()
        self._model = None
        self.name = "xtts"
        self._speakers = []

    def load(self) -> None:
        if self._model is not None:
            return
        self._model = TTS(self.model_name).to(self.device)
        if hasattr(self._model, "speakers") and self._model.speakers:
            self._speakers = list(self._model.speakers)

    def unload(self) -> None:
        self._model = None
        clear_gpu_cache()

    def is_loaded(self) -> bool:
        return self._model is not None

    def get_speakers(self) -> List[str]:
        if not self.is_loaded():
            return []
        return self._speakers

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self.is_loaded():
            self.load()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        if voice.type == "cloned" and voice.reference_path:
            self._model.tts_to_file(
                text=text,
                speaker_wav=voice.reference_path,
                language=voice.language,
                file_path=output_path,
                speed=voice.speed
            )
        else:
            speaker = voice.speaker_id if voice.speaker_id else (self._speakers[0] if self._speakers else None)
            self._model.tts_to_file(
                text=text,
                speaker=speaker,
                language=voice.language,
                file_path=output_path,
                speed=voice.speed
            )
        return output_path

    def clone_voice(self, reference_path: str, name: str) -> str:
        """XTTS cloning is done on-the-fly via reference_path during synthesis.
        This method validates the reference and returns a voice identifier."""
        if not os.path.exists(reference_path):
            raise FileNotFoundError(f"Reference audio not found: {reference_path}")
        return f"xtts_clone_{name}"
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_xtts_engine.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/xtts_engine.py tests/test_xtts_engine.py
git commit -m "feat: add XTTS v2 engine implementation"
```

---

### Task 8: Bark Engine

**Files:**
- Create: `core/bark_engine.py`
- Create: `tests/test_bark_engine.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
from unittest.mock import patch, MagicMock
from core.bark_engine import BarkEngine


def test_bark_engine_properties():
    engine = BarkEngine(device="cpu", model_size="small")
    assert engine.name == "bark"
    assert engine.model_size == "small"
    assert engine.is_loaded() is False


def test_bark_get_speakers():
    engine = BarkEngine(device="cpu")
    speakers = engine.get_speakers()
    assert isinstance(speakers, list)
    assert len(speakers) > 0
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_bark_engine.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement bark_engine.py**

```python
import os
from typing import List
from core.tts_engine import TTSBase
from core.project import Voice
from utils.gpu_utils import select_best_device, clear_gpu_cache


class BarkEngine(TTSBase):
    HISTORY_PROMPTS = [
        "v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2", "v2/en_speaker_3",
        "v2/en_speaker_4", "v2/en_speaker_5", "v2/en_speaker_6", "v2/en_speaker_7",
        "v2/en_speaker_8", "v2/en_speaker_9",
        "v2/es_speaker_0", "v2/es_speaker_1", "v2/es_speaker_2", "v2/es_speaker_3",
        "v2/es_speaker_4", "v2/es_speaker_5", "v2/es_speaker_6", "v2/es_speaker_7",
        "v2/es_speaker_8", "v2/es_speaker_9",
    ]

    def __init__(self, device: str = "auto", model_size: str = "small"):
        self.device = device if device != "auto" else select_best_device()
        self.model_size = model_size
        self.name = "bark"
        self._model = None
        self._processor = None

    def load(self) -> None:
        if self.is_loaded():
            return
        try:
            from transformers import AutoProcessor, BarkModel
            model_name = f"suno/bark-{self.model_size}"
            self._processor = AutoProcessor.from_pretrained(model_name)
            self._model = BarkModel.from_pretrained(model_name)
            self._model = self._model.to(self.device)
        except ImportError:
            raise ImportError("Bark requires 'transformers' and 'accelerate'. Install: pip install transformers accelerate")

    def unload(self) -> None:
        self._model = None
        self._processor = None
        clear_gpu_cache()

    def is_loaded(self) -> bool:
        return self._model is not None

    def get_speakers(self) -> List[str]:
        return self.HISTORY_PROMPTS

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        if not self.is_loaded():
            self.load()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        speaker = voice.speaker_id if voice.speaker_id else self.HISTORY_PROMPTS[0]
        inputs = self._processor(text, voice_preset=speaker)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        import torch
        with torch.no_grad():
            audio_array = self._model.generate(**inputs)
            audio_array = audio_array.cpu().numpy().squeeze()
        import scipy.io.wavfile as wavfile
        wavfile.write(output_path, rate=self._model.generation_config.sample_rate, data=audio_array)
        return output_path

    def clone_voice(self, reference_path: str, name: str) -> str:
        raise NotImplementedError("Bark voice cloning is limited. Use XTTS for voice cloning.")
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_bark_engine.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/bark_engine.py tests/test_bark_engine.py
git commit -m "feat: add Bark TTS engine implementation"
```

---

## Phase 3: Audio Processing

### Task 9: Audio Effects

**Files:**
- Create: `audio/__init__.py`
- Create: `audio/effects.py`
- Create: `tests/test_effects.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import numpy as np
from audio.effects import fade_in, fade_out, add_silence


def test_fade_in_shape():
    audio = np.ones(24000, dtype=np.float32)
    faded = fade_in(audio, sample_rate=24000, duration_ms=500)
    assert faded.shape == audio.shape
    assert faded[0] < faded[-1]


def test_fade_out_shape():
    audio = np.ones(24000, dtype=np.float32)
    faded = fade_out(audio, sample_rate=24000, duration_ms=500)
    assert faded.shape == audio.shape
    assert faded[-1] < faded[0]


def test_add_silence():
    audio = np.ones(24000, dtype=np.float32)
    result = add_silence(audio, sample_rate=24000, duration_ms=1000)
    assert len(result) == 24000 + 24000
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_effects.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement effects.py**

```python
import numpy as np


def fade_in(audio: np.ndarray, sample_rate: int, duration_ms: int) -> np.ndarray:
    samples = int(sample_rate * duration_ms / 1000)
    if samples <= 0:
        return audio
    if samples > len(audio):
        samples = len(audio)
    fade_curve = np.linspace(0.0, 1.0, samples)
    result = audio.copy()
    result[:samples] *= fade_curve
    return result


def fade_out(audio: np.ndarray, sample_rate: int, duration_ms: int) -> np.ndarray:
    samples = int(sample_rate * duration_ms / 1000)
    if samples <= 0:
        return audio
    if samples > len(audio):
        samples = len(audio)
    fade_curve = np.linspace(1.0, 0.0, samples)
    result = audio.copy()
    result[-samples:] *= fade_curve
    return result


def add_silence(audio: np.ndarray, sample_rate: int, duration_ms: int) -> np.ndarray:
    silence_samples = int(sample_rate * duration_ms / 1000)
    silence = np.zeros(silence_samples, dtype=audio.dtype)
    return np.concatenate([audio, silence])
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_effects.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add audio/__init__.py audio/effects.py tests/test_effects.py
git commit -m "feat: add audio effects (fade in/out, silence)"
```

---

### Task 10: Normalizer

**Files:**
- Create: `audio/normalizer.py`
- Create: `tests/test_normalizer.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import numpy as np
from audio.normalizer import normalize_peak, normalize_lufs


def test_normalize_peak():
    audio = np.array([0.5, 1.0, 0.5], dtype=np.float32)
    normalized = normalize_peak(audio, target_db=-6.0)
    peak = np.max(np.abs(normalized))
    assert abs(peak - 0.5) < 0.01


def test_normalize_peak_empty():
    audio = np.array([], dtype=np.float32)
    result = normalize_peak(audio, target_db=-6.0)
    assert len(result) == 0
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_normalizer.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement normalizer.py**

```python
import numpy as np


def db_to_linear(db: float) -> float:
    return 10 ** (db / 20.0)


def linear_to_db(value: float) -> float:
    return 20 * np.log10(max(abs(value), 1e-10))


def normalize_peak(audio: np.ndarray, target_db: float = -1.0) -> np.ndarray:
    if len(audio) == 0:
        return audio
    peak = np.max(np.abs(audio))
    if peak == 0:
        return audio
    target_peak = db_to_linear(target_db)
    gain = target_peak / peak
    return audio * gain


def normalize_lufs(audio: np.ndarray, sample_rate: int, target_lufs: float = -14.0) -> np.ndarray:
    """Simple RMS-based approximation of LUFS normalization."""
    if len(audio) == 0:
        return audio
    rms = np.sqrt(np.mean(audio ** 2))
    if rms == 0:
        return audio
    target_rms = db_to_linear(target_lufs)
    gain = target_rms / rms
    return np.clip(audio * gain, -1.0, 1.0)
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_normalizer.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add audio/normalizer.py tests/test_normalizer.py
git commit -m "feat: add audio peak normalization"
```

---

### Task 11: Mixer

**Files:**
- Create: `audio/mixer.py`
- Create: `tests/test_mixer.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import numpy as np
from audio.mixer import mix_with_background, apply_ducking


def test_mix_with_background():
    voice = np.ones(24000, dtype=np.float32) * 0.5
    bg = np.ones(24000, dtype=np.float32) * 0.3
    mixed = mix_with_background(voice, bg, bg_volume_db=-10)
    assert len(mixed) == len(voice)
    assert np.max(np.abs(mixed)) <= 1.0


def test_apply_ducking():
    bg = np.ones(24000, dtype=np.float32) * 0.5
    ducked = apply_ducking(bg, duck_db=12)
    assert np.max(np.abs(ducked)) < 0.5
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_mixer.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement mixer.py**

```python
import numpy as np
from audio.normalizer import db_to_linear


def mix_with_background(voice: np.ndarray, background: np.ndarray, bg_volume_db: float = -18.0) -> np.ndarray:
    bg_gain = db_to_linear(bg_volume_db)
    bg_adjusted = background * bg_gain
    if len(bg_adjusted) < len(voice):
        repeats = int(np.ceil(len(voice) / len(bg_adjusted)))
        bg_adjusted = np.tile(bg_adjusted, repeats)
    bg_adjusted = bg_adjusted[:len(voice)]
    mixed = voice + bg_adjusted
    return np.clip(mixed, -1.0, 1.0)


def apply_ducking(background: np.ndarray, duck_db: float = 12.0) -> np.ndarray:
    duck_gain = db_to_linear(-duck_db)
    return background * duck_gain
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_mixer.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add audio/mixer.py tests/test_mixer.py
git commit -m "feat: add audio mixer with background and ducking"
```

---

### Task 12: Exporter

**Files:**
- Create: `audio/exporter.py`
- Create: `tests/test_exporter.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import numpy as np
import tempfile
import os
from audio.exporter import export_audio


def test_export_wav():
    audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 24000)).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.wav")
        export_audio(audio, path, sample_rate=24000)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_exporter.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement exporter.py**

```python
import os
import numpy as np
import soundfile as sf
from pydub import AudioSegment


def export_audio(audio: np.ndarray, output_path: str, sample_rate: int = 24000) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".wav":
        sf.write(output_path, audio, sample_rate, subtype="PCM_16")
    elif ext == ".mp3":
        temp_wav = output_path.replace(".mp3", "_temp.wav")
        sf.write(temp_wav, audio, sample_rate, subtype="PCM_16")
        segment = AudioSegment.from_wav(temp_wav)
        segment.export(output_path, format="mp3", bitrate="192k")
        os.remove(temp_wav)
    elif ext == ".flac":
        sf.write(output_path, audio, sample_rate)
    else:
        sf.write(output_path, audio, sample_rate, subtype="PCM_16")
    return output_path
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_exporter.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add audio/exporter.py tests/test_exporter.py
git commit -m "feat: add audio exporter (WAV/MP3/FLAC)"
```

---

## Phase 4: Pipeline and Batch Generation

### Task 13: Audio Pipeline

**Files:**
- Create: `core/audio_pipeline.py`
- Create: `tests/test_audio_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
import numpy as np
import tempfile
import os
from unittest.mock import patch, MagicMock
from core.audio_pipeline import AudioPipeline
from core.project import Project, Section, Voice


def test_pipeline_init():
    pipeline = AudioPipeline(output_dir="output")
    assert pipeline.output_dir == "output"


def test_pipeline_generate_section():
    with tempfile.TemporaryDirectory() as tmp:
        pipeline = AudioPipeline(output_dir=tmp)
        project = Project(name="Test")
        v = Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es")
        project.add_voice(v)
        project.add_section("Intro", "Hello", "v1")
        
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = os.path.join(tmp, "test.wav")
        engines = {"xtts": mock_engine}
        
        with patch.object(pipeline, '_load_or_get_engine', return_value=mock_engine):
            with patch('core.audio_pipeline.sf.read', return_value=(np.ones(24000, dtype=np.float32), 24000)):
                result = pipeline.generate_section(project, project.sections[0], engines)
        assert result is not None
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_audio_pipeline.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement audio_pipeline.py**

```python
import os
import numpy as np
import soundfile as sf
from typing import Dict, Optional
from core.project import Project, Section, Voice
from core.tts_engine import TTSBase
from audio.effects import fade_in, fade_out, add_silence
from audio.normalizer import normalize_peak
from audio.mixer import mix_with_background, apply_ducking
from audio.exporter import export_audio


class AudioPipeline:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir

    def _load_or_get_engine(self, engine_name: str, engines: Dict[str, TTSBase]) -> TTSBase:
        engine = engines.get(engine_name)
        if engine is None:
            raise ValueError(f"Engine '{engine_name}' not available")
        if not engine.is_loaded():
            engine.load()
        return engine

    def generate_section(self, project: Project, section: Section, engines: Dict[str, TTSBase]) -> str:
        voice = project.get_voice(section.voice_id)
        if voice is None:
            raise ValueError(f"Voice '{section.voice_id}' not found in project")
        
        engine = self._load_or_get_engine(voice.engine, engines)
        
        safe_title = "".join(c if c.isalnum() else "_" for c in section.title)[:30]
        output_name = f"{section.id}_{safe_title}.wav"
        output_path = os.path.join(self.output_dir, sanitize_filename(project.name), output_name)
        
        engine.synthesize(section.text, voice, output_path)
        
        audio, sample_rate = sf.read(output_path, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        
        if project.settings.normalize_audio:
            audio = normalize_peak(audio, target_db=-1.0)
        
        audio = fade_in(audio, sample_rate, project.settings.fade_in_ms)
        audio = fade_out(audio, sample_rate, project.settings.fade_out_ms)
        audio = add_silence(audio, sample_rate, section.pause_after_ms)
        
        if section.music and section.music.get("track"):
            if os.path.exists(section.music["track"]):
                bg_audio, bg_sr = sf.read(section.music["track"], dtype=np.float32)
                if bg_audio.ndim > 1:
                    bg_audio = bg_audio.mean(axis=1)
                if bg_sr != sample_rate:
                    import resampy
                    bg_audio = resampy.resample(bg_audio, bg_sr, sample_rate)
                if len(bg_audio) < len(audio):
                    repeats = int(np.ceil(len(audio) / len(bg_audio)))
                    bg_audio = np.tile(bg_audio, repeats)
                bg_audio = bg_audio[:len(audio)]
                bg_volume = section.music.get("volume_db", -18)
                if section.music.get("ducking"):
                    bg_audio = apply_ducking(bg_audio, duck_db=12)
                audio = mix_with_background(audio, bg_audio, bg_volume_db=bg_volume)
        
        final_ext = project.settings.output_format
        final_path = output_path.replace(".wav", f".{final_ext}")
        export_audio(audio, final_path, sample_rate)
        
        if final_path != output_path and os.path.exists(output_path):
            os.remove(output_path)
        
        return final_path


def sanitize_filename(name: str) -> str:
    import re
    return re.sub(r'[^\w\s-]', '_', name).strip()[:50]
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_audio_pipeline.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/audio_pipeline.py tests/test_audio_pipeline.py
git commit -m "feat: add audio pipeline for section generation"
```

---

### Task 14: Batch Generator

**Files:**
- Create: `core/batch_generator.py`
- Create: `tests/test_batch_generator.py`

- [ ] **Step 1: Write failing test**

```python
import pytest
from unittest.mock import patch, MagicMock
from core.batch_generator import BatchGenerator, GenerationTask
from core.project import Project, Voice


def test_create_task():
    task = GenerationTask(section_id="sec_001", status="pending")
    assert task.section_id == "sec_001"
    assert task.status == "pending"


def test_batch_generator_queue():
    gen = BatchGenerator()
    project = Project(name="Test")
    project.add_voice(Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es"))
    project.add_section("Intro", "Hello", "v1")
    gen.add_project(project)
    assert len(gen.queue) == 1
    assert gen.queue[0].section_id == "sec_001"
```

- [ ] **Step 2: Run test (expect FAIL)**

```bash
pytest tests/test_batch_generator.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: Implement batch_generator.py**

```python
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from core.project import Project, Section
from core.audio_pipeline import AudioPipeline
from core.tts_engine import TTSBase


@dataclass
class GenerationTask:
    section_id: str
    status: str = "pending"  # pending, running, completed, failed
    output_path: Optional[str] = None
    error: Optional[str] = None


class BatchGenerator:
    def __init__(self, pipeline: Optional[AudioPipeline] = None):
        self.pipeline = pipeline or AudioPipeline()
        self.queue: List[GenerationTask] = []
        self.engines: Dict[str, TTSBase] = {}
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def register_engine(self, name: str, engine: TTSBase) -> None:
        self.engines[name] = engine

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        self._progress_callback = callback

    def add_project(self, project: Project) -> None:
        for section in project.sections:
            task = GenerationTask(section_id=section.id)
            self.queue.append(task)

    def run(self, project: Project) -> List[GenerationTask]:
        total = len(self.queue)
        for i, task in enumerate(self.queue):
            if task.status == "completed":
                continue
            task.status = "running"
            if self._progress_callback:
                self._progress_callback(i + 1, total, f"Generating {task.section_id}...")
            
            section = None
            for s in project.sections:
                if s.id == task.section_id:
                    section = s
                    break
            
            if section is None:
                task.status = "failed"
                task.error = "Section not found"
                continue
            
            try:
                output_path = self.pipeline.generate_section(project, section, self.engines)
                task.output_path = output_path
                task.status = "completed"
                project.generation_state["completed_sections"].append(task.section_id)
                project.generation_state["output_files"][task.section_id] = output_path
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
        
        project.generation_state["status"] = "completed" if all(t.status == "completed" for t in self.queue) else "partial"
        if self._progress_callback:
            completed = sum(1 for t in self.queue if t.status == "completed")
            self._progress_callback(completed, total, "Done")
        return self.queue

    def reset(self) -> None:
        self.queue.clear()
```

- [ ] **Step 4: Run test (expect PASS)**

```bash
pytest tests/test_batch_generator.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add core/batch_generator.py tests/test_batch_generator.py
git commit -m "feat: add batch generator with progress callbacks"
```

---

## Phase 5: GUI (PyQt6)

### Task 15: Main Window

**Files:**
- Create: `gui/__init__.py`
- Create: `gui/main_window.py`

- [ ] **Step 1: Write main_window.py**

```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt

from gui.project_panel import ProjectPanel
from gui.script_editor import ScriptEditor
from gui.voice_manager import VoiceManager
from gui.generation_panel import GenerationPanel
from gui.audio_player import AudioPlayer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Podcast Voice Generator")
        self.setMinimumSize(1200, 800)
        
        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.project_panel = ProjectPanel()
        self.script_editor = ScriptEditor()
        self.voice_manager = VoiceManager()
        self.generation_panel = GenerationPanel()
        self.audio_player = AudioPlayer()
        
        self.tabs.addTab(self.project_panel, "Proyecto")
        self.tabs.addTab(self.script_editor, "Guion")
        self.tabs.addTab(self.voice_manager, "Voces")
        self.tabs.addTab(self.generation_panel, "Generar")
        self.tabs.addTab(self.audio_player, "Reproductor")
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
    
    def show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
    
    def show_info(self, message: str):
        QMessageBox.information(self, "Info", message)
```

- [ ] **Step 2: Commit**

```bash
git add gui/__init__.py gui/main_window.py
git commit -m "feat: add main window with tabbed interface"
```

---

### Task 16: Project Panel

**Files:**
- Create: `gui/project_panel.py`

- [ ] **Step 1: Implement project_panel.py**

```python
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

from core.project import Project
from utils.file_utils import ensure_dir


class ProjectPanel(QWidget):
    project_changed = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        group = QGroupBox("Proyecto")
        group_layout = QVBoxLayout(group)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Mi Podcast #1")
        name_layout.addWidget(self.name_input)
        group_layout.addLayout(name_layout)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("Nuevo")
        self.new_btn.clicked.connect(self._new_project)
        btn_layout.addWidget(self.new_btn)
        
        self.open_btn = QPushButton("Abrir")
        self.open_btn.clicked.connect(self._open_project)
        btn_layout.addWidget(self.open_btn)
        
        self.save_btn = QPushButton("Guardar")
        self.save_btn.clicked.connect(self._save_project)
        btn_layout.addWidget(self.save_btn)
        
        group_layout.addLayout(btn_layout)
        layout.addWidget(group)
        layout.addStretch()
    
    def _new_project(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Atención", "Ingresa un nombre para el proyecto")
            return
        self.project = Project(name=name)
        ensure_dir("projects")
        self.project.save(f"projects/{name}.json")
        self.project_changed.emit(self.project)
        QMessageBox.information(self, "Listo", f"Proyecto '{name}' creado")
    
    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir Proyecto", "projects", "JSON (*.json)")
        if path:
            self.project = Project.load(path)
            self.name_input.setText(self.project.name)
            self.project_changed.emit(self.project)
    
    def _save_project(self):
        if self.project is None:
            QMessageBox.warning(self, "Atención", "No hay proyecto activo")
            return
        ensure_dir("projects")
        self.project.save(f"projects/{self.project.name}.json")
        QMessageBox.information(self, "Listo", "Proyecto guardado")
```

- [ ] **Step 2: Commit**

```bash
git add gui/project_panel.py
git commit -m "feat: add project panel with new/open/save"
```

---

### Task 17: Script Editor

**Files:**
- Create: `gui/script_editor.py`

- [ ] **Step 1: Implement script_editor.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QComboBox, QSpinBox, QGroupBox,
    QMessageBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal

from core.project import Project, Section


class ScriptEditor(QWidget):
    project_updated = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.section_list = QListWidget()
        self.section_list.itemClicked.connect(self._load_section)
        layout.addWidget(QLabel("Secciones:"))
        layout.addWidget(self.section_list)
        
        group = QGroupBox("Editar Sección")
        form = QVBoxLayout(group)
        
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Título:"))
        self.title_input = QLineEdit()
        title_layout.addWidget(self.title_input)
        form.addLayout(title_layout)
        
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(QLabel("Voz:"))
        self.voice_combo = QComboBox()
        voice_layout.addWidget(self.voice_combo)
        form.addLayout(voice_layout)
        
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidad:"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(50, 200)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix("%")
        speed_layout.addWidget(self.speed_spin)
        form.addLayout(speed_layout)
        
        form.addWidget(QLabel("Texto:"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Escribe el guion aquí...")
        form.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Agregar Sección")
        self.add_btn.clicked.connect(self._add_section)
        btn_layout.addWidget(self.add_btn)
        
        self.update_btn = QPushButton("Actualizar")
        self.update_btn.clicked.connect(self._update_section)
        btn_layout.addWidget(self.update_btn)
        
        self.delete_btn = QPushButton("Eliminar")
        self.delete_btn.clicked.connect(self._delete_section)
        btn_layout.addWidget(self.delete_btn)
        
        form.addLayout(btn_layout)
        layout.addWidget(group)
    
    def set_project(self, project: Project):
        self.project = project
        self._refresh_list()
        self.voice_combo.clear()
        for voice in project.voices:
            self.voice_combo.addItem(voice.name, voice.id)
    
    def _refresh_list(self):
        self.section_list.clear()
        if self.project:
            for section in self.project.sections:
                item = QListWidgetItem(f"{section.id}: {section.title}")
                item.setData(0, section.id)
                self.section_list.addItem(item)
    
    def _load_section(self, item: QListWidgetItem):
        section_id = item.data(0)
        for section in self.project.sections:
            if section.id == section_id:
                self.title_input.setText(section.title)
                self.text_edit.setPlainText(section.text)
                self.speed_spin.setValue(int(section.speed * 100))
                idx = self.voice_combo.findData(section.voice_id)
                if idx >= 0:
                    self.voice_combo.setCurrentIndex(idx)
                break
    
    def _add_section(self):
        if self.project is None:
            QMessageBox.warning(self, "Atención", "Abre o crea un proyecto primero")
            return
        title = self.title_input.text().strip() or "Sin título"
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Atención", "El texto no puede estar vacío")
            return
        voice_id = self.voice_combo.currentData()
        speed = self.speed_spin.value() / 100.0
        self.project.add_section(title, text, voice_id, speed=speed)
        self._refresh_list()
        self.project_updated.emit(self.project)
    
    def _update_section(self):
        item = self.section_list.currentItem()
        if not item or self.project is None:
            return
        section_id = item.data(0)
        for section in self.project.sections:
            if section.id == section_id:
                section.title = self.title_input.text().strip()
                section.text = self.text_edit.toPlainText().strip()
                section.voice_id = self.voice_combo.currentData()
                section.speed = self.speed_spin.value() / 100.0
                self._refresh_list()
                self.project_updated.emit(self.project)
                break
    
    def _delete_section(self):
        item = self.section_list.currentItem()
        if not item or self.project is None:
            return
        section_id = item.data(0)
        self.project.remove_section(section_id)
        self._refresh_list()
        self.project_updated.emit(self.project)
```

- [ ] **Step 2: Commit**

```bash
git add gui/script_editor.py
git commit -m "feat: add script editor with sections"
```

---

### Task 18: Voice Manager

**Files:**
- Create: `gui/voice_manager.py`

- [ ] **Step 1: Implement voice_manager.py**

```python
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFileDialog, QMessageBox, QGroupBox,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal

from core.project import Project, Voice
from utils.file_utils import ensure_dir


class VoiceManager(QWidget):
    voices_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.project = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.voice_list = QListWidget()
        layout.addWidget(QLabel("Voces del proyecto:"))
        layout.addWidget(self.voice_list)
        
        group = QGroupBox("Agregar Voz")
        form = QVBoxLayout(group)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        form.addLayout(name_layout)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("Pre-entrenada", "pretrained")
        self.type_combo.addItem("Clonada", "cloned")
        type_layout.addWidget(self.type_combo)
        form.addLayout(type_layout)
        
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Motor:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("XTTS v2", "xtts")
        self.engine_combo.addItem("Bark", "bark")
        engine_layout.addWidget(self.engine_combo)
        form.addLayout(engine_layout)
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Idioma:"))
        self.lang_combo = QComboBox()
        for code in ["es", "en", "fr", "de", "it", "pt"]:
            self.lang_combo.addItem(code.upper(), code)
        lang_layout.addWidget(self.lang_combo)
        form.addLayout(lang_layout)
        
        self.ref_btn = QPushButton("Seleccionar audio de referencia (para clonación)")
        self.ref_btn.clicked.connect(self._select_reference)
        form.addWidget(self.ref_btn)
        self.ref_path = ""
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Agregar Voz")
        self.add_btn.clicked.connect(self._add_voice)
        btn_layout.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton("Eliminar")
        self.delete_btn.clicked.connect(self._delete_voice)
        btn_layout.addWidget(self.delete_btn)
        
        form.addLayout(btn_layout)
        layout.addWidget(group)
        layout.addStretch()
    
    def set_project(self, project: Project):
        self.project = project
        self._refresh_list()
    
    def _refresh_list(self):
        self.voice_list.clear()
        if self.project:
            for voice in self.project.voices:
                item = QListWidgetItem(f"{voice.name} ({voice.type}, {voice.engine})")
                item.setData(0, voice.id)
                self.voice_list.addItem(item)
    
    def _select_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "Audio de referencia", "", "Audio (*.wav *.mp3 *.flac)")
        if path:
            self.ref_path = path
            self.ref_btn.setText(f"Referencia: {os.path.basename(path)}")
    
    def _add_voice(self):
        if self.project is None:
            QMessageBox.warning(self, "Atención", "Abre un proyecto primero")
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Atención", "Ingresa un nombre")
            return
        voice_type = self.type_combo.currentData()
        engine = self.engine_combo.currentData()
        lang = self.lang_combo.currentData()
        
        vid = f"voice_{len(self.project.voices) + 1}"
        voice = Voice(
            id=vid,
            name=name,
            type=voice_type,
            engine=engine,
            language=lang,
            reference_path=self.ref_path if voice_type == "cloned" else None
        )
        self.project.add_voice(voice)
        self._refresh_list()
        self.voices_changed.emit()
    
    def _delete_voice(self):
        item = self.voice_list.currentItem()
        if not item or self.project is None:
            return
        voice_id = item.data(0)
        self.project.voices = [v for v in self.project.voices if v.id != voice_id]
        self._refresh_list()
        self.voices_changed.emit()
```

- [ ] **Step 2: Commit**

```bash
git add gui/voice_manager.py
git commit -m "feat: add voice manager with cloning support"
```

---

### Task 19: Generation Panel

**Files:**
- Create: `gui/generation_panel.py`

- [ ] **Step 1: Implement generation_panel.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QComboBox, QCheckBox, QMessageBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, QThread

from core.project import Project
from core.batch_generator import BatchGenerator
from core.xtts_engine import XTTSEngine
from core.bark_engine import BarkEngine
from utils.config_manager import ConfigManager


class GenerationWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished_generation = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, project, generator):
        super().__init__()
        self.project = project
        self.generator = generator
    
    def run(self):
        try:
            self.generator.set_progress_callback(
                lambda current, total, msg: self.progress.emit(current, total, msg)
            )
            results = self.generator.run(self.project)
            self.finished_generation.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class GenerationPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.project = None
        self.generator = BatchGenerator()
        self.worker = None
        self._setup_ui()
        self._setup_engines()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        group = QGroupBox("Configuración de generación")
        form = QVBoxLayout(group)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("MP3", "mp3")
        self.format_combo.addItem("WAV", "wav")
        self.format_combo.addItem("FLAC", "flac")
        format_layout.addWidget(self.format_combo)
        form.addLayout(format_layout)
        
        self.normalize_check = QCheckBox("Normalizar audio")
        self.normalize_check.setChecked(True)
        form.addWidget(self.normalize_check)
        
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generar Audio")
        self.generate_btn.clicked.connect(self._start_generation)
        btn_layout.addWidget(self.generate_btn)
        
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        form.addLayout(btn_layout)
        layout.addWidget(group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Listo")
        layout.addWidget(self.status_label)
        layout.addStretch()
    
    def _setup_engines(self):
        cm = ConfigManager()
        xtts = XTTSEngine(device=cm.get("gpu.device"))
        bark = BarkEngine(device=cm.get("gpu.device"))
        self.generator.register_engine("xtts", xtts)
        self.generator.register_engine("bark", bark)
    
    def set_project(self, project: Project):
        self.project = project
        if project:
            fmt = self.format_combo.currentData()
            project.settings.output_format = fmt
            project.settings.normalize_audio = self.normalize_check.isChecked()
    
    def _start_generation(self):
        if self.project is None or len(self.project.sections) == 0:
            QMessageBox.warning(self, "Atención", "No hay secciones para generar")
            return
        self.generator.reset()
        self.generator.add_project(self.project)
        
        self.generate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.worker = GenerationWorker(self.project, self.generator)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished_generation.connect(self._generation_finished)
        self.worker.error.connect(self._generation_error)
        self.worker.start()
    
    def _update_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"{current}/{total}: {msg}")
    
    def _generation_finished(self, results):
        self.generate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        completed = sum(1 for r in results if r.status == "completed")
        QMessageBox.information(self, "Listo", f"Generación completada: {completed}/{len(results)} secciones")
        self.status_label.setText(f"Completado: {completed}/{len(results)}")
    
    def _generation_error(self, error_msg):
        self.generate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Error", f"Error durante generación: {error_msg}")
```

- [ ] **Step 2: Commit**

```bash
git add gui/generation_panel.py
git commit -m "feat: add generation panel with progress bar"
```

---

### Task 20: Audio Player

**Files:**
- Create: `gui/audio_player.py`

- [ ] **Step 1: Implement audio_player.py**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl


class AudioPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self._select_file)
        layout.addWidget(QLabel("Archivos generados:"))
        layout.addWidget(self.file_list)
        
        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("Reproducir")
        self.play_btn.clicked.connect(self._play)
        btn_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.clicked.connect(self._stop)
        btn_layout.addWidget(self.stop_btn)
        
        self.load_btn = QPushButton("Cargar archivo")
        self.load_btn.clicked.connect(self._load_file)
        btn_layout.addWidget(self.load_btn)
        
        layout.addLayout(btn_layout)
        self.status_label = QLabel("Sin archivo")
        layout.addWidget(self.status_label)
    
    def _select_file(self, item: QListWidgetItem):
        path = item.data(0)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.status_label.setText(f"Seleccionado: {path}")
    
    def _play(self):
        if self.player.source().isEmpty():
            return
        self.player.play()
    
    def _stop(self):
        self.player.stop()
    
    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir audio", "output", "Audio (*.mp3 *.wav *.flac)")
        if path:
            item = QListWidgetItem(path)
            item.setData(0, path)
            self.file_list.addItem(item)
            self.player.setSource(QUrl.fromLocalFile(path))
            self.status_label.setText(f"Cargado: {path}")
    
    def add_file(self, path: str):
        if not path:
            return
        item = QListWidgetItem(path)
        item.setData(0, path)
        self.file_list.addItem(item)
```

- [ ] **Step 2: Commit**

```bash
git add gui/audio_player.py
git commit -m "feat: add audio player widget"
```

---

## Phase 6: Main Entry Point and Integration

### Task 21: Main Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement main.py**

```python
import sys
import os
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from utils.file_utils import ensure_dir


def main():
    ensure_dir("projects")
    ensure_dir("output")
    ensure_dir("voices/clones")
    ensure_dir("music")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Podcast Voice Generator")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: add main entry point"
```

---

### Task 22: GUI Integration Wiring

**Files:**
- Modify: `gui/main_window.py`

- [ ] **Step 1: Modify main_window.py to wire project across tabs**

Replace the `__init__` and `_setup_ui` methods with:

```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStatusBar, QMessageBox
)

from gui.project_panel import ProjectPanel
from gui.script_editor import ScriptEditor
from gui.voice_manager import VoiceManager
from gui.generation_panel import GenerationPanel
from gui.audio_player import AudioPlayer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Podcast Voice Generator")
        self.setMinimumSize(1200, 800)
        self._setup_ui()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.project_panel = ProjectPanel()
        self.script_editor = ScriptEditor()
        self.voice_manager = VoiceManager()
        self.generation_panel = GenerationPanel()
        self.audio_player = AudioPlayer()
        
        self.tabs.addTab(self.project_panel, "Proyecto")
        self.tabs.addTab(self.script_editor, "Guion")
        self.tabs.addTab(self.voice_manager, "Voces")
        self.tabs.addTab(self.generation_panel, "Generar")
        self.tabs.addTab(self.audio_player, "Reproductor")
        
        self.project_panel.project_changed.connect(self._on_project_changed)
        self.script_editor.project_updated.connect(self._on_project_updated)
        self.voice_manager.voices_changed.connect(self._on_voices_changed)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
    
    def _on_project_changed(self, project):
        self.script_editor.set_project(project)
        self.voice_manager.set_project(project)
        self.generation_panel.set_project(project)
        self.status_bar.showMessage(f"Proyecto: {project.name}")
    
    def _on_project_updated(self, project):
        self.generation_panel.set_project(project)
    
    def _on_voices_changed(self):
        if self.project_panel.project:
            self.script_editor.set_project(self.project_panel.project)
    
    def show_error(self, message: str):
        QMessageBox.critical(self, "Error", message)
    
    def show_info(self, message: str):
        QMessageBox.information(self, "Info", message)
```

- [ ] **Step 2: Commit**

```bash
git add gui/main_window.py
git commit -m "feat: wire project state across all GUI tabs"
```

---

## Phase 7: Final Integration Tests

### Task 23: Integration Tests

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
import pytest
import tempfile
import os
from core.project import Project
from core.batch_generator import BatchGenerator
from core.audio_pipeline import AudioPipeline
from unittest.mock import patch, MagicMock


def test_full_pipeline_mock():
    with tempfile.TemporaryDirectory() as tmp:
        project = Project(name="Integration Test")
        project.add_voice(type="pretrained", engine="xtts", language="es", id="v1", name="Host")
        project.add_section("Intro", "Hello world", "v1")
        
        pipeline = AudioPipeline(output_dir=tmp)
        generator = BatchGenerator(pipeline)
        
        mock_engine = MagicMock()
        mock_engine.is_loaded.return_value = True
        mock_engine.synthesize.return_value = os.path.join(tmp, "test.wav")
        generator.register_engine("xtts", mock_engine)
        generator.add_project(project)
        
        with patch('core.audio_pipeline.sf.read', return_value=(__import__('numpy').ones(24000, dtype=__import__('numpy').float32), 24000)):
            results = generator.run(project)
        
        assert len(results) == 1
        assert results[0].status == "completed"
```

- [ ] **Step 2: Run test (expect PASS)**

```bash
pytest tests/test_integration.py -v
```

Expected: 1 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for full generation pipeline"
```

---

## Self-Review

### Spec coverage check

| Spec Section | Implementing Task |
|--------------|-------------------|
| Arquitectura 4 capas | Tasks 1-23 |
| Config YAML | Task 1 |
| ConfigManager | Task 2 |
| GPU utils | Task 4 |
| Project model | Task 5 |
| TTSBase | Task 6 |
| XTTS engine | Task 7 |
| Bark engine | Task 8 |
| Audio effects | Task 9 |
| Normalizer | Task 10 |
| Mixer | Task 11 |
| Exporter | Task 12 |
| Audio pipeline | Task 13 |
| Batch generator | Task 14 |
| GUI tabs | Tasks 15-20 |
| Main entry | Task 21 |
| Integration | Task 22-23 |

### Placeholder scan
- No TBD, TODO, or incomplete sections found
- All code blocks contain real code
- Every test has implementation code
- No vague steps like "add appropriate error handling"

### Type consistency check
- `Voice.id`, `Section.id`, `Project.name` consistent across all files
- `TTSBase.synthesize(text, voice, output_path)` consistent in XTTS and Bark
- `BatchGenerator.register_engine(name, engine)` used consistently
- `AudioPipeline.generate_section(project, section, engines)` consistent

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-31-podcast-voice-generator.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach?**
