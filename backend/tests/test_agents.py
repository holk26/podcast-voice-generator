"""Tests for the multi-agent content generation system."""

import json
import unittest

from agents.llm_provider import MockProvider
from agents.content_cleaner_agent import ContentCleanerAgent
from agents.script_writer_agent import ScriptWriterAgent
from agents.script_editor_agent import ScriptEditorAgent
from agents.character_caster_agent import CharacterCasterAgent
from agents.metadata_agent import MetadataAgent
from agents.orchestrator import AgentOrchestrator


class MockResponses:
    CLEANER = json.dumps({
        "title": "Noticias Tech",
        "summary": "Resumen de noticias tecnológicas.",
        "key_points": ["NVIDIA anuncia GPU", "Apple presenta IA"],
        "cleaned_text": "NVIDIA anunció una nueva GPU. Apple presentó funciones de IA.",
        "language": "es"
    })

    WRITER = json.dumps({
        "script_text": "PRESENTADOR: NVIDIA anunció una nueva GPU.\nPRESENTADORA: Apple presentó funciones de IA.",
        "scene_notes": ["Ambiente de estudio"],
        "estimated_duration_minutes": 5.0,
        "content_warnings": []
    })

    EDITOR = json.dumps({
        "improved_script": "PRESENTADOR: NVIDIA acaba de anunciar una nueva GPU increíble.\nPRESENTADORA: Y Apple no se queda atrás con sus funciones de IA.",
        "changes_made": ["Mejorado el lenguaje"],
        "quality_score": 8.5,
        "issues_found": [],
        "suggestions": []
    })

    CASTER = json.dumps({
        "casting_map": {
            "PRESENTADOR": "homer",
            "PRESENTADORA": "dalia"
        },
        "reasoning": ["Homero es voz principal masculina", "Dalia es voz femenina"]
    })

    METADATA = json.dumps({
        "title": "TechPulse: NVIDIA y Apple",
        "description": "Resumen tech con noticias de NVIDIA y Apple. #tech #ai",
        "summary": "Noticias de NVIDIA y Apple.",
        "tags": ["tech", "nvidia", "apple", "ia"],
        "category": "Technology"
    })


class TestContentCleanerAgent(unittest.TestCase):
    def test_clean_with_mock(self):
        provider = MockProvider({"limpiar": MockResponses.CLEANER})
        agent = ContentCleanerAgent(provider=provider)
        result = agent.run({
            "content": "<html><body>NVIDIA anunció... Apple presentó...</body></html>",
            "source": "rss",
            "content_type": "news"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.data["language"], "es")
        self.assertIn("NVIDIA", result.data["cleaned_text"])


class TestScriptWriterAgent(unittest.TestCase):
    def test_write_with_mock(self):
        provider = MockProvider({"escribe": MockResponses.WRITER})
        agent = ScriptWriterAgent(provider=provider)
        result = agent.run({
            "content": {
                "title": "Tech News",
                "cleaned_text": "NVIDIA and Apple news",
                "summary": "Summary",
                "key_points": ["NVIDIA GPU", "Apple AI"]
            },
            "content_type": "news",
            "voice_cast": ["homer", "dalia"]
        })
        self.assertTrue(result.success)
        self.assertIn("PRESENTADOR", result.data["script_text"])


class TestScriptEditorAgent(unittest.TestCase):
    def test_edit_with_mock(self):
        provider = MockProvider({"revisa": MockResponses.EDITOR})
        agent = ScriptEditorAgent(provider=provider)
        result = agent.run({
            "script_text": "PRESENTADOR: Hola.\nPRESENTADORA: Adiós.",
            "content_type": "news"
        })
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.data["quality_score"], 8.0)


class TestCharacterCasterAgent(unittest.TestCase):
    def test_cast_with_mock(self):
        provider = MockProvider({"asigna": MockResponses.CASTER})
        agent = CharacterCasterAgent(provider=provider)
        result = agent.run({
            "script_text": "PRESENTADOR: Hola.\nPRESENTADORA: Adiós.",
            "available_voices": []
        })
        self.assertTrue(result.success)
        self.assertEqual(result.data["casting_map"]["PRESENTADOR"], "homer")


class TestMetadataAgent(unittest.TestCase):
    def test_metadata_with_mock(self):
        provider = MockProvider({"metadata": MockResponses.METADATA})
        agent = MetadataAgent(provider=provider)
        result = agent.run({
            "content": {"title": "Tech", "summary": "Summary"},
            "script_text": "PRESENTADOR: Hola.",
            "content_type": "news",
            "episode_number": 1
        })
        self.assertTrue(result.success)
        self.assertEqual(result.data["category"], "Technology")


class TestAgentOrchestrator(unittest.TestCase):
    def test_full_pipeline_with_mock(self):
        responses = {
            "limpiar": MockResponses.CLEANER,
            "escribe": MockResponses.WRITER,
            "revisa": MockResponses.EDITOR,
            "asigna": MockResponses.CASTER,
            "metadata": MockResponses.METADATA
        }
        provider = MockProvider(responses)
        orchestrator = AgentOrchestrator(provider=provider)

        result = orchestrator.run(
            raw_content="NVIDIA anunció nueva GPU. Apple presentó IA.",
            source="rss",
            content_type="news",
            episode_number=42
        )

        self.assertTrue(result.success, result.error)
        self.assertIn("media_package", result.data)
        self.assertIn("casting_map", result.data)
        self.assertEqual(result.data["casting_map"]["PRESENTADOR"], "homer")
        self.assertEqual(result.data["manifest"].episode_number, 42)
        self.assertEqual(result.data["manifest"].category, "Technology")
        self.assertGreater(len(result.data["media_package"].script), 0)


if __name__ == "__main__":
    unittest.main()
