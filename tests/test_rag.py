"""Tests for the RAG context builder used by the «Спроси у HR-агента» chat.

These tests intentionally avoid touching GigaChat — the builder is a pure
function over agent state. The LLM call itself is exercised by the existing
fallback path in ``gigachat.py`` (mock response when no credentials).
"""
from __future__ import annotations

from src.api.rag import RAGContextBuilder


def _make_insight(topic: str, what: str = "wc", why: str = "wi", rec: str = "rc",
                  risk: str = "medium") -> dict:
    return {
        "topic": topic,
        "topic_name": topic,
        "what_changed": what,
        "why_important": why,
        "recommendation": rec,
        "risk_level": risk,
    }


def _make_alert(topic: str, title: str, risk: str = "high") -> dict:
    return {
        "title": title,
        "content": f"content about {topic}",
        "risk_level": risk,
        "topic": topic,
        "source": "rss-test",
    }


def _make_observation(topic: str, title: str) -> dict:
    return {
        "title": title,
        "classification": {"topic": topic},
        "source": "rss-test",
    }


def test_empty_state_yields_empty_context():
    ctx = RAGContextBuilder().build("Что нового?", [], [], [])
    assert ctx.is_empty()
    assert ctx.prompt_text == ""


def test_limits_are_enforced():
    insights = [_make_insight("hiring", what=f"insight #{i}") for i in range(20)]
    alerts = [_make_alert("hiring", f"alert #{i}") for i in range(20)]
    observations = [_make_observation("hiring", f"obs #{i}") for i in range(40)]

    ctx = RAGContextBuilder(
        insight_limit=3, alert_limit=2, observation_limit=5
    ).build("найм", insights, alerts, observations)

    assert len(ctx.insights) == 3
    assert len(ctx.alerts) == 2
    assert len(ctx.observations) == 5
    assert "insight #0" in ctx.prompt_text


def test_topic_match_floats_to_top():
    """When the question mentions a topic, matching items must come first."""
    insights = [
        _make_insight("hiring", what="hiring item"),
        _make_insight("burnout", what="burnout item"),
        _make_insight("hiring", what="another hiring item"),
    ]
    ctx = RAGContextBuilder().build("выгорание сотрудников", insights, [], [])

    # 'выгорание' is the Russian label for the burnout topic — that item
    # should be ranked first regardless of original list order.
    assert ctx.insights[0].get("what_changed") == "burnout item"


def test_prompt_contains_section_headers_only_when_data_present():
    ctx = RAGContextBuilder().build(
        "вопрос",
        insights=[_make_insight("hiring")],
        alerts=[],
        observations=[],
    )
    assert "### Текущие инсайты агента" in ctx.prompt_text
    assert "### Активные риск-уведомления" not in ctx.prompt_text
    assert "### Последние наблюдения" not in ctx.prompt_text


def test_long_strings_get_truncated():
    long_text = "x" * 2000
    ctx = RAGContextBuilder().build(
        "вопрос",
        insights=[_make_insight("hiring", what=long_text)],
        alerts=[],
        observations=[],
    )
    # Truncated to ~220 chars + ellipsis, not the full 2000.
    assert long_text not in ctx.prompt_text
    assert "…" in ctx.prompt_text
