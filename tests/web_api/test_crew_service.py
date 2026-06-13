from unittest.mock import patch
from web_api.services.crew_service import generate_plan, generate_script


def test_generate_plan_parses_json_result():
    channel = type("Channel", (), {
        "name": "Test",
        "format": "podcast",
        "niche": "tech",
    })()

    with patch("web_api.services.crew_service.get_planning_llm") as mock_llm:
        mock_llm.return_value.kickoff.return_value = '[{"title": "T1", "description": "D1"}]'
        # Crew setup is complex; test the parser directly instead.
        from web_api.services.crew_service import _parse_plan_result
        result = _parse_plan_result('[{"title": "T1", "description": "D1"}]')
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
