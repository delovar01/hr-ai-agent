
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
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.3"))

# HR Topics
HR_TOPICS = {
    "hiring": "Найм и рекрутинг",
    "layoffs": "Сокращения и увольнения",
    "salaries": "Зарплаты и компенсации",
    "skills": "Навыки и обучение",
    "burnout": "Выгорание и вовлечённость",
    "culture": "Корпоративная культура",
    "diversity": "Разнообразие и инклюзия"
}

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
RISK_LEVELS = {
    "critical": {"threshold": 0.8, "color": "#FF4444", "label": "Критический"},
    "high": {"threshold": 0.6, "color": "#FF8C00", "label": "Высокий"},
    "medium": {"threshold": 0.4, "color": "#FFD700", "label": "Средний"},
    "low": {"threshold": 0.0, "color": "#32CD32", "label": "Низкий"}
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
