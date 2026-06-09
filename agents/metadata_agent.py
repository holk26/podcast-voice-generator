"""
Metadata Agent — generates podcast/episode metadata from content.

Input: { "content": cleaned_data, "script_text": str, "content_type": str }
Output: {
    "title": str,
    "description": str,
    "summary": str,
    "tags": [str],
    "category": str,
    "episode_number": int (optional)
}
"""

import json
from typing import Any, Dict

from agents.base import BaseAgent, AgentResult


class MetadataAgent(BaseAgent):
    """Generates SEO-friendly metadata for episodes."""

    name = "metadata_agent"
    description = "Genera metadatos, títulos y descripciones optimizados para podcasts."

    SYSTEM_PROMPT = """Eres un especialista en SEO y marketing de podcasts en español. Generas títulos y descripciones atractivas.

Reglas:
1. Títulos: máximo 80 caracteres, atractivos, con palabras clave relevantes
2. Descripciones: 2-4 oraciones, incluye hashtags y palabras clave
3. Summary: 1 oración para iTunes/Google Podcasts
4. Tags: 5-10 palabras clave relevantes
5. Categoría: elige una de [Technology, Arts, Health, Business, Education, Comedy, News, Sports]

Responde SIEMPRE en formato JSON con este schema:
{
  "title": "Título del episodio",
  "description": "Descripción larga para plataformas de podcast...",
  "summary": "Resumen de una oración.",
  "tags": ["tag1", "tag2"],
  "category": "Technology"
}"""

    def run(self, input_data: Dict[str, Any]) -> AgentResult:
        content = input_data.get("content", {})
        script_text = input_data.get("script_text", "")
        content_type = input_data.get("content_type", "news")
        episode_number = input_data.get("episode_number")

        title_hint = content.get("title", "") if isinstance(content, dict) else ""
        summary_hint = content.get("summary", "") if isinstance(content, dict) else ""
        key_points = content.get("key_points", []) if isinstance(content, dict) else []

        user = f"""Tipo de contenido: {content_type}
Título original: {title_hint}
Resumen original: {summary_hint}
Puntos clave: {', '.join(key_points)}

Fragmento del guion:
---
{script_text[:1500]}
---

Genera metadatos optimizados en formato JSON según el schema."""

        try:
            raw = self._ask_llm(self.SYSTEM_PROMPT, user, temperature=0.6)
            cleaned = self._extract_markdown_block(raw, "json")
            data = json.loads(cleaned)

            required = ["title", "description", "summary", "tags", "category"]
            for key in required:
                if key not in data:
                    data[key] = [] if key == "tags" else ""

            if episode_number is not None:
                data["episode_number"] = episode_number

            data["content_type"] = content_type

            return AgentResult.ok(data=data, raw_output=raw)

        except (json.JSONDecodeError, Exception) as e:
            # Fallback deterministic metadata
            return AgentResult.ok(
                data={
                    "title": title_hint or "Episodio de podcast",
                    "description": summary_hint or "Episodio generado automáticamente.",
                    "summary": summary_hint or "Episodio generado automáticamente.",
                    "tags": ["podcast", content_type, "automático"],
                    "category": "Technology" if content_type == "news" else "Arts",
                    "episode_number": episode_number,
                    "content_type": content_type
                },
                raw_output=raw if 'raw' in locals() else "",
                metadata={"warning": f"Metadata generation fallback: {e}"}
            )
