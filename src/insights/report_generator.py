"""Daily HR summary report generation.

Turns the agent's accumulated state into a self-contained Markdown document
the analyst can hand to a manager or paste into a Telegram channel. Closes
the «пересмотреть выводимые данные / добавление отчёта» item from the team
chat after the previous defence.

The renderer is deliberately pure: it takes the dashboard data dict (the
same one ``HRAgent.get_dashboard_data`` already produces) and returns a
string. No filesystem, no Streamlit imports — that keeps it trivially
testable and lets the dashboard wrap it in ``st.download_button``.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from config.settings import HR_TOPICS, USER_ROLES


# Risk level → human-readable Russian label used in the report header bar.
RISK_LABELS_RU = {
    "critical": "Критический",
    "high": "Высокий",
    "medium": "Средний",
    "low": "Низкий",
}

URGENCY_LABELS_RU = {
    "immediate": "немедленно",
    "week": "в течение недели",
    "month": "в течение месяца",
}


def generate_daily_summary_markdown(
    dashboard_data: dict,
    hours_window: int = 24,
    now: Optional[datetime] = None,
) -> str:
    """Render a Markdown daily summary from the dashboard data dict.

    Sections (in committee-friendly order):
      1. Шапка с датой, ролью пользователя и временным окном.
      2. Критические алерты за последние ``hours_window`` часов.
      3. Топ-5 трендов по риск-направлению.
      4. Свежие инсайты с рекомендациями.
      5. Сводные метрики.
    """
    now = now or datetime.now()
    cutoff = now - timedelta(hours=hours_window)

    user_config = dashboard_data.get("user_config", {}) or {}
    role_id = user_config.get("role", "analyst")
    role_name = USER_ROLES.get(role_id, {}).get("name", role_id)

    alerts = _filter_recent(dashboard_data.get("alerts", []), "created_at", cutoff)
    insights = dashboard_data.get("insights", [])[:8]
    trends = dashboard_data.get("trends", {}) or {}
    metrics = dashboard_data.get("metrics", {}) or {}

    out: list = []
    out.append(f"# HR Daily Summary — {now.strftime('%d.%m.%Y %H:%M')}")
    out.append("")
    out.append(f"**Роль:** {role_name}  ")
    out.append(f"**Период:** последние {hours_window} ч  ")
    out.append(f"**Источник:** автогенерация HR AI Agent")
    out.append("")

    out.append("---")
    out.append("## 🚨 Критические события за период")
    if alerts:
        critical_first = sorted(
            alerts,
            key=lambda a: _risk_order(a.get("risk_level", "medium")),
        )
        for alert in critical_first[:10]:
            label = RISK_LABELS_RU.get(alert.get("risk_level", "medium"), "Средний")
            title = alert.get("title", "—")
            content = _short(alert.get("content", ""), 220)
            source = alert.get("source", "—")
            out.append(f"- **[{label}] {title}**")
            if content:
                out.append(f"  {content}")
            out.append(f"  _Источник: {source}_")
    else:
        out.append("_За указанный период критических событий не зафиксировано._")
    out.append("")

    out.append("---")
    out.append("## 📈 Топ-5 направлений по динамике риска")
    ranked_trends = _rank_trends(trends)[:5]
    if ranked_trends:
        out.append("| Тема | Направление | Изменение | Комментарий |")
        out.append("|------|-------------|-----------|-------------|")
        for topic_id, info in ranked_trends:
            label = HR_TOPICS.get(topic_id, topic_id)
            direction = {
                "up": "↑ Рост",
                "down": "↓ Снижение",
                "stable": "→ Стабильно",
            }.get(info.get("direction", "stable"), "—")
            change = info.get("change", 0)
            desc = _short(info.get("description", "—"), 80)
            out.append(f"| {label} | {direction} | {change:+.1f}% | {desc} |")
    else:
        out.append("_Недостаточно данных для расчёта трендов._")
    out.append("")

    out.append("---")
    out.append("## 💡 Свежие инсайты для команды")
    if insights:
        for idx, ins in enumerate(insights, 1):
            topic = ins.get("topic_name") or HR_TOPICS.get(ins.get("topic", ""), "HR")
            risk_lbl = RISK_LABELS_RU.get(ins.get("risk_level", "medium"), "Средний")
            urgency_lbl = URGENCY_LABELS_RU.get(ins.get("urgency", "week"), "в течение недели")
            out.append(f"### {idx}. {topic} · риск {risk_lbl} · реакция {urgency_lbl}")
            out.append(f"- **Что произошло:** {ins.get('what_changed', '—')}")
            out.append(f"- **Почему важно:** {ins.get('why_important', '—')}")
            out.append(f"- **Рекомендация:** {ins.get('recommendation', '—')}")
            if ins.get("source"):
                out.append(f"- _Источник: {ins['source']}_")
            out.append("")
    else:
        out.append("_Свежих инсайтов нет. Запустите цикл анализа для обновления._")
        out.append("")

    out.append("---")
    out.append("## 📊 Сводные метрики агента")
    out.append(f"- Циклов мониторинга: **{metrics.get('total_sources_checked', 0)}**")
    out.append(f"- Сгенерировано инсайтов: **{metrics.get('total_insights_generated', 0)}**")
    out.append(f"- Аномалий зафиксировано: **{metrics.get('anomalies_detected', 0)}**")
    out.append(f"- Дублей отфильтровано: **{metrics.get('content_duplicates_skipped', 0)}**")
    out.append("")
    out.append("---")
    out.append("_Отчёт сгенерирован автоматически модулем `report_generator.py`._")

    return "\n".join(out)


def _filter_recent(items: list, ts_key: str, cutoff: datetime) -> list:
    """Keep items whose ``ts_key`` ISO timestamp is past ``cutoff``.

    Items without a parseable timestamp are kept on the conservative side —
    the analyst will rather see one stale alert than miss a fresh one.
    """
    result = []
    for item in items:
        ts_raw = item.get(ts_key)
        if not ts_raw:
            result.append(item)
            continue
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", ""))
        except (ValueError, TypeError):
            result.append(item)
            continue
        if ts >= cutoff:
            result.append(item)
    return result


def _risk_order(level: str) -> int:
    """Sort key: critical first, low last."""
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(level, 4)


def _rank_trends(trends: dict) -> list:
    """Return (topic_id, info) sorted by absolute change desc."""
    pairs = []
    for topic_id, info in trends.items():
        try:
            change = abs(float(info.get("change", 0) or 0))
        except (ValueError, TypeError):
            change = 0
        pairs.append((change, topic_id, info))
    pairs.sort(key=lambda p: p[0], reverse=True)
    return [(tid, info) for _change, tid, info in pairs]


def _short(text: str, limit: int) -> str:
    if not text:
        return ""
    text = str(text).replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
