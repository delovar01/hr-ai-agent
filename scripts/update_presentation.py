"""Apply pre-defense edits to the team presentation.

Updates the following slides in HR_AI_Agent_clean_revised.pptx so the deck
reflects what is actually on main today (and not the older state from before
the merges and source-catalog expansion):

  Slide 5  — drop the obsolete 'часть данных для демонстрации' bullet
  Slide 6  — replace 'целевой пул на следующем этапе' with concrete numbers
  Slide 9  — rewrite all 5 'iteration improvements' cards to highlight
             109 tests + CI, source_manager, source_analytics, SimHash dedup,
             labeled_news Cohen Kappa
  Slide 11 — refresh project tree to include tests/, docs/, scripts/,
             .github/, Dockerfile

Run from the project root:
  python scripts/update_presentation.py <input.pptx> <output.pptx>

If arguments are omitted, defaults to the Telegram Desktop input and writes to
docs/HR_AI_Agent_revised_v2.pptx.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


DEFAULT_IN = Path.home() / "Downloads" / "Telegram Desktop" / "HR_AI_Agent_clean_revised.pptx"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "docs" / "HR_AI_Agent_revised_v2.pptx"


def replace_keep_format(text_frame, new_text: str) -> None:
    """Replace text in a text frame while keeping the first run's font.

    python-pptx's ``text_frame.text = ...`` strips run-level formatting; we
    grab font attributes from the first run before the assignment and reapply
    them afterwards. Multi-line input is split on newlines into paragraphs.
    """
    first_para = text_frame.paragraphs[0] if text_frame.paragraphs else None
    first_run = first_para.runs[0] if first_para and first_para.runs else None
    saved = None
    if first_run is not None:
        font = first_run.font
        saved = {
            "name": font.name,
            "size": font.size,
            "bold": font.bold,
            "italic": font.italic,
        }
        try:
            if font.color and font.color.type is not None:
                saved["rgb"] = font.color.rgb
        except (AttributeError, ValueError):
            pass

    lines = new_text.split("\n")
    text_frame.text = lines[0]
    for extra in lines[1:]:
        para = text_frame.add_paragraph()
        para.text = extra

    if saved:
        for para in text_frame.paragraphs:
            for run in para.runs:
                if saved.get("name"):
                    run.font.name = saved["name"]
                if saved.get("size"):
                    run.font.size = saved["size"]
                if saved.get("bold") is not None:
                    run.font.bold = saved["bold"]
                if saved.get("italic") is not None:
                    run.font.italic = saved["italic"]
                if saved.get("rgb"):
                    run.font.color.rgb = saved["rgb"]


# (slide_index, shape_index, new_text) — slide_index is 0-based.
EDITS: list[tuple[int, int, str]] = [
    # Slide 5 — Недостатки MVP: drop obsolete demo-data bullet
    (
        4,
        39,
        "• ограниченный пул внешних API\n"
        "• локальное JSON-состояние\n"
        "• ручной запуск цикла\n"
        "• датасет разметки на стадии расширения",
    ),
    # Slide 6 — Курируемый пул: replace plan-language with concrete numbers
    (
        5,
        6,
        "Каталог содержит 26 источников: 14 активных и 12 кандидатов на "
        "A/B-тестирование. У каждого зафиксированы quality_score, "
        "topics_covered, region и обоснование выбора rationale.",
    ),
    # Slide 9 — Доработки за итерацию: rewrite all 5 cards to surface real artifacts
    (8, 5, "Тесты и CI"),
    (
        8,
        6,
        "109 автотестов проходят зелёными, CI на GitHub Actions с матрицей "
        "Python 3.10 / 3.11, Ruff lint и pytest-coverage.",
    ),
    (8, 9, "Авторегуляция пула"),
    (
        8,
        10,
        "Модуль source_manager отслеживает duplicate_rate и активность "
        "источников и автоматически рекомендует деактивацию шумных и "
        "активацию ценных кандидатов.",
    ),
    (8, 13, "Аналитика источников"),
    (
        8,
        14,
        "source_analytics считает per-source метрики: items_fetched, "
        "duplicate_rate, avg_risk_score, topic_coverage, "
        "unique_contribution — реальные цифры в дашборде.",
    ),
    (8, 17, "SimHash-дедупликация"),
    (
        8,
        18,
        "Двухуровневая фильтрация: URL-уровень и контентный SimHash. "
        "Самописная имплементация без внешних зависимостей, видны кросс-"
        "источниковые дубли.",
    ),
    (8, 21, "Качество классификации"),
    (
        8,
        22,
        "Размеченный датасет labeled_news.json (35 новостей, 7 HR-тем, "
        "RU/EN). По нему считается Cohen's Kappa между разметчиками — "
        "верхняя граница качества модели.",
    ),
    # Slide 11 — Структура проекта: refresh tree
    (
        10,
        5,
        "hr-ai-agent/\n"
        "├─ config/\n"
        "│  ├─ settings.py\n"
        "│  └─ sources_catalog.py   ← 26 источников\n"
        "├─ dashboard/app.py\n"
        "├─ src/\n"
        "│  ├─ agent/\n"
        "│  ├─ processing/deduplicator.py  ← SimHash\n"
        "│  ├─ sources/source_manager.py   ← авторегуляция\n"
        "│  └─ sources/source_analytics.py ← per-source метрики\n"
        "├─ tests/                  ← 109 тестов\n"
        "│  └─ fixtures/labeled_news.json\n"
        "├─ docs/\n"
        "│  ├─ METHODOLOGY.md\n"
        "│  └─ defense_script_mvp.md\n"
        "├─ scripts/demo_start.{sh,ps1}\n"
        "├─ .github/workflows/tests.yml\n"
        "├─ Dockerfile + docker-compose.yml\n"
        "└─ requirements.txt + requirements-dev.txt",
    ),
]


def apply_edits(src: Path, dst: Path) -> None:
    prs = Presentation(src)
    for slide_idx, shape_idx, new_text in EDITS:
        slide = prs.slides[slide_idx]
        shape = slide.shapes[shape_idx]
        if not shape.has_text_frame:
            print(f"[skip] slide {slide_idx + 1} shape {shape_idx}: no text frame")
            continue
        old_preview = shape.text_frame.text.strip()[:60].replace("\n", " / ")
        replace_keep_format(shape.text_frame, new_text)
        new_preview = shape.text_frame.text.strip()[:60].replace("\n", " / ")
        print(f"[ok]   slide {slide_idx + 1} shape {shape_idx}: {old_preview!r} -> {new_preview!r}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    prs.save(dst)
    print(f"\nWrote: {dst}")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    apply_edits(src, dst)
