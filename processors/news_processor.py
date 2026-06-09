"""
News Processor — converts raw news articles into a MediaPackage via agents.

Input: list of article dicts from RSSFetcher
Output: MediaPackage ready for audio rendering
"""

from typing import List, Dict, Any, Optional

from agents.orchestrator import AgentOrchestrator
from agents.llm_provider import LLMProvider
from core.media_package import MediaPackage


class NewsProcessor:
    """Processes news articles into a dramatized podcast MediaPackage."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        target_duration_minutes: float = 8.0,
        voice_cast=None
    ):
        self.orchestrator = AgentOrchestrator(
            provider=provider,
            voice_cast=voice_cast
        )
        self.target_duration = target_duration_minutes

    def process_articles(
        self,
        articles: List[Dict[str, Any]],
        episode_number: Optional[int] = None,
        show_title: str = "TechPulse"
    ) -> MediaPackage:
        """
        Combine multiple articles into a single news podcast episode.
        """
        # Merge articles into a single raw content block
        merged_content = self._merge_articles(articles, show_title)

        result = self.orchestrator.run(
            raw_content=merged_content,
            source="rss",
            content_type="news",
            content_title=show_title,
            source_url=articles[0].get("source_url", "") if articles else "",
            episode_number=episode_number,
            target_duration_minutes=self.target_duration
        )

        if not result.success:
            raise RuntimeError(f"News processing failed: {result.error}")

        package = result.data["media_package"]
        # Override title with show title + episode if needed
        if show_title and episode_number:
            package.manifest.title = f"{show_title} #{episode_number}: {package.manifest.title}"

        return package

    def _merge_articles(self, articles: List[Dict[str, Any]], show_title: str) -> str:
        parts = [f"# {show_title}\n"]
        for i, article in enumerate(articles, 1):
            parts.append(f"\n## Noticia {i}: {article.get('title', '')}\n")
            parts.append(article.get("content", article.get("description", "")))
            parts.append(f"\nFuente: {article.get('url', article.get('source_url', ''))}")
        return "\n".join(parts)
