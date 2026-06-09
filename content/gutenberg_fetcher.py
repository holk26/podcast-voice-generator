"""
Gutenberg Fetcher — search and download public domain books from Project Gutenberg.

Uses requests + BeautifulSoup (if available) or regex fallback.
"""

import re
import html
from typing import List, Dict, Any, Optional
from pathlib import Path

import requests


try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class GutenbergFetcher:
    """Fetch public domain books from Project Gutenberg."""

    BASE_URL = "https://www.gutenberg.org"
    CATALOG_URL = "https://www.gutenberg.org/ebooks/search/"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    def search(
        self,
        query: str = "",
        language: str = "es",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search Project Gutenberg and return a list of book results."""
        params = {
            "query": query,
            "submit_search": "Search",
        }
        if language:
            params["lang"] = language

        response = requests.get(self.CATALOG_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        return self._parse_search_results(response.text, max_results)

    def _parse_search_results(self, html_text: str, max_results: int) -> List[Dict[str, Any]]:
        books = []

        if HAS_BS4:
            soup = BeautifulSoup(html_text, "html.parser")
            for li in soup.select("li.booklink")[:max_results]:
                title_el = li.select_one("span.title")
                author_el = li.select_one("span.subtitle")
                link_el = li.select_one("a.link")

                if not title_el or not link_el:
                    continue

                href = link_el.get("href", "")
                book_id = href.strip("/").split("/")[-1] if href else ""

                books.append({
                    "title": title_el.get_text(strip=True),
                    "author": author_el.get_text(strip=True) if author_el else "Unknown",
                    "book_id": book_id,
                    "url": f"{self.BASE_URL}{href}" if href.startswith("/") else href
                })
        else:
            # Regex fallback
            pattern = re.compile(
                r'<li[^>]*class="booklink"[^>]*>.*?<a[^>]*href="(/ebooks/\d+)"[^>]*class="link"[^>]*>.*?</a>.*?<span[^>]*class="title"[^>]*>(.*?)</span>.*?<span[^>]*class="subtitle"[^>]*>(.*?)</span>.*?</li>',
                re.DOTALL
            )
            for match in pattern.findall(html_text)[:max_results]:
                href, title, author = match
                book_id = href.strip("/").split("/")[-1]
                books.append({
                    "title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(),
                    "author": html.unescape(re.sub(r"<[^>]+>", "", author)).strip(),
                    "book_id": book_id,
                    "url": f"{self.BASE_URL}{href}"
                })

        return books

    def fetch_text(self, book_id: str) -> str:
        """Download the plain text version of a book by its Gutenberg ID."""
        text_url = f"{self.BASE_URL}/files/{book_id}/{book_id}-0.txt"
        alt_url = f"{self.BASE_URL}/ebooks/{book_id}.txt.utf-8"

        for url in [text_url, alt_url]:
            try:
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    return response.text
            except Exception:
                continue

        raise FileNotFoundError(f"Could not download text for book {book_id}")

    def fetch_book(self, book_id: str) -> Dict[str, Any]:
        """Fetch a book's full text and metadata."""
        text = self.fetch_text(book_id)

        # Extract title from text
        title_match = re.search(r"Title:\s*(.+)", text)
        author_match = re.search(r"Author:\s*(.+)", text)

        title = title_match.group(1).strip() if title_match else f"Book {book_id}"
        author = author_match.group(1).strip() if author_match else "Unknown"

        # Clean text: remove Gutenberg headers/footers
        cleaned = self._clean_text(text)

        return {
            "title": title,
            "author": author,
            "book_id": book_id,
            "url": f"{self.BASE_URL}/ebooks/{book_id}",
            "full_text": text,
            "cleaned_text": cleaned,
            "content": cleaned,
            "source": "gutenberg",
            "source_url": f"{self.BASE_URL}/ebooks/{book_id}"
        }

    def _clean_text(self, text: str) -> str:
        """Remove Gutenberg header/footer and normalize whitespace."""
        # Find start marker
        start_markers = [
            "*** START OF THE PROJECT GUTENBERG EBOOK",
            "*** START OF THIS PROJECT GUTENBERG EBOOK",
            "*END*THE SMALL PRINT!"
        ]
        end_markers = [
            "*** END OF THE PROJECT GUTENBERG EBOOK",
            "*** END OF THIS PROJECT GUTENBERG EBOOK",
            "End of Project Gutenberg"
        ]

        start_idx = 0
        for marker in start_markers:
            idx = text.find(marker)
            if idx != -1:
                start_idx = text.find("\n", idx) + 1
                break

        end_idx = len(text)
        for marker in end_markers:
            idx = text.find(marker)
            if idx != -1:
                end_idx = idx
                break

        cleaned = text[start_idx:end_idx].strip()
        # Normalize whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    def split_into_chapters(self, text: str) -> List[Dict[str, str]]:
        """
        Split a book text into chapters/segments.
        Returns list of {title, text} dicts.
        """
        # Common chapter patterns
        patterns = [
            r"\n\s*CAPÍTULO\s+[IVX\d]+[^\n]*\n",
            r"\n\s*CAPITULO\s+[IVX\d]+[^\n]*\n",
            r"\n\s*Chapter\s+[IVX\d]+[^\n]*\n",
            r"\n\s*CHAPTER\s+[IVX\d]+[^\n]*\n",
            r"\n\s*\d+\.\s+[^\n]+\n",  # Numeric chapter titles
        ]

        combined_pattern = "|".join(f"({p})" for p in patterns)
        splits = list(re.finditer(combined_pattern, text, re.IGNORECASE))

        chapters = []
        if not splits:
            # No chapters found, return whole text
            chapters.append({"title": "Capítulo 1", "text": text})
            return chapters

        # Text before first chapter
        if splits[0].start() > 0:
            preface = text[:splits[0].start()].strip()
            if preface:
                chapters.append({"title": "Prólogo", "text": preface})

        for i, match in enumerate(splits):
            start = match.start()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            chapter_text = text[start:end].strip()
            title = match.group(0).strip()
            chapters.append({"title": title, "text": chapter_text})

        return chapters
