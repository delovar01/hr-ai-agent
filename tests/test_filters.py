"""Tests for keyword/topic filtering on insights and alerts."""
from __future__ import annotations

from src.insights.filters import filter_alerts, filter_insights


def _insight(topic: str, what: str = "", source: str = "src") -> dict:
    return {
        "topic": topic,
        "topic_name": topic.title(),
        "what_changed": what,
        "why_important": "",
        "recommendation": "",
        "source": source,
        "source_title": "",
    }


def _alert(topic: str, title: str, content: str = "", source: str = "src") -> dict:
    return {
        "topic": topic,
        "title": title,
        "content": content,
        "source": source,
    }


def test_empty_query_and_topics_returns_all():
    items = [_insight("hiring"), _insight("burnout")]
    assert filter_insights(items) == items
    assert filter_insights(items, query="   ") == items
    assert filter_insights(items, topics=[]) == items


def test_topic_filter_keeps_only_selected_topics():
    items = [_insight("hiring"), _insight("burnout"), _insight("hiring")]
    result = filter_insights(items, topics=["hiring"])
    assert len(result) == 2
    assert all(i["topic"] == "hiring" for i in result)


def test_keyword_filter_is_case_insensitive():
    items = [
        _insight("hiring", what="Massive Layoff at TechCorp"),
        _insight("hiring", what="Stable hiring"),
    ]
    result = filter_insights(items, query="MASSIVE")
    assert len(result) == 1
    assert "Massive" in result[0]["what_changed"]


def test_query_and_topic_combined_use_AND_semantics():
    # All items have query-irrelevant what_changed text so the keyword
    # search only matches against the explicit text below.
    items = [
        {"topic": "hiring", "topic_name": "Найм", "what_changed": "критический сигнал"},
        {"topic": "burnout", "topic_name": "Выгорание", "what_changed": "критический сигнал"},
        {"topic": "burnout", "topic_name": "Выгорание", "what_changed": "обычное наблюдение"},
    ]
    result = filter_insights(items, query="критический", topics=["burnout"])
    assert len(result) == 1
    assert result[0]["topic"] == "burnout"
    assert "критический" in result[0]["what_changed"]


def test_query_matches_source_field():
    items = [
        _insight("hiring", source="harvard-business-review"),
        _insight("hiring", source="vc-ru"),
    ]
    result = filter_insights(items, query="harvard")
    assert len(result) == 1
    assert result[0]["source"] == "harvard-business-review"


def test_alert_filter_searches_title_and_content():
    items = [
        _alert("burnout", title="Burnout signals", content="team feeling stressed"),
        _alert("hiring", title="Hiring boom", content="more applicants"),
    ]
    by_title = filter_alerts(items, query="boom")
    by_content = filter_alerts(items, query="stressed")
    assert len(by_title) == 1
    assert len(by_content) == 1


def test_alert_filter_combined_with_topic():
    items = [
        _alert("burnout", title="signal"),
        _alert("hiring", title="signal"),
    ]
    result = filter_alerts(items, query="signal", topics=["burnout"])
    assert len(result) == 1
    assert result[0]["topic"] == "burnout"
