"""Precompute Cohen's Kappa for the HR topic classifier and persist it.

Usage:
    python scripts/compute_kappa.py

Reads ``tests/fixtures/labeled_news.json``, runs ``classify_content`` on
each item via GigaChat (slow — 30+ seconds for 35 items), saves the
resulting KappaReport to ``data/quality_metrics.json``. The dashboard
reads that cache file — it does NOT recompute on load.

Re-run this manually after:
  * expanding the labeled fixtures,
  * tuning the classifier prompt,
  * upgrading GigaChat models.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.processing.classifier import classify_content
from src.processing.quality_metrics import (
    METRICS_CACHE_PATH,
    evaluate_classifier,
    save_report,
)


def main() -> int:
    print("Запуск GigaChat-классификатора по labeled_news.json...")
    report = evaluate_classifier(classify_content)
    save_report(report)
    print(f"  Cohen's Kappa: {report.kappa:.3f}")
    print(f"  Accuracy:      {report.accuracy:.1%}")
    print(f"  Items:         {report.n_items}")
    print(f"  Saved to:      {METRICS_CACHE_PATH}")
    print()
    print("Per-topic accuracy:")
    for topic, total in sorted(report.per_topic_total.items()):
        correct = report.per_topic_correct.get(topic, 0)
        print(f"  {topic:12s}  {correct}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
