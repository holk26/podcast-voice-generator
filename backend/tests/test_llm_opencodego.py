import json
import os
import pytest
from pathlib import Path

from backend.app.services.llm_provider import (
    KNOWN_PROVIDERS,
    get_llm,
    list_providers,
    save_opencodego_api_key,
    get_opencodego_api_key,
)
from crewai import LLM


def test_opencodego_provider_registration():
    """Verify opencodego is in KNOWN_PROVIDERS and listed."""
    assert "opencodego" in KNOWN_PROVIDERS

    providers = list_providers()
    entry = next((p for p in providers if p["id"] == "opencodego"), None)
    assert entry is not None
    assert entry["name"] == "OpenCode Go"
    assert entry["default_model"] == "kimi-k2.6"


def test_opencodego_token_management(tmp_path):
    """Test saving and retrieving OpenCode Go token."""
    import backend.app.services.llm_provider as lp
    original_path = lp.DATA_DIR_OPENCODEGO_TOKEN

    test_token_path = tmp_path / "opencodego_token.json"
    lp.DATA_DIR_OPENCODEGO_TOKEN = test_token_path

    try:
        assert not test_token_path.exists()

        lp.save_opencodego_api_key("test-opencodego-key")
        assert test_token_path.exists()

        assert lp.get_opencodego_api_key() == "test-opencodego-key"
    finally:
        lp.DATA_DIR_OPENCODEGO_TOKEN = original_path


def test_get_llm_opencodego():
    """Test get_llm returns a properly configured CrewAI LLM for OpenCode Go."""
    import backend.app.services.llm_provider as lp
    import tempfile
    original_path = lp.DATA_DIR_OPENCODEGO_TOKEN

    temp_dir = tempfile.mkdtemp()
    lp.DATA_DIR_OPENCODEGO_TOKEN = Path(temp_dir) / "opencodego_token.json"
    lp.save_opencodego_api_key("fake-opencodego-key")

    try:
        llm = lp.get_llm(provider="opencodego", model="kimi-k2.6")
        assert llm.model == "kimi-k2.6"
        assert llm.api_key == "fake-opencodego-key"
    finally:
        lp.DATA_DIR_OPENCODEGO_TOKEN = original_path
