"""
Agent Orchestrator — coordinates the multi-agent content generation pipeline.

Pipeline:
1. ContentCleanerAgent cleans raw source content
2. ScriptWriterAgent writes a dramatized script
3. ScriptEditorAgent reviews and improves the script
4. CharacterCasterAgent assigns voices to characters
5. MetadataAgent generates episode metadata

Output: a MediaPackage ready for audio rendering.
"""

from typing import Any, Dict, List, Optional

from agents.base import AgentResult
from agents.llm_provider import LLMProvider, MockProvider
from agents.content_cleaner_agent import ContentCleanerAgent
from agents.script_writer_agent import ScriptWriterAgent
from agents.script_editor_agent import ScriptEditorAgent
from agents.character_caster_agent import CharacterCasterAgent
from agents.metadata_agent import MetadataAgent

from cast.voice_cast_manager import VoiceCastManager
from core.media_package import MediaPackage, Manifest, ScriptLine
from processors.dialogue_parser import DialogueParser


class AgentOrchestrator:
    """Coordinates all content generation agents into a single pipeline."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        voice_cast: Optional[VoiceCastManager] = None,
        min_quality_score: float = 6.5,
        max_editor_iterations: int = 2
    ):
        self.provider = provider or MockProvider()
        self.voice_cast = voice_cast or VoiceCastManager()
        self.min_quality_score = min_quality_score
        self.max_editor_iterations = max_editor_iterations

        # Initialize agents
        self.cleaner = ContentCleanerAgent(provider=self.provider)
        self.writer = ScriptWriterAgent(provider=self.provider)
        self.editor = ScriptEditorAgent(provider=self.provider)
        self.caster = CharacterCasterAgent(provider=self.provider)
        self.metadata = MetadataAgent(provider=self.provider)

    def run(
        self,
        raw_content: str,
        source: str = "raw",
        content_type: str = "news",
        content_title: str = "",
        source_url: str = "",
        episode_number: Optional[int] = None,
        target_duration_minutes: float = 8.0
    ) -> AgentResult:
        """
        Run the full agent pipeline on raw content.

        Returns AgentResult with:
          - media_package: MediaPackage object
          - casting_map: dict of character → voice_id
          - manifest: Manifest object
          - logs: list of step results
        """
        logs = []

        # ── Step 1: Clean content ───────────────────────────────────────
        clean_result = self.cleaner.run({
            "content": raw_content,
            "source": source,
            "content_type": content_type,
            "source_url": source_url,
            "title": content_title
        })
        logs.append({"step": "clean", "success": clean_result.success, "error": clean_result.error})
        if not clean_result.success:
            return AgentResult.fail(f"Content cleaning failed: {clean_result.error}", metadata={"logs": logs})

        cleaned = clean_result.data

        # ── Step 2: Write script ────────────────────────────────────────
        writer_result = self.writer.run({
            "content": cleaned,
            "content_type": content_type,
            "voice_cast": self.voice_cast.list_voice_ids()
        })
        logs.append({"step": "write", "success": writer_result.success, "error": writer_result.error})
        if not writer_result.success:
            return AgentResult.fail(f"Script writing failed: {writer_result.error}", metadata={"logs": logs})

        script_data = writer_result.data
        script_text = script_data.get("script_text", "")

        # ── Step 3: Edit script (with optional iteration) ───────────────
        current_script = script_text
        for iteration in range(self.max_editor_iterations):
            editor_result = self.editor.run({
                "script_text": current_script,
                "content_type": content_type,
                "target_duration_minutes": target_duration_minutes
            })
            logs.append({
                "step": f"edit_iter_{iteration + 1}",
                "success": editor_result.success,
                "error": editor_result.error
            })
            if not editor_result.success:
                break

            edited = editor_result.data
            current_script = edited.get("improved_script", current_script)
            quality = edited.get("quality_score", 0.0)

            if quality >= self.min_quality_score:
                break

        # ── Step 4: Cast characters to voices ───────────────────────────
        available_voices = self.voice_cast.list_profiles()
        caster_result = self.caster.run({
            "script_text": current_script,
            "available_voices": available_voices
        })
        logs.append({"step": "cast", "success": caster_result.success, "error": caster_result.error})
        casting_map = caster_result.data.get("casting_map", {}) if caster_result.success else {}

        # ── Step 5: Generate metadata ───────────────────────────────────
        meta_result = self.metadata.run({
            "content": cleaned,
            "script_text": current_script,
            "content_type": content_type,
            "episode_number": episode_number
        })
        logs.append({"step": "metadata", "success": meta_result.success, "error": meta_result.error})
        meta = meta_result.data if meta_result.success else {}

        # ── Step 6: Build MediaPackage ──────────────────────────────────
        manifest = Manifest(
            title=meta.get("title", cleaned.get("title", "Episodio")),
            description=meta.get("description", cleaned.get("summary", "")),
            summary=meta.get("summary", cleaned.get("summary", "")),
            category=meta.get("category", "Technology"),
            tags=meta.get("tags", []),
            language=cleaned.get("language", "es"),
            episode_number=episode_number,
            content_type=content_type,
            source_url=source_url
        )

        # Parse script into ScriptLine list
        parser = DialogueParser()
        lines = parser.parse_with_character_map(current_script, casting_map)

        package_id = f"{content_type}_{episode_number or 'auto'}"
        package = MediaPackage(package_id=package_id)
        package.set_manifest(manifest)
        package.add_lines(lines)

        return AgentResult.ok(
            data={
                "media_package": package,
                "casting_map": casting_map,
                "manifest": manifest,
                "cleaned_content": cleaned,
                "final_script": current_script,
                "metadata": meta
            },
            metadata={"logs": logs}
        )

    def run_from_sources(
        self,
        sources: List[Dict[str, Any]],
        content_type: str = "news",
        target_duration_minutes: float = 8.0
    ) -> List[AgentResult]:
        """Run the pipeline on multiple content sources and return a list of results."""
        results = []
        for i, source in enumerate(sources):
            result = self.run(
                raw_content=source.get("content", ""),
                source=source.get("source", "raw"),
                content_type=content_type,
                content_title=source.get("title", ""),
                source_url=source.get("url", ""),
                episode_number=source.get("episode_number", i + 1),
                target_duration_minutes=target_duration_minutes
            )
            results.append(result)
        return results
