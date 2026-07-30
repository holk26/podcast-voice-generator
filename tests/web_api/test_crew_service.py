import pytest
from unittest.mock import patch
from web_api.services.crew_service import generate_plan, generate_script, _parse_plan_result


def test_parse_plan_result_valid_json():
    result = _parse_plan_result('[{"title": "T1", "description": "D1"}]')
    assert len(result) == 1
    assert result[0].title == "T1"
    assert result[0].description == "D1"


def test_parse_plan_result_valid_json_no_description():
    result = _parse_plan_result('[{"title": "T1"}]')
    assert len(result) == 1
    assert result[0].title == "T1"
    assert result[0].description is None


def test_parse_plan_result_strips_markdown():
    raw = '```json\n[{"title": "T1", "description": "D1"}]\n```'
    result = _parse_plan_result(raw)
    assert len(result) == 1
    assert result[0].title == "T1"


def test_parse_plan_result_extracts_json_block():
    raw = 'Aquí tienes las ideas:\n```json\n[{"title": "T1", "description": "D1"}]\n```\nEspero que te sirvan.'
    result = _parse_plan_result(raw)
    assert len(result) == 1
    assert result[0].title == "T1"


def test_parse_plan_result_fixes_missing_commas_between_objects():
    raw = '[\n  {"title": "T1", "description": "D1"}\n  {"title": "T2", "description": "D2"}\n]'
    result = _parse_plan_result(raw)
    assert len(result) == 2
    assert result[0].title == "T1"
    assert result[1].title == "T2"


def test_parse_plan_result_fixes_trailing_comma():
    raw = '[{"title": "T1", "description": "D1",}]'
    result = _parse_plan_result(raw)
    assert len(result) == 1
    assert result[0].title == "T1"


def test_parse_plan_result_fixes_single_quotes():
    raw = "[{'title': 'T1', 'description': 'D1'}]"
    result = _parse_plan_result(raw)
    assert len(result) == 1
    assert result[0].title == "T1"


def test_generate_script_returns_string():
    channel = type("Channel", (), {
        "name": "Test",
        "format": "podcast",
        "niche": "tech",
    })()
    entry = type("Entry", (), {
        "title": "T1",
        "description": "D1",
    })()

    with patch("web_api.services.crew_service.Crew") as mock_crew:
        mock_crew.return_value.kickoff.return_value = " ".join(["Guion"] * 150)
        result = generate_script(channel, entry)
        assert result == " ".join(["Guion"] * 150)


def test_generate_script_rejects_llm_refusal():
    """Un rechazo del LLM nunca debe convertirse en episodio: el job falla."""
    channel = type("Channel", (), {
        "name": "Test",
        "format": "podcast",
        "niche": "tech",
    })()
    entry = type("Entry", (), {
        "title": "T1",
        "description": "D1",
    })()

    with patch("web_api.services.crew_service.Crew") as mock_crew:
        mock_crew.return_value.kickoff.return_value = (
            "Sorry, but I can't assist with that. "
            "If you have any other questions, feel free to ask!"
        )
        with pytest.raises(ValueError, match="rechazó"):
            generate_script(channel, entry)


def test_generate_script_survives_voice_director_collapse():
    """Si la limpieza TTS colapsa el guion a unas líneas, se usa el original."""
    channel = type("Channel", (), {
        "name": "Test",
        "format": "podcast",
        "niche": "tech",
    })()
    entry = type("Entry", (), {
        "title": "T1",
        "description": "D1",
    })()
    long_script = " ".join(["contenido"] * 300)

    with patch("web_api.services.crew_service.Crew") as mock_crew:
        class FakeCrew:
            def __init__(self, agents=None, tasks=None, verbose=False):
                self._task_desc = tasks[0].description if tasks else ""

            def kickoff(self):
                if "FINAL PARA SÍNTESIS DE VOZ" in self._task_desc:
                    return "Hasta la próxima. ¡Que tengáis un día fantástico!"
                if "JSON" in self._task_desc and "action" in self._task_desc:
                    return '{"action": "ok", "reason": "ok"}'
                return long_script

        mock_crew.side_effect = lambda **kw: FakeCrew(**kw)
        result = generate_script(channel, entry)
        assert len(result.split()) >= 100
