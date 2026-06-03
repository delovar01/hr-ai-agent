"""Daily HR summary report generation.

Turns the agent's accumulated state into a self-contained document the
analyst can hand to a manager or paste into a Telegram channel. Closes
the «пересмотреть выводимые данные / добавление отчёта» item from the
team chat after the previous defence.

Two formats:
  * Markdown (default) — universal, renders in GitHub, Telegram, any IDE.
  * PDF (optional) — for committee members who insist on paper.

The renderer is deliberately pure: it takes the dashboard data dict (the
same one ``HRAgent.get_dashboard_data`` already produces) and returns a
string (MD) or bytes (PDF). No filesystem, no Streamlit imports — that
keeps it trivially testable and lets the dashboard wrap it in
``st.download_button``.
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


def generate_daily_summary_pdf(
    dashboard_data: dict,
    hours_window: int = 24,
    now: Optional[datetime] = None,
) -> bytes:
    """Render the same daily summary as PDF bytes.

    Uses fpdf2 — a pure-Python library with no system dependencies (unlike
    weasyprint, which needs GTK/Cairo and would not survive Streamlit Cloud).
    Cyrillic is rendered through DejaVu Sans which ships with the OS in most
    environments; if it is not found we fall back to a Latin-only built-in
    font and the report becomes ASCII-only — acceptable for a fallback path.
    """
    from fpdf import FPDF  # local import — fpdf2 is optional at module level

    md = generate_daily_summary_markdown(dashboard_data, hours_window=hours_window, now=now)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # Try to register a Cyrillic-capable TrueType font. fpdf2 does not bundle
    # DejaVu; we look in common system locations and fall back gracefully.
    font_set = False
    candidate_paths = [
        r"C:\Windows\Fonts\DejaVuSans.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidate_paths:
        try:
            # fpdf2 ≥ 2.5 auto-detects unicode TTFs — no `uni=True` needed.
            pdf.add_font("Body", "", path)
            pdf.set_font("Body", size=10)
            font_set = True
            break
        except (RuntimeError, FileNotFoundError, OSError):
            continue
    if not font_set:
        pdf.set_font("Helvetica", size=10)

    # Render Markdown line-by-line. We don't parse full MD — committee
    # only needs readable structure, not perfect typesetting.
    for raw_line in md.splitlines():
        line = raw_line.rstrip()
        if not font_set:
            # Strip non-ASCII to avoid fpdf encoding errors on the fallback.
            line = line.encode("ascii", "ignore").decode("ascii")
        # Markdown table separators like |---|---| have no content value in
        # PDF — skip them entirely. Long lines without spaces (e.g. URLs)
        # break fpdf's word-wrap; we hard-truncate to a safe width.
        if line.startswith("|") and set(line.replace("|", "").replace(" ", "")) <= {"-", ":"}:
            continue
        line = _safe_pdf_line(line)
        if line.startswith("# "):
            _set_size(pdf, 16, bold=True, font_set=font_set)
            pdf.multi_cell(pdf.epw, 8, line[2:])
            _set_size(pdf, 10, bold=False, font_set=font_set)
        elif line.startswith("## "):
            pdf.ln(2)
            _set_size(pdf, 13, bold=True, font_set=font_set)
            pdf.multi_cell(pdf.epw, 7, line[3:])
            _set_size(pdf, 10, bold=False, font_set=font_set)
        elif line.startswith("### "):
            _set_size(pdf, 11, bold=True, font_set=font_set)
            pdf.multi_cell(pdf.epw, 6, line[4:])
            _set_size(pdf, 10, bold=False, font_set=font_set)
        elif line.startswith("---"):
            pdf.ln(2)
        elif line.startswith("- ") or line.startswith("* "):
            pdf.multi_cell(pdf.epw, 5, "  • " + line[2:])
        elif line == "":
            pdf.ln(2)
        else:
            pdf.multi_cell(pdf.epw, 5, line)

    out = pdf.output(dest="S")
    # fpdf2 returns bytearray; Streamlit's download_button wants bytes.
    return bytes(out)


def _safe_pdf_line(line: str, max_word_len: int = 60) -> str:
    """Break long unbroken tokens so fpdf2's word-wrap can handle them.

    fpdf2 raises "Not enough horizontal space to render a single character"
    when a single token (e.g. a long URL or a markdown table cell) is wider
    than the page width. We insert a zero-cost soft break (a space) every
    ``max_word_len`` characters within long tokens.
    """
    parts = []
    for token in line.split(" "):
        if len(token) <= max_word_len:
            parts.append(token)
            continue
        chunks = [token[i:i + max_word_len] for i in range(0, len(token), max_word_len)]
        parts.append(" ".join(chunks))
    return " ".join(parts)


def _set_size(pdf, size: int, bold: bool, font_set: bool) -> None:
    """Switch font size without losing the registered Cyrillic font.

    fpdf2's ``style="B"`` would need a separate Bold-weight TTF — registering
    one isn't worth the complexity here. Bold-ish emphasis comes from the
    larger font size used for headers, which is enough for a daily report.
    """
    if font_set:
        pdf.set_font("Body", size=size)
    else:
        style = "B" if bold else ""
        pdf.set_font("Helvetica", style=style, size=size)


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
