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
