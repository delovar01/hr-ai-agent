"""Search and topic filters for insights, alerts and observations.

Pulled out into a separate module so the dashboard layer stays thin and the
filter logic is independently testable. Closes the «возможное добавление
поиска новостей по собственному запросу» item from the team chat — we
don't do a fresh web search (that's a different product), we filter the
already-collected agent state by keyword + topic.

All filters are *case-insensitive* substring matches and they operate on
whichever text fields are most natural for each item type. Whitespace-only
queries are treated as "no filter" so users can use the topic dropdown
alone.
"""
from __future__ import annotations

from typing import Iterable, List, Optional


def filter_insights(
    insights: Iterable[dict],
    query: str = "",
    topics: Optional[List[str]] = None,
) -> List[dict]:
    """Return insights matching the keyword and/or topic filter.

    Searched fields: ``what_changed``, ``why_important``, ``recommendation``,
    ``source_title``, ``source``, ``topic_name``.
    """
    q = (query or "").strip().lower()
    selected = set(topics or [])
    out: List[dict] = []
    for ins in insights:
        if selected and ins.get("topic") not in selected:
            continue
        if q and not _matches_text(q, [
            ins.get("what_changed"),
            ins.get("why_important"),
            ins.get("recommendation"),
            ins.get("source_title"),
            ins.get("source"),
            ins.get("topic_name"),
        ]):
            continue
        out.append(ins)
    return out


def filter_alerts(
    alerts: Iterable[dict],
    query: str = "",
    topics: Optional[List[str]] = None,
) -> List[dict]:
    """Return alerts matching the filter. Searched fields: title, content, source."""
    q = (query or "").strip().lower()
    selected = set(topics or [])
    out: List[dict] = []
    for alert in alerts:
        if selected and alert.get("topic") not in selected:
            continue
        if q and not _matches_text(q, [
            alert.get("title"),
            alert.get("content"),
            alert.get("source"),
        ]):
            continue
        out.append(alert)
    return out


def _matches_text(query: str, fields: Iterable[Optional[str]]) -> bool:
    """True if any non-empty field contains the (already lower-cased) query."""
    for value in fields:
        if value and query in str(value).lower():
            return True
    return False
