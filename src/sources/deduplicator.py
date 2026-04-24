import re
from simhash import Simhash

class SimHashDeduplicator:
    def __init__(self, threshold: int = 3):
        """
        :param threshold: Максимальное расстояние Хэмминга. 
        3 — это стандарт (тексты почти идентичны). 
        Если нужно отсекать даже сильный рерайт, ставьте 5-8.
        """
        self.threshold = threshold

    def _preprocess(self, text: str) -> str:
        """Очистка текста для улучшения точности хеширования."""
        # Убираем HTML-теги, пунктуацию и приводим к нижнему регистру
        text = text.lower()
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'[^\w\s]', '', text)
        # Убираем лишние пробелы
        text = " ".join(text.split())
        return text

    def get_hash(self, text: str) -> str:
        """Генерирует SimHash в виде строки (или числа)."""
        if not text or len(text) < 10:
            return ""
        return str(Simhash(self._preprocess(text)).value)

    def is_duplicate(self, new_hash: str, existing_hashes: list) -> bool:
        """Проверяет, есть ли похожий хэш в списке уже обработанных."""
        if not new_hash:
            return False
        
        new_s = Simhash(int(new_hash))
        for h in existing_hashes:
            if not h: continue
            if new_s.distance(Simhash(int(h))) <= self.threshold:
                return True
        return False
