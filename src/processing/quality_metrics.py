"""Cohen's Kappa quality metric for the HR topic classifier.

Why this exists
---------------
Critierion 4 of the УрФУ rubric — «Архитектура решения и использование ИИ»
— explicitly distinguishes между «формальным использованием ИИ» (4 баллов)
и «обоснованными методами применения ИИ» (10 баллов). To stand on the high
side we need a measurable quality number, not «GigaChat умно работает».

Cohen's Kappa compares the classifier's labels against expert-annotated
labels stored in ``tests/fixtures/labeled_news.json``. Unlike plain
accuracy, kappa subtracts the agreement you would expect by chance, which
matters when topic frequencies are uneven (HR datasets always are —
``hiring`` and ``layoffs`` dominate).

Caching
-------
Computing kappa with the live GigaChat classifier is slow (~30s for 35
items) and burns API quota — we do *not* want to recompute on every
dashboard load. The metric is precomputed by ``scripts/compute_kappa.py``
into ``data/quality_metrics.json`` and the dashboard simply reads that
file. If the file is missing we show «не рассчитано», not a stale value.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from config.settings import DATA_DIR


LABELED_FIXTURES_DEFAULT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "labeled_news.json"
METRICS_CACHE_PATH = DATA_DIR / "quality_metrics.json"


@dataclass
class KappaReport:
    """Result of one classifier-vs-expert evaluation run."""

    kappa: float
    accuracy: float
    n_items: int
    per_topic_correct: dict  # topic -> int
    per_topic_total: dict    # topic -> int
    computed_at: str         # ISO timestamp

    def to_dict(self) -> dict:
        return {
            "kappa": self.kappa,
            "accuracy": self.accuracy,
            "n_items": self.n_items,
            "per_topic_correct": self.per_topic_correct,
            "per_topic_total": self.per_topic_total,
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KappaReport":
        return cls(
            kappa=float(data.get("kappa", 0.0)),
            accuracy=float(data.get("accuracy", 0.0)),
            n_items=int(data.get("n_items", 0)),
            per_topic_correct=dict(data.get("per_topic_correct", {})),
            per_topic_total=dict(data.get("per_topic_total", {})),
            computed_at=str(data.get("computed_at", "")),
        )


def cohen_kappa(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Compute Cohen's Kappa for two equal-length label sequences.

    No external deps (sklearn is too heavy for one metric). Implements the
    standard formula::

        kappa = (Po - Pe) / (1 - Pe)

    where Po is observed agreement and Pe is chance agreement based on each
    rater's marginal label distribution.

    Returns 0.0 when sequences are empty or fully uniform (no signal).
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    n = len(y_true)
    if n == 0:
        return 0.0

    labels = sorted(set(y_true) | set(y_pred))
    po = sum(1 for a, b in zip(y_true, y_pred) if a == b) / n

    pe = 0.0
    for label in labels:
        p_true = sum(1 for v in y_true if v == label) / n
        p_pred = sum(1 for v in y_pred if v == label) / n
        pe += p_true * p_pred

    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


def evaluate_classifier(
    classifier_fn: Callable[[str], dict],
    labeled_path: Optional[Path] = None,
) -> KappaReport:
    """Run ``classifier_fn`` on every labeled item and return a KappaReport.

    ``classifier_fn`` mirrors ``classify_content`` — takes text, returns
    a dict with at least a ``topic`` key.
    """
    from datetime import datetime

    labeled_path = labeled_path or LABELED_FIXTURES_DEFAULT
    items = _load_labeled(labeled_path)

    y_true: List[str] = []
    y_pred: List[str] = []
    per_correct: dict = {}
    per_total: dict = {}

    for item in items:
        expected = item.get("expected_topic")
        text = " ".join(filter(None, [item.get("title"), item.get("content")]))
        if not expected or not text:
            continue
        predicted = (classifier_fn(text) or {}).get("topic", "culture")
        y_true.append(expected)
        y_pred.append(predicted)
        per_total[expected] = per_total.get(expected, 0) + 1
        if predicted == expected:
            per_correct[expected] = per_correct.get(expected, 0) + 1

    n = len(y_true)
    accuracy = sum(1 for a, b in zip(y_true, y_pred) if a == b) / n if n else 0.0
    kappa = cohen_kappa(y_true, y_pred) if n else 0.0

    return KappaReport(
        kappa=kappa,
        accuracy=accuracy,
        n_items=n,
        per_topic_correct=per_correct,
        per_topic_total=per_total,
        computed_at=datetime.now().isoformat(timespec="seconds"),
    )


def save_report(report: KappaReport, path: Optional[Path] = None) -> Path:
    """Persist report to JSON for later dashboard reads."""
    path = path or METRICS_CACHE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def load_cached_report(path: Optional[Path] = None) -> Optional[KappaReport]:
    """Read a previously saved report; return None if missing/corrupt."""
    path = path or METRICS_CACHE_PATH
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return KappaReport.from_dict(json.load(f))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _load_labeled(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
