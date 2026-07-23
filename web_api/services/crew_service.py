import ast
import json
import re
from typing import List
from crewai import Agent, Task, Crew
from web_api.schemas import PlanEntryCreate
from web_api.services.llm_provider import get_planning_llm, get_script_llm


PLAN_PROMPT = """Eres un estratega de contenidos. Para el canal "{name}" ({format}) sobre el nicho "{niche}",
propón {count} ideas de episodios variadas y atractivas. Devuélvelas EXACTAMENTE en este formato JSON:
[
  {{"title": "Título 1", "description": "Descripción corta 1"}},
  ...
]
Solo JSON, sin explicaciones."""

CRITIC_PROMPT = """Eres el editor jefe del canal "{name}". Del listado de ideas anterior,
selecciona las {count} MEJORES para la audiencia del nicho "{niche}" y pule sus títulos y descripciones.
Descarta las repetidas, genéricas o poco viables.
Devuelve SOLO el array JSON final con exactamente {count} objetos {{"title": ..., "description": ...}},
sin explicaciones."""


SCRIPT_PROMPT = """Eres un guionista de audio. Escribe un guion completo en español para un episodio de tipo "{format}"
titulado "{title}". Descripción: {description}. Nicho: {niche}.
El guion debe tener entre 300 y 800 palabras, ser natural al leerse en voz alta y no incluir notas de producción.
Devuelve SOLO el texto del guion, sin introducciones ni comentarios."""

CLEAN_PROMPT = """Del guion anterior, prepara la versión FINAL PARA SÍNTESIS DE VOZ (TTS).
Elimina TODO lo que no deba leerse en voz alta: notas de producción, indicaciones
("Intro Musical", "Narrador:", "Pausa", efectos de sonido), formato markdown
(**, ##, *), títulos de sección y cualquier comentario técnico.
Devuelve SOLO el texto hablable, en español, tal cual debe pronunciarse."""


_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_block(raw: str) -> str:
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```", 2)
        if len(parts) >= 2:
            inner = parts[1].strip()
            if inner.lower().startswith("json"):
                inner = inner[4:].strip()
            return inner
    start = raw.find("[")
    if start == -1:
        start = raw.find("{")
    if start == -1:
        return raw
    end = raw.rfind("]") if raw[start] == "[" else raw.rfind("}")
    if end == -1 or end < start:
        return raw
    return raw[start : end + 1]


def _repair_json(raw: str) -> str:
    # Add missing commas between consecutive objects/arrays
    raw = re.sub(r"}\s*{", "},{", raw)
    raw = re.sub(r"]\s*\[", "],[", raw)
    # Remove trailing commas before closing braces/brackets
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    return raw


def _parse_json_flexible(raw: str):
    cleaned = _extract_json_block(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    repaired = _repair_json(cleaned)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Fallback for single-quoted dicts/lists (e.g. Python repr)
    try:
        return ast.literal_eval(repaired)
    except Exception as e:
        raise ValueError(
            f"Could not parse plan result as JSON: {e}\nRaw snippet: {raw[:500]}"
        )


def _parse_plan_result(raw: str) -> List[PlanEntryCreate]:
    data = _parse_json_flexible(raw)
    if not isinstance(data, list):
        raise ValueError("Plan result is not a list")
    return [
        PlanEntryCreate(title=item["title"], description=item.get("description"))
        for item in data
    ]


def generate_plan(channel, count: int = 5) -> List[PlanEntryCreate]:
    """Congreso de agentes: el estratega propone ideas en bruto y el editor
    jefe las debate, filtra y pule hasta quedarse con las mejores."""
    strategist = Agent(
        role="Content Strategist",
        goal="Proponer ideas de episodios relevantes para un canal",
        backstory="Experto en contenido digital y nichos de audiencia.",
        llm=get_planning_llm(),
        verbose=False,
    )
    chief_editor = Agent(
        role="Chief Editor",
        goal="Seleccionar y pulir las mejores ideas para el canal",
        backstory="Editor jefe con años de criterio editorial; descarta lo genérico.",
        llm=get_planning_llm(),
        verbose=False,
    )

    propose_task = Task(
        description=PLAN_PROMPT.format(
            name=channel.name,
            format=channel.format,
            niche=channel.niche or "general",
            count=count + 3,  # ideas de sobra para que el editor descarte
        ),
        expected_output="Un array JSON con objetos title y description",
        agent=strategist,
    )
    critique_task = Task(
        description=CRITIC_PROMPT.format(
            name=channel.name,
            niche=channel.niche or "general",
            count=count,
        ),
        expected_output=f"Un array JSON con exactamente {count} objetos title y description",
        agent=chief_editor,
        context=[propose_task],
    )

    crew = Crew(
        agents=[strategist, chief_editor],
        tasks=[propose_task, critique_task],
        verbose=False,
    )
    result = crew.kickoff()
    return _parse_plan_result(str(result))[:count]


def _strip_markup(text: str) -> str:
    """Red de seguridad: quita formato markdown residual del guion final."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def generate_script(channel, entry) -> str:
    """Congreso de agentes: el guionista escribe, el editor pule y el director
    de voz deja el texto limpio para síntesis TTS."""
    writer = Agent(
        role="Script Writer",
        goal="Escribir guiones atractivos para audio",
        backstory="Experto en escritura para podcast y narración hablada.",
        llm=get_script_llm(),
        verbose=False,
    )
    editor = Agent(
        role="Script Editor",
        goal="Revisar guiones para mejorar ritmo y claridad",
        backstory="Editor con oído para contenido hablado.",
        llm=get_script_llm(),
        verbose=False,
    )
    voice_director = Agent(
        role="Voice Director",
        goal="Dejar el guion listo para síntesis de voz, sin marcas ni indicaciones",
        backstory="Director de doblaje: solo le importa lo que se pronuncia.",
        llm=get_script_llm(),
        verbose=False,
    )

    write_task = Task(
        description=SCRIPT_PROMPT.format(
            format=channel.format,
            title=entry.title,
            description=entry.description or "",
            niche=channel.niche or "general",
        ),
        expected_output="Un guion en español listo para leer en voz alta",
        agent=writer,
    )

    edit_task = Task(
        description="Revisa el guion anterior, mejora ritmo y claridad, y devuelve SOLO el texto final del guion.",
        expected_output="Guion final pulido",
        agent=editor,
        context=[write_task],
    )

    clean_task = Task(
        description=CLEAN_PROMPT,
        expected_output="Texto hablable limpio, sin markdown ni indicaciones",
        agent=voice_director,
        context=[edit_task],
    )

    crew = Crew(
        agents=[writer, editor, voice_director],
        tasks=[write_task, edit_task, clean_task],
        verbose=False,
    )
    result = crew.kickoff()
    return _strip_markup(str(result))
