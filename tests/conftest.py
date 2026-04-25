"""Shared pytest fixtures.

Tests must NEVER touch the real ``data/state.json``. The ``isolated_state``
fixture provides a fresh AgentState rooted at a temporary directory.
"""
import sys
from pathlib import Path

import pytest

# Ensure the project root is importable when running pytest from any CWD.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Provide a fresh AgentState instance backed by a temp file."""
    from src.agent.state import AgentState

    state = AgentState.__new__(AgentState)
    state.state_file = tmp_path / "state.json"
    state.state = state._default_state()
    return state


@pytest.fixture
def labeled_news_fixture():
    """Placeholder loader for the labeled news dataset.

    The actual fixture file ``tests/fixtures/labeled_news.json`` is authored by
    Беспамятных Евгений (аналитик данных). See ``tests/fixtures/README.md``.
    """
    import json

    fixture_path = Path(__file__).parent / "fixtures" / "labeled_news.json"
    if not fixture_path.exists():
        pytest.skip("labeled_news.json fixture not yet provided by the data analyst")
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)
