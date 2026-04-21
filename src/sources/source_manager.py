"""
Rule-based source pool manager.

Reviews per-source metrics and produces RECOMMENDATIONS to enable/disable
sources in the active pool. By default the manager is "dry-run": it proposes
actions but does not apply them. The team can decide via dashboard whether to
apply or override each recommendation.

This is not ML — just transparent rules that justify the decision in words.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from config.sources_catalog import SOURCES_CATALOG, set_active
from src.sources.source_analytics import build_source_report


# ---- Tunable thresholds (exposed so the team can adjust from one place) ----

# Consider deactivating sources whose dedup rate stays above this level.
DUPLICATE_RATE_WARN = 0.7

# Require this many cycles of sustained high duplicate rate before acting.
MIN_CYCLES_FOR_DUPLICATE_ACTION = 3

# Deactivate if a source fails to produce any new item for this many cycles.
STALE_CYCLES_THRESHOLD = 5

# Flag as valuable: high unique contribution + any insights.
VALUABLE_MIN_UNIQUE = 20
VALUABLE_MIN_INSIGHTS = 3

# Minimum events a source must have before it can be judged.
MIN_EVENTS_FOR_EVALUATION = 5


ACTION_DEACTIVATE = "deactivate"
ACTION_ACTIVATE_VALUABLE = "activate_valuable"
ACTION_KEEP = "keep"
ACTION_INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class SourceRecommendation:
    """One recommendation row for the source manager journal."""

    source_id: str
    source_name: str
    action: str
    reason: str
    currently_active: bool
    metrics_snapshot: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "action": self.action,
            "reason": self.reason,
            "currently_active": self.currently_active,
            "metrics": self.metrics_snapshot,
            "created_at": self.created_at,
        }


class SourceManager:
    """Produces recommendations about which sources to keep, drop or promote."""

    def __init__(
        self,
        duplicate_rate_warn: float = DUPLICATE_RATE_WARN,
        stale_cycles_threshold: int = STALE_CYCLES_THRESHOLD,
        min_cycles_for_duplicate_action: int = MIN_CYCLES_FOR_DUPLICATE_ACTION,
    ):
        self.duplicate_rate_warn = duplicate_rate_warn
        self.stale_cycles_threshold = stale_cycles_threshold
        self.min_cycles_for_duplicate_action = min_cycles_for_duplicate_action

    def evaluate(self) -> List[SourceRecommendation]:
        """Produce one recommendation per source in the catalog."""
        report = build_source_report()
        recommendations: List[SourceRecommendation] = []

        for row in report:
            rec = self._evaluate_row(row)
            recommendations.append(rec)

        return recommendations

    def _evaluate_row(self, row: dict) -> SourceRecommendation:
        sid = row["id"]
        name = row.get("name") or sid
        is_active = row.get("is_active", False)

        fetched = row.get("items_fetched", 0)
        accepted = row.get("items_accepted", 0)
        duplicates = row.get("duplicates", 0)
        duplicate_rate = row.get("duplicate_rate", 0.0)
        insights = row.get("insights_generated", 0)
        cycles_without_new = row.get("cycles_without_new", 0)
        cycles_seen = row.get("cycles_seen", 0)

        snapshot = {
            "items_fetched": fetched,
            "items_accepted": accepted,
            "duplicates": duplicates,
            "duplicate_rate": round(duplicate_rate, 3),
            "insights_generated": insights,
            "cycles_without_new": cycles_without_new,
            "cycles_seen": cycles_seen,
        }

        # Cannot judge sources we have almost no data on.
        if fetched < MIN_EVENTS_FOR_EVALUATION:
            return SourceRecommendation(
                source_id=sid,
                source_name=name,
                action=ACTION_INSUFFICIENT_DATA,
                reason=(
                    f"Недостаточно данных: собрано всего {fetched} элементов "
                    f"(минимум {MIN_EVENTS_FOR_EVALUATION} для оценки)."
                ),
                currently_active=is_active,
                metrics_snapshot=snapshot,
            )

        # 1. High duplicate rate over several cycles → deactivate.
        if (
            is_active
            and duplicate_rate >= self.duplicate_rate_warn
            and cycles_seen >= self.min_cycles_for_duplicate_action
        ):
            return SourceRecommendation(
                source_id=sid,
                source_name=name,
                action=ACTION_DEACTIVATE,
                reason=(
                    f"Высокий уровень дублирования: {duplicate_rate:.0%} элементов — "
                    f"дубли уже учтённых новостей. Наблюдалось на протяжении "
                    f"{cycles_seen} циклов."
                ),
                currently_active=is_active,
                metrics_snapshot=snapshot,
            )

        # 2. Source produces nothing new for many cycles → deactivate.
        if is_active and cycles_without_new >= self.stale_cycles_threshold:
            return SourceRecommendation(
                source_id=sid,
                source_name=name,
                action=ACTION_DEACTIVATE,
                reason=(
                    f"Источник не приносит новых материалов уже "
                    f"{cycles_without_new} циклов подряд."
                ),
                currently_active=is_active,
                metrics_snapshot=snapshot,
            )

        # 3. Inactive but valuable by evidence → propose activating.
        if (
            not is_active
            and accepted >= VALUABLE_MIN_UNIQUE
            and insights >= VALUABLE_MIN_INSIGHTS
        ):
            return SourceRecommendation(
                source_id=sid,
                source_name=name,
                action=ACTION_ACTIVATE_VALUABLE,
                reason=(
                    f"Источник принёс {accepted} уникальных материалов и "
                    f"{insights} инсайтов, хотя помечен неактивным. Рекомендуется "
                    f"вернуть в активный пул."
                ),
                currently_active=is_active,
                metrics_snapshot=snapshot,
            )

        # 4. Default — keep as is, but explain why.
        verdict_bits = []
        if duplicate_rate < self.duplicate_rate_warn:
            verdict_bits.append(f"уровень дублей {duplicate_rate:.0%} в норме")
        if cycles_without_new < self.stale_cycles_threshold:
            verdict_bits.append("источник активно поставляет материал")
        if insights:
            verdict_bits.append(f"сгенерировано инсайтов: {insights}")
        reason = "Состояние в норме: " + ", ".join(verdict_bits) if verdict_bits else "Состояние в норме."

        return SourceRecommendation(
            source_id=sid,
            source_name=name,
            action=ACTION_KEEP,
            reason=reason,
            currently_active=is_active,
            metrics_snapshot=snapshot,
        )

    def apply(self, recommendation: SourceRecommendation) -> bool:
        """Apply a single recommendation to the catalog. Returns True on change."""
        if recommendation.action == ACTION_DEACTIVATE and recommendation.currently_active:
            return set_active(recommendation.source_id, False)
        if recommendation.action == ACTION_ACTIVATE_VALUABLE and not recommendation.currently_active:
            return set_active(recommendation.source_id, True)
        return False


def evaluate_sources() -> List[dict]:
    """Convenience wrapper returning serialisable recommendations."""
    manager = SourceManager()
    return [r.to_dict() for r in manager.evaluate()]
