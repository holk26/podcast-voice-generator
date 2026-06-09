"""
Script Editor Agent — reviews and improves scripts for quality, pacing, and audio suitability.

Input: { "script_text": str, "content_type": str, "target_duration_minutes": float }
Output: {
    "improved_script": str,
    "changes_made": [str],
    "quality_score": float,  # 0.0 to 10.0
    "issues_found": [str],
    "suggestions": [str]
}
"""

import json
from typing import Any, Dict

from agents.base import BaseAgent, AgentResult


class ScriptEditorAgent(BaseAgent):
    """Reviews and improves dramatized scripts."""

    name = "script_editor"
    description = "Revisa y mejora guiones para calidad, ritmo y adaptación al audio."

    SYSTEM_PROMPT = """Eres un editor senior de guiones de audio en español. Tu trabajo es revisar guiones dramatizados y mejorarlos.

Criterios de revisión:
1. Ritmo: las líneas deben ser de longitud variada, no monótonas
2. Naturalidad: el diálogo debe sonar como una conversación real
3. Claridad: conceptos técnicos deben explicarse de forma accesible
4. Audio-adaptación: evita listas largas o datos que se confundan al escuchar
5. Duración: ajusta la cantidad de contenido para alcanzar la duración objetivo
6. Transiciones: asegura transiciones suaves entre secciones

Responde SIEMPRE en formato JSON con este schema:
{
  "improved_script": "guion mejorado en formato PERSONAJE: texto",
  "changes_made": ["cambio 1", "cambio 2"],
  "quality_score": 8.5,
  "issues_found": ["problema 1"],
  "suggestions": ["sugerencia 1"]
}"""

    def run(self, input_data: Dict[str, Any]) -> AgentResult:
        script_text = input_data.get("script_text", "")
        content_type = input_data.get("content_type", "news")
        target_duration = input_data.get("target_duration_minutes", 8.0)

        if not script_text.strip():
            return AgentResult.fail("No script provided to edit.")

        user = f"""Tipo de contenido: {content_type}
Duración objetivo: {target_duration} minutos

Guion a revisar:
---
{script_text}
---

Revisa el guion y devuélvelo mejorado en formato JSON según el schema indicado."""

        try:
            raw = self._ask_llm(self.SYSTEM_PROMPT, user, temperature=0.5)
            cleaned = self._extract_markdown_block(raw, "json")
            data = json.loads(cleaned)

            required = ["improved_script", "changes_made", "quality_score", "issues_found", "suggestions"]
            for key in required:
                if key not in data:
                    data[key] = [] if key in ("changes_made", "issues_found", "suggestions") else (script_text if key == "improved_script" else 7.0)

            data["original_script"] = script_text
            data["content_type"] = content_type

            return AgentResult.ok(data=data, raw_output=raw)

        except json.JSONDecodeError:
            return AgentResult.ok(
                data={
                    "improved_script": script_text,
                    "changes_made": [],
                    "quality_score": 7.0,
                    "issues_found": ["No se pudo parsear la respuesta del editor"],
                    "suggestions": [],
                    "original_script": script_text,
                    "content_type": content_type
                },
                raw_output=raw if 'raw' in locals() else "",
                metadata={"warning": "LLM did not return valid JSON, using original script."}
            )
        except Exception as e:
            return AgentResult.fail(str(e))
