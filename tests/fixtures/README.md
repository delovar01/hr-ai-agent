# Test Fixtures

## `labeled_news.json` — ответственный: Беспамятных Евгений

50–100 реальных HR-новостей (mix RU/EN), каждая размечена вручную:

```json
[
  {
    "id": "001",
    "title": "...",
    "content": "...",
    "lang": "en",
    "source": "shrm",
    "expected_topic": "layoffs",
    "expected_risk_level": "high",
    "expert_notes": "массовые сокращения в Big Tech, упоминание 10k мест"
  }
]
```

### Поля

| Поле | Значения |
|---|---|
| `expected_topic` | один из: `hiring`, `layoffs`, `salaries`, `skills`, `burnout`, `culture`, `diversity` |
| `expected_risk_level` | `critical`, `high`, `medium`, `low` |
| `lang` | `ru` или `en` |

### Для расчёта Cohen's Kappa

Второй разметчик — Коновалов Степан — делает независимую разметку в файл
`labeled_news_reviewer2.json` с той же схемой. Cohen's Kappa считается
автоматически в `tests/test_classifier_quality.py` после загрузки обеих разметок.

## `reference_translations.json` — ответственный: Беспамятных Евгений

20 эталонных пар EN→RU перевода HR-текстов:

```json
[
  {
    "en": "Major tech companies announced mass layoffs affecting 10,000 employees.",
    "ru": "Крупные технологические компании объявили о массовых сокращениях, затронувших 10 000 сотрудников.",
    "key_terms": ["mass layoffs → массовые сокращения"]
  }
]
```
