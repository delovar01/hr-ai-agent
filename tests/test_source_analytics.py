"""Integration-ish tests for source analytics aggregation.

Uses the real AgentState singleton, so we reset and restore it around each test
to keep the real state.json untouched.
"""
import copy

import pytest


@pytest.fixture
def clean_agent_state():
    """Reset the singleton agent_state around the test, restoring after."""
    from src.agent.state import agent_state

    original = copy.deepcopy(agent_state.state)
    agent_state.state = agent_state._default_state()
    try:
        yield agent_state
    finally:
        agent_state.state = original
        # Don't save — we don't want to overwrite real state.


class TestComputeSourceMetrics:
    def test_empty_state_returns_empty(self, clean_agent_state):
        from src.sources.source_analytics import compute_source_metrics

        assert compute_source_metrics() == {}

    def test_counts_fetched_and_accepted(self, clean_agent_state):
        from src.sources.source_analytics import compute_source_metrics

        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "fetched", "count": 5, "cycle": "c1"})
        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "accepted", "item_id": "u1", "cycle": "c1"})
        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "accepted", "item_id": "u2", "cycle": "c1"})
        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "duplicate", "matched_item_id": "u0", "cycle": "c1"})

        metrics = compute_source_metrics()
        assert "hbr" in metrics
        assert metrics["hbr"]["items_fetched"] == 5
        assert metrics["hbr"]["items_accepted"] == 2
        assert metrics["hbr"]["duplicates"] == 1
        assert metrics["hbr"]["duplicate_rate"] == pytest.approx(0.2)

    def test_avg_risk_from_observations(self, clean_agent_state):
        from src.sources.source_analytics import compute_source_metrics

        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "fetched", "count": 2, "cycle": "c1"})
        clean_agent_state.state["observations"].extend([
            {"source_id": "hbr", "risk_score": 0.2, "classification": {"topic": "hiring"}},
            {"source_id": "hbr", "risk_score": 0.8, "classification": {"topic": "layoffs"}},
        ])
        metrics = compute_source_metrics()
        assert metrics["hbr"]["avg_risk_score"] == pytest.approx(0.5)
        assert set(metrics["hbr"]["topic_coverage"]) == {"hiring", "layoffs"}

    def test_cycles_without_new_counts_only_fetch_only_cycles(self, clean_agent_state):
        from src.sources.source_analytics import compute_source_metrics

        # Cycle c1: fetched + accepted (productive)
        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "fetched", "count": 1, "cycle": "c1"})
        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "accepted", "item_id": "u1", "cycle": "c1"})
        # Cycles c2, c3: fetched only (stale)
        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "fetched", "count": 1, "cycle": "c2"})
        clean_agent_state.log_source_event({"source_id": "hbr", "kind": "fetched", "count": 1, "cycle": "c3"})

        metrics = compute_source_metrics()
        assert metrics["hbr"]["cycles_without_new"] == 2


class TestBuildSourceReport:
    def test_report_has_row_per_catalog_source(self, clean_agent_state):
        from config.sources_catalog import SOURCES_CATALOG
        from src.sources.source_analytics import build_source_report

        report = build_source_report()
        catalog_ids = {s["id"] for s in SOURCES_CATALOG}
        report_ids = {row["id"] for row in report}
        assert catalog_ids.issubset(report_ids)

    def test_unknown_source_appears_as_orphan(self, clean_agent_state):
        from src.sources.source_analytics import build_source_report

        clean_agent_state.log_source_event({"source_id": "ghost_source", "kind": "fetched", "count": 1})
        report = build_source_report()
        ghost = next((r for r in report if r["id"] == "ghost_source"), None)
        assert ghost is not None
        assert ghost["is_active"] is False


class TestFindCrossSourcePairs:
    def test_pairs_traced_via_url(self, clean_agent_state):
        from src.sources.source_analytics import find_duplicate_pairs_between_sources

        # Observation from SHRM with url=u1
        clean_agent_state.state["observations"].append({
            "source_id": "shrm",
            "url": "u1",
            "classification": {"topic": "layoffs"},
        })
        # HBR saw a duplicate that matched u1 (i.e. shrm's article).
        clean_agent_state.log_source_event({
            "source_id": "hbr",
            "kind": "duplicate",
            "matched_item_id": "u1",
        })

        pairs = find_duplicate_pairs_between_sources()
        assert len(pairs) == 1
        assert set([pairs[0]["source_a"], pairs[0]["source_b"]]) == {"hbr", "shrm"}
        assert pairs[0]["duplicate_pairs"] == 1
