"""Base agent class for the multi-agent content generation system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents.llm_provider import LLMProvider, MockProvider, get_first_available_provider


@dataclass
class AgentResult:
    """Standardized output from any agent."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    raw_output: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Dict[str, Any], raw_output: str = "", metadata: Optional[Dict] = None) -> "AgentResult":
        return cls(success=True, data=data, raw_output=raw_output, metadata=metadata or {})

    @classmethod
    def fail(cls, error: str, raw_output: str = "", metadata: Optional[Dict] = None) -> "AgentResult":
        return cls(success=False, error=error, raw_output=raw_output, metadata=metadata or {})


class BaseAgent(ABC):
    """Base class for all content generation agents."""

    name: str = "base_agent"
    description: str = ""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ):
        # Use provided provider, or auto-detect from env/config, or fallback to mock
        self.provider = provider or get_first_available_provider()
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _ask_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """Send a structured prompt to the LLM and return the response."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.provider.chat(
            messages,
            temperature=temperature or self.temperature,
            max_tokens=self.max_tokens
        )

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute the agent's task. Must be implemented by subclasses."""
        pass

    def _extract_markdown_block(self, text: str, language: str = "") -> str:
        """Extract content from a markdown code block."""
        import re
        pattern = rf"```{language}\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Try without newline after language
        pattern2 = rf"```{language}\s*(.*?)```"
        match = re.search(pattern2, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
