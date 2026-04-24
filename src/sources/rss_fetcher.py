
"""
RSS feed fetcher for HR news sources.
"""
import feedparser
import json
import os
from datetime import datetime
from typing import List
from config.settings import RSS_SOURCES

from src.sources.deduplicator import SimHashDeduplicator
from src.sources.source_analytics import SourceAnalytics

class RSSFetcher:
    """Fetches and parses RSS feeds from HR news sources."""
    
    def __init__(self, state_path="data/state.json"):
        self.sources = RSS_SOURCES
        self.state_path = state_path
        self.deduplicator = SimHashDeduplicator(threshold=3)
        self.analytics = SourceAnalytics() # Инициализация аналитики
        self.processed_hashes = self._load_state()
    
    def _load_state(self) -> list:
        """Загрузка списка хэшей из файла состояния."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("processed_hashes", [])
            except Exception:
                return []
        return []

    def _save_state(self):
        """Сохранение обновленного списка хэшей."""
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump({"processed_hashes": self.processed_hashes}, f, indent=4)

    def fetch_all(self) -> List[dict]:
        """Fetch from all configured RSS sources."""
        all_items = []
        for source in self.sources:
            items = self._fetch_source(source)
            all_items.extend(items)
        
        self._save_state()
        
        # Вывод отчета в консоль после завершения прогона
        print(self.analytics.build_source_report())
        self.analytics.save_stats()
        
        return all_items
    
    def _fetch_source(self, source: dict) -> List[dict]:
        """Fetch items from a single RSS source."""
        items = []
        
        # Интеграция source_id: берем из конфига или генерируем из названия
        source_id = source.get("id", source["name"].lower().replace(" ", "_"))
        
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:10]:  # Limit to 10 per source
                title = entry.get("title", "")
                content = entry.get("summary", entry.get("description", ""))
                
                # Вместо примитивной проверки URL используем SimHash контента
                full_text = f"{title} {content}"
                current_hash = self.deduplicator.get_hash(full_text)
                
                # Проверяем на дубликат
                is_dup = self.deduplicator.is_duplicate(current_hash, self.processed_hashes)
                
                # Логируем действие для аналитики
                self.analytics.log_fetch(source_id, source["name"], is_dup)
                
                if is_dup:
                    continue

                item = {
                    "id": entry.get("id", entry.get("link", "")),
                    "source_id": source_id, # Добавляем идентификатор в результат
                    "url": entry.get("link", ""),
                    "title": title,
                    "content": content,
                    "published": entry.get("published", ""),
                    "source": source["name"],
                    "lang": source.get("lang", "en"),
                    "type": "rss"
                }
                items.append(item)
                
                if current_hash:
                    self.processed_hashes.append(current_hash)

        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")
        return items

