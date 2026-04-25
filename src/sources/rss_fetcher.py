"""
RSS feed fetcher for HR news sources.

Sources are loaded from the central catalog in ``config.sources_catalog``.
Each fetched item carries the originating ``source_id`` so downstream modules
(analytics, deduplication, source manager) can attribute it back to the source.
"""
import feedparser
from typing import List, Optional

from config.sources_catalog import load_sources


class RSSFetcher:
    """Fetches and parses RSS feeds from HR news sources."""

    DEFAULT_ITEMS_PER_SOURCE = 10
    # Browser-like UA: Reddit, MIT Sloan and a few others reject the default
    # feedparser UA with 403. The HR-Agent identifier preserves traceability.
    USER_AGENT = "Mozilla/5.0 (compatible; HR-AI-Agent/1.0; +https://github.com/delovar01/hr-ai-agent)"

    def __init__(self, sources: Optional[List[dict]] = None, items_per_source: int = DEFAULT_ITEMS_PER_SOURCE):
        self.sources = sources if sources is not None else load_sources(active_only=True)
        self.items_per_source = items_per_source

    def fetch_all(self) -> List[dict]:
        """Fetch from all configured RSS sources."""
        all_items = []
        for source in self.sources:
            all_items.extend(self._fetch_source(source))
        return all_items

    def _fetch_source(self, source: dict) -> List[dict]:
        """Fetch items from a single RSS source."""
        items = []
        try:
            feed = feedparser.parse(source["url"], agent=self.USER_AGENT)
            for entry in feed.entries[: self.items_per_source]:
                items.append({
                    "id": entry.get("id", entry.get("link", "")),
                    "url": entry.get("link", ""),
                    "title": entry.get("title", ""),
                    "content": entry.get("summary", entry.get("description", "")),
                    "published": entry.get("published", ""),
                    "source": source["name"],
                    "source_id": source.get("id"),
                    "lang": source.get("lang", "en"),
                    "type": "rss",
                })
        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")
        return items
