"""Unit tests for AgentState persistence and capped collections."""
import json


def test_default_state_has_all_keys(isolated_state):
    state = isolated_state.state
    expected = {
        "last_check",
        "observations",
        "insights",
        "trends",
        "alerts",
        "processed_urls",
        "content_fingerprints",
        "source_events",
        "metrics",
    }
    assert expected.issubset(state.keys())


def test_save_and_reload(isolated_state, tmp_path):
    from src.agent.state import AgentState

    isolated_state.add_observation({"title": "Hello"})
    isolated_state.save()

    # Re-hydrate from file.
    reloaded = AgentState.__new__(AgentState)
    reloaded.state_file = isolated_state.state_file
    reloaded.state = reloaded._load_state()
    assert len(reloaded.state["observations"]) == 1
    assert reloaded.state["observations"][0]["title"] == "Hello"


def test_observations_capped_at_500(isolated_state):
    for i in range(600):
        isolated_state.add_observation({"i": i})
    assert len(isolated_state.state["observations"]) == 500
    # Oldest dropped, newest kept.
    assert isolated_state.state["observations"][-1]["i"] == 599


def test_insights_capped_at_100_newest_first(isolated_state):
    for i in range(120):
        isolated_state.add_insight({"i": i})
    assert len(isolated_state.state["insights"]) == 100
    assert isolated_state.state["insights"][0]["i"] == 119


def test_add_trend_point_caps_at_100(isolated_state):
    for i in range(150):
        isolated_state.add_trend_point("layoffs", 0.5)
    assert len(isolated_state.state["trends"]["layoffs"]) == 100


def test_trend_point_ignored_for_unknown_topic(isolated_state):
    isolated_state.add_trend_point("nonexistent", 0.5)
    assert "nonexistent" not in isolated_state.state["trends"]


def test_is_url_processed_and_mark(isolated_state):
    assert isolated_state.is_url_processed("http://x") is False
    isolated_state.mark_url_processed("http://x")
    assert isolated_state.is_url_processed("http://x") is True


def test_mark_url_processed_dedupes(isolated_state):
    isolated_state.mark_url_processed("http://x")
    isolated_state.mark_url_processed("http://x")
    assert isolated_state.state["processed_urls"].count("http://x") == 1


def test_processed_urls_capped_at_1000(isolated_state):
    for i in range(1500):
        isolated_state.mark_url_processed(f"http://{i}")
    assert len(isolated_state.state["processed_urls"]) == 1000


def test_alerts_capped_at_50(isolated_state):
    for i in range(70):
        isolated_state.add_alert({"title": f"alert-{i}"})
    assert len(isolated_state.state["alerts"]) == 50


def test_reset_restores_defaults(isolated_state):
    isolated_state.add_observation({"title": "x"})
    isolated_state.add_insight({"i": 1})
    isolated_state.reset()
    assert isolated_state.state["observations"] == []
    assert isolated_state.state["insights"] == []


def test_content_fingerprints_capped(isolated_state):
    big = [{"fingerprint": i, "exact": str(i), "item_id": str(i)} for i in range(2000)]
    isolated_state.set_content_fingerprints(big)
    assert len(isolated_state.state["content_fingerprints"]) == isolated_state.MAX_FINGERPRINTS


def test_record_content_duplicate_increments_metric(isolated_state):
    isolated_state.record_content_duplicate()
    isolated_state.record_content_duplicate()
    assert isolated_state.state["metrics"]["content_duplicates_skipped"] == 2


def test_source_events_capped(isolated_state):
    for i in range(6000):
        isolated_state.log_source_event({"source_id": "x", "kind": "fetched", "count": 1})
    assert len(isolated_state.state["source_events"]) == isolated_state.MAX_SOURCE_EVENTS


def test_source_event_gets_timestamp_when_missing(isolated_state):
    isolated_state.log_source_event({"source_id": "x", "kind": "fetched"})
    ev = isolated_state.get_source_events()[0]
    assert "timestamp" in ev and ev["timestamp"]


def test_corrupted_state_file_falls_back_to_default(tmp_path):
    from src.agent.state import AgentState

    bad = tmp_path / "state.json"
    bad.write_text("{{{not valid json", encoding="utf-8")
    state = AgentState.__new__(AgentState)
    state.state_file = bad
    loaded = state._load_state()
    assert "observations" in loaded
    assert loaded["observations"] == []


def test_state_json_is_utf8_with_russian(isolated_state):
    isolated_state.add_insight({"what_changed": "Крупные сокращения"})
    with open(isolated_state.state_file, encoding="utf-8") as f:
        raw = f.read()
    assert "Крупные" in raw  # ensure_ascii=False
    assert json.loads(raw)["insights"][0]["what_changed"] == "Крупные сокращения"
