"""Unit tests for SourceManager recommendation logic."""
import pytest

from src.sources.source_manager import (
    ACTION_ACTIVATE_VALUABLE,
    ACTION_DEACTIVATE,
    ACTION_INSUFFICIENT_DATA,
    ACTION_KEEP,
    MIN_EVENTS_FOR_EVALUATION,
    STALE_CYCLES_THRESHOLD,
    SourceManager,
)


def _row(**overrides):
    """Build a source-report row with sane defaults."""
    base = {
        "id": "test_src",
        "name": "Test Source",
        "is_active": True,
        "items_fetched": 100,
        "items_accepted": 30,
        "duplicates": 20,
        "duplicate_rate": 0.2,
        "insights_generated": 3,
        "cycles_without_new": 0,
        "cycles_seen": 10,
        "cycles_with_new": 10,
    }
    base.update(overrides)
    return base


class TestEvaluateRow:
    def setup_method(self):
        self.mgr = SourceManager()

    def test_insufficient_data(self):
        rec = self.mgr._evaluate_row(_row(items_fetched=MIN_EVENTS_FOR_EVALUATION - 1))
        assert rec.action == ACTION_INSUFFICIENT_DATA

    def test_high_duplicate_rate_triggers_deactivation(self):
        rec = self.mgr._evaluate_row(_row(
            duplicate_rate=0.8,
            duplicates=80,
            cycles_seen=5,
        ))
        assert rec.action == ACTION_DEACTIVATE
        assert "дублирования" in rec.reason.lower() or "дубли" in rec.reason.lower()

    def test_high_duplicate_rate_but_few_cycles_keeps(self):
        rec = self.mgr._evaluate_row(_row(
            duplicate_rate=0.8,
            duplicates=80,
            cycles_seen=1,
        ))
        # Not enough cycles to act on duplicates yet.
        assert rec.action != ACTION_DEACTIVATE

    def test_stale_source_is_deactivated(self):
        rec = self.mgr._evaluate_row(_row(
            cycles_without_new=STALE_CYCLES_THRESHOLD,
            duplicate_rate=0.1,
        ))
        assert rec.action == ACTION_DEACTIVATE
        assert "новых" in rec.reason.lower()

    def test_inactive_but_valuable_is_activated(self):
        rec = self.mgr._evaluate_row(_row(
            is_active=False,
            items_accepted=50,
            insights_generated=10,
            items_fetched=60,
            duplicate_rate=0.1,
        ))
        assert rec.action == ACTION_ACTIVATE_VALUABLE

    def test_normal_source_is_kept(self):
        rec = self.mgr._evaluate_row(_row(
            duplicate_rate=0.2,
            cycles_without_new=1,
            insights_generated=5,
        ))
        assert rec.action == ACTION_KEEP

    def test_recommendation_serializable(self):
        rec = self.mgr._evaluate_row(_row())
        as_dict = rec.to_dict()
        assert as_dict["source_id"] == "test_src"
        assert "action" in as_dict
        assert "reason" in as_dict
        assert "created_at" in as_dict


class TestEvaluateFull:
    def test_returns_recommendation_per_catalog_source(self):
        # Every catalog entry must get a recommendation. Orphan sources that
        # appear in events/observations but not in the catalog (legacy state
        # after schema migration) may also surface, so we assert the catalog
        # is a subset of recommendations, not strict equality.
        from config.sources_catalog import SOURCES_CATALOG

        recs = SourceManager().evaluate()
        rec_ids = {r.source_id for r in recs}
        catalog_ids = {s["id"] for s in SOURCES_CATALOG}
        assert catalog_ids.issubset(rec_ids)
