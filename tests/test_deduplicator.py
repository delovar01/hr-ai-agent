"""Unit tests for the SimHash-based content deduplicator."""
import pytest

from src.processing.deduplicator import (
    ContentDeduplicator,
    HASH_BITS,
    compute_simhash,
    exact_hash,
    find_cross_source_duplicates,
    hamming_distance,
)


# Realistic article length (~150 tokens) — SimHash is unstable on very short
# inputs. Real RSS summaries typically exceed this length, so the fixtures
# reflect production conditions.
ARTICLE = (
    "Крупнейшие технологические компании объявили о массовых сокращениях в текущем квартале. "
    "По оценкам отраслевых аналитиков и рыночных экспертов, под увольнения попадут "
    "десятки тысяч сотрудников в различных регионах. Компании объясняют свои решения "
    "оптимизацией операционных расходов, сдвигом стратегического фокуса на разработку "
    "AI-проектов и общим охлаждением венчурного рынка. Эксперты прогнозируют, что тенденция "
    "продлится в течение ближайших кварталов и затронет как крупные корпорации, так и "
    "средний бизнес. Особенно чувствительно ситуация отразится на специалистах среднего звена, "
    "менеджерах продуктов и рекрутерах. Профсоюзы готовят обращения к регуляторам и требуют "
    "расширенных компенсационных пакетов для увольняемых работников."
)

# Realistic near-duplicate: same article republished by an aggregator — identical
# body with different wrapper text. This is the core scenario SimHash is built for.
ARTICLE_NEAR_DUPLICATE = (
    "По сообщениям зарубежных СМИ и информационных агентств: "
    + ARTICLE
    + " Данный материал публикуется на основе пресс-релиза агентства Reuters."
)

DIFFERENT_ARTICLE = (
    "Запущена новая программа обучения и профессиональной переквалификации для выпускников "
    "технических вузов. В рамках программы молодые специалисты смогут пройти углублённые курсы "
    "по data science, машинному обучению, современным языкам программирования и разработке "
    "облачных решений. Длительность курсов составит шесть месяцев с гарантированной оплачиваемой "
    "стажировкой в крупных IT-компаниях. Организаторы рассчитывают, что программа поможет "
    "выпускникам преодолеть разрыв между академической подготовкой и требованиями индустрии. "
    "Приём заявок открыт круглогодично, первые потоки стартуют уже в следующем месяце."
)


class TestSimHash:
    def test_identical_text_same_hash(self):
        assert compute_simhash(ARTICLE) == compute_simhash(ARTICLE)

    def test_short_text_returns_none(self):
        assert compute_simhash("слишком коротко") is None

    def test_empty_text_returns_none(self):
        assert compute_simhash("") is None

    def test_near_duplicate_small_distance(self):
        a = compute_simhash(ARTICLE)
        b = compute_simhash(ARTICLE_NEAR_DUPLICATE)
        # Same body wrapped with intro/outro should stay well within the
        # default near-dup threshold (4 bits) and definitely < 10.
        assert hamming_distance(a, b) <= 10

    def test_unrelated_text_large_distance(self):
        a = compute_simhash(ARTICLE)
        b = compute_simhash(DIFFERENT_ARTICLE)
        assert hamming_distance(a, b) > 10


class TestHammingDistance:
    def test_same_value_zero_distance(self):
        assert hamming_distance(0xDEADBEEF, 0xDEADBEEF) == 0

    def test_bit_difference_counted(self):
        assert hamming_distance(0b1010, 0b1111) == 2

    def test_max_distance_is_bit_width(self):
        all_ones = (1 << HASH_BITS) - 1
        assert hamming_distance(0, all_ones) == HASH_BITS


class TestExactHash:
    def test_ignores_whitespace_case(self):
        a = exact_hash("  Hello World  ")
        b = exact_hash("hello world")
        assert a == b

    def test_strips_html(self):
        a = exact_hash("<p>Hello World</p>")
        b = exact_hash("hello world")
        assert a == b


class TestContentDeduplicator:
    def test_first_item_is_not_duplicate(self):
        dd = ContentDeduplicator()
        match = dd.check(ARTICLE)
        assert match.is_duplicate is False

    def test_exact_repeat_is_duplicate(self):
        dd = ContentDeduplicator()
        dd.add(ARTICLE, item_id="a1")
        match = dd.check(ARTICLE)
        assert match.is_duplicate is True
        assert match.distance == 0
        assert match.matched_item_id == "a1"

    def test_near_duplicate_is_detected(self):
        # Same article wrapped with a different intro/outro — the classic "republished" case.
        dd = ContentDeduplicator()  # default threshold
        dd.add(ARTICLE, item_id="a1")
        match = dd.check(ARTICLE_NEAR_DUPLICATE)
        assert match.is_duplicate is True
        assert match.matched_item_id == "a1"

    def test_different_article_is_not_duplicate(self):
        dd = ContentDeduplicator()
        dd.add(ARTICLE, item_id="a1")
        match = dd.check(DIFFERENT_ARTICLE)
        assert match.is_duplicate is False

    def test_check_does_not_register(self):
        dd = ContentDeduplicator()
        dd.check(ARTICLE)
        assert len(dd) == 0

    def test_add_registers(self):
        dd = ContentDeduplicator()
        dd.add(ARTICLE)
        assert len(dd) == 1

    def test_check_and_add_idempotent(self):
        dd = ContentDeduplicator()
        r1 = dd.check_and_add(ARTICLE, item_id="a1")
        r2 = dd.check_and_add(ARTICLE, item_id="a2")
        assert r1.is_duplicate is False
        assert r2.is_duplicate is True
        assert r2.matched_item_id == "a1"
        assert len(dd) == 1  # second add was skipped

    def test_max_window_enforced(self):
        dd = ContentDeduplicator(max_window=5)
        for i in range(10):
            dd.add(f"{ARTICLE} variant {i}", item_id=f"a{i}")
        assert len(dd) == 5

    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError):
            ContentDeduplicator(threshold=-1)
        with pytest.raises(ValueError):
            ContentDeduplicator(threshold=HASH_BITS + 1)

    def test_empty_text_is_not_duplicate(self):
        dd = ContentDeduplicator()
        assert dd.check("").is_duplicate is False

    def test_export_and_load_state_roundtrip(self):
        dd1 = ContentDeduplicator()
        dd1.add(ARTICLE, item_id="a1")
        snapshot = dd1.export_state()

        dd2 = ContentDeduplicator()
        dd2.load_state(snapshot)
        # After reload, the same article should be detected as duplicate.
        match = dd2.check(ARTICLE)
        assert match.is_duplicate is True


class TestFindCrossSourceDuplicates:
    def test_detects_cross_source_duplicate(self):
        items = [
            {"title": "Tech layoffs", "content": ARTICLE, "source": "hbr"},
            {"title": "Tech layoffs", "content": ARTICLE_NEAR_DUPLICATE, "source": "shrm"},
            {"title": "Training program", "content": DIFFERENT_ARTICLE, "source": "vc_ru"},
        ]
        pairs = find_cross_source_duplicates(items)
        assert any((a == 0 and b == 1) or (a == 1 and b == 0) for a, b, _ in pairs)
        # The different article should not appear in any pair.
        assert not any(2 in (a, b) for a, b, _ in pairs)

    def test_empty_list(self):
        assert find_cross_source_duplicates([]) == []
