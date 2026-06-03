"""RAG context builder for the «Спроси у HR-агента» chat.

The agent is primarily proactive, but the defence committee asked for a way
to query the accumulated state in natural language. Instead of hitting RSS
sources again on every question, we feed GigaChat a curated context made of:

* the latest insights (already distilled "what / why / what to do" summaries),
* the unacknowledged alerts (so questions about current risks have grounding),
* a handful of the most recent raw observations (titles + topics).

Keeping this in a dedicated module — separate from ``GigaChatClient`` — makes
the boundary between *infrastructure* (state, LLM) and *retrieval policy*
(what to feed the LLM, how to truncate) explicit and testable without an API
key.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from config.settings import HR_TOPICS


# Hard caps protect us from blowing the GigaChat context window when state
# grows large. These numbers are conservative — the prompt below stays well
# under 4k characters even when all caps are hit.
DEFAULT_INSIGHT_LIMIT = 8
DEFAULT_ALERT_LIMIT = 6
DEFAULT_OBSERVATION_LIMIT = 10
MAX_OBSERVATION_TITLE_LEN = 140


# Lightweight keyword map for the topic-hint detector. We don't ship a real
# tokenizer for the MVP — a hand-curated keyword list per topic is enough to
# bias retrieval toward the right slice when the user asks about e.g.
# «выгорание сотрудников» or «массовые сокращения».
TOPIC_KEYWORDS: dict = {
    "hiring":    ["найм", "рекрутинг", "вакансии", "hiring", "recruit", "talent"],
    "layoffs":   ["сокращен", "увольнен", "layoff", "fired", "downsizing"],
    "salaries":  ["зарплат", "компенсац", "оплат", "salary", "salaries", "pay"],
    "skills":    ["навык", "обучен", "развит", "skill", "training", "learning"],
    "burnout":   ["выгоран", "стресс", "burnout", "mental", "work-life"],
    "culture":   ["культур", "ценност", "вовлеч", "culture", "engagement"],
    "diversity": ["разнообразие", "инклюз", "diversity", "d&i", "dei"],
}


@dataclass
class RAGContext:
    """Structured context handed to the LLM, plus a debug-friendly view."""

    insights: List[dict]
    alerts: List[dict]
    observations: List[dict]
    prompt_text: str

    def is_empty(self) -> bool:
        return not (self.insights or self.alerts or self.observations)


class RAGContextBuilder:
    """Picks the most relevant slice of agent state for a question.

    The current policy is intentionally simple: recency + risk_level. If the
    question mentions a known HR topic we surface items matching that topic
    first; otherwise we fall back to plain recency. Smarter retrieval (e.g.
    embedding similarity) is out of scope for the MVP and would require an
    embedding model that GigaChat does not expose for free.
    """

    def __init__(
        self,
        insight_limit: int = DEFAULT_INSIGHT_LIMIT,
        alert_limit: int = DEFAULT_ALERT_LIMIT,
        observation_limit: int = DEFAULT_OBSERVATION_LIMIT,
    ):
        self.insight_limit = insight_limit
        self.alert_limit = alert_limit
        self.observation_limit = observation_limit

    def build(
        self,
        question: str,
        insights: List[dict],
        alerts: List[dict],
        observations: List[dict],
    ) -> RAGContext:
        """Return the context object used by ``GigaChatClient.answer_question``."""
        topic_hint = self._detect_topic(question)

        chosen_insights = self._rank(insights, topic_hint)[: self.insight_limit]
        chosen_alerts = self._rank(alerts, topic_hint)[: self.alert_limit]
        chosen_observations = self._rank(observations, topic_hint)[: self.observation_limit]

        prompt_text = self._format_prompt(
            chosen_insights, chosen_alerts, chosen_observations
        )

        return RAGContext(
            insights=chosen_insights,
            alerts=chosen_alerts,
            observations=chosen_observations,
            prompt_text=prompt_text,
        )

    # ---- internals ----------------------------------------------------------

    def _detect_topic(self, question: str) -> Optional[str]:
        """Return the first HR topic whose keyword appears in the question.

        Uses ``TOPIC_KEYWORDS`` (substring match against RU/EN stems) instead
        of comparing to the full Russian label — labels like «Выгорание и
        вовлечённость» rarely appear verbatim in a question, but the stem
        «выгоран» does. Order in ``HR_TOPICS`` defines tie-break priority.
        """
        q = (question or "").lower()
        if not q:
            return None
        for topic_id in HR_TOPICS.keys():
            for keyword in TOPIC_KEYWORDS.get(topic_id, []):
                if keyword in q:
                    return topic_id
        return None

    def _rank(self, items: List[dict], topic_hint: Optional[str]) -> List[dict]:
        """Stable-sort items so topic matches come first, recency as a tie-break.

        The input lists are already roughly ordered newest-first (``state.py``
        inserts at index 0). We preserve that order and just shuffle topic
        matches to the front when a hint is present.
        """
        if not items:
            return []
        if topic_hint is None:
            return list(items)
        head: List[dict] = []
        tail: List[dict] = []
        for item in items:
            if item.get("topic") == topic_hint or item.get("classification", {}).get("topic") == topic_hint:
                head.append(item)
            else:
                tail.append(item)
        return head + tail

    def _format_prompt(self, insights: List[dict], alerts: List[dict], observations: List[dict]) -> str:
        """Render context as plain text the LLM can read directly."""
        lines: List[str] = []

        if insights:
            lines.append("### Текущие инсайты агента:")
            for idx, ins in enumerate(insights, 1):
                topic = ins.get("topic_name") or HR_TOPICS.get(ins.get("topic", ""), ins.get("topic", "HR"))
                risk = ins.get("risk_level", "—")
                lines.append(
                    f"{idx}. [{topic}, риск={risk}] "
                    f"Что произошло: {self._short(ins.get('what_changed', '—'))} "
                    f"Почему важно: {self._short(ins.get('why_important', '—'))} "
                    f"Рекомендация: {self._short(ins.get('recommendation', '—'))}"
                )
            lines.append("")

        if alerts:
            lines.append("### Активные риск-уведомления:")
            for idx, alert in enumerate(alerts, 1):
                lines.append(
                    f"{idx}. [{alert.get('risk_level', '—')}] "
                    f"{alert.get('title', '—')} — {self._short(alert.get('content', '—'))} "
                    f"(источник: {alert.get('source', '—')})"
                )
            lines.append("")

        if observations:
            lines.append("### Последние наблюдения (заголовки источников):")
            for idx, obs in enumerate(observations, 1):
                title = self._short(obs.get("title", "—"), MAX_OBSERVATION_TITLE_LEN)
                topic_id = obs.get("classification", {}).get("topic") or obs.get("topic", "")
                topic = HR_TOPICS.get(topic_id, topic_id or "—")
                lines.append(
                    f"{idx}. [{topic}] {title} (источник: {obs.get('source', '—')})"
                )

        return "\n".join(lines).strip()

    @staticmethod
    def _short(text: str, limit: int = 220) -> str:
        if not text:
            return "—"
        text = str(text).replace("\n", " ").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"


# Module-level singleton — cheap to share, no per-call state.
rag_context_builder = RAGContextBuilder()
