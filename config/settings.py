"""
Global settings and methodology constants for HR AI Agent.

All tunable thresholds that affect business behaviour live in this file (not
buried in code) so that the methodology owner can review and adjust them in
one place. Justification for each value is documented in docs/METHODOLOGY.md.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# GigaChat
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

# Agent
AGENT_CHECK_INTERVAL = int(os.getenv("AGENT_CHECK_INTERVAL_MINUTES", "15"))
# ANOMALY_THRESHOLD: relative deviation from rolling mean (in fractions) above
# which a topic value is reported as anomalous. 0.3 = 30%. Calibrated against
# weekly variance of HR news streams — values <0.2 produce noise, >0.5 misses
# real spikes. See docs/METHODOLOGY.md §4.
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.3"))

# ---- Rubricator (HR topics) -------------------------------------------------
# Семь тем покрывают весь жизненный цикл сотрудника: вход в компанию (hiring),
# материальная мотивация (salaries), развитие (skills), удержание/состояние
# (burnout, culture), уход (layoffs) и горизонтальный срез справедливости
# (diversity). Дробить дальше на MVP не имеет смысла:
#   - меньше 7 — теряем интерпретируемость для HR-аналитика;
#   - больше 7 — растёт класс «прочее», падает precision GigaChat-классификации.
# При выходе за MVP рассмотреть подкатегории: salaries → {compensation, benefits},
# culture → {leadership, communication, dei_culture}, layoffs → {layoffs, restructuring}.
RUBRICATOR_VERSION = "v1.0-mvp"

HR_TOPICS = {
    "hiring": "Найм и рекрутинг",
    "layoffs": "Сокращения и увольнения",
    "salaries": "Зарплаты и компенсации",
    "skills": "Навыки и обучение",
    "burnout": "Выгорание и вовлечённость",
    "culture": "Корпоративная культура",
    "diversity": "Разнообразие и инклюзия",
}

# ---- Risk scoring & alerts --------------------------------------------------
# Пороги генерации алертов в зависимости от чувствительности профиля
# пользователя. Калибровка:
#   high   = 0.30 — аналитик видит «всё что выглядит подозрительным», даёт
#                   высокий recall, низкий precision; подходит для разведки
#                   новой темы
#   medium = 0.50 — рабочий режим по умолчанию, баланс recall/precision
#   low    = 0.70 — режим топ-менеджера: только то, что почти наверняка
#                   значимо; высокий precision, низкий recall
# Значения совпадают с "пограничным" risk_score (см. RISK_LEVELS), что делает
# их интерпретируемыми: чувствительность high → ловим всё от среднего риска
# и выше; medium → от среднего; low → от высокого.
SENSITIVITY_THRESHOLDS = {
    "high": 0.30,
    "medium": 0.50,
    "low": 0.70,
}

# Если тема в фокусе пользователя — снижаем порог на эту дельту (т.е. для
# focus-темы быстрее срабатываем). Калибровано так, что medium-фокус ≈ high
# для остальных тем (0.50 - 0.15 = 0.35 ≈ 0.30).
FOCUS_TOPIC_DELTA = 0.15

# User roles
USER_ROLES = {
    "analyst": {
        "name": "HR-аналитик",
        "focus": ["salaries", "hiring", "layoffs"],
        "detail_level": "high"
    },
    "partner": {
        "name": "HR-партнёр",
        "focus": ["culture", "burnout", "skills"],
        "detail_level": "medium"
    },
    "manager": {
        "name": "HR-руководитель",
        "focus": ["layoffs", "hiring", "diversity"],
        "detail_level": "summary"
    }
}

# RSS Sources (derived from sources catalog)
# Full catalog with metadata and rationale lives in config/sources_catalog.py.
# RSS_SOURCES is kept as a thin compatibility shim — it contains only active sources
# in the legacy {"url", "name", "lang"} shape expected by older code paths.
from config.sources_catalog import load_sources as _load_sources

RSS_SOURCES = [
    {"url": s["url"], "name": s["name"], "lang": s["lang"]}
    for s in _load_sources(active_only=True)
]

# Risk levels
# Пороги уровней риска. Шаг 0.20 выбран так, чтобы каждый класс занимал
# равный диапазон [0.0, 0.4) low, [0.4, 0.6) medium, [0.6, 0.8) high,
# [0.8, 1.0] critical. Соответствует ожиданиям HR-аналитика: «средний»
# риск = ровно середина шкалы, «критический» = верхние 20%.
RISK_LEVELS = {
    "critical": {"threshold": 0.8, "color": "#FF4444", "label": "Критический"},
    "high": {"threshold": 0.6, "color": "#FF8C00", "label": "Высокий"},
    "medium": {"threshold": 0.4, "color": "#FFD700", "label": "Средний"},
    "low": {"threshold": 0.0, "color": "#32CD32", "label": "Низкий"},
}

# Time range options
TIME_RANGES = {
    "1h": {"hours": 1, "label": "Последний час"},
    "6h": {"hours": 6, "label": "Последние 6 часов"},
    "24h": {"hours": 24, "label": "Последние 24 часа"},
    "3d": {"days": 3, "label": "Последние 3 дня"},
    "7d": {"days": 7, "label": "Последняя неделя"},
    "30d": {"days": 30, "label": "Последний месяц"},
    "all": {"label": "Всё время"}
}
