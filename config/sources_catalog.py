"""
config/sources_catalog.py
--------------------------
Курируемый каталог RSS-источников для HR-агрегатора.

Контентную кураторскую работу (отбор, классификация, quality-score) выполнил
Беспамятных Евгений. Методологические поля (topics_covered, region, rationale)
добавлены для обоснования пула источников в отчётах защиты MVP.

Критерии отбора (Беспамятных Е.):
  - Авторитет:        признанные издания / организации в HR, бизнес, tech сфере
  - Обновляемость:    активный RSS-фид, публикации не реже 2-3 раз в неделю
  - HR-релевантность: контент пересекается хотя бы с одной темой из HR_TOPICS
  - Язык:             ru или en (смешанные не добавляются)
  - RSS:              фид должен быть публично доступен без авторизации

Статус is_active=False означает кандидата для A/B-тестирования —
источник не тянется агентом, пока не переведён в активный.

Архитектура модуля:
  - ``Source``            — dataclass с полным описанием источника
  - ``SOURCES``           — типизированный список Source (канонический)
  - ``SOURCES_CATALOG``   — production view в виде list[dict], синхронизируется
                            автоматически через ``_rebuild_catalog_view()``.
                            Используется analytics / source_manager / тестами.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Literal, Optional


Category = Literal["hr_official", "media", "community", "tech", "biz"]
Lang = Literal["ru", "en"]


CATEGORIES = {
    "hr_official": "Профессиональные HR-ассоциации",
    "media": "Бизнес- и HR-медиа",
    "community": "Сообщества и форумы",
    "tech": "Tech- и AI-медиа",
    "biz": "Бизнес-аналитика",
}

REGIONS = ("RU", "EN", "Global")


@dataclass
class Source:
    source_id: str                               # slug kebab-case, уникальный
    name: str                                    # читаемое название
    url: str                                     # URL RSS-фида
    lang: Lang                                   # язык контента
    category: Category                           # тематическая категория
    is_active: bool                              # участвует ли в парсинге
    quality_score: float                         # оценка качества 0.0-1.0
    added_date: str                              # ISO 8601 (YYYY-MM-DD)
    description: str = ""                        # краткое описание источника
    topics_covered: List[str] = field(default_factory=list)  # ключи из HR_TOPICS
    region: str = "Global"                       # RU | EN | Global
    rationale: str = ""                          # зачем источник в каталоге

    def to_dict(self) -> dict:
        """Legacy dict shape used by analytics, source_manager, tests.

        Maps ``source_id`` -> ``id`` and fills ``rationale`` from
        ``description`` when not set explicitly.
        """
        d = asdict(self)
        d["id"] = d.pop("source_id")
        if not d["rationale"]:
            d["rationale"] = d["description"]
        return d


SOURCES: List[Source] = [

    # ── hr_official ───────────────────────────────────────────────────────────

    Source(
        source_id="shrm-news",
        name="SHRM News",
        url="https://www.shrm.org/rss/pages/rss.aspx",
        lang="en",
        category="hr_official",
        is_active=True,
        quality_score=0.90,
        added_date="2024-01-01",
        description="Официальный фид Society for Human Resource Management.",
        topics_covered=["hiring", "layoffs", "salaries", "culture", "diversity"],
        region="EN",
        rationale="Крупнейшая HR-ассоциация мира (300k+ членов). Первоисточник по регуляторике труда США и best practices.",
    ),
    Source(
        source_id="atd-org",
        name="ATD (Association for Talent Development)",
        url="https://www.td.org/rss",
        lang="en",
        category="hr_official",
        is_active=True,
        quality_score=0.85,
        added_date="2025-01-15",
        description="Лидирующая ассоциация по развитию талантов и L&D.",
        topics_covered=["skills", "culture"],
        region="EN",
        rationale="Профессиональный стандарт в L&D. Даёт оперативную картину по корпоративному обучению и карьерному развитию.",
    ),
    Source(
        source_id="worldatwork",
        name="WorldatWork",
        url="https://worldatwork.org/feed",
        lang="en",
        category="hr_official",
        is_active=False,  # A/B кандидат
        quality_score=0.80,
        added_date="2025-04-22",
        description="Ассоциация специалистов по компенсациям и льготам (Total Rewards).",
        topics_covered=["salaries"],
        region="EN",
        rationale="Узкоспециализированный источник по зарплатной политике и бенефитам — нужен для темы salaries.",
    ),
    Source(
        source_id="hr-com",
        name="HR.com",
        url="https://www.hr.com/en/rss_feeds/",
        lang="en",
        category="hr_official",
        is_active=False,  # A/B кандидат
        quality_score=0.75,
        added_date="2025-04-22",
        description="Комьюнити и новости для HR-профессионалов.",
        topics_covered=["hiring", "salaries", "skills", "culture", "diversity"],
        region="EN",
        rationale="Широкое покрытие HR-тем, но смешанное качество (есть пресс-релизы) — поэтому кандидат, не активный.",
    ),

    # ── media EN ──────────────────────────────────────────────────────────────

    Source(
        source_id="hbr",
        name="Harvard Business Review",
        url="https://hbr.org/feed",
        lang="en",
        category="media",
        is_active=True,
        quality_score=0.90,
        added_date="2024-01-01",
        description="Академически строгие статьи по менеджменту, лидерству и HR.",
        topics_covered=["culture", "skills", "burnout", "diversity", "hiring"],
        region="Global",
        rationale="Мировой эталон управленческой аналитики. Глубокие материалы по лидерству и HR-трендам от исследователей Гарварда.",
    ),
    Source(
        source_id="fast-company-work",
        name="Fast Company — Work Life",
        url="https://www.fastcompany.com/work-life/rss",
        lang="en",
        category="media",
        is_active=True,
        quality_score=0.80,
        added_date="2025-01-15",
        description="Трудовая культура, карьера, будущее работы.",
        topics_covered=["culture", "burnout", "skills", "hiring"],
        region="EN",
        rationale="Оперативный материал о трендах в workplace culture и будущем работы — догоняет HBR по скорости.",
    ),
    Source(
        source_id="forbes-work",
        name="Forbes — Leadership",
        url="https://www.forbes.com/leadership/feed/",
        lang="en",
        category="media",
        is_active=True,
        quality_score=0.78,
        added_date="2025-01-15",
        description="HR-аналитика и истории с уклоном в бизнес-результат.",
        topics_covered=["hiring", "layoffs", "culture", "diversity"],
        region="EN",
        rationale="Связка HR-решений с бизнес-метриками — важно для коммуникации с топ-менеджментом.",
    ),
    Source(
        source_id="fortune-at-work",
        name="Fortune — At Work",
        url="https://fortune.com/section/at-work/feed/",
        lang="en",
        category="media",
        is_active=True,
        quality_score=0.80,
        added_date="2025-01-15",
        description="Найм, увольнения, тренды рынка труда от Fortune.",
        topics_covered=["hiring", "layoffs", "salaries", "culture"],
        region="EN",
        rationale="Один из быстрейших источников по массовым увольнениям в Fortune 500 — критично для темы layoffs.",
    ),
    Source(
        source_id="the-muse",
        name="The Muse",
        url="https://www.themuse.com/rss",
        lang="en",
        category="media",
        is_active=True,
        quality_score=0.70,
        added_date="2024-01-01",
        description="Карьерные советы и истории для соискателей и рекрутеров.",
        topics_covered=["hiring", "skills", "culture"],
        region="EN",
        rationale="Сигналы со стороны соискателей: как кандидаты видят рынок, какие навыки востребованы.",
    ),

    # ── media RU ──────────────────────────────────────────────────────────────

    Source(
        source_id="vc-ru",
        name="VC.ru",
        url="https://vc.ru/feed",
        lang="ru",
        category="media",
        is_active=True,
        quality_score=0.75,
        added_date="2024-01-01",
        description="Бизнес и технологии, регулярные материалы о рынке труда в IT.",
        topics_covered=["hiring", "layoffs", "salaries", "culture"],
        region="RU",
        rationale="Главное русскоязычное бизнес-издание о российском IT и стартапах. Оперативные новости о найме и сокращениях.",
    ),
    Source(
        source_id="rbc-hr",
        name="РБК — Карьера",
        url="https://rbc.ru/v10/ajax/get-rss-news/person/",
        lang="ru",
        category="media",
        is_active=True,
        quality_score=0.82,
        added_date="2025-01-15",
        description="Новости рынка труда, зарплатные исследования, увольнения.",
        topics_covered=["hiring", "layoffs", "salaries"],
        region="RU",
        rationale="Деловое СМИ верхнего эшелона в РФ, регулярные зарплатные обзоры.",
    ),
    Source(
        source_id="vedomosti-hr",
        name="Ведомости — Менеджмент",
        url="https://www.vedomosti.ru/rss/rubric/management",
        lang="ru",
        category="media",
        is_active=True,
        quality_score=0.83,
        added_date="2025-01-15",
        description="Деловые новости с фокусом на управление персоналом.",
        topics_covered=["hiring", "layoffs", "culture"],
        region="RU",
        rationale="Рубрика «Менеджмент» Ведомостей — высокое качество и фокус на решения для топ-HR.",
    ),
    Source(
        source_id="kommersant-hr",
        name="Коммерсантъ — Управление",
        url="https://www.kommersant.ru/RSS/section-management.xml",
        lang="ru",
        category="media",
        is_active=False,  # A/B кандидат
        quality_score=0.80,
        added_date="2025-04-22",
        description="HR-материалы из раздела «Менеджмент» Коммерсанта.",
        topics_covered=["layoffs", "salaries", "diversity"],
        region="RU",
        rationale="Пересечение с Ведомостями есть — пускаем как A/B кандидата, замеряем duplicate_rate.",
    ),
    Source(
        source_id="hr-tv-ru",
        name="HR-tv.ru",
        url="https://hr-tv.ru/rss.xml",
        lang="ru",
        category="media",
        is_active=False,  # A/B кандидат
        quality_score=0.72,
        added_date="2025-04-22",
        description="Российское HR-медиа: интервью, кейсы, аналитика.",
        topics_covered=["culture", "skills", "hiring"],
        region="RU",
        rationale="Нишевое HR-медиа — кандидат на проверку уникальности контента.",
    ),

    # ── community ─────────────────────────────────────────────────────────────

    Source(
        source_id="habr",
        name="Habr",
        url="https://habr.com/ru/rss/all/",
        lang="ru",
        category="community",
        is_active=True,
        quality_score=0.75,
        added_date="2024-01-01",
        description="IT-сообщество: карьера в технологиях, управление командами.",
        topics_covered=["hiring", "skills", "salaries", "burnout"],
        region="RU",
        rationale="Крупнейшее русскоязычное IT-сообщество. Первоисточник по настроениям и зарплатам в IT.",
    ),
    Source(
        source_id="hacker-news",
        name="Hacker News",
        url="https://news.ycombinator.com/rss",
        lang="en",
        category="community",
        is_active=True,
        quality_score=0.72,
        added_date="2024-01-01",
        description="Технологическое сообщество: стартапы, найм, рынок труда в tech.",
        topics_covered=["hiring", "layoffs", "salaries", "skills"],
        region="Global",
        rationale="Ранний индикатор сдвигов в Big Tech — обсуждения появляются здесь за часы до мейнстрим-СМИ.",
    ),
    Source(
        source_id="reddit-humanresources",
        name="Reddit r/humanresources",
        url="https://www.reddit.com/r/humanresources/.rss",
        lang="en",
        category="community",
        is_active=True,
        quality_score=0.70,
        added_date="2025-01-15",
        description="Обсуждения практикующих HR-специалистов со всего мира.",
        topics_covered=["hiring", "salaries", "culture", "burnout", "diversity"],
        region="EN",
        rationale="Голос практиков HR — живые кейсы и реальные проблемы, которые редко попадают в медиа.",
    ),
    Source(
        source_id="reddit-cs-careers",
        name="Reddit r/cscareerquestions",
        url="https://www.reddit.com/r/cscareerquestions/.rss",
        lang="en",
        category="community",
        is_active=False,  # A/B кандидат — tech-уклон, слабо релевантен HR
        quality_score=0.65,
        added_date="2024-01-01",
        description="Карьерные вопросы в IT — полезно для рекрутинга разработчиков.",
        topics_covered=["hiring", "salaries", "skills", "burnout"],
        region="Global",
        rationale="Узкий сегмент (IT-кандидаты) — держим как кандидата, активируем если усилится фокус на IT-найм.",
    ),
    Source(
        source_id="medium-hr",
        name="Medium — Human Resources",
        url="https://medium.com/feed/tag/human-resources",
        lang="en",
        category="community",
        is_active=True,
        quality_score=0.68,
        added_date="2025-01-15",
        description="Авторские колонки практиков по HR, культуре и лидерству.",
        topics_covered=["hiring", "culture", "skills", "diversity"],
        region="Global",
        rationale="Дополняет формальные медиа авторскими кейсами и субъективным опытом.",
    ),
    Source(
        source_id="hr-ru",
        name="HR.ru",
        url="https://hr.ru/rss/news.xml",
        lang="ru",
        category="community",
        is_active=True,
        quality_score=0.72,
        added_date="2025-04-22",
        description="Российское HR-комьюнити: вакансии, новости, кейсы.",
        topics_covered=["hiring", "skills", "culture", "burnout", "diversity"],
        region="RU",
        rationale="Русскоязычное HR-коммьюнити — локальные кейсы, которых нет в западных источниках.",
    ),

    # ── tech ──────────────────────────────────────────────────────────────────

    Source(
        source_id="techcrunch-hr",
        name="TechCrunch — HR",
        url="https://techcrunch.com/tag/hr/feed/",
        lang="en",
        category="tech",
        is_active=True,
        quality_score=0.78,
        added_date="2025-01-15",
        description="HR-tech стартапы, инструменты рекрутинга, автоматизация.",
        topics_covered=["hiring", "skills"],
        region="EN",
        rationale="Закрывает тему HR-tech инструментов — ATS, онбординг-софт, AI-рекрутинг.",
    ),
    Source(
        source_id="wired-work",
        name="Wired — Work",
        url="https://www.wired.com/feed/tag/work/rss",
        lang="en",
        category="tech",
        is_active=True,
        quality_score=0.80,
        added_date="2025-04-22",
        description="Влияние технологий на труд, удалёнка, AI на рабочем месте.",
        topics_covered=["burnout", "culture", "skills"],
        region="EN",
        rationale="Критично для тем remote work, work-life balance, AI-замещение навыков.",
    ),
    Source(
        source_id="venturebeat-ai",
        name="VentureBeat — AI",
        url="https://venturebeat.com/category/ai/feed/",
        lang="en",
        category="tech",
        is_active=False,  # A/B кандидат
        quality_score=0.74,
        added_date="2025-04-22",
        description="AI-инструменты для HR, автоматизация найма и онбординга.",
        topics_covered=["skills", "hiring"],
        region="EN",
        rationale="Узкая ниша AI-в-HR — кандидат, активировать при усилении фокуса на автоматизацию.",
    ),

    # ── biz ───────────────────────────────────────────────────────────────────

    Source(
        source_id="economist-business",
        name="The Economist — Business",
        url="https://www.economist.com/business/rss.xml",
        lang="en",
        category="biz",
        is_active=True,
        quality_score=0.88,
        added_date="2025-04-22",
        description="Глобальные бизнес-тренды, рынок труда, управление компаниями.",
        topics_covered=["hiring", "layoffs", "salaries", "culture"],
        region="Global",
        rationale="Макро-картинка рынка труда глобально — контекст для локальных наблюдений.",
    ),
    Source(
        source_id="mit-sloan",
        name="MIT Sloan Management Review",
        url="https://sloanreview.mit.edu/feed/",
        lang="en",
        category="biz",
        is_active=True,
        quality_score=0.87,
        added_date="2025-04-22",
        description="Исследования по менеджменту, лидерству и будущему работы.",
        topics_covered=["culture", "skills", "diversity", "burnout"],
        region="Global",
        rationale="Академическая глубина уровня MIT — используется как tie-breaker при противоречивых сигналах.",
    ),
]


# ── Производное dict-представление (для обратной совместимости) ───────────────
# Модули analytics / source_manager / тесты работают с dict-формой. Держим
# SOURCES как источник истины, а SOURCES_CATALOG — как синхронизированное
# view. Любые мутации (set_active) должны менять обе коллекции — см. set_active().

def _rebuild_catalog_view() -> List[dict]:
    return [s.to_dict() for s in SOURCES]


SOURCES_CATALOG: List[dict] = _rebuild_catalog_view()


# ── API для работы с Source (новое, предложено Беспамятных) ──────────────────

def get_all_sources() -> List[Source]:
    """Вернуть все источники из каталога."""
    return SOURCES


def get_active_sources() -> List[Source]:
    """Вернуть только активные источники (is_active=True)."""
    return [s for s in SOURCES if s.is_active]


def get_by_id(source_id: str) -> Optional[Source]:
    """Найти источник по его slug-идентификатору. Вернуть None если не найден."""
    return next((s for s in SOURCES if s.source_id == source_id), None)


def get_by_category(category: Category) -> List[Source]:
    """Вернуть все источники заданной категории (активные и неактивные)."""
    return [s for s in SOURCES if s.category == category]


def get_by_lang(lang: Lang) -> List[Source]:
    """Вернуть все источники заданного языка."""
    return [s for s in SOURCES if s.lang == lang]


# ── API для работы с dict-представлением (legacy, используется кодом ─────────
#    analytics / source_manager / rss_fetcher / settings / tests) ─────────────

def load_sources(active_only: bool = True) -> List[dict]:
    """Return sources in legacy dict shape.

    Args:
        active_only: If True, return only is_active sources.
    """
    items = get_active_sources() if active_only else SOURCES
    return [s.to_dict() for s in items]


def get_source(source_id: str) -> Optional[dict]:
    """Return source by id in legacy dict shape."""
    src = get_by_id(source_id)
    return src.to_dict() if src else None


def set_active(source_id: str, active: bool) -> bool:
    """Toggle is_active flag. Returns True if source was found.

    Mutates both ``SOURCES`` (dataclass list) and ``SOURCES_CATALOG`` (dict view).
    """
    found = False
    for s in SOURCES:
        if s.source_id == source_id:
            s.is_active = active
            found = True
            break
    if found:
        for d in SOURCES_CATALOG:
            if d["id"] == source_id:
                d["is_active"] = active
                break
    return found


def validate_source(source: dict) -> List[str]:
    """Validate a dict-shaped source entry. Returns list of error messages."""
    errors = []
    required = ["id", "url", "name", "lang", "category", "topics_covered"]
    for required_field in required:
        if required_field not in source:
            errors.append(f"Missing required field: {required_field}")

    if source.get("lang") not in ("ru", "en"):
        errors.append(f"Invalid lang: {source.get('lang')} (expected 'ru' or 'en')")

    if source.get("category") not in CATEGORIES:
        errors.append(f"Invalid category: {source.get('category')}")

    if source.get("region") and source["region"] not in REGIONS:
        errors.append(f"Invalid region: {source.get('region')}")

    quality = source.get("quality_score")
    if quality is not None and not (0.0 <= quality <= 1.0):
        errors.append(f"quality_score must be in [0.0, 1.0], got {quality}")

    return errors
