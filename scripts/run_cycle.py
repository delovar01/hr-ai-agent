"""Headless single-cycle runner.

Usage:
    python scripts/run_cycle.py

Calls ``hr_agent.run_cycle()`` once and prints a one-line summary. Intended
for CI cron schedules and local cron — keeps the agent's state warm so the
dashboard always has fresh insights without anyone having to click
"▶️ Запустить цикл анализа" in Streamlit.

Closes the «не полностью проактивен» line item from слайд 7 (architecture
weaknesses).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent.core import hr_agent  # noqa: E402


def main() -> int:
    result = hr_agent.run_cycle()
    print(
        f"sources_checked={result['sources_checked']} "
        f"new_items={result['new_items']} "
        f"duplicates_skipped={result['duplicates_skipped']} "
        f"insights={len(result['insights_generated'])} "
        f"alerts={len(result['alerts_created'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
