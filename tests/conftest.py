import os
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_gigachat_env():
    """Автоматически мокаем GigaChat для всех тестов, если креды не заданы"""
    if not os.getenv("GIGACHAT_CREDENTIALS"):
        with patch("src.api.gigachat.GigaChatClient._make_request") as mock:
            mock.return_value = {"choices": [{"message": {"content": "Mock response"}}]}
            yield
    else:
        yield
