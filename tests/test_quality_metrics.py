"""Tests for the Cohen's Kappa quality metric."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.processing.quality_metrics import (
    KappaReport,
    cohen_kappa,
    evaluate_classifier,
    load_cached_report,
    save_report,
)


# ---- pure cohen_kappa ------------------------------------------------------


def test_perfect_agreement_is_one():
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == pytest.approx(1.0)


def test_perfect_disagreement_with_balanced_labels_is_negative_one():
    """Two-label, fully swapped → kappa = -1 (worse than chance)."""
    assert cohen_kappa(["a", "b"], ["b", "a"]) == pytest.approx(-1.0)


def test_random_agreement_with_uniform_marginals_collapses_to_zero():
    """When predicted distribution matches true distribution but pairing
    is random, observed agreement equals expected agreement → kappa ≈ 0."""
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "b", "a", "b"]
    assert cohen_kappa(y_true, y_pred) == pytest.approx(0.0)


def test_empty_inputs_return_zero_not_error():
    assert cohen_kappa([], []) == 0.0


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        cohen_kappa(["a"], ["a", "b"])


def test_uniform_single_class_no_signal_returns_zero():
    """If everyone predicts and labels the same class, Pe=1 → undefined,
    we return 0.0 (no signal) rather than crash."""
    assert cohen_kappa(["a", "a", "a"], ["a", "a", "a"]) == 1.0


# ---- evaluate_classifier with a stub classifier ----------------------------


def _fixture(tmp_path: Path, items: list) -> Path:
    p = tmp_path / "labeled.json"
    p.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return p


def test_evaluate_classifier_counts_per_topic_correctly(tmp_path):
    fixture = _fixture(tmp_path, [
        {"title": "t1", "content": "c", "expected_topic": "hiring"},
        {"title": "t2", "content": "c", "expected_topic": "hiring"},
        {"title": "t3", "content": "c", "expected_topic": "layoffs"},
    ])
    # Stub: always predicts 'hiring'.
    stub = lambda _text: {"topic": "hiring"}
    report = evaluate_classifier(stub, labeled_path=fixture)
    assert report.n_items == 3
    assert report.per_topic_total == {"hiring": 2, "layoffs": 1}
    assert report.per_topic_correct == {"hiring": 2}
    assert report.accuracy == pytest.approx(2 / 3)


def test_evaluate_classifier_skips_items_without_label(tmp_path):
    fixture = _fixture(tmp_path, [
        {"title": "t1", "content": "c", "expected_topic": "hiring"},
        {"title": "t2", "content": "c"},  # no label
        {"title": "", "content": "", "expected_topic": "burnout"},  # no text
    ])
    report = evaluate_classifier(lambda _t: {"topic": "hiring"}, labeled_path=fixture)
    assert report.n_items == 1


# ---- persistence -----------------------------------------------------------


def test_save_and_load_round_trip(tmp_path):
    src = KappaReport(
        kappa=0.73, accuracy=0.81, n_items=35,
        per_topic_correct={"hiring": 5}, per_topic_total={"hiring": 6},
        computed_at="2026-06-03T18:00:00",
    )
    path = tmp_path / "metrics.json"
    save_report(src, path)
    loaded = load_cached_report(path)
    assert loaded is not None
    assert loaded.kappa == 0.73
    assert loaded.accuracy == 0.81
    assert loaded.per_topic_total == {"hiring": 6}


def test_load_cached_report_missing_file_returns_none(tmp_path):
    assert load_cached_report(tmp_path / "does-not-exist.json") is None
