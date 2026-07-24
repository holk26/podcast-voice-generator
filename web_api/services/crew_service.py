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


RESEARCH_PROMPT = """Eres un investigador. Para un episodio de tipo "{format}" titulado "{title}"
(nicho: {niche}; descripción: {description}), recopila los puntos clave: datos interesantes,
contexto, curiosidades y ángulos que harán el episodio rico y entretenido.
Devuelve una lista de 6-10 puntos en texto plano, sin numerar páginas ni citar fuentes."""

OUTLINE_PROMPT = """Eres el planificador de un episodio de audio de tipo "{format}" titulado "{title}"
(nicho: {niche}) de unos {minutes} minutos. Diseña un esquema con {sections} secciones
(incluye una introducción con gancho y un cierre memorable).
Devuelve EXACTAMENTE este JSON:
[
  {{"title": "Nombre de la sección", "points": "qué contar en ella"}},
  ...
]
Solo JSON, sin explicaciones."""

SECTION_PROMPT = """Eres un guionista de audio escribiendo una sección de un episodio de tipo "{format}"
titulado "{title}" (nicho: {niche}).
Esquema completo del episodio:
{outline}

Investigación disponible:
{research}

Escribe SOLO el texto de la sección "{section_title}" ({section_points}): entre 250 y 400 palabras,
en español, natural al leerse en voz alta, con transiciones suaves, sin notas de producción
ni encabezados. Continúa el tono del episodio sin repetir la introducción si ya pasó."""

SCRIPT_PROMPT = """Eres un guionista de audio. Escribe un guion completo en español para un episodio de tipo "{format}"
titulado "{title}". Descripción: {description}. Nicho: {niche}.
El guion debe tener entre 300 y 800 palabras, ser natural al leerse en voz alta y no incluir notas de producción.
Devuelve SOLO el texto del guion, sin introducciones ni comentarios."""

EDIT_FULL_PROMPT = """Eres el editor de un episodio de audio. Revisa el guion completo siguiente:
elimina repeticiones, mejora las transiciones entre secciones y el ritmo general,
y asegúrate de que se lee natural en voz alta. Devuelve SOLO el guion completo final,
sin comentarios ni notas.

Guion:
{script}"""

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
    # Empieza por el delimitador que aparezca primero ([ de un array o { de un objeto)
    bracket = raw.find("[")
    brace = raw.find("{")
    if bracket != -1 and (brace == -1 or bracket < brace):
        start, closer = bracket, "]"
    elif brace != -1:
        start, closer = brace, "}"
    else:
        return raw
    end = raw.rfind(closer)
    if end == -1 or end < start:
        return raw[start:]  # posible JSON truncado: lo repara _close_truncated_json
    return raw[start : end + 1]


