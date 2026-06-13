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
        mock_crew.return_value.kickoff.return_value = "Guion final"
        result = generate_script(channel, entry)
        assert result == "Guion final"
