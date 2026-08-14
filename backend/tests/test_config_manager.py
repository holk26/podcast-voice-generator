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
