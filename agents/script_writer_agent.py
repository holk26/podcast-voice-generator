"""
Script Writer Agent — writes dramatized scripts from cleaned content.

Input: { "content": cleaned_data, "content_type": "news|book|meditation|motivation", "voice_cast": [...] }
Output: {
    "script_text": str,      # In screenplay format: CHARACTER: text
    "scene_notes": [str],
    "estimated_duration_minutes": float,
    "content_warnings": [str]
}
"""

import json
from typing import Any, Dict, List

from agents.base import BaseAgent, AgentResult


class ScriptWriterAgent(BaseAgent):
    """Generates dramatized scripts from structured content."""

    name = "script_writer"
    description = "Escribe guiones dramatizados a partir de contenido limpio."

    def _system_prompt(self, content_type: str, voice_cast: List[str]) -> str:
        base = """Eres un guionista experto de podcasts y audiolibros dramatizados en español.
Tu trabajo es convertir contenido limpio en un guion dramatizado con múltiples voces.

Reglas de formato:
- Usa formato guion teatral: NOMBRE_PERSONAJE: texto del diálogo
- Puedes usar (emoción) al final de una línea para indicar emociones, ej: ESTOY FELIZ (happy)
- Máximo 2-3 personajes principales para podcasts de noticias
- Para audiolibros, respeta los diálogos del texto original
- Las líneas deben ser naturales, no muy largas (máximo 40 palabras por línea)
- Incluye un narrador para introducir contexto cuando sea necesario
- El guion debe fluir como una conversación real, no como una lectura de noticias

Responde SIEMPRE en formato JSON con este schema:
{
  "script_text": "PERSONAJE1: Línea 1\\nPERSONAJE2: Línea 2\\n...",
  "scene_notes": ["nota sobre ambiente", "nota sobre efecto de sonido"],
  "estimated_duration_minutes": 8.5,
  "content_warnings": []
}"""

        if content_type == "news":
            base += """

Específico para noticias:
- Un presentador principal y una co-presentadora hacen el diálogo
- Introduce 3-5 noticias principales
- Cierra con un comentario breve sobre el tema más importante
"""
        elif content_type == "book":
            base += """

Específico para audiolibros:
- Respeta las voces de los personajes del libro
- Usa un narrador para descripciones
- Mantén fidelidad al texto original
"""
        elif content_type == "meditation":
            base += """

Específico para meditación:
- Usa una sola voz calmada y pausada
- Incluye instrucciones de respiración
- Mantén un tono suave y relajado
"""
        elif content_type == "motivation":
            base += """

Específico para motivación:
- Usa 1-2 voces con energía positiva
- Incluye una cita inspiradora
- Termina con un llamado a la acción
"""

        base += f"\n\nVoces disponibles: {', '.join(voice_cast)}\n"
        return base

    def run(self, input_data: Dict[str, Any]) -> AgentResult:
        content = input_data.get("content", {})
        content_type = input_data.get("content_type", "news")
        voice_cast = input_data.get("voice_cast", ["homer", "dalia", "narrador"])

        if not content:
            return AgentResult.fail("No cleaned content provided.")

        cleaned_text = content.get("cleaned_text", "")
        title = content.get("title", "Sin título")
        key_points = content.get("key_points", [])

        if not cleaned_text.strip():
            return AgentResult.fail("Cleaned text is empty.")

        system = self._system_prompt(content_type, voice_cast)
        user = f"""Título: {title}

Puntos clave:
{chr(10).join(f'- {kp}' for kp in key_points)}

Texto limpio:
---
{cleaned_text}
---

Escribe el guion dramatizado en formato JSON según el schema indicado."""

        try:
            raw = self._ask_llm(system, user, temperature=0.8)
            cleaned = self._extract_markdown_block(raw, "json")
            data = json.loads(cleaned)

            required = ["script_text", "scene_notes", "estimated_duration_minutes", "content_warnings"]
            for key in required:
                if key not in data:
                    data[key] = [] if key in ("scene_notes", "content_warnings") else ("" if key == "script_text" else 0.0)

            data["source_title"] = title
            data["source_summary"] = content.get("summary", "")
            data["content_type"] = content_type

            return AgentResult.ok(data=data, raw_output=raw)

        except json.JSONDecodeError as e:
            # Fallback: try to extract screenplay lines from raw text
            return AgentResult.ok(
                data={
                    "script_text": raw if 'raw' in locals() else cleaned_text,
                    "scene_notes": [],
                    "estimated_duration_minutes": 5.0,
                    "content_warnings": [],
                    "source_title": title,
                    "source_summary": content.get("summary", ""),
                    "content_type": content_type
                },
                raw_output=raw if 'raw' in locals() else "",
                metadata={"warning": f"LLM did not return valid JSON: {e}"}
            )
        except Exception as e:
            return AgentResult.fail(str(e))
