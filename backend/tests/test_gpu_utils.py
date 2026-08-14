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
