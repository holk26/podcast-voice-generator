import json
from typing import List
from crewai import Agent, Task, Crew
from web_api.schemas import PlanEntryCreate
from web_api.services.llm_provider import get_planning_llm, get_script_llm


PLAN_PROMPT = """Eres un estratega de contenidos. Para el canal "{name}" ({format}) sobre el nicho "{niche}",
propón {count} ideas de episodios. Devuélvelas EXACTAMENTE en este formato JSON:
[
  {{"title": "Título 1", "description": "Descripción corta 1"}},
  ...
]
Solo JSON, sin explicaciones."""


SCRIPT_PROMPT = """Eres un guionista de audio. Escribe un guion completo en español para un episodio de tipo "{format}"
titulado "{title}". Descripción: {description}. Nicho: {niche}.
El guion debe tener entre 300 y 800 palabras, ser natural al leerse en voz alta y no incluir notas de producción.
Devuelve SOLO el texto del guion, sin introducciones ni comentarios."""


def _parse_plan_result(raw: str) -> List[PlanEntryCreate]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Plan result is not a list")
    return [PlanEntryCreate(title=item["title"], description=item.get("description")) for item in data]


def generate_plan(channel, count: int = 5) -> List[PlanEntryCreate]:
    strategist = Agent(
        role="Content Strategist",
        goal="Proponer ideas de episodios relevantes para un canal",
        backstory="Experto en contenido digital y nichos de audiencia.",
        llm=get_planning_llm(),
        verbose=False,
    )

    task = Task(
        description=PLAN_PROMPT.format(
            name=channel.name,
            format=channel.format,
            niche=channel.niche or "general",
            count=count,
        ),
        expected_output="Un array JSON con objetos title y description",
        agent=strategist,
    )

    crew = Crew(agents=[strategist], tasks=[task], verbose=False)
    result = crew.kickoff()
    return _parse_plan_result(str(result))


def generate_script(channel, entry) -> str:
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

    crew = Crew(agents=[writer, editor], tasks=[write_task, edit_task], verbose=False)
    result = crew.kickoff()
    return str(result).strip()
