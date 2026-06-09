"""Tests for content acquisition modules."""

import tempfile
import unittest
from pathlib import Path

from content.rss_fetcher import RSSFetcher
from content.gutenberg_fetcher import GutenbergFetcher
from content.template_engine import TemplateEngine


class TestRSSFetcher(unittest.TestCase):
    def test_parse_rss_xml(self):
        """Test parsing a minimal RSS XML string."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article One</title>
      <link>http://example.com/1</link>
      <description>First article description.</description>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Article Two</title>
      <link>http://example.com/2</link>
      <description>Second article description.</description>
    </item>
  </channel>
</rss>"""
        fetcher = RSSFetcher()
        # Monkey-patch fetch to test parsing directly
        articles = []
        root = __import__("xml.etree.ElementTree", fromlist=["fromstring"]).fromstring(xml)
        channel = root.find("channel")
        for item in channel.findall("item"):
            articles.append(fetcher._parse_rss_item(item, "http://test.feed"))

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["title"], "Article One")
        self.assertEqual(articles[0]["url"], "http://example.com/1")


class TestGutenbergFetcher(unittest.TestCase):
    def test_clean_text(self):
        fetcher = GutenbergFetcher()
        raw = "Header\n*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\nBody text\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\nFooter"
        cleaned = fetcher._clean_text(raw)
        self.assertIn("Body text", cleaned)
        self.assertNotIn("Header", cleaned)
        self.assertNotIn("Footer", cleaned)

    def test_split_chapters(self):
        fetcher = GutenbergFetcher()
        text = "Preface\n\nCAPÍTULO I\nPrimer capítulo.\n\nCAPÍTULO II\nSegundo capítulo."
        chapters = fetcher.split_into_chapters(text)
        self.assertGreaterEqual(len(chapters), 2)
        self.assertTrue(any("CAPÍTULO I" in ch["title"] for ch in chapters))


class TestTemplateEngine(unittest.TestCase):
    def test_meditation_generation(self):
        engine = TemplateEngine()
        result = engine.generate_meditation(duration_minutes=5, topic="calma", seed=42)
        self.assertEqual(result["topic"], "calma")
        self.assertEqual(result["duration_minutes"], 5)
        self.assertIn("calma", result["content"].lower())

    def test_motivation_generation(self):
        engine = TemplateEngine()
        result = engine.generate_motivation(topic="disciplina", seed=42)
        self.assertEqual(result["topic"], "disciplina")
        self.assertIn("disciplina", result["content"].lower())

    def test_deterministic_with_seed(self):
        engine = TemplateEngine()
        r1 = engine.generate_meditation(seed=123)
        r2 = engine.generate_meditation(seed=123)
        self.assertEqual(r1["topic"], r2["topic"])


if __name__ == "__main__":
    unittest.main()
