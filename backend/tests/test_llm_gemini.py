import json
import os
import pytest
from pathlib import Path

from backend.app.services.llm_provider import (
    KNOWN_PROVIDERS,
    get_llm,
    list_providers,
    list_models,
    save_gemini_api_key,
    get_gemini_api_key,
)
from crewai import LLM


def test_gemini_provider_registration():
    """Verify gemini is in KNOWN_PROVIDERS and listed."""
    assert "gemini" in KNOWN_PROVIDERS
    
    providers = list_providers()
    gemini_entry = next((p for p in providers if p["id"] == "gemini"), None)
    assert gemini_entry is not None
    assert gemini_entry["name"] == "Gemini"
    assert gemini_entry["default_model"] == "gemini-2.5-flash"


def test_gemini_token_management(tmp_path):
    """Test saving and retrieving Gemini token."""
    # Temporarily override DATA_DIR_GEMINI_TOKEN path to avoid pollution
    import backend.app.services.llm_provider as lp
    original_path = lp.DATA_DIR_GEMINI_TOKEN
    
    test_token_path = tmp_path / "gemini_token.json"
    lp.DATA_DIR_GEMINI_TOKEN = test_token_path
    
    try:
        # Initial status
        assert not test_token_path.exists()
        
        # Save token
        lp.save_gemini_api_key("test-key-12345")
        assert test_token_path.exists()
        
        # Retrieve token
        assert lp.get_gemini_api_key() == "test-key-12345"
    finally:
        lp.DATA_DIR_GEMINI_TOKEN = original_path


def test_get_llm_gemini():
    """Test get_llm returns a properly configured CrewAI LLM for Gemini."""
    import backend.app.services.llm_provider as lp
    original_path = lp.DATA_DIR_GEMINI_TOKEN
    
    # Force mock token in data dir
    import tempfile
    temp_dir = tempfile.mkdtemp()
    lp.DATA_DIR_GEMINI_TOKEN = Path(temp_dir) / "gemini_token.json"
    lp.save_gemini_api_key("fake-gemini-key")
    
    try:
        llm = lp.get_llm(provider="gemini", model="gemini-2.5-flash")
        assert llm.model == "gemini-2.5-flash"
        assert llm.api_key == "fake-gemini-key"
    finally:
        lp.DATA_DIR_GEMINI_TOKEN = original_path
