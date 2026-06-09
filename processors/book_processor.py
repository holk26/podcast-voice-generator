"""
Book Processor — converts a Gutenberg book into chapter MediaPackages via agents.

Input: book dict from GutenbergFetcher
Output: list of MediaPackages, one per chapter/segment
"""

from typing import List, Dict, Any, Optional

from agents.orchestrator import AgentOrchestrator
from agents.llm_provider import LLMProvider
from core.media_package import MediaPackage


class BookProcessor:
    """Processes public-domain books into dramatized audiobook chapters."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        target_duration_minutes: float = 15.0,
        voice_cast=None,
        max_words_per_chapter: int = 2500
    ):
        self.orchestrator = AgentOrchestrator(
            provider=provider,
            voice_cast=voice_cast
        )
        self.target_duration = target_duration_minutes
        self.max_words = max_words_per_chapter

    def process_book(self, book: Dict[str, Any]) -> List[MediaPackage]:
        """
        Process a full book into a list of chapter MediaPackages.
        """
        from content.gutenberg_fetcher import GutenbergFetcher

        text = book.get("cleaned_text", book.get("content", ""))
        if not text:
            raise ValueError("Book has no text content.")

        # Split into chapters or chunks
        fetcher = GutenbergFetcher()
        chapters = fetcher.split_into_chapters(text)

        packages = []
        for i, chapter in enumerate(chapters):
            # Further split if chapter is too long
            segments = self._split_if_needed(chapter["text"])
            for j, segment_text in enumerate(segments):
                segment_title = chapter["title"] if len(segments) == 1 else f"{chapter['title']} (Parte {j+1})"

                result = self.orchestrator.run(
                    raw_content=segment_text,
                    source="gutenberg",
                    content_type="book",
                    content_title=f"{book.get('title', 'Audiolibro')} — {segment_title}",
                    source_url=book.get("source_url", ""),
                    episode_number=i + 1,
                    target_duration_minutes=self.target_duration
                )

                if result.success:
                    package = result.data["media_package"]
                    package.manifest.title = f"{book.get('title', '')} — {segment_title}"
                    package.manifest.author = book.get("author", "")
                    package.manifest.category = "Arts"
                    package.manifest.content_type = "audiobook"
                    packages.append(package)

        return packages

    def _split_if_needed(self, text: str) -> List[str]:
        """Split long text into chunks of max_words."""
        words = text.split()
        if len(words) <= self.max_words:
            return [text]

        segments = []
        current = []
        for word in words:
            current.append(word)
            if len(current) >= self.max_words:
                # Try to end at sentence boundary
                segment_text = " ".join(current)
                segments.append(segment_text)
                current = []

        if current:
            segments.append(" ".join(current))

        return segments
