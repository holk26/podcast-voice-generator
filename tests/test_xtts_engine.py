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
