"""
Source catalog for HR AI Agent.

Curated list of candidate RSS/Atom sources with metadata.
Team owner (content curation): Беспамятных Евгений.

Fields per source:
    id                — stable unique identifier (snake_case)
    url               — RSS/Atom feed URL
    name              — display name
    lang              — "ru" | "en"
    region            — "RU" | "Global" | "EN"
    category          — news | community | research | corporate | job_board | analytical
    topics_covered    — list of HR topic keys from HR_TOPICS (subset of 7)
    update_frequency  — "hourly" | "daily" | "weekly"
    audience_size     — "large" | "medium" | "niche"
    quality_score     — float 0.0-1.0 (expert assessment)
    is_active         — whether source is in the active pool
    rationale         — 1-2 sentences, why this source is in the catalog
"""
from typing import List, Optional


CATEGORIES = {
    "news": "Новостные издания",
    "community": "Сообщества и форумы",
    "research": "Исследовательские публикации",
    "corporate": "Корпоративные блоги",
    "job_board": "Работные площадки",
    "analytical": "Аналитика и консалтинг",
}

UPDATE_FREQUENCIES = ("hourly", "daily", "weekly")
AUDIENCE_SIZES = ("large", "medium", "niche")
REGIONS = ("RU", "EN", "Global")


SOURCES_CATALOG: List[dict] = [
    # ========== EN · Research / Analytical ==========
    {
        "id": "hbr",
        "url": "https://hbr.org/feed",
        "name": "Harvard Business Review",
        "lang": "en",
        "region": "Global",
        "category": "research",
        "topics_covered": ["culture", "skills", "burnout", "diversity"],
        "update_frequency": "daily",
        "audience_size": "large",
        "quality_score": 0.95,
        "is_active": True,
        "rationale": "Мировой эталон управленческой аналитики. Глубокие материалы по лидерству, корпоративной культуре и HR-трендам от исследователей Гарварда.",
    },
    {
        "id": "shrm",
        "url": "https://www.shrm.org/rss/pages/rss.aspx",
        "name": "SHRM News",
        "lang": "en",
        "region": "EN",
        "category": "research",
        "topics_covered": ["hiring", "layoffs", "salaries", "culture", "diversity"],
        "update_frequency": "daily",
        "audience_size": "large",
        "quality_score": 0.9,
        "is_active": True,
        "rationale": "Крупнейшая HR-ассоциация мира (300k+ членов). Первоисточник по регуляторике труда США и best practices.",
    },
    # ========== EN · Community ==========
    {
        "id": "the_muse",
        "url": "https://www.themuse.com/rss",
        "name": "The Muse",
        "lang": "en",
        "region": "EN",
        "category": "community",
        "topics_covered": ["hiring", "skills", "culture"],
        "update_frequency": "daily",
        "audience_size": "medium",
        "quality_score": 0.7,
        "is_active": True,
        "rationale": "Сигналы со стороны соискателей: как кандидаты смотрят на рынок, какие навыки и компании востребованы.",
    },
    {
        "id": "hacker_news",
        "url": "https://news.ycombinator.com/rss",
        "name": "Hacker News",
        "lang": "en",
        "region": "Global",
        "category": "community",
        "topics_covered": ["hiring", "layoffs", "salaries", "skills"],
        "update_frequency": "hourly",
        "audience_size": "large",
        "quality_score": 0.75,
        "is_active": True,
        "rationale": "Ранний индикатор технологических и рыночных сдвигов. Обсуждения сокращений в Big Tech и рынка IT-труда появляются здесь за часы до мейнстрим-СМИ.",
    },
    {
        "id": "reddit_cscareers",
        "url": "https://www.reddit.com/r/cscareerquestions/.rss",
        "name": "Reddit /r/cscareerquestions",
        "lang": "en",
        "region": "Global",
        "category": "community",
        "topics_covered": ["hiring", "salaries", "skills", "burnout"],
        "update_frequency": "hourly",
        "audience_size": "large",
        "quality_score": 0.65,
        "is_active": True,
        "rationale": "Голос кандидатов в IT: реальные уровни зарплат, отзывы о процессах найма, сигналы о выгорании.",
    },
    # ========== RU · News ==========
    {
        "id": "vc_ru",
        "url": "https://vc.ru/feed",
        "name": "VC.ru",
        "lang": "ru",
        "region": "RU",
        "category": "news",
        "topics_covered": ["hiring", "layoffs", "salaries", "culture"],
        "update_frequency": "hourly",
        "audience_size": "large",
        "quality_score": 0.75,
        "is_active": True,
        "rationale": "Главное русскоязычное бизнес-издание о российском IT и стартапах. Оперативные новости о найме, сокращениях и корпоративной культуре.",
    },
    {
        "id": "habr",
        "url": "https://habr.com/ru/rss/all/",
        "name": "Habr",
        "lang": "ru",
        "region": "RU",
        "category": "community",
        "topics_covered": ["hiring", "skills", "salaries", "burnout"],
        "update_frequency": "hourly",
        "audience_size": "large",
        "quality_score": 0.8,
        "is_active": True,
        "rationale": "Крупнейшее русскоязычное IT-сообщество. Первоисточник по настроениям, зарплатным обзорам и техническим навыкам.",
    },
    # ========== Кандидаты на расширение (TODO: Беспамятных Евгений) ==========
    # Ниже перечислены потенциальные источники. Финальное решение о включении
    # принимается после ручной проверки наличия RSS и качества контента.
    {
        "id": "hh_ru_blog",
        "url": "https://hh.ru/rss/articles",
        "name": "HH.ru Блог",
        "lang": "ru",
        "region": "RU",
        "category": "job_board",
        "topics_covered": ["hiring", "salaries", "skills"],
        "update_frequency": "weekly",
        "audience_size": "large",
        "quality_score": 0.8,
        "is_active": False,
        "rationale": "Крупнейшая работная площадка РФ. Собственные зарплатные обзоры и исследования рынка труда. TODO: проверить RSS.",
    },
    {
        "id": "rbc_pro",
        "url": "https://pro.rbc.ru/rss",
        "name": "RBC Pro",
        "lang": "ru",
        "region": "RU",
        "category": "analytical",
        "topics_covered": ["hiring", "layoffs", "culture", "skills"],
        "update_frequency": "daily",
        "audience_size": "large",
        "quality_score": 0.85,
        "is_active": False,
        "rationale": "Деловая аналитика РБК с фокусом на менеджмент и HR. TODO: уточнить валидный RSS URL.",
    },
    {
        "id": "vedomosti_career",
        "url": "https://www.vedomosti.ru/rss/rubric/career",
        "name": "Ведомости / Карьера",
        "lang": "ru",
        "region": "RU",
        "category": "news",
        "topics_covered": ["hiring", "salaries", "culture"],
        "update_frequency": "daily",
        "audience_size": "large",
        "quality_score": 0.85,
        "is_active": False,
        "rationale": "Деловое СМИ с регулярной рубрикой о карьере и рынке труда. TODO: проверить RSS.",
    },
    {
        "id": "kommersant_society",
        "url": "https://www.kommersant.ru/RSS/section-society.xml",
        "name": "Коммерсант / Общество",
        "lang": "ru",
        "region": "RU",
        "category": "news",
        "topics_covered": ["layoffs", "salaries", "diversity"],
        "update_frequency": "hourly",
        "audience_size": "large",
        "quality_score": 0.8,
        "is_active": False,
        "rationale": "Оперативное освещение социально-трудовых тем. TODO: фильтрация только релевантных HR-тем.",
    },
    {
        "id": "forbes_ru_career",
        "url": "https://www.forbes.ru/karera/rss",
        "name": "Forbes Russia / Карьера",
        "lang": "ru",
        "region": "RU",
        "category": "analytical",
        "topics_covered": ["salaries", "culture", "hiring"],
        "update_frequency": "daily",
        "audience_size": "medium",
        "quality_score": 0.75,
        "is_active": False,
        "rationale": "Качественные лонгриды о карьере и лидерстве в российском корпоративном секторе. TODO: проверить RSS.",
    },
    {
        "id": "hr_portal_ru",
        "url": "https://hr-portal.ru/rss.xml",
        "name": "HR-Portal.ru",
        "lang": "ru",
        "region": "RU",
        "category": "community",
        "topics_covered": ["hiring", "skills", "culture", "burnout", "diversity"],
        "update_frequency": "daily",
        "audience_size": "medium",
        "quality_score": 0.6,
        "is_active": False,
        "rationale": "Профильный русскоязычный HR-портал. Низкий quality_score из-за смеси пресс-релизов. TODO: валидация.",
    },
    {
        "id": "mckinsey_organization",
        "url": "https://www.mckinsey.com/capabilities/people-and-organizational-performance/our-insights/rss",
        "name": "McKinsey Organization",
        "lang": "en",
        "region": "Global",
        "category": "analytical",
        "topics_covered": ["culture", "skills", "diversity", "layoffs"],
        "update_frequency": "weekly",
        "audience_size": "large",
        "quality_score": 0.95,
        "is_active": False,
        "rationale": "Консалтинговая аналитика уровня Tier-1. Исследования о трансформации организаций и HR-стратегии. TODO: проверить RSS.",
    },
    {
        "id": "deloitte_hc",
        "url": "https://www2.deloitte.com/us/en/insights/focus/human-capital-trends.rss",
        "name": "Deloitte Human Capital",
        "lang": "en",
        "region": "Global",
        "category": "analytical",
        "topics_covered": ["hiring", "culture", "skills", "diversity"],
        "update_frequency": "weekly",
        "audience_size": "large",
        "quality_score": 0.9,
        "is_active": False,
        "rationale": "Ежегодный Global Human Capital Trends — референс для HR-стратегов. TODO: проверить RSS.",
    },
]


