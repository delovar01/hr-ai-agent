
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

# RSS Sources (real HR news feeds)
RSS_SOURCES = [
    # Существующие
    {"url": "https://hbr.org/feed", "name": "Harvard Business Review", "lang": "en"},
    {"url": "https://www.shrm.org/rss/pages/rss.aspx", "name": "SHRM News", "lang": "en"},

    # новые источники
    {"url": "https://vc.ru/feed", "name": "VC.ru", "lang": "ru"},
    {"url": "https://habr.com/ru/rss/all/", "name": "Habr", "lang": "ru"},
    {"url": "https://www.themuse.com/rss", "name": "The Muse", "lang": "en"},
    # Быстрые обновления
    {"url": "https://news.ycombinator.com/rss", "name": "Hacker News", "lang": "en"},
    {"url": "https://www.reddit.com/r/cscareerquestions/.rss", "name": "Reddit CS Careers", "lang": "en"},
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
