"""
Content Cleaner Agent — cleans and structures raw content from RSS, Gutenberg, etc.

Input: { "source": "rss|gutenberg|raw", "content": str, "content_type": "news|book|template" }
Output: {
    "cleaned_text": str,
    "title": str,
    "summary": str,
    "key_points": [str],
    "language": str,
    "source_url": str (optional)
}
"""

import json
from typing import Any, Dict

from agents.base import BaseAgent, AgentResult


class ContentCleanerAgent(BaseAgent):
    """Cleans raw text into structured content ready for script writing."""

    name = "content_cleaner"
    description = "Limpia y estructura contenido crudo de fuentes externas."

    SYSTEM_PROMPT = """Eres un editor experto de contenido en español. Tu trabajo es limpiar y estructurar texto crudo.

Reglas:
1. Elimina publicidad, enlaces rotos, repetición innecesaria y elementos de navegación web.
2. Extrae el título principal del contenido.
3. Resume los puntos clave en una lista de 3 a 7 bullets.
4. Detecta el idioma del texto.
5. Preserva citas, datos importantes y nombres propios.
6. Si el contenido es HTML, ignora las etiquetas y extrae solo el texto relevante.

Responde SIEMPRE en formato JSON con este schema:
{
  "title": "Título del contenido",
  "summary": "Resumen de 2-3 oraciones",
  "key_points": ["punto 1", "punto 2", ...],
  "cleaned_text": "Texto limpio y coherente, sin formato HTML ni basura",
  "language": "es"
}"""

    def run(self, input_data: Dict[str, Any]) -> AgentResult:
        content = input_data.get("content", "")
        content_type = input_data.get("content_type", "raw")
        source = input_data.get("source", "raw")

        if not content.strip():
            return AgentResult.fail("No content provided to clean.")

        user_prompt = f"Fuente: {source}\nTipo: {content_type}\n\nTexto crudo:\n---\n{content}\n---\n\nLimpia y estructura este contenido según las instrucciones. Responde SOLO con JSON válido."

        try:
            raw = self._ask_llm(self.SYSTEM_PROMPT, user_prompt, temperature=0.3)
            cleaned = self._extract_markdown_block(raw, "json")
            data = json.loads(cleaned)

            required = ["title", "summary", "key_points", "cleaned_text", "language"]
            for key in required:
                if key not in data:
                    data[key] = ""

            data["source_url"] = input_data.get("source_url", "")
            data["source"] = source
            data["content_type"] = content_type

            return AgentResult.ok(data=data, raw_output=raw)

        except json.JSONDecodeError as e:
            # Fallback: return a basic structure with the raw content
            return AgentResult.ok(
                data={
                    "title": input_data.get("title", ""),
                    "summary": content[:300] + "..." if len(content) > 300 else content,
                    "key_points": [],
                    "cleaned_text": content,
                    "language": "es",
                    "source_url": input_data.get("source_url", ""),
                    "source": source,
                    "content_type": content_type
                },
                raw_output=raw if 'raw' in locals() else "",
                metadata={"warning": f"LLM did not return valid JSON: {e}"}
            )
        except Exception as e:
            return AgentResult.fail(str(e))
