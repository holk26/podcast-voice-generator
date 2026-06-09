"""
LLM Provider abstraction — supports OpenAI, Anthropic, Ollama (local), and a mock provider for tests.

Uses requests (no SDK dependencies) to keep the project lightweight.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

import requests


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1500) -> str:
        """Send a chat completion request and return the generated text."""
        pass

    def is_available(self) -> bool:
        """Check if this provider is configured and reachable."""
        return True


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (OpenAI, Groq, Together, etc.)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1500) -> str:
        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY env var.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com/v1",
        model: str = "claude-3-5-sonnet-20241022"
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1500) -> str:
        if not self.api_key:
            raise RuntimeError("Anthropic API key not configured. Set ANTHROPIC_API_KEY env var.")

        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        # Anthropic uses 'system' separately
        system_msg = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg += m["content"] + "\n"
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages
        }
        if system_msg.strip():
            payload["system"] = system_msg.strip()

        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


class OllamaProvider(LLMProvider):
    """Provider for Ollama local LLMs."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1500) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


class MockProvider(LLMProvider):
    """Deterministic mock provider for testing and offline fallback."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.call_count = 0

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1500) -> str:
        self.call_count += 1
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break

        # Check for keyword-based canned responses
        for key, response in self.responses.items():
            if key.lower() in last_user.lower():
                return response

        return "[MOCK LLM RESPONSE]"


def create_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> LLMProvider:
    """Factory for creating LLM providers based on config or env."""
    name = (provider_name or os.getenv("LLM_PROVIDER", "openai")).lower()

    if name == "openai":
        return OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")
    if name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
    if name == "ollama":
        return OllamaProvider(model=model or "llama3.1")
    if name == "mock":
        return MockProvider()

    raise ValueError(f"Unknown LLM provider: {name}")


def get_first_available_provider(preferred: Optional[str] = None) -> LLMProvider:
    """Try preferred provider, then fallback through available providers."""
    providers_to_try = []
    if preferred:
        providers_to_try.append(preferred)
    providers_to_try.extend(["openai", "anthropic", "ollama", "mock"])

    for name in providers_to_try:
        try:
            provider = create_provider(name)
            if provider.is_available():
                return provider
        except Exception:
            continue

    return MockProvider()
