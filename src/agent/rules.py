
"""
HR-specific rules and logic for the agent.

Все методологические константы (пороги риска, чувствительность алертов, дельта
фокусной темы) вынесены в config/settings.py — этот модуль только применяет
их. Если нужно что-то откалибровать — правьте settings.py, не правьте здесь.
Обоснование значений см. docs/METHODOLOGY.md.
"""
from datetime import datetime, timedelta
from config.settings import (
    HR_TOPICS,
    RISK_LEVELS,
    ANOMALY_THRESHOLD,
    SENSITIVITY_THRESHOLDS,
    FOCUS_TOPIC_DELTA,
)


class HRRules:
    """HR domain rules for agent decision-making."""

    # Keywords that indicate risk by topic.
    # Покрывают все 7 тем рубрикатора. Список — это первичный фильтр для
    # быстрого rule-based score; основной классификатор — GigaChat.
    # Поддерживается русский и английский: новости приходят из обоих языков.
    RISK_KEYWORDS = {
        "layoffs": [
            "сокращение", "увольнение", "массовое увольнение", "оптимизация штата",
            "layoff", "downsizing", "restructuring", "job cuts", "headcount reduction",
            "workforce reduction",
        ],
        "burnout": [
            "выгорание", "стресс", "переработка", "психическое здоровье",
            "burnout", "overwork", "mental health", "quit", "great resignation",
            "quiet quitting",
        ],
        "salaries": [
            "снижение зарплат", "задержка зарплаты", "заморозка зарплат", "урезание премий",
            "salary cut", "wage freeze", "pay cut", "compensation cut",
        ],
        "hiring": [
            # Сигналы напряжения на рынке найма (не сам найм, а его сбои).
            "заморозка найма", "hiring freeze", "rescinded offers", "отозванные офферы",
            "талантливый дефицит", "talent shortage",
        ],
        "skills": [
            "skill gap", "разрыв навыков", "устаревшие навыки", "skills mismatch",
            "automation displacement", "автоматизация рабочих мест",
        ],
        "culture": [
            "токсичная культура", "harassment", "дискриминация", "конфликт",
            "toxic culture", "workplace conflict", "scandal",
        ],
        "diversity": [
            "discrimination", "bias incident", "pay gap", "разрыв в оплате",
            "gender gap", "неравенство",
        ],
    }

    # Keywords that indicate positive signals (subtract from risk).
    POSITIVE_KEYWORDS = {
        "hiring": [
            "найм", "вакансии", "расширение штата", "набор команды",
            "hiring surge", "talent acquisition", "new positions", "headcount growth",
        ],
        "skills": [
            "обучение", "развитие", "переквалификация", "карьерный рост",
            "upskilling", "reskilling", "training program", "career growth", "learning",
        ],
        "culture": [
            "благополучие", "вовлечённость", "well-being", "employee satisfaction",
            "engagement", "wellbeing", "psychological safety",
        ],
        "salaries": [
            "повышение зарплат", "индексация", "бонусы", "премирование",
            "salary increase", "raise", "compensation review",
        ],
        "diversity": [
            "инклюзия", "равные возможности", "inclusion", "equal opportunity",
            "DEI initiative", "diverse hiring",
        ],
    }

    @staticmethod
    def calculate_risk_score(text: str, topic: str) -> float:
        """Calculate risk score based on content."""
        text_lower = text.lower()
        score = 0.5  # Base score

        # Check risk keywords
        for risk_topic, keywords in HRRules.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if risk_topic == topic:
                        score += 0.15
                    else:
                        score += 0.05

        # Check positive keywords (reduce risk)
        for pos_topic, keywords in HRRules.POSITIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score -= 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def get_risk_level(score: float) -> dict:
        """Get risk level based on score."""
        for level, config in RISK_LEVELS.items():
            if score >= config["threshold"]:
                return {"level": level, **config}
        return {"level": "low", **RISK_LEVELS["low"]}

    @staticmethod
    def should_generate_alert(risk_score: float, topic: str, user_config: dict) -> bool:
        """Determine if alert should be generated.

        Threshold map and focus-topic delta live in config/settings.py.
        Unknown sensitivity falls back to medium.
        """
        sensitivity = user_config.get("sensitivity", "medium")
        focus_topics = user_config.get("focus_topics", [])

        threshold = SENSITIVITY_THRESHOLDS.get(sensitivity, SENSITIVITY_THRESHOLDS["medium"])

        # Lower threshold for focus topics — пользователь явно отметил тему
        # как приоритетную, повышаем чувствительность именно для неё.
        if topic in focus_topics:
            threshold -= FOCUS_TOPIC_DELTA

        return risk_score >= threshold
    
    @staticmethod
    def detect_anomaly(current_value: float, historical: list) -> dict:
        """Detect if current value is anomalous."""
        if len(historical) < 5:
            return {"is_anomaly": False, "deviation": 0}
        
        values = [h["value"] for h in historical[-20:]]
        avg = sum(values) / len(values)
        
        if avg == 0:
            return {"is_anomaly": False, "deviation": 0}
        
        deviation = abs(current_value - avg) / avg
        is_anomaly = deviation > ANOMALY_THRESHOLD
        
        return {
            "is_anomaly": is_anomaly,
            "deviation": deviation,
            "direction": "up" if current_value > avg else "down",
            "average": avg
        }
    
    @staticmethod
    def prioritize_insight(insight: dict, user_role: str) -> int:
        """Calculate priority score for insight based on user role."""
        base_priority = 50
        
        # Risk level impact
        risk_weights = {"critical": 40, "high": 25, "medium": 10, "low": 0}
        base_priority += risk_weights.get(insight.get("risk_level", "low"), 0)
        
        # Urgency impact
        urgency_weights = {"immediate": 30, "week": 15, "month": 5}
        base_priority += urgency_weights.get(insight.get("urgency", "month"), 0)
        
        return min(100, base_priority)
    
    @staticmethod
    def get_topic_trend_summary(trend_data: list) -> dict:
        """Summarize trend for a topic."""
        if len(trend_data) < 2:
            return {"direction": "stable", "change": 0, "description": "Недостаточно данных"}
        
        recent = trend_data[-5:] if len(trend_data) >= 5 else trend_data
        older = trend_data[-10:-5] if len(trend_data) >= 10 else trend_data[:len(trend_data)//2]
        
        recent_avg = sum(r["value"] for r in recent) / len(recent)
        older_avg = sum(o["value"] for o in older) / len(older) if older else recent_avg
        
        if older_avg == 0:
            change = 0
        else:
            change = ((recent_avg - older_avg) / older_avg) * 100
        
        if change > 10:
            direction = "up"
            desc = f"Рост на {change:.1f}%"
        elif change < -10:
            direction = "down"
            desc = f"Снижение на {abs(change):.1f}%"
        else:
            direction = "stable"
            desc = "Стабильно"
        
        return {"direction": direction, "change": change, "description": desc}


hr_rules = HRRules()

