"""
Source analytics: per-source quality and contribution metrics.

Computes metrics used both on the "Sources" dashboard page and by
:mod:`src.sources.source_manager` to decide which sources stay in the pool.

Inputs:
    - agent_state.source_events  — append-only log of fetch/accept/duplicate events
    - agent_state.observations   — processed items (carry source_id, risk_score, topic)
    - agent_state.insights       — generated insights (carry source, source_title)
    - sources_catalog            — static metadata (name, lang, topics_covered)

Output per source:
    items_fetched          — total items pulled from this source
    items_accepted         — items that passed dedup and were processed
    duplicate_rate         — duplicates / fetched (0..1)
    unique_contribution    — accepted items with no earlier duplicate match
    insights_generated     — count of insights traced back to this source
    avg_risk_score         — mean risk_score across accepted items
    last_seen              — timestamp of most recent fetched event
    topic_coverage         — list of topics actually produced (from observations)
    cycles_without_new     — consecutive cycles with zero accepted items
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from config.sources_catalog import SOURCES_CATALOG, get_source
from src.agent.state import agent_state


def _empty_metrics() -> dict:
    return {
        "items_fetched": 0,
        "items_accepted": 0,
        "duplicates": 0,
        "duplicate_rate": 0.0,
        "unique_contribution": 0,
        "insights_generated": 0,
        "risk_sum": 0.0,
        "risk_count": 0,
        "avg_risk_score": 0.0,
        "last_seen": None,
        "topic_coverage": [],
        "cycles_seen": set(),
        "cycles_with_new": set(),
        "cycles_without_new": 0,
    }


def _resolve_source_id(obs_or_insight: dict) -> Optional[str]:
    """Extract a source_id from an observation or insight dict.

    Observations carry ``source_id`` directly (added by the fetcher). Insights
    historically carry only ``source`` (display name) — we look it up in the catalog.
    """
    sid = obs_or_insight.get("source_id")
    if sid:
        return sid
    display = obs_or_insight.get("source")
    if not display:
        return None
    for s in SOURCES_CATALOG:
        if s.get("name") == display:
            return s["id"]
    return None


def compute_source_metrics() -> Dict[str, dict]:
    """Aggregate per-source metrics from agent state.

    Returns a mapping ``source_id -> metrics`` covering every source that has
    appeared in events OR observations, even if not in the active catalog.
    """
    per_source: Dict[str, dict] = defaultdict(_empty_metrics)

    # Walk the event log for fetch/accept/duplicate counts and freshness.
    for event in agent_state.get_source_events():
        sid = event.get("source_id")
        if not sid:
            continue
        m = per_source[sid]
        kind = event.get("kind")
        ts = event.get("timestamp")
        cycle = event.get("cycle") or ts

        if kind == "fetched":
            count = event.get("count", 1)
            m["items_fetched"] += count
            if ts and (m["last_seen"] is None or ts > m["last_seen"]):
                m["last_seen"] = ts
            if cycle:
                m["cycles_seen"].add(cycle)
        elif kind == "accepted":
            m["items_accepted"] += 1
            m["unique_contribution"] += 1
            if cycle:
                m["cycles_with_new"].add(cycle)
        elif kind == "duplicate":
            m["duplicates"] += 1

    # Walk observations for risk score and topic coverage.
    topic_sets: Dict[str, set] = defaultdict(set)
    for obs in agent_state.state.get("observations", []):
        sid = _resolve_source_id(obs)
        if not sid:
            continue
        m = per_source[sid]
        rs = obs.get("risk_score")
        if isinstance(rs, (int, float)):
            m["risk_sum"] += float(rs)
            m["risk_count"] += 1
        topic = obs.get("classification", {}).get("topic")
        if topic:
            topic_sets[sid].add(topic)

    # Count insights per source.
    for insight in agent_state.state.get("insights", []):
        sid = _resolve_source_id(insight)
        if not sid:
            continue
        per_source[sid]["insights_generated"] += 1

    # Finalize derived fields.
    results: Dict[str, dict] = {}
    for sid, m in per_source.items():
        fetched = m["items_fetched"]
        duplicates = m["duplicates"]
        m["duplicate_rate"] = (duplicates / fetched) if fetched else 0.0
        m["avg_risk_score"] = (m["risk_sum"] / m["risk_count"]) if m["risk_count"] else 0.0
        m["topic_coverage"] = sorted(topic_sets.get(sid, set()))
        m["cycles_without_new"] = len(m["cycles_seen"] - m["cycles_with_new"])
        # Drop internal-only accumulators from the public shape.
        del m["risk_sum"]
        del m["risk_count"]
        m["cycles_seen"] = len(m["cycles_seen"])
        m["cycles_with_new"] = len(m["cycles_with_new"])
        results[sid] = m

    return results


def build_source_report() -> List[dict]:
    """Combine catalog metadata with computed metrics for dashboard display.

    Result is one row per source from the catalog, enriched with live metrics
    (zero-filled if the source has never been fetched yet).
    """
    metrics = compute_source_metrics()
    report: List[dict] = []
    seen_ids = set()

    for source in SOURCES_CATALOG:
        sid = source["id"]
        seen_ids.add(sid)
        row = {
            "id": sid,
            "name": source.get("name"),
            "lang": source.get("lang"),
            "region": source.get("region"),
            "category": source.get("category"),
            "is_active": source.get("is_active", False),
            "quality_score": source.get("quality_score"),
            "topics_covered": source.get("topics_covered", []),
            "rationale": source.get("rationale"),
            **metrics.get(sid, _public_zero_metrics()),
        }
        report.append(row)

    # Orphan sources — present in events/observations but not in the catalog.
    for sid, m in metrics.items():
        if sid in seen_ids:
            continue
        row = {
            "id": sid,
            "name": sid,
            "lang": None,
            "region": None,
            "category": None,
            "is_active": False,
            "quality_score": None,
            "topics_covered": [],
            "rationale": "(источник не в каталоге)",
            **m,
        }
        report.append(row)

    return report


def _public_zero_metrics() -> dict:
    """Zero-filled metrics for sources without any events yet."""
    m = _empty_metrics()
    # Convert set-typed internal fields to their public counts.
    del m["risk_sum"]
    del m["risk_count"]
    m["cycles_seen"] = 0
    m["cycles_with_new"] = 0
    return m


def find_duplicate_pairs_between_sources(min_pairs: int = 1) -> List[dict]:
    """Summarise cross-source duplication from event log.

    For each duplicate event, if we can trace ``matched_item_id`` to another
    source, count the pair. Returns rows ``{source_a, source_b, duplicate_pairs}``.
    """
    # Build url -> source_id from observations.
    url_to_source: Dict[str, str] = {}
    for obs in agent_state.state.get("observations", []):
        sid = _resolve_source_id(obs)
        url = obs.get("url") or obs.get("id")
        if sid and url:
            url_to_source[url] = sid

    pair_counts: Dict[tuple, int] = defaultdict(int)
    for event in agent_state.get_source_events():
        if event.get("kind") != "duplicate":
            continue
        sid_a = event.get("source_id")
        matched = event.get("matched_item_id")
        sid_b = url_to_source.get(matched)
        if not sid_a or not sid_b or sid_a == sid_b:
            continue
        key = tuple(sorted((sid_a, sid_b)))
        pair_counts[key] += 1

    rows = [
        {"source_a": a, "source_b": b, "duplicate_pairs": n}
        for (a, b), n in pair_counts.items()
        if n >= min_pairs
    ]
    rows.sort(key=lambda r: r["duplicate_pairs"], reverse=True)
    return rows
