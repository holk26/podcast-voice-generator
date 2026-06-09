"""
RSS Fetcher — fetches and parses RSS feeds without external dependencies.

Uses requests + xml.etree.ElementTree (no feedparser needed).
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests


def _get_text(element: Optional[ET.Element], default: str = "") -> str:
    if element is None:
        return default
    return (element.text or "").strip()


class RSSFetcher:
    """Fetch and parse RSS feeds into structured article dicts."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def fetch(self, feed_url: str, max_articles: int = 5) -> List[Dict[str, Any]]:
        """Fetch an RSS feed and return a list of article dicts."""
        response = requests.get(feed_url, timeout=self.timeout)
        response.raise_for_status()

        # Try to detect encoding
        content = response.content
        root = ET.fromstring(content)

        # Find channel and items, handling RSS 2.0 and Atom variants
        articles = []

        # RSS 2.0: <rss><channel><item>...</item></item></channel></rss>
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:max_articles]:
                articles.append(self._parse_rss_item(item, feed_url))
            return articles

        # Atom: <feed><entry>...</entry></entry></feed>
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        if entries:
            for entry in entries[:max_articles]:
                articles.append(self._parse_atom_entry(entry, feed_url, ns))
            return articles

        return articles

    def _parse_rss_item(self, item: ET.Element, source_url: str) -> Dict[str, Any]:
        title = _get_text(item.find("title"))
        link = _get_text(item.find("link"))
        description = _get_text(item.find("description"))
        summary = _get_text(item.find("{http://purl.org/rss/1.0/modules/content/}encoded")) or description
        pub_date = _get_text(item.find("pubDate"))

        return {
            "title": title,
            "url": link,
            "description": description,
            "summary": summary,
            "published": pub_date,
            "source": "rss",
            "source_url": source_url,
            "content": f"{title}\n\n{description}\n\n{summary}".strip()
        }

    def _parse_atom_entry(self, entry: ET.Element, source_url: str, ns: Dict[str, str]) -> Dict[str, Any]:
        title = _get_text(entry.find("atom:title", ns))
        link_el = entry.find("atom:link", ns)
        link = link_el.get("href") if link_el is not None else ""
        summary = _get_text(entry.find("atom:summary", ns))
        content = _get_text(entry.find("atom:content", ns)) or summary
        pub_date = _get_text(entry.find("atom:updated", ns)) or _get_text(entry.find("atom:published", ns))

        return {
            "title": title,
            "url": link,
            "description": summary,
            "summary": summary,
            "published": pub_date,
            "source": "rss",
            "source_url": source_url,
            "content": f"{title}\n\n{content}".strip()
        }

    def fetch_multi(self, feed_urls: List[str], max_articles_per_feed: int = 3) -> List[Dict[str, Any]]:
        """Fetch multiple feeds and merge results."""
        all_articles = []
        for url in feed_urls:
            try:
                articles = self.fetch(url, max_articles=max_articles_per_feed)
                all_articles.extend(articles)
            except Exception as e:
                print(f"[RSSFetcher] Failed to fetch {url}: {e}")
        return all_articles
