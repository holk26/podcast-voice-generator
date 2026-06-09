"""
Character Caster Agent — assigns voices from the VoiceCast to characters in a script.

Input: { "script_text": str, "available_voices": [VoiceProfile] }
Output: {
    "casting_map": { "CharacterName": "voice_id", ... },
    "reasoning": [str]
}
"""

import json
import re
from typing import Any, Dict, List

from agents.base import BaseAgent, AgentResult


class CharacterCasterAgent(BaseAgent):
    """Assigns optimal voices to characters in a script."""

    name = "character_caster"
    description = "Asigna voces del elenco a personajes del guion."

    SYSTEM_PROMPT = """Eres un director de casting de audio dramatizado en español. Tu trabajo es asignar la voz más adecuada a cada personaje.

Reglas:
1. Reserva voces masculinas para personajes masculinos y femeninas para femeninos cuando sea posible
2. El narrador debe tener una voz clara y neutra (preferiblemente Alvaro/Elvira)
3. El protagonista puede usar la voz clonada principal (homer) si es masculino
4. Personajes secundarios usan voces alternativas (jorge, dalia, elvira)
5. Justifica cada asignación en una frase

Responde SIEMPRE en formato JSON con este schema:
{
  "casting_map": {"NombrePersonaje": "voice_id"},
  "reasoning": ["Personaje X usa voz Y porque..."]
}"""

    def _extract_characters(self, script_text: str) -> List[str]:
        """Extract character names from screenplay format."""
        pattern = re.compile(r"^\s*([A-ZÁÉÍÓÚÑa-záéíóúñ_][A-ZÁÉÍÓÚÑa-záéíóúñ0-9_\s]*?):\s*.+$", re.MULTILINE)
        chars = set()
        for m in pattern.finditer(script_text):
            chars.add(m.group(1).strip())
        return sorted(chars)

    def run(self, input_data: Dict[str, Any]) -> AgentResult:
        script_text = input_data.get("script_text", "")
        available_voices = input_data.get("available_voices", [])

        if not script_text.strip():
            return AgentResult.fail("No script provided.")

        characters = self._extract_characters(script_text)
        if not characters:
            return AgentResult.fail("No characters found in script.")

        voice_info = []
        for v in available_voices:
            if hasattr(v, "to_dict"):
                voice_info.append(v.to_dict())
            else:
                voice_info.append(v)

        user = f"""Personajes encontrados en el guion:
{chr(10).join(f'- {c}' for c in characters)}

Voces disponibles:
{json.dumps(voice_info, ensure_ascii=False, indent=2)}

Guion:
---
{script_text}
---

Asigna una voz a cada personaje y responde en JSON según el schema."""

        try:
            raw = self._ask_llm(self.SYSTEM_PROMPT, user, temperature=0.4)
            cleaned = self._extract_markdown_block(raw, "json")
            data = json.loads(cleaned)

            if "casting_map" not in data:
                data["casting_map"] = {}
            if "reasoning" not in data:
                data["reasoning"] = []

            # Fallback deterministic assignments if LLM missed any
            for char in characters:
                if char not in data["casting_map"]:
                    data["casting_map"][char] = self._deterministic_fallback(char, available_voices)

            return AgentResult.ok(data=data, raw_output=raw)

        except (json.JSONDecodeError, Exception) as e:
            # Full deterministic fallback
            casting = {}
            for char in characters:
                casting[char] = self._deterministic_fallback(char, available_voices)
            return AgentResult.ok(
                data={"casting_map": casting, "reasoning": ["Asignación determinística por fallo del LLM."]},
                raw_output=raw if 'raw' in locals() else "",
                metadata={"warning": str(e)}
            )

    def _deterministic_fallback(self, character: str, available_voices: List[Any]) -> str:
        """Assign a voice deterministically when LLM fails."""
        char_lower = character.lower()
        voice_ids = [v.voice_id if hasattr(v, "voice_id") else v.get("voice_id", "") for v in available_voices]

        # Map common roles
        if "narrador" in char_lower:
            return "narrador" if "narrador" in voice_ids else voice_ids[0]
        if "presentador" in char_lower and "a" not in char_lower[-4:]:
            return "homer" if "homer" in voice_ids else voice_ids[0]
        if "presentadora" in char_lower:
            return "dalia" if "dalia" in voice_ids else ("elvira" if "elvira" in voice_ids else voice_ids[0])

        # Use first available non-narrator voice
        for vid in voice_ids:
            if vid != "narrador":
                return vid
        return voice_ids[0] if voice_ids else "homer"
