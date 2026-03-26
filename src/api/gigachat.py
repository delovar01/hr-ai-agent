"""
GigaChat API wrapper for translation, classification and insight generation.
"""
import json
from typing import Optional

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import GIGACHAT_CREDENTIALS, GIGACHAT_SCOPE


class GigaChatClient:
    """Wrapper for GigaChat API with HR-specific enhanced prompts."""

    def __init__(self):
        self.credentials = GIGACHAT_CREDENTIALS
        self.scope = GIGACHAT_SCOPE
        self._client = None

    @property
    def client(self):
        if not GIGACHAT_AVAILABLE:
            return None
        if self._client is None and self.credentials:
            self._client = GigaChat(
                credentials=self.credentials,
                scope=self.scope,
                verify_ssl_certs=False
            )
        return self._client

    def _chat(self, system_prompt: str, user_message: str) -> str:
        """Send message to GigaChat and get response."""
        if not self.client:
            return self._mock_response(system_prompt, user_message)
        try:
            response = self.client.chat(Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                    Messages(role=MessagesRole.USER, content=user_message)
                ],
                temperature=0.4,
                max_tokens=1500
            ))
            return response.choices[0].message.content
        except Exception as e:
            print(f"GigaChat error: {e}")
            return self._mock_response(system_prompt, user_message)

    def _mock_response(self, system_prompt: str, user_message: str) -> str:
        """Fallback mock response when GigaChat unavailable."""
        if "переведи" in system_prompt.lower():
            return user_message
        if "классифицируй" in system_prompt.lower():
            return json.dumps({
                "topic": "culture",
                "confidence": 0.7,
                "keywords": ["HR", "новости"]
            }, ensure_ascii=False)
        if "инсайт" in system_prompt.lower():
            return json.dumps({
                "what_changed": "Обнаружены новые данные в HR-сфере, требующие внимания",
                "why_important": "Изменения на рынке труда могут повлиять на стратегию компании",
                "recommendation": "Провести анализ и обсудить на ближайшем HR-совещании",
                "risk_level": "medium",
                "urgency": "week"
            }, ensure_ascii=False)
        if "тренд" in system_prompt.lower() or "trend" in system_prompt.lower():
            return json.dumps({
                "trend_direction": "stable",
                "change_percent": 5.0,
                "anomaly_detected": False,
                "analysis": "Ситуация стабильная, значительных изменений не обнаружено"
            }, ensure_ascii=False)
        return "{}"

    def _parse_json(self, text: str) -> dict:
        """Safely parse JSON from LLM response."""
        try:
            # Clean markdown code blocks
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            return {}

    def translate_to_russian(self, text: str) -> str:
        """Translate text to Russian preserving HR terminology."""
        system = """Ты — профессиональный переводчик, специализирующийся на HR и бизнес-текстах.

ЗАДАЧА: Переведи текст на русский язык.

ПРАВИЛА:
1. Сохраняй профессиональную HR-терминологию
2. Общепринятые термины оставляй на английском: HR, KPI, CEO, IT, B2B
3. Переводи смысл, не дословно
4. Сохраняй деловой стиль оригинала

Ответь ТОЛЬКО переводом, без комментариев."""

        user = f"Переведи:\n\n{text}"
        result = self._chat(system, user)
        return result if result else text

    def classify_hr_topic(self, text: str) -> dict:
        """Classify text into HR topics with confidence score."""
        system = """Ты — эксперт-аналитик в области управления персоналом (HR) с 15-летним опытом.

ЗАДАЧА: Определи HR-категорию текста.

КАТЕГОРИИ:
• hiring — Найм, рекрутинг, вакансии, привлечение талантов, онбординг
• layoffs — Сокращения, увольнения, реструктуризация, оптимизация штата
• salaries — Зарплаты, компенсации, бонусы, льготы, пересмотр оплаты
• skills — Навыки, обучение, развитие, повышение квалификации, карьера
• burnout — Выгорание, стресс, ментальное здоровье, work-life balance
• culture — Корпоративная культура, ценности, вовлечённость, климат
• diversity — Разнообразие, инклюзия, равные возможности, D&I

ПРАВИЛА:
1. Выбери ОДНУ доминирующую категорию
2. confidence: 0.9+ для очевидных, 0.6-0.8 для неоднозначных
3. Выдели 2-3 ключевых слова-маркера

ОТВЕТ — только JSON:
{"topic": "category", "confidence": 0.85, "keywords": ["слово1", "слово2"]}"""

        user = f"Классифицируй:\n\n{text[:1000]}"
        result = self._chat(system, user)
        parsed = self._parse_json(result)

        # Validate
        valid_topics = ["hiring", "layoffs", "salaries", "skills", "burnout", "culture", "diversity"]
        if parsed.get("topic") not in valid_topics:
            parsed["topic"] = "culture"
        if not isinstance(parsed.get("confidence"), (int, float)):
            parsed["confidence"] = 0.5
        if not isinstance(parsed.get("keywords"), list):
            parsed["keywords"] = []

        return parsed

    def generate_insight(self, data: dict, context: str) -> dict:
        """Generate proactive HR insight with actionable recommendation."""
        system = f"""Ты — проактивный HR-аналитик в крупной российской компании.

КОНТЕКСТ: {context}

ЗАДАЧА: Сформулируй ценный инсайт для HR-специалиста.

СТРУКТУРА:

1. what_changed — Что произошло? (факт, 1-2 предложения, конкретика)
2. why_important — Почему это важно? (риски или возможности для компании)
3. recommendation — Что делать? (конкретный следующий шаг, не общие слова)
4. risk_level — Уровень риска:
   • critical — реагировать немедленно
   • high — рассмотреть за 1-2 дня
   • medium — включить в еженедельный обзор
   • low — принять к сведению
5. urgency — Срочность: immediate / week / month

СТИЛЬ: Деловой, конкретный, без воды. Как сообщение занятому руководителю.

ОТВЕТ — только JSON:
{{"what_changed": "...", "why_important": "...", "recommendation": "...", "risk_level": "...", "urgency": "..."}}"""

        user = f"""ДАННЫЕ:
Тема: {data.get('topic', 'HR')}
Заголовок: {data.get('title', '')}
Источник: {data.get('source', '')}
Риск: {data.get('risk_score', 0.5):.0%}
Аномалия: {'ДА ⚠️' if data.get('anomaly', {}).get('is_anomaly') else 'нет'}

Текст:
{data.get('content_preview', '')[:500]}

Сгенерируй инсайт."""

        result = self._chat(system, user)
        parsed = self._parse_json(result)

        # Fallback values
        defaults = {
            "what_changed": "Обнаружены новые данные для анализа",
            "why_important": "Требует внимания HR-специалиста",
            "recommendation": "Провести детальный анализ источника",
            "risk_level": "medium",
            "urgency": "week"
        }
        for key, default in defaults.items():
            if not parsed.get(key):
                parsed[key] = default

        return parsed

    def analyze_trend(self, historical: list, current: dict) -> dict:
        """Analyze trend and detect anomalies."""
        system = """Ты — аналитик HR-метрик и трендов рынка труда.

ЗАДАЧА: Сравни текущие данные с историей, выяви тренд.

ДАННЫЕ:
- value — риск-скор от 0.0 до 1.0
- Рост value = больше негативных сигналов
- Падение value = улучшение ситуации
- ~0.5 = норма

КРИТЕРИИ АНОМАЛИИ:
- Отклонение > 30% от среднего
- Резкий разворот тренда
- 3+ точки подряд в одном направлении

ОТВЕТ — только JSON:
{
    "trend_direction": "up|down|stable",
    "change_percent": число,
    "anomaly_detected": true|false,
    "analysis": "Вывод для HR на русском, 1-2 предложения"
}"""

        # Format history
        hist_lines = [f"{h.get('timestamp', '?')[:10]}: {h.get('value', 0):.2f}"
                      for h in historical[-10:]]

        current_val = current.get('value', current.get('risk_score', 0.5))

        user = f"""ИСТОРИЯ (последние {len(hist_lines)} точек):
{chr(10).join(hist_lines) if hist_lines else 'Нет данных'}

ТЕКУЩЕЕ: {current_val:.2f}
ТЕМА: {current.get('topic', 'не указана')}

Проанализируй."""

        result = self._chat(system, user)
        parsed = self._parse_json(result)

        # Fallback
        defaults = {
            "trend_direction": "stable",
            "change_percent": 0,
            "anomaly_detected": False,
            "analysis": "Недостаточно данных для детального анализа тренда"
        }
        for key, default in defaults.items():
            if key not in parsed:
                parsed[key] = default

        return parsed


# Singleton instance
gigachat_client = GigaChatClient()
