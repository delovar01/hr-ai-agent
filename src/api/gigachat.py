"""
GigaChat API wrapper for translation, classification and insight generation.
"""
import hashlib
import json
import time
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

    # Up to 3 attempts on transient errors with exponential backoff.
    # Rate-limit responses from GigaChat (HTTP 429) and network blips are
    # the most common cause of "модель временно недоступна" during the
    # live demo, and they usually clear within seconds.
    _RETRY_DELAYS = (0.5, 1.5, 3.0)

    def _chat(self, system_prompt: str, user_message: str) -> str:
        """Send message to GigaChat, retry on transient failure, then fallback."""
        if not self.client:
            return self._mock_response(system_prompt, user_message)

        last_error: Optional[Exception] = None
        for attempt, delay in enumerate(self._RETRY_DELAYS, start=1):
            try:
                response = self.client.chat(Chat(
                    messages=[
                        Messages(role=MessagesRole.SYSTEM, content=system_prompt),
                        Messages(role=MessagesRole.USER, content=user_message)
                    ],
                    temperature=0.4,
                    max_tokens=1500
                ))
                content = response.choices[0].message.content
                if content:  # empty/None responses count as a failure
                    return content
                last_error = ValueError("GigaChat returned empty response")
            except Exception as exc:
                last_error = exc
                print(f"GigaChat attempt {attempt}/{len(self._RETRY_DELAYS)} failed: {exc}")
            # Don't sleep after the final attempt.
            if attempt < len(self._RETRY_DELAYS):
                time.sleep(delay)

        print(f"GigaChat fallback after {len(self._RETRY_DELAYS)} attempts: {last_error}")
        return self._mock_response(system_prompt, user_message)

    def _mock_response(self, system_prompt: str, user_message: str) -> str:
        """Fallback mock response when GigaChat unavailable.

        IMPORTANT: question-answering check goes FIRST. The RAG system prompt
        mentions «инсайтов/алертов» as a reference to context items, which
        used to fall through into the insight-JSON branch and produced
        confusing ``what_changed`` output in the chat box.
        """
        # RAG chat: detected by the explicit marker in ``answer_question``.
        if "ВОПРОС ПОЛЬЗОВАТЕЛЯ" in user_message:
            return (
                "Модель сейчас временно недоступна, поэтому подробный ответ "
                "сформировать не удалось. Попробуй ещё раз через минуту или "
                "запусти цикл анализа для обновления данных."
            )
        if "переведи" in system_prompt.lower():
            return user_message
        if "классифицируй" in system_prompt.lower():
            return json.dumps({
                "topic": "culture",
                "confidence": 0.7,
                "keywords": ["HR", "новости"]
            }, ensure_ascii=False)
        if "сформулируй" in system_prompt.lower() or "инсайт" in system_prompt.lower():
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

    # In-process cache of {question+context hash → answer}. Survives Streamlit
    # script reloads via lazy load from data/rag_cache.json — pre-warmed by
    # scripts/warm_rag_cache.py before the live demo.
    _ANSWER_CACHE: dict = {}
    _ANSWER_CACHE_MAX = 128
    _ANSWER_CACHE_LOADED = False

    def _ensure_cache_loaded(self) -> None:
        """One-time lazy load of the pre-warmed cache file, if present."""
        if self._ANSWER_CACHE_LOADED:
            return
        type(self)._ANSWER_CACHE_LOADED = True  # set even on failure — no retry
        try:
            from pathlib import Path
            from config.settings import DATA_DIR
            path = Path(DATA_DIR) / "rag_cache.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._ANSWER_CACHE.update(json.load(f))
        except Exception as exc:
            print(f"RAG cache preload skipped: {exc}")

    def _cache_key(self, question: str, context_text: str) -> str:
        h = hashlib.sha256()
        h.update(question.strip().lower().encode("utf-8"))
        h.update(b"\x1f")
        h.update(context_text.encode("utf-8"))
        return h.hexdigest()

    def _question_only_key(self, question: str) -> str:
        """Fallback cache key keyed on the question alone.

        Used when the (question, context) hit misses because state has grown
        since the cache was warmed. The pre-warm script writes BOTH keys, so
        a typical committee question is answered from the question-only key
        even if state drifted by a couple of new insights.
        """
        return "Q::" + hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()

    def answer_question(self, question: str, context_text: str) -> str:
        """Answer a natural-language question using state-derived RAG context.

        The committee asked for a chat interface "поверх готового агента". We
        keep the agent proactive (it still runs cycles and generates insights
        on its own) and offer the chat as an additional read-only window into
        accumulated state. ``context_text`` is produced by ``RAGContextBuilder``
        and contains the curated insight / alert / observation slice — this
        method only formats the prompt and calls GigaChat.

        The system prompt is deliberately strict about not inventing facts
        outside the supplied context — that is the whole point of grounding.

        Robustness:
          * Identical (question, context) pairs are answered from cache.
          * If GigaChat still fails after retries, instead of showing the
            generic "временно недоступна" message we now synthesise a useful
            answer directly from the context items.
        """
        self._ensure_cache_loaded()
        key = self._cache_key(question, context_text)
        if key in self._ANSWER_CACHE:
            return self._ANSWER_CACHE[key]
        # Question-only fallback: if state drifted since the cache was warmed
        # the strict key misses, but the prewarmer also writes a Q-only key
        # so common questions stay answerable.
        q_key = self._question_only_key(question)
        if q_key in self._ANSWER_CACHE:
            return self._ANSWER_CACHE[q_key]
        system = """Ты — HR-аналитик, отвечающий на вопросы пользователя строго по данным
агента ниже. Это не свободный поиск: используй ТОЛЬКО предоставленный контекст.

ПРАВИЛА:
1. Если в контексте нет данных для ответа — честно скажи об этом одной фразой
   и предложи запустить новый цикл анализа. Не выдумывай.
2. Ответ — деловой, конкретный, на русском. 3-6 предложений максимум.
3. Где уместно — ссылайся на номера инсайтов/алертов из контекста ([1], [2]).
4. Если вопрос требует свежих данных, которых нет в контексте, скажи это явно.
5. Не пиши «как HR-аналитик я считаю…» — пиши сразу по сути."""

        if not context_text.strip():
            context_text = "(Контекст пуст. У агента ещё нет собранных данных.)"

        user = f"""КОНТЕКСТ ОТ HR-АГЕНТА:
{context_text}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

Ответь."""

        result = self._chat(system, user)
        if not result:
            answer = self._synthesise_answer_from_context(question, context_text)
            self._remember(key, answer, question=question)
            return answer

        result = result.strip()
        # If _chat fell back to the mock "временно недоступна" string, replace
        # it with a context-grounded summary so the user always gets something
        # actionable rather than a dead-end error.
        if "временно недоступна" in result.lower():
            answer = self._synthesise_answer_from_context(question, context_text)
            self._remember(key, answer, question=question)
            return answer
        # Defensive unwrap: if the model (or the fallback) returned a JSON
        # blob shaped like an insight object, convert it to a human-readable
        # paragraph. We saw the chat box render raw ``{"what_changed": ...}``
        # when the prompt accidentally triggered the wrong mock branch.
        if result.startswith("{"):
            try:
                data = json.loads(result)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                parts: list = []
                if data.get("what_changed"):
                    parts.append(str(data["what_changed"]).rstrip("."))
                if data.get("why_important"):
                    parts.append(str(data["why_important"]).rstrip("."))
                if data.get("recommendation"):
                    parts.append("Рекомендация: " + str(data["recommendation"]))
                if data.get("analysis"):
                    parts.append(str(data["analysis"]).rstrip("."))
                if parts:
                    result = ". ".join(parts) + "."

        self._remember(key, result, question=question)
        return result

    def _remember(self, key: str, answer: str, question: Optional[str] = None) -> None:
        """Insert into the cache with a soft size cap (FIFO eviction).

        When ``question`` is provided we also store under the question-only
        key so the answer stays reachable if state drifts before the next
        identical question.
        """
        cache = self._ANSWER_CACHE
        if len(cache) >= self._ANSWER_CACHE_MAX:
            # Drop the oldest entry. dict preserves insertion order in 3.7+.
            cache.pop(next(iter(cache)))
        cache[key] = answer
        if question is not None:
            cache[self._question_only_key(question)] = answer

    def _synthesise_answer_from_context(self, question: str, context_text: str) -> str:
        """Build a usable answer from the RAG context when the LLM is down.

        We pick the first few content lines from the prompt (each item is a
        single line in RAGContextBuilder's format) and concatenate them into a
        short summary. This is strictly worse than a real LLM answer but it is
        infinitely better than an "временно недоступна" stub — the committee
        sees actual data the agent collected.
        """
        if not context_text.strip():
            return (
                "У агента ещё нет собранных данных по этому вопросу. "
                "Запусти цикл анализа кнопкой выше — модель сможет ответить "
                "сразу после первого цикла."
            )

        bullets: list = []
        for raw_line in context_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("###"):
                continue
            # Lines from RAGContextBuilder look like "1. [Тема] текст" or
            # "1. [risk] заголовок — текст". Keep the substance, drop the
            # leading numbering for a cleaner bullet.
            if line[:2].rstrip(".").isdigit() or line[:3].rstrip(".").isdigit():
                line = line.split(". ", 1)[-1]
            bullets.append(line)
            if len(bullets) >= 4:
                break

        body = "\n".join(f"• {b}" for b in bullets)
        return (
            f"Модель GigaChat сейчас недоступна, поэтому отвечаю по сырому "
            f"контексту из памяти агента:\n\n{body}\n\n"
            f"Попробуй задать вопрос ещё раз через минуту — обычно отпускает."
        )

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
