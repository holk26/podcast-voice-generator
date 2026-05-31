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
