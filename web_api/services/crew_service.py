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
{specs}
Devuelve una lista de 6-10 puntos en texto plano, sin numerar páginas ni citar fuentes."""

OUTLINE_PROMPT = """Eres el planificador de un episodio de audio de tipo "{format}" titulado "{title}"
(nicho: {niche}) de unos {minutes} minutos. Diseña un esquema con {sections} secciones
(incluye una introducción con gancho y un cierre memorable).
{specs}
Devuelve EXACTAMENTE este JSON:
[
  {{"title": "Nombre de la sección", "points": "qué contar en ella"}},
  ...
]
Solo JSON, sin explicaciones."""

SECTION_PROMPT = """Eres un guionista de audio escribiendo la sección {section_number} de {total_sections} de un episodio
de tipo "{format}" titulado "{title}" (nicho: {niche}).
Esquema completo del episodio:
{outline}

Investigación disponible:
{research}

Escribe SOLO el texto de la sección "{section_title}" ({section_points}): entre {min_words} y {max_words}
palabras (es OBLIGATORIO llegar al mínimo), natural al leerse en voz alta, con transiciones suaves,
sin notas de producción ni encabezados.
{position_rules}
{specs}
RESPETA el idioma indicado en las especificaciones."""

SCRIPT_PROMPT = """Eres un guionista de audio. Escribe un guion completo en español para un episodio de tipo "{format}"
titulado "{title}". Descripción: {description}. Nicho: {niche}.
El guion debe tener entre 300 y 800 palabras, ser natural al leerse en voz alta y no incluir notas de producción.
Devuelve SOLO el texto del guion, sin introducciones ni comentarios."""

EDIT_FULL_PROMPT = """Eres el editor de un episodio de audio. Revisa el guion completo siguiente:
elimina repeticiones, mejora las transiciones entre secciones y el ritmo general,
y asegúrate de que se lee natural en voz alta. NO ACORTES el guion: conserva toda su
longitud y contenido. Devuelve SOLO el guion completo final, sin comentarios ni notas.