def _close_truncated_json(raw: str) -> str:
    """Cierra strings, arrays y objetos abiertos (LLM cortó por max tokens)."""
    out = raw.rstrip()
    if out.count('"') % 2 == 1:
        out += '"'
    open_brackets = out.count("[") - out.count("]")
    open_braces = out.count("{") - out.count("}")
    # Cierra primero el último objeto de un array de objetos
    if open_braces > 0:
        out += "}" * open_braces
    if open_brackets > 0:
        out += "]" * open_brackets
    return out


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
    for candidate in (cleaned, _close_truncated_json(cleaned)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        repaired = _repair_json(candidate)
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


def generate_script(channel, entry, target_minutes: int = 10, on_progress=None) -> str:
    """Congreso de agentes: investigador → planificador → guionista por
    secciones → editor → director de voz. Genera guiones largos
    (~150 palabras/minuto hablado).

    on_progress(step, message, content=None) se invoca al empezar cada paso y
    al terminarlo con la salida del agente (historial completo para SSE/UI).
    """
    def emit(step: str, message: str, content: str | None = None) -> None:
        if on_progress:
            on_progress(step, message, content)

    def make_agent(role: str, goal: str, backstory: str) -> Agent:
        return Agent(role=role, goal=goal, backstory=backstory,
                     llm=get_script_llm(), verbose=False)

    researcher = make_agent("Researcher", "Recopilar datos y ángulos interesantes",
                            "Periodista de investigación con gran memoria para datos.")
    planner = make_agent("Episode Planner", "Diseñar la estructura del episodio",
                         "Productor veterano de podcasts narrativos.")
    writer = make_agent("Script Writer", "Escribir secciones atractivas para audio",
                        "Experto en escritura para podcast y narración hablada.")
    editor = make_agent("Script Editor", "Unificar y pulir el guion completo",
                        "Editor con oído para contenido hablado.")
    voice_director = make_agent("Voice Director",
                                "Dejar el guion listo para síntesis de voz",
                                "Director de doblaje: solo le importa lo que se pronuncia.")

    fmt = channel.format
    niche = channel.niche or "general"
    desc = entry.description or ""

    # 1. Investigación
    emit("research", "El investigador recopila datos y curiosidades…")
    research = _run_single_task(
        researcher,
        RESEARCH_PROMPT.format(format=fmt, title=entry.title, niche=niche, description=desc),
        "Lista de puntos clave",
    )
    emit("research_done", "Investigación lista", research)

    # 2. Esquema
    n_sections = max(3, min(8, target_minutes // 2))
    emit("outline", f"El planificador diseña el esquema ({n_sections} secciones)…")
    outline_raw = _run_single_task(
        planner,
        OUTLINE_PROMPT.format(format=fmt, title=entry.title, niche=niche,
                              minutes=target_minutes, sections=n_sections),
        "Un array JSON de secciones",
    )
    emit("outline_done", "Esquema del episodio", outline_raw)

    try:
        sections = _parse_json_flexible(outline_raw)
        if not isinstance(sections, list) or not sections:
            raise ValueError("esquema vacío")
        sections = [
            {"title": str(s.get("title", f"Sección {i + 1}")),
             "points": str(s.get("points", ""))}
            for i, s in enumerate(sections)
        ]
    except Exception:
        # Fallback: una sola sección con todo el tema
        sections = [{"title": entry.title, "points": desc}]

    # 3. Escritura por secciones
    parts: list[str] = []
    for i, section in enumerate(sections):
        emit("write_section",
             f"El guionista escribe la sección {i + 1}/{len(sections)}: «{section['title']}»…")
        part = _run_single_task(
            writer,
            SECTION_PROMPT.format(
                format=fmt, title=entry.title, niche=niche,
                outline=outline_raw, research=research,
                section_title=section["title"], section_points=section["points"],
            ),
            "Texto de la sección en español",
        )
        emit(f"write_section_done", f"Sección {i + 1}/{len(sections)} escrita", part)
        parts.append(part.strip())

    draft = "\n\n".join(parts)

    # 4. Edición completa
    emit("editor", "El editor unifica y pule el guion completo…")
    polished = _run_single_task(
        editor,
        EDIT_FULL_PROMPT.format(script=draft),
        "Guion completo pulido",
    )
    emit("editor_done", "Versión pulida por el editor", polished)

    # 5. Limpieza para TTS
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


SEASON_PROMPT = """Eres el estratega jefe del canal "{name}" ({format}) sobre el nicho "{niche}".
Diseña la TEMPORADA {season} completa a largo plazo: {weeks} semanas, {per_week} episodios por semana
({total} episodios en total).
Piensa como un showrunner: un arco temático que enganche, progresión entre episodios,
variedad para no repetir, y un cierre de temporada memorable.
Devuelve EXACTAMENTE este JSON:
{{
  "theme": "Tema o arco de la temporada en una frase",
  "episodes": [
    {{"title": "Título del episodio", "description": "Descripción corta", "week": 1}},
    ...
  ]
}}
Cada "week" es un entero entre 1 y {weeks}. Solo JSON, sin explicaciones."""


def generate_season(channel, season_number: int = 1, weeks: int = 4, on_progress=None) -> dict:
    """Estratega de temporadas: diseña un arco completo con episodios por semana.

    Devuelve {"theme": str, "episodes": [{title, description, week}]}.
    """
    def emit(step: str, message: str, content: str | None = None) -> None:
        if on_progress:
            on_progress(step, message, content)

    per_week = max(1, getattr(channel, "episodes_per_week", 2) or 2)
    showrunner = Agent(
        role="Season Showrunner",
        goal="Diseñar temporadas de podcast con arco a largo plazo",
        backstory="Showrunner veterano: piensa en temporadas, arcos y fidelización.",
        llm=get_planning_llm(),
        verbose=False,
    )

    emit("showrunner",
         f"El showrunner diseña la temporada {season_number} de «{channel.name}» ({weeks} semanas)…")
    raw = _run_single_task(
        showrunner,
        SEASON_PROMPT.format(
            name=channel.name,
            format=channel.format,
            niche=channel.niche or "general",
            season=season_number,
            weeks=weeks,
            per_week=per_week,
            total=weeks * per_week,
        ),
        "Un objeto JSON con theme y episodes",
    )
    emit("showrunner_done", f"Temporada {season_number} diseñada", raw)

    data = _parse_json_flexible(raw)
    if not isinstance(data, dict) or not isinstance(data.get("episodes"), list):
        raise ValueError("La temporada no tiene el formato esperado")

    episodes = []
    for item in data["episodes"]:
        try:
            week = int(item.get("week", 1))
        except (TypeError, ValueError):
            week = 1
        episodes.append({
            "title": str(item.get("title", "")).strip(),
            "description": str(item.get("description", "")).strip(),
            "week": max(1, min(week, weeks)),
        })
    episodes = [e for e in episodes if e["title"]]
    if not episodes:
        raise ValueError("La temporada no contiene episodios")

    return {"theme": str(data.get("theme", "")).strip(), "episodes": episodes}
