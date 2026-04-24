"""
Analytics for monitoring data source efficiency.
"""
import json
import os

class SourceAnalytics:
    def __init__(self, stats_path="data/source_stats.json"):
        self.stats_path = stats_path
        self.stats = {}

    def log_fetch(self, source_id: str, source_name: str, is_duplicate: bool):
        """Записывает результат получения новости для конкретного источника."""
        if source_id not in self.stats:
            self.stats[source_id] = {
                "name": source_name,
                "total_fetched": 0,
                "unique_items": 0,
                "duplicates_skipped": 0
            }
        
        self.stats[source_id]["total_fetched"] += 1
        if is_duplicate:
            self.stats[source_id]["duplicates_skipped"] += 1
        else:
            self.stats[source_id]["unique_items"] += 1

    def build_source_report(self) -> str:
        """Генерирует текстовый отчет по эффективности источников."""
        report = ["\n=== SOURCE ANALYTICS REPORT ==="]
        for s_id, data in self.stats.items():
            total = data["total_fetched"]
            unique = data["unique_items"]
            perc = (unique / total * 100) if total > 0 else 0
            report.append(f"Source: {data['name']} [{s_id}]")
            report.append(f"  - Efficiency: {perc:.1f}% ({unique} unique out of {total})")
        return "\n".join(report)

    def save_stats(self):
        """Сохраняет накопленную статистику в файл."""
        os.makedirs(os.path.dirname(self.stats_path), exist_ok=True)
        with open(self.stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=4, ensure_ascii=False)