Guion:
{script}"""

CLEAN_PROMPT = """Del guion anterior, prepara la versión FINAL PARA SÍNTESIS DE VOZ (TTS).
Elimina TODO lo que no deba leerse en voz alta: notas de producción, indicaciones
("Intro Musical", "Narrador:", "Pausa", efectos de sonido), formato markdown
(**, ##, *), títulos de sección y cualquier comentario técnico.
NO ACORTES ni resumas: conserva TODO el contenido y la longitud.

EXPRESIVIDAD (motor Higgs): inserta UN token de emoción al inicio de cada
sección o cambio de tono claro, usando SOLO esta lista cerrada:
{emotions}
Formato exacto: <|emotion:nombre_en_inglés|> — ejemplo: "<|emotion:enthusiasm|> Hoy vamos a…"
No traduzcas los tokens, no inventes otros, no uses más de uno por párrafo.
Conserva intactos los tokens <|…|> ya presentes.

Devuelve SOLO el texto hablable, tal cual debe pronunciarse."""

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

    prompt = PLAN_PROMPT.format(
        name=channel.name,
        format=channel.format,
        niche=channel.niche or "general",
        count=count + 3,  # ideas de sobra para que el editor descarte
    )
    emit("strategist", f"El estratega propone ideas para «{channel.name}»…", prompt)
    raw_ideas = _run_single_task(
        strategist, prompt, "Un array JSON con objetos title y description"
    )
    emit("strategist_done", "El estratega terminó su propuesta", raw_ideas)

    prompt = CRITIC_PROMPT.format(
        name=channel.name,
        niche=channel.niche or "general",
        count=count,
    ) + f"\n\nIdeas propuestas por el estratega:\n{raw_ideas}"
    emit("critic", "El editor jefe debate y selecciona las mejores…", prompt)
    final = _run_single_task(
        chief_editor, prompt,
        f"Un array JSON con exactamente {count} objetos title y description",
    )
    emit("critic_done", "El editor jefe publicó su selección", final)

    emit("parse", "Validando el plan final…")
    return _parse_plan_result(final)[:count]


_META_PREFIX_RE = re.compile(
    r"^(guion|aquí|texto|versión|script|borrador|claro|por supuesto|vale|perfecto"
    r"|here|sure|certainly|translation|translated|let me)[^\n]*:\s*",
    re.IGNORECASE,
)

# Rechazos del LLM: si la "salida" es una negativa, no es un guion válido.
_REFUSAL_RE = re.compile(
    r"(i can'?t assist|i cannot assist|i'?m sorry|lo siento.{0,40}(no puedo|no me es posible)"
    r"|no puedo (ayudar|cumplir|generar|escribir)|can'?t help with that"
    r"|as an ai\b|como (modelo de )?ia\b)",
    re.IGNORECASE,
)


def _ensure_valid_script(text: str, min_words: int = 100) -> str:
    """Red final: un rechazo o un texto irrisorio nunca debe llegar a TTS."""
    words = len(text.split())
    if _REFUSAL_RE.search(text[:500]):
        raise ValueError(
            f"El LLM rechazó generar el guion (modelo inadecuado o filtro): {text[:120]!r}"
        )
    if words < min_words:
        raise ValueError(
            f"El guion generado es demasiado corto ({words} palabras, mínimo {min_words})"
        )
    return text

# Líneas de meta-comentario del LLM (introducciones/cierres que NO son guion)
_META_LINE_RE = re.compile(
    r"(me alegra presentarte|versión final del guion|texto hablable|a continuación"
    r"|este es el texto final|listo para síntesis|espero que (te )?sirva"
    r"|here is the (final )?script|ready for (voice|tts))",
    re.IGNORECASE,
)


def _strip_markup(text: str) -> str:
    """Red de seguridad: quita formato markdown y meta-comentarios del LLM."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.strip()
    # Quita primeras líneas meta ("Guion revisado y corregido:", "Aquí está el guion:"...)
    lines = text.split("\n", 1)
    if len(lines) == 2 and _META_PREFIX_RE.match(lines[0].strip()):
        text = lines[1].strip()
    text = _META_PREFIX_RE.sub("", text, count=1).strip()
    # Quita bloques meta al inicio (párrafos enteros de presentación)
    while True:
        first_block, sep, rest = text.partition("\n\n")
        if sep and _META_LINE_RE.search(first_block) and len(first_block) < 400:
            text = rest.strip()
        else:
            break
    # Quita líneas meta sueltas al inicio
    while True:
        first_line, sep, rest = text.partition("\n")
        if sep and _META_LINE_RE.search(first_line) and len(first_line) < 200:
            text = rest.strip()
        else:
            break
    # Quita líneas meta sueltas al final ("Este es el texto final...")
    while True:
        rest, sep, last_line = text.rpartition("\n")
        if sep and _META_LINE_RE.search(last_line) and len(last_line) < 200:
            text = rest.strip()
        else:
            break
    return text


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
    specs = _specs(channel)
    prompt = RESEARCH_PROMPT.format(format=fmt, title=entry.title, niche=niche, description=desc, specs=specs)
    emit("research", "El investigador recopila datos y curiosidades…", prompt)
    research = _run_single_task(researcher, prompt, "Lista de puntos clave")
    emit("research_done", "Investigación lista", research)

    # 2. Esquema
    # Con modelos pequeños cada sección rinde ~250-350 palabras; mejor más
    # secciones que pedir más palabras por sección (no lo cumple).
    n_sections = max(3, min(10, target_minutes))
    prompt = OUTLINE_PROMPT.format(format=fmt, title=entry.title, niche=niche,
                                   minutes=target_minutes, sections=n_sections, specs=specs)
    emit("outline", f"El planificador diseña el esquema ({n_sections} secciones)…", prompt)
    outline_raw = _run_single_task(planner, prompt, "Un array JSON de secciones")
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
    total = len(sections)
    for i, section in enumerate(sections):
        if i == 0:
            position_rules = (
                "Esta es la PRIMERA sección: abre con el gancho del episodio. "
                "NO te despidas ni cierres."
            )
        elif i == total - 1:
            position_rules = (
                "Esta es la ÚLTIMA sección: solo aquí va el cierre y la despedida "
                "del episodio. NO abras con una nueva introducción."
            )
        else:
            position_rules = (
                "Esta es una sección INTERMEDIA: NO saludes, NO te despidas, "
                "NO cierres el episodio y NO hagas introducción; continúa el hilo "
                "directamente y deja una transición abierta hacia la siguiente sección."
            )
        # Palabras por sección según la duración objetivo (~150 palabras/min)
        per_section = max(300, round(target_minutes * 150 / total))
        prompt = SECTION_PROMPT.format(
            format=fmt, title=entry.title, niche=niche,
            outline=outline_raw, research=research,
            section_title=section["title"], section_points=section["points"],
            section_number=i + 1, total_sections=total,
            position_rules=position_rules,
            specs=specs,
            min_words=round(per_section * 0.9), max_words=round(per_section * 1.25),
        )
        emit("write_section",
             f"El guionista escribe la sección {i + 1}/{len(sections)}: «{section['title']}»…",
             prompt)
        part = _run_single_task(writer, prompt, "Texto de la sección en español")
        emit(f"write_section_done", f"Sección {i + 1}/{len(sections)} escrita", part)
        parts.append(part.strip())

    # 3b. Garantía de longitud: el modelo a veces escribe de menos; las secciones
    # cortas se expanden con ejemplos y detalle hasta llegar al objetivo.
    target_words = round(target_minutes * 130)
    for i, part in enumerate(parts):
        if len(part.split()) >= per_section * 0.7:
            continue
        emit("expand_section",
             f"La sección {i + 1} quedó corta; el guionista la expande…")
        expand_prompt = (
            f"Esta sección de un episodio titulado \"{entry.title}\" quedó demasiado corta. "
            f"Expándela hasta al menos {round(per_section * 0.9)} palabras añadiendo ejemplos, "
            f"historias y detalle práctico, manteniendo el mismo tono hablado y sin repetir ideas. "
            f"Devuelve SOLO la sección completa expandida, sin comentarios.\n\n"
            f"Sección:\n{part}"
        )
        expanded = _run_single_task(writer, expand_prompt, "Sección expandida")
        if len(expanded.split()) > len(part.split()):
            parts[i] = expanded.strip()
            emit("expand_section_done", f"Sección {i + 1} expandida", expanded)

    # Segunda pasada si aún falta mucho texto
    total_words = sum(len(p.split()) for p in parts)
    if total_words < target_words * 0.75:
        emit("expand_global", "El guion es corto para la duración; expansión global…")
        deficit = target_words - total_words
        global_prompt = (
            f"El guion del episodio \"{entry.title}\" tiene {total_words} palabras y necesita "
            f"unas {target_words}. Añade aproximadamente {deficit} palabras más de contenido "
            f"valioso (ejemplos, historias, consejos prácticos) distribuidas en el guion, "
            f"sin repetir y manteniendo el tono hablado. Devuelve SOLO el guion completo ampliado.\n\n"
            f"Guion:\n" + "\n\n".join(parts)
        )
        expanded = _run_single_task(writer, global_prompt, "Guion completo ampliado")
        if len(expanded.split()) > total_words:
            emit("expand_global_done", "Guion ampliado", expanded)
            parts = [expanded]

    # Sin pasada de "editor": con modelos pequeños recorta la mitad del guion.
    # Las secciones ya vienen coherentes del esquema compartido.
    polished = "\n\n".join(parts)

    # 5. Limpieza para TTS
    from core.emotion_tags import HIGGS_EMOTION_NAMES  # lista cerrada para el prompt
    emotions = ", ".join(HIGGS_EMOTION_NAMES)
    prompt = CLEAN_PROMPT.format(emotions=emotions) + f"\n\nGuion:\n{polished}"
    emit("voice_director", "El director de voz lo deja listo para TTS…", prompt)
    cleaned = _run_single_task(
        voice_director, prompt,
        "Texto hablable limpio, sin markdown ni indicaciones",
    )
    # Modelos pequeños a veces colapsan un guion largo a unas líneas (solo la
    # despedida, un resumen…). Si la limpieza encoge demasiado el texto, se
    # descarta y se usa el guion sin limpiar (_strip_markup ya quita markdown).
    if len(cleaned.split()) < 0.4 * len(polished.split()):
        emit("voice_director_fallback",
             f"La limpieza colapsó el guion ({len(cleaned.split())} de "
             f"{len(polished.split())} palabras); se usa el texto sin limpiar",
             cleaned)
        final = polished
    else:
        final = cleaned
    emit("voice_director_done", "Texto final para síntesis de voz", final)

    # 6. El Director de Producción supervisa: decide si el guion cumple el
    # brief (idioma, tema) y ordena correcciones SOLO si hacen falta.
    director = make_agent("Production Director",
                          "Supervisar que cada guion cumple el brief del canal",
                          "Director de producción: nada sale al aire sin su visto bueno.")
    es_hint = round(_spanish_ratio(final) * 100)
    director_prompt = DIRECTOR_PROMPT.format(
        specs=specs, title=entry.title, es_hint=es_hint, script=final[:3000],
    )
    emit("director", "El Director de Producción revisa el guion…", director_prompt)
    verdict_raw = _run_single_task(
        director, director_prompt,
        'Un JSON {"action": "ok"|"translate_en"|"translate_es", "reason": "..."}',
    )
    emit("director_done", "Veredicto del Director", verdict_raw)

    action = "ok"
    reason = ""
    try:
        verdict = _parse_json_flexible(verdict_raw)
        if isinstance(verdict, dict):
            action = str(verdict.get("action", "ok")).strip().lower()
            reason = str(verdict.get("reason", "")).strip()
    except Exception:
        # Veredicto ilegible: no se toca el guion (seguro por defecto)
        action = "ok"

    if action in ("translate_en", "translate_es"):
        target_lang = "inglés" if action == "translate_en" else "español"
        translator = make_agent("Translator",
                                "Traducir guiones de forma fiel",
                                "Traductor profesional: fiel al texto, sin añadir nada.")
        emit("translate", f"Por orden del Director, el traductor pasa el guion a {target_lang}…",
             reason or None)
        prompt_template = TRANSLATE_EN_PROMPT if action == "translate_en" else TRANSLATE_ES_PROMPT
        translated = _run_single_task(
            translator,
            prompt_template + f"\n\n{final}",
            f"Faithful translation to {target_lang}",
        )
        # Misma guarda que en la limpieza: una traducción que colapsa el
        # guion se descarta y se mantiene el texto original.
        if len(translated.split()) < 0.4 * len(final.split()):
            emit("translate_fallback",
                 f"La traducción colapsó el guion ({len(translated.split())} de "
                 f"{len(final.split())} palabras); se mantiene el original",
                 translated)
        else:
            final = translated
        emit("translate_done", f"Guion traducido a {target_lang}", final)
    else:
        emit("approved", "El Director aprueba el guion sin cambios ✓",
             reason or None)

    return _ensure_valid_script(_strip_markup(final))


def _clean_dialogue_lines(text: str) -> str:
    """Deja solo líneas de diálogo válidas y sus continuaciones.

    - Normaliza "Alejandra:Texto" a "Alejandra: Texto".
    - Elimina encabezados, bullets, paréntesis de producción y líneas meta.
    - Colapsa líneas vacías múltiples.
    """
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        # Quita marcadores markdown y notas de producción
        if stripped.startswith(("* ", "- ", "# ", "## ", "(", "[")):
            continue
        if stripped.lower().startswith(("mini repaso", "repaso", "review", "notes", "espera")):
            continue
        # Normaliza el espacio tras el nombre del speaker
        stripped = re.sub(r"^(Alejandra|Homero):\s*", r"\1: ", stripped, flags=re.IGNORECASE)
        out.append(stripped)
    # Colapsa múltiples líneas vacías
    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def generate_dialogue_script(channel, entry, target_minutes: int = 10, on_progress=None) -> str:
    """Genera un guion en formato diálogo bilingüe Alejandra-Homero por secciones.

    on_progress(step, message, content=None) se invoca al empezar y terminar.
    """
    def emit(step: str, message: str, content: str | None = None) -> None:
        if on_progress:
            on_progress(step, message, content)

    planner = Agent(
        role="Dialogue Planner",
        goal="Diseñar la estructura didáctica de un episodio bilingüe",
        backstory="Productor experto en cursos de idiomas por audio.",
        llm=get_script_llm(),
        verbose=False,
    )
    writer = Agent(
        role="Bilingual Dialogue Writer",
        goal="Escribir diálogos didácticos inglés-español entre profesora y alumno",
        backstory="Guionista especializado en podcasts educativos bilingües con dos voces.",
        llm=get_script_llm(),
        verbose=False,
    )

    specs = _specs(channel)
    niche = channel.niche or "general"
    desc = entry.description or ""

    # 1. Planificar secciones
    n_sections = max(3, min(10, target_minutes))
    outline_prompt = DIALOGUE_OUTLINE_PROMPT.format(
        title=entry.title,
        niche=niche,
        description=desc,
        minutes=target_minutes,
        sections=n_sections,
        specs=specs,
    )
    emit("outline", f"El planificador diseña el esquema ({n_sections} secciones)…", outline_prompt)
    outline_raw = _run_single_task(planner, outline_prompt, "Un array JSON de secciones")
    emit("outline_done", "Esquema del episodio", outline_raw)

    sections = None

    def _extract_sections_from_parsed(parsed) -> list[dict] | None:
        """Extrae lista de secciones desde el JSON parseado, manejando
        dicts envueltos como {'sections': [...]} u otras claves comunes."""
        if isinstance(parsed, dict) and not isinstance(parsed, list):
            for key in ("sections", "items", "data", "outline", "episodes"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
        if not isinstance(parsed, list) or len(parsed) == 0:
            return None
        result = []
        for i, s in enumerate(parsed):
            if isinstance(s, dict):
                result.append({
                    "title": str(s.get("title", f"Sección {i + 1}")),
                    "points": str(s.get("points", s.get("description", ""))),
                })
            else:
                result.append({
                    "title": str(s),
                    "points": "",
                })
        return result

    min_acceptable = max(2, n_sections // 2)
    for attempt in range(2):
        try:
            parsed = _parse_json_flexible(outline_raw)
            extracted = _extract_sections_from_parsed(parsed)
            if extracted and len(extracted) >= min_acceptable:
                sections = extracted
                break
            elif extracted and len(extracted) >= 2 and attempt == 1:
                # Segundo intento: aceptar al menos 2 secciones
                sections = extracted
                break
            elif attempt == 0:
                emit("outline", f"Esquema incompleto ({len(extracted) if extracted else 0} secciones), reintentando…")
                stronger_prompt = outline_prompt + (
                    f"\n\nIMPORTANTE: Debes devolver EXACTAMENTE {n_sections} elementos en el array JSON. "
                    f"No menos de {n_sections}. Cada sección es un objeto con 'title' y 'points'."
                )
                outline_raw = _run_single_task(planner, stronger_prompt, "Un array JSON de secciones")
                emit("outline_done", "Esquema reintentado", outline_raw)
        except Exception:
            if attempt == 0:
                emit("outline", "Error parseando esquema, reintentando…")
                outline_raw = _run_single_task(planner, outline_prompt, "Un array JSON de secciones")

    if sections is None or len(sections) < 2:
        # Esquema por defecto si todo lo anterior falló
        n_default = max(3, min(8, target_minutes))
        default_sections = [
            {"title": "Introducción y bienvenida",
             "points": "Saludo, presentación del tema y gancho del episodio"},
        ]
        n_mid = max(1, n_default - 2)
        for j in range(1, n_mid + 1):
            default_sections.append({
                "title": f"Expresión {j}",
                "points": f"Vocabulario y expresiones útiles en inglés con ejemplos prácticos (parte {j})"
            })
        default_sections.append({
            "title": "Repaso y despedida",
            "points": "Mini repaso de lo aprendido y cierre del episodio"
        })
        sections = default_sections
        emit("outline", f"Usando esquema por defecto ({len(sections)} secciones)")

    # 2. Escribir diálogo por secciones
    parts: list[str] = []
    total = len(sections)
    outline_text = json.dumps(sections, ensure_ascii=False)
    for i, section in enumerate(sections):
        if i == 0:
            position_rules = (
                "Esta es la PRIMERA sección: abre con el saludo y el gancho del episodio. "
                "NO te despidas ni cierres."
            )
        elif i == total - 1:
            position_rules = (
                "Esta es la ÚLTIMA sección: incluye el mini repaso y la despedida. "
                "NO abras con una nueva introducción."
            )
        else:
            position_rules = (
                "Esta es una sección INTERMEDIA: NO saludes, NO te despidas, "
                "NO cierres el episodio; continúa el hilo directamente."
            )

        # ~180 palabras/minuto en diálogo bilingüe (pausas, traducciones);
        # el modelo rinde mejor con objetivos ambiciosos por sección.
        words_per_section = max(250, (target_minutes * 180) // total)
        min_words = int(words_per_section * 0.85)
        # Sin techo explícito: pedimos "al menos" min_words y damos margen amplio
        max_words = int(words_per_section * 2.0)

        section_prompt = DIALOGUE_SECTION_PROMPT.format(
            section_number=i + 1,
            total_sections=total,
            title=entry.title,
            outline=outline_text,
            section_title=section["title"],
            section_points=section["points"],
            min_words=min_words,
            max_words=max_words,
            position_rules=position_rules,
            specs=specs,
        )
        emit("dialogue", f"Escribiendo sección {i + 1}/{total}: {section['title']}…", section_prompt)
        raw = _run_single_task(
            writer, section_prompt,
            "Diálogo bilingüe con cada línea prefijada por Alejandra: o Homero:",
        )
        section_text = _strip_markup(raw)
        section_words = len(section_text.split())
        if section_words < min_words * 0.75:
            emit("dialogue", f"Sección {i + 1}/{total} corta ({section_words} palabras, mínimo {min_words}), reintentando…")
            stronger = section_prompt + (
                f"\n\nIMPORTANTE: Tu sección anterior tuvo solo {section_words} palabras. "
                f"Escribe AL MENOS {min_words} palabras. Desarrolla más ejemplos, "
                "más práctica de conversación, más repeticiones. No resumas."
            )
            raw = _run_single_task(
                writer, stronger,
                "Diálogo bilingüe con cada línea prefijada por Alejandra: o Homero:",
            )
            section_text = _strip_markup(raw)
            section_words = len(section_text.split())
            if section_words < min_words * 0.6:
                # Tercer intento con énfasis extremo
                emit("dialogue", f"Sección {i + 1}/{total} aún corta ({section_words} palabras), tercer intento…")
                ultra_strong = section_prompt + (
                    f"\n\nCRÍTICO: Necesitas escribir {min_words} palabras mínimo. "
                    f"Tu intento anterior tuvo {section_words}. "
                    "Cada vez que expliques una expresión: ponla en inglés, pronúnciala, "
                    "da 2-3 ejemplos de uso, pide a Homero que la repita y comente "
                    "en español, y luego da un mini diálogo de práctica. "
                    "No escatimes en palabras."
                )
                raw = _run_single_task(
                    writer, ultra_strong,
                    "Diálogo bilingüe con cada línea prefijada por Alejandra: o Homero:",
                )
                section_text = _strip_markup(raw)
        parts.append(section_text)
        emit("dialogue_part", f"Sección {i + 1}/{total} lista", raw)

    # Separa secciones con línea en blanco para que el parser no las una
    cleaned = "\n\n".join(parts)
    cleaned = _clean_dialogue_lines(cleaned)
    # La limpieza puede quitar los prefijos si interpreta los dos puntos como markdown;
    # reforzamos el formato exacto esperado por el parser.
    min_total_words = max(100, int(target_minutes * 150))
    return _ensure_valid_script(cleaned, min_words=min_total_words)


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

    prompt = SEASON_PROMPT.format(
        name=channel.name,
        format=channel.format,
        niche=channel.niche or "general",
        season=season_number,
        weeks=weeks,
        per_week=per_week,
        total=weeks * per_week,
    )
    emit("showrunner",
         f"El showrunner diseña la temporada {season_number} de «{channel.name}» ({weeks} semanas)…",
         prompt)
    raw = _run_single_task(showrunner, prompt, "Un objeto JSON con theme y episodes")
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


IMPROVE_PROMPT = """Eres un productor ejecutivo de podcasts. Para el canal "{name}" ({format})
sobre el nicho "{niche}", con esta descripción actual:
"{description}"

Reescribe y MEJORA el brief de producción del canal para que sea específico y accionable.
Debe incluir en 4-8 líneas y de forma explícita:
- IDIOMA exacto del contenido hablado (p. ej. "100% español", "narración en español con vocabulario en inglés", "80% inglés / 20% español")
- Audiencia objetivo y nivel
- Tono y estilo (p. ej. cercano, didáctico, energético)
- Estructura de cada episodio (gancho, desarrollo, cierre)
- Reglas concretas que NUNCA se deben romper
Devuelve SOLO el brief, sin introducciones ni comentarios."""

QUALITY_PROMPT = """Eres el control de calidad de un canal de podcast. Revisa el guion siguiente
contra las especificaciones del canal y CORRÍGELO si se desvía.

ESPECIFICACIONES DEL CANAL (obligatorias):
{specs}

Comprueba sobre todo:
1. IDIOMA: ¿el guion respeta el idioma indicado en las especificaciones?
   SI NO CUMPLE: REESCRIBE el guion completo en el idioma correcto (tradúcelo
   fielmente, manteniendo estructura y duración). Esto es OBLIGATORIO.
2. TEMA: ¿trata exactamente «{title}» del nicho "{niche}"?
3. FORMATO: ¿es texto hablable natural, sin notas de producción ni markdown?

Devuelve SOLO el guion final corregido (o el original si ya cumple),
sin comentarios, sin encabezados, sin frases como "Guion revisado".

Guion:
{script}"""


DIRECTOR_PROMPT = """Eres el director de producción de un canal de podcast. Revisa el guion
contra las especificaciones del canal y decide si necesita corrección de IDIOMA.

ESPECIFICACIONES DEL CANAL:
{specs}

Título del episodio: "{title}"
Detección automática: el guion parece ~{es_hint}% español.

Reglas de decisión:
- "ok": el idioma del guion ya cumple las especificaciones (o están en duda).
- "translate_en": las especificaciones exigen inglés y el guion está en español.
- "translate_es": las especificaciones exigen español y el guion está en inglés.
Ante la duda, responde "ok". No traduzcas si no es estrictamente necesario.

Responde SOLO este JSON, sin comentarios:
{{"action": "ok|translate_en|translate_es", "reason": "justificación en una frase"}}

Guion:
{script}"""

TRANSLATE_EN_PROMPT = """Translate the following Spanish podcast script to natural, spoken English.
Keep the same structure, sections and approximate length. Keep names and proper nouns.
Output ONLY the English text, nothing else — no comments, no headers."""

TRANSLATE_ES_PROMPT = """Traduce el siguiente guion de podcast del inglés a un español natural y hablado.
Mantén la misma estructura, secciones y longitud aproximada. Conserva nombres propios.
Devuelve SOLO el texto en español, nada más — sin comentarios ni encabezados."""


DIALOGUE_OUTLINE_PROMPT = """Eres el planificador de un episodio educativo bilingüe titulado "{title}"
(nicho: {niche}; descripción: {description}) de unos {minutes} minutos.
Diseña un esquema con {sections} secciones didácticas. Cada sección debe enseñar
1-2 expresiones o vocabulario de inglés con ejemplos prácticos.
{specs}
Devuelve EXACTAMENTE este JSON:
[
  {{"title": "Nombre de la sección", "points": "expresiones y ejemplos a cubrir"}},
  ...
]
Solo JSON, sin explicaciones."""

DIALOGUE_SECTION_PROMPT = """Eres un guionista de podcasts educativos bilingües. Escribe la sección {section_number} de {total_sections} de un episodio en formato diálogo entre:
- Alejandra: profesora de inglés, voz femenina, paciente y clara.
- Homero: alumno, voz masculina, curioso y algo informal.

REGLAS OBLIGATORIAS:
- Cada línea debe empezar EXACTAMENTE con "Alejandra: " o "Homero: " (nombre, dos puntos, espacio).
- NO uses comillas, paréntesis de producción, notas de escena ni acotaciones.
- Alejandra presenta una frase, vocabulario o expresión en inglés, la pronuncia y luego explica el significado y uso en español.
- Homero pregunta, repite o pide ejemplos; usa español para dudas y puede intentar decir la frase en inglés con acento marcado para practicar.
- Mezcla aproximadamente 50% inglés / 50% español.
- Tono cercano, motivador y didáctico.
- No uses markdown, encabezados ni notas de producción.
- {position_rules}

Título del episodio: {title}
Esquema completo: {outline}
Sección actual: "{section_title}" — {section_points}
Escribe AL MENOS {min_words} palabras para esta sección. Esto es OBLIGATORIO.
Desarrolla cada expresión con múltiples ejemplos, repeticiones de práctica y conversación natural.
No resumas, no abrevies: cada línea de diálogo cuenta como palabra.
Si terminas antes de {min_words} palabras, añade más ejemplos y práctica de conversación.
{specs}

Devuelve SOLO el diálogo de esta sección, línea por línea. Empieza directamente con "Alejandra: " o "Homero: "."""


_DUAL_SPEAKER_HINT_RE = re.compile(r"Alejandra.*Homero|Homero.*Alejandra|diálogo|dialogue", re.IGNORECASE)
_ENGLISH_HINT_RE = re.compile(r"ingl[eé]s|english", re.IGNORECASE)
_ES_STOPWORDS = re.compile(
    r"\b(el|la|los|las|de|del|que|en|por|para|con|una|este|esta|hoy|vamos|nuestro|también)\b",
    re.IGNORECASE,
)
_EN_STOPWORDS = re.compile(
    r"\b(the|and|you|your|is|are|to|of|in|for|with|we|this|today)\b",
    re.IGNORECASE,
)


def _needs_english(specs: str) -> bool:
    return bool(_ENGLISH_HINT_RE.search(specs))


def _is_dialogue_mode(channel) -> bool:
    if getattr(channel, "num_speakers", 1) >= 2:
        return True
    text = f"{channel.name} {channel.brief or ''}"
    return bool(_DUAL_SPEAKER_HINT_RE.search(text))


def _spanish_ratio(text: str) -> float:
    es = len(_ES_STOPWORDS.findall(text))
    en = len(_EN_STOPWORDS.findall(text))
    return es / max(1, es + en)


def _specs(channel) -> str:
    """Bloque de especificaciones del canal para los prompts (si tiene brief)."""
    brief = getattr(channel, "brief", None)
    if brief:
        return f"ESPECIFICACIONES DEL CANAL (obligatorias):\n{brief}"
    return (
        f"Canal: {channel.name} ({channel.format}), nicho: {channel.niche or 'general'}. "
        "Idioma del contenido: español salvo que el título/tema indique lo contrario."
    )


def improve_channel_prompt(channel) -> str:
    """Agente optimizador: convierte la descripción vaga del canal en un brief
    de producción específico y accionable."""
    producer = Agent(
        role="Executive Producer",
        goal="Definir briefs de producción precisos para canales",
        backstory="Productor ejecutivo: convierte ideas vagas en especificaciones claras.",
        llm=get_planning_llm(),
        verbose=False,
    )
    prompt = IMPROVE_PROMPT.format(
        name=channel.name,
        format=channel.format,
        niche=channel.niche or "general",
        description=(channel.description or "sin descripción").strip(),
    )
    brief = _run_single_task(producer, prompt, "Brief de producción mejorado")
    return _strip_markup(brief)


CURATE_PROMPT = """Eres el curador de un audiolibro en español. Prepara este fragmento del libro
"{title}" para ser NARRADO en voz alta. Es una tarea de LIMPIEZA fiel, no de reescritura:

- Elimina: números de página, notas de transcripción, pies de ilustración ("Ilustración", "Grabado"),
  corchetes editoriales [así], líneas de guiones bajos o separadores decorativos, cabeceras repetidas.
- Conserva TODO el texto narrativo original, palabra por palabra: no resumas, no modernices,
  no traduzcas, no añadas nada.
- Normaliza la puntuación para que las pausas sean naturales al escucharlo.
- Si un fragmento es solo ruido sin contenido narrativo, devuelve una línea vacía.

Devuelve SOLO el texto curado, sin comentarios.

Fragmento:
{chunk}"""


def _word_chunks(text: str, max_words: int = 1200) -> list[str]:
    """Trocea por palabras respetando párrafos cuando se puede."""
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    for paragraph in text.split("\n"):
        para_words = paragraph.split()
        if current and len(current) + len(para_words) > max_words:
            chunks.append(" ".join(current))
            current = []
        current.extend(para_words)
    if current:
        chunks.append(" ".join(current))
    return chunks


def curate_audiobook(text: str, title: str, on_progress=None) -> str:
    """Curaduría de audiolibro: un agente limpia el texto crudo para narración,
    troceado en chunks (capítulos de Gutenberg traen ruido editorial)."""
    def emit(step: str, message: str, content: str | None = None) -> None:
        if on_progress:
            on_progress(step, message, content)

    curator = Agent(
        role="Audiobook Curator",
        goal="Limpiar texto de libros para narración fiel en audio",
        backstory="Editor de audiolibros: quita el ruido editorial sin tocar el texto.",
        llm=get_script_llm(),
        verbose=False,
    )

    chunks = _word_chunks(text)
    emit("curate", f"El curador prepara el texto ({len(chunks)} fragmentos)…")
    curated: list[str] = []
    for i, chunk in enumerate(chunks):
        prompt = CURATE_PROMPT.format(title=title, chunk=chunk)
        emit("curate_chunk", f"Curando fragmento {i + 1}/{len(chunks)}…", prompt)
        part = _run_single_task(curator, prompt, "Texto curado fiel")
        curated.append(part.strip())
        emit("curate_chunk_done", f"Fragmento {i + 1}/{len(chunks)} curado", part)

    return _strip_markup("\n\n".join(p for p in curated if p))
