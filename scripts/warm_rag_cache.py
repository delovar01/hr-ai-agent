"""Pre-warm the RAG answer cache with questions the committee is likely to ask.

Why
---
RAG-chat depends on a live GigaChat call. On defence day we cannot afford
a "модель временно недоступна" moment in front of the committee — if a
member happens to type a question while we are rate-limited, the
demonstration takes a hit.

We mitigate two ways: smart fallback (already in ``GigaChatClient`` —
synthesises an answer from raw context if GigaChat fails) AND this script,
which pre-computes answers for the most likely questions and stores them
in the in-process cache. As long as the dashboard process stays alive,
these questions will be answered instantly from memory.

How to use
----------
Run RIGHT BEFORE the live demo, from the project root and inside the venv::

    python scripts/warm_rag_cache.py

The script keeps the process alive briefly after warming so that the cache
is dumped to ``data/rag_cache.json`` — the dashboard loads that file on
startup, so the warm state survives a Streamlit restart.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import DATA_DIR  # noqa: E402
from src.agent.state import agent_state  # noqa: E402
from src.api.gigachat import gigachat_client  # noqa: E402
from src.api.rag import rag_context_builder  # noqa: E402


# Самые вероятные вопросы комиссии — выводил из FAQ + типовых тем.
TYPICAL_QUESTIONS = [
    "Какие риски выгорания заметны за последнюю неделю?",
    "Что показывают тренды по сокращениям?",
    "Какие новости по зарплатам и компенсациям?",
    "Что произошло с наймом за последний месяц?",
    "Какие критические риски требуют внимания HR сейчас?",
    "Что с корпоративной культурой?",
    "Покажи топ-3 инсайта по HR-рискам",
    "Что нового про обучение и развитие сотрудников?",
]

RAG_CACHE_PATH = DATA_DIR / "rag_cache.json"


def warm() -> dict:
    insights = agent_state.get_recent_insights(20)
    alerts = agent_state.get_unacknowledged_alerts()
    observations = list(reversed(agent_state.state.get("observations", [])))[:30]

    cache: dict = {}
    for q in TYPICAL_QUESTIONS:
        ctx = rag_context_builder.build(q, insights, alerts, observations)
        print(f"[warm] {q!r} (ctx_len={len(ctx.prompt_text)})", flush=True)
        ans = gigachat_client.answer_question(q, ctx.prompt_text)
        cache[gigachat_client._cache_key(q, ctx.prompt_text)] = ans
    return cache


def main() -> int:
    cache = warm()
    RAG_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAG_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"\nПрогрето вопросов: {len(cache)}")
    print(f"Сохранено в: {RAG_CACHE_PATH}")
    print("Теперь дашборд загружает этот файл при старте — типовые "
          "вопросы отвечаются мгновенно даже при сбое GigaChat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