def load_sources(active_only: bool = True) -> List[dict]:
    """Load sources from catalog.

    Args:
        active_only: If True, return only sources with is_active=True.
    """
    if active_only:
        return [s for s in SOURCES_CATALOG if s.get("is_active")]
    return list(SOURCES_CATALOG)


def get_source(source_id: str) -> Optional[dict]:
    """Get single source by id."""
    for s in SOURCES_CATALOG:
        if s["id"] == source_id:
            return s
    return None


def set_active(source_id: str, active: bool) -> bool:
    """Toggle is_active flag for source. Returns True if source was found."""
    for s in SOURCES_CATALOG:
        if s["id"] == source_id:
            s["is_active"] = active
            return True
    return False


def validate_source(source: dict) -> List[str]:
    """Validate source dict. Returns list of error messages (empty if valid)."""
    errors = []
    required = ["id", "url", "name", "lang", "category", "topics_covered"]
    for field in required:
        if field not in source:
            errors.append(f"Missing required field: {field}")

    if source.get("lang") not in ("ru", "en"):
        errors.append(f"Invalid lang: {source.get('lang')} (expected 'ru' or 'en')")

    if source.get("category") not in CATEGORIES:
        errors.append(f"Invalid category: {source.get('category')}")

    if source.get("region") and source["region"] not in REGIONS:
        errors.append(f"Invalid region: {source.get('region')}")

    if source.get("update_frequency") and source["update_frequency"] not in UPDATE_FREQUENCIES:
        errors.append(f"Invalid update_frequency: {source.get('update_frequency')}")

    if source.get("audience_size") and source["audience_size"] not in AUDIENCE_SIZES:
        errors.append(f"Invalid audience_size: {source.get('audience_size')}")

    quality = source.get("quality_score")
    if quality is not None and not (0.0 <= quality <= 1.0):
        errors.append(f"quality_score must be in [0.0, 1.0], got {quality}")

    return errors
