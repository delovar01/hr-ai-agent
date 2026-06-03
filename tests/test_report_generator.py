"""Tests for the Markdown daily-summary renderer."""
from __future__ import annotations

from datetime import datetime, timedelta

from src.insights.report_generator import (
    generate_daily_summary_markdown,
    generate_daily_summary_pdf,
)


def _now() -> datetime:
    return datetime(2026, 6, 3, 12, 0, 0)


def _state(**overrides) -> dict:
    base = {
        "user_config": {"role": "analyst"},
        "alerts": [],
        "insights": [],
        "trends": {},
        "metrics": {},
    }
    base.update(overrides)
    return base


def test_empty_state_renders_safe_placeholders():
    md = generate_daily_summary_markdown(_state(), now=_now())
    assert "# HR Daily Summary" in md
    assert "критических событий не зафиксировано" in md
    assert "Недостаточно данных" in md
    assert "Свежих инсайтов нет" in md


def test_critical_alerts_appear_first():
    now = _now()
    alerts = [
        {"title": "low one", "risk_level": "low", "created_at": now.isoformat()},
        {"title": "CRIT one", "risk_level": "critical", "created_at": now.isoformat()},
        {"title": "med one", "risk_level": "medium", "created_at": now.isoformat()},
    ]
    md = generate_daily_summary_markdown(_state(alerts=alerts), now=now)
    crit_idx = md.find("CRIT one")
    low_idx = md.find("low one")
    assert crit_idx != -1 and low_idx != -1
    assert crit_idx < low_idx


def test_alerts_outside_window_filtered_out():
    now = _now()
    fresh = {"title": "FRESH", "risk_level": "high", "created_at": now.isoformat()}
    stale = {
        "title": "STALE",
        "risk_level": "high",
        "created_at": (now - timedelta(hours=48)).isoformat(),
    }
    md = generate_daily_summary_markdown(
        _state(alerts=[fresh, stale]), hours_window=24, now=now
    )
    assert "FRESH" in md
    assert "STALE" not in md


def test_trends_ranked_by_absolute_change():
    trends = {
        "hiring":  {"direction": "up",   "change": 2.0,  "description": "small"},
        "layoffs": {"direction": "up",   "change": 15.0, "description": "big"},
        "burnout": {"direction": "down", "change": -8.0, "description": "drop"},
    }
    md = generate_daily_summary_markdown(_state(trends=trends), now=_now())
    big_idx = md.find("big")
    small_idx = md.find("small")
    assert big_idx != -1 and small_idx != -1
    # 15% absolute change must appear before 2% in the ranked table.
    assert big_idx < small_idx


def test_insights_rendered_with_all_sections():
    insights = [{
        "topic_name": "Выгорание",
        "topic": "burnout",
        "what_changed": "growing burnout signals",
        "why_important": "team morale at risk",
        "recommendation": "run pulse survey",
        "risk_level": "high",
        "urgency": "immediate",
        "source": "harvard-business",
    }]
    md = generate_daily_summary_markdown(_state(insights=insights), now=_now())
    assert "growing burnout signals" in md
    assert "team morale at risk" in md
    assert "run pulse survey" in md
    assert "немедленно" in md
    assert "harvard-business" in md


def test_pdf_generation_returns_valid_pdf_bytes():
    """Smoke test: PDF is real bytes and starts with the %PDF magic marker."""
    state = _state(
        insights=[{
            "topic_name": "Выгорание",
            "what_changed": "growing burnout",
            "why_important": "morale at risk",
            "recommendation": "run survey",
            "risk_level": "high",
            "urgency": "immediate",
        }],
        metrics={"total_sources_checked": 5},
    )
    pdf = generate_daily_summary_pdf(state, now=_now())
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-"), "Output is not a valid PDF stream"
    # PDF should be non-trivially sized — empty state still yields headers.
    assert len(pdf) > 1000


def test_metrics_block_uses_supplied_numbers():
    metrics = {
        "total_sources_checked": 12,
        "total_insights_generated": 47,
        "anomalies_detected": 3,
        "content_duplicates_skipped": 9,
    }
    md = generate_daily_summary_markdown(_state(metrics=metrics), now=_now())
    assert "Циклов мониторинга: **12**" in md
    assert "Сгенерировано инсайтов: **47**" in md
    assert "Аномалий зафиксировано: **3**" in md
    assert "Дублей отфильтровано: **9**" in md
