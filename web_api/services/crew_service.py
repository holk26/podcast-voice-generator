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

CHANNEL_SUGGEST_PROMPT = """Eres un estratega de canales de podcast. Propón UN canal de audio atractivo.
{hint_line}
Devuelve EXACTAMENTE este JSON:
{{"name": "Nombre corto y llamativo", "description": "Descripción de 1-2 frases", "niche": "nicho temático", "format": "podcast"}}
El campo "format" debe ser uno de: podcast, news, meditation, motivation.
Solo JSON, sin explicaciones."""


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


def _run_single_task(agent: Agent, description: str, expected_output: str) -> str:
    """Ejecuta una tarea con un agente y devuelve su salida como texto."""
    task = Task(description=description, expected_output=expected_output, agent=agent)
    return str(Crew(agents=[agent], tasks=[task], verbose=False).kickoff())


def generate_plan(channel, count: int = 5, on_progress=None) -> List[PlanEntryCreate]:
    """Congreso de agentes: el estratega propone ideas en bruto y el editor
    jefe las debate, filtra y pule hasta quedarse con las mejores.

    on_progress(step, message, content=None) se invoca al empezar cada paso y
    al terminarlo con la salida del agente (historial completo para SSE/UI).
    """
    def emit(step: str, message: str, content: str | None = None) -> None:
        if on_progress:
            on_progress(step, message, content)

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

    emit("strategist", f"El estratega propone ideas para «{channel.name}»…")
    raw_ideas = _run_single_task(
        strategist,
        PLAN_PROMPT.format(
            name=channel.name,
            format=channel.format,
            niche=channel.niche or "general",
            count=count + 3,  # ideas de sobra para que el editor descarte
        ),
        "Un array JSON con objetos title y description",
    )
    emit("strategist_done", "El estratega terminó su propuesta", raw_ideas)

    emit("critic", "El editor jefe debate y selecciona las mejores…")
    final = _run_single_task(
        chief_editor,
        CRITIC_PROMPT.format(
            name=channel.name,
            niche=channel.niche or "general",
            count=count,
        )
        + f"\n\nIdeas propuestas por el estratega:\n{raw_ideas}",
        f"Un array JSON con exactamente {count} objetos title y description",
    )
    emit("critic_done", "El editor jefe publicó su selección", final)

    emit("parse", "Validando el plan final…")
    return _parse_plan_result(final)[:count]


def _strip_markup(text: str) -> str:
    """Red de seguridad: quita formato markdown residual del guion final."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def generate_script(channel, entry, on_progress=None) -> str:
    """Congreso de agentes: el guionista escribe, el editor pule y el director
    de voz deja el texto limpio para síntesis TTS.

    on_progress(step, message, content=None) se invoca al empezar cada paso y
    al terminarlo con la salida del agente (historial completo para SSE/UI).
    """
    def emit(step: str, message: str, content: str | None = None) -> None:
        if on_progress:
            on_progress(step, message, content)

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

    emit("writer", f"El guionista escribe «{entry.title}»…")
    draft = _run_single_task(
        writer,
        SCRIPT_PROMPT.format(
            format=channel.format,
            title=entry.title,
            description=entry.description or "",
            niche=channel.niche or "general",
        ),
        "Un guion en español listo para leer en voz alta",
    )
    emit("writer_done", "Borrador del guionista", draft)

    emit("editor", "El editor pule ritmo y claridad…")
    polished = _run_single_task(
        editor,
        "Revisa el guion siguiente, mejora ritmo y claridad, y devuelve SOLO "
        f"el texto final del guion.\n\nGuion:\n{draft}",
        "Guion final pulido",
    )
    emit("editor_done", "Versión pulida por el editor", polished)

    emit("voice_director", "El director de voz lo deja listo para TTS…")
    final = _run_single_task(
        voice_director,
        CLEAN_PROMPT + f"\n\nGuion:\n{polished}",
        "Texto hablable limpio, sin markdown ni indicaciones",
    )
    emit("voice_director_done", "Texto final para síntesis de voz", final)

    return _strip_markup(final)


VALID_FORMATS = {"podcast", "news", "meditation", "motivation"}


def suggest_channel(hint: str | None = None) -> dict:
    """Propone un canal completo (name/description/niche/format) con un agente."""
    strategist = Agent(
        role="Channel Strategist",
        goal="Idear canales de podcast atractivos",
        backstory="Experto en formatos de audio y nichos de audiencia.",
        llm=get_planning_llm(),
        verbose=False,
    )
    hint_line = f"Tema indicado por el usuario: {hint}." if hint else "Elige un tema popular con gancho."
    result = _run_single_task(
        strategist,
        CHANNEL_SUGGEST_PROMPT.format(hint_line=hint_line),
        "Un objeto JSON con name, description, niche y format",
    )
    data = _parse_json_flexible(result)
    if not isinstance(data, dict):
        raise ValueError("La sugerencia no es un objeto JSON")
    if data.get("format") not in VALID_FORMATS:
        data["format"] = "podcast"
    return {
        "name": str(data.get("name", "")).strip(),
        "description": str(data.get("description", "")).strip(),
        "niche": str(data.get("niche", "")).strip(),
        "format": data["format"],
    }
