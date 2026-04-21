"""Unit tests for the sources catalog."""
import pytest

from config.sources_catalog import (
    CATEGORIES,
    REGIONS,
    SOURCES_CATALOG,
    get_source,
    load_sources,
    set_active,
    validate_source,
)
from config.settings import HR_TOPICS, RSS_SOURCES


class TestCatalogStructure:
    def test_all_ids_unique(self):
        ids = [s["id"] for s in SOURCES_CATALOG]
        assert len(ids) == len(set(ids)), "source ids must be unique"

    def test_all_sources_valid(self):
        for source in SOURCES_CATALOG:
            errors = validate_source(source)
            assert not errors, f"Source {source.get('id')} has validation errors: {errors}"

    def test_topics_covered_are_known(self):
        known = set(HR_TOPICS.keys())
        for source in SOURCES_CATALOG:
            for topic in source.get("topics_covered", []):
                assert topic in known, f"Unknown topic '{topic}' in source {source['id']}"

    def test_categories_consistent(self):
        for source in SOURCES_CATALOG:
            assert source.get("category") in CATEGORIES

    def test_regions_consistent(self):
        for source in SOURCES_CATALOG:
            region = source.get("region")
            if region is not None:
                assert region in REGIONS

    def test_has_at_least_seven_active_sources(self):
        # The defence baseline is 7 sources; catalog must not drop below that.
        active = load_sources(active_only=True)
        assert len(active) >= 7

    def test_catalog_has_candidate_sources_beyond_active(self):
        # Key point for the commission: the pool can grow. We should have
        # more candidates in the catalog than we currently activate.
        assert len(SOURCES_CATALOG) > len(load_sources(active_only=True))


class TestLoadSources:
    def test_active_only_filter(self):
        active = load_sources(active_only=True)
        assert all(s["is_active"] for s in active)

    def test_all_sources(self):
        all_sources = load_sources(active_only=False)
        assert len(all_sources) == len(SOURCES_CATALOG)


class TestGetSource:
    def test_returns_source_when_exists(self):
        src = get_source("hbr")
        assert src is not None
        assert src["name"] == "Harvard Business Review"

    def test_returns_none_when_missing(self):
        assert get_source("does_not_exist") is None


class TestSetActive:
    def test_toggle_and_restore(self):
        # HBR is active by default; toggle off then back on.
        original = get_source("hbr")["is_active"]
        try:
            assert set_active("hbr", False) is True
            assert get_source("hbr")["is_active"] is False
            assert set_active("hbr", True) is True
            assert get_source("hbr")["is_active"] is True
        finally:
            set_active("hbr", original)

    def test_unknown_source_returns_false(self):
        assert set_active("nonexistent", True) is False


class TestBackwardCompatibility:
    def test_rss_sources_shape_preserved(self):
        # Legacy code reads RSS_SOURCES expecting {"url", "name", "lang"} dicts.
        assert RSS_SOURCES, "RSS_SOURCES must not be empty"
        for entry in RSS_SOURCES:
            assert set(entry.keys()) == {"url", "name", "lang"}

    def test_rss_sources_match_active_catalog(self):
        active = load_sources(active_only=True)
        assert len(RSS_SOURCES) == len(active)


class TestValidateSource:
    def test_missing_required_field(self):
        errors = validate_source({"url": "http://x", "name": "X"})
        assert any("Missing required field" in e for e in errors)

    def test_invalid_lang(self):
        errors = validate_source({
            "id": "x", "url": "http://x", "name": "X",
            "lang": "fr", "category": "news", "topics_covered": [],
        })
        assert any("lang" in e for e in errors)

    def test_invalid_quality_score(self):
        errors = validate_source({
            "id": "x", "url": "http://x", "name": "X",
            "lang": "en", "category": "news", "topics_covered": [],
            "quality_score": 1.5,
        })
        assert any("quality_score" in e for e in errors)

    def test_valid_minimal_source(self):
        errors = validate_source({
            "id": "x", "url": "http://x", "name": "X",
            "lang": "en", "category": "news", "topics_covered": [],
        })
        assert errors == []
