"""Unit tests for HR rules (deterministic business logic)."""
import pytest

from src.agent.rules import HRRules


# ---- calculate_risk_score ----

class TestCalculateRiskScore:
    def test_clean_text_returns_base_score(self):
        # Neutral text with no keywords → starts at base 0.5.
        score = HRRules.calculate_risk_score("Обычная новость о погоде", "culture")
        assert score == 0.5

    def test_matching_topic_keyword_increases_score(self):
        score = HRRules.calculate_risk_score("Объявлено массовое сокращение персонала", "layoffs")
        assert score > 0.5

    def test_non_matching_topic_keyword_adds_less(self):
        matching = HRRules.calculate_risk_score("сокращение", "layoffs")
        non_matching = HRRules.calculate_risk_score("сокращение", "hiring")
        # matching topic: +0.15, non-matching: +0.05
        assert matching > non_matching

    def test_positive_keyword_reduces_score(self):
        # Note: substring match is literal — use exact keyword "обучение", not "обучения".
        score = HRRules.calculate_risk_score("обучение сотрудников training program", "skills")
        assert score < 0.5

    def test_score_clamped_to_upper_bound(self):
        text = "сокращение увольнение layoff downsizing restructuring job cuts"
        score = HRRules.calculate_risk_score(text, "layoffs")
        assert score <= 1.0

    def test_score_clamped_to_lower_bound(self):
        text = "найм вакансии hiring surge talent acquisition new positions обучение развитие"
        score = HRRules.calculate_risk_score(text, "hiring")
        assert score >= 0.0

    def test_case_insensitive(self):
        lower = HRRules.calculate_risk_score("сокращение", "layoffs")
        upper = HRRules.calculate_risk_score("СОКРАЩЕНИЕ", "layoffs")
        assert lower == upper

    def test_empty_text_returns_base_score(self):
        assert HRRules.calculate_risk_score("", "layoffs") == 0.5


# ---- get_risk_level ----

class TestGetRiskLevel:
    @pytest.mark.parametrize("score,expected_level", [
        (0.95, "critical"),
        (0.80, "critical"),
        (0.79, "high"),
        (0.60, "high"),
        (0.59, "medium"),
        (0.40, "medium"),
        (0.39, "low"),
        (0.00, "low"),
    ])
    def test_boundaries(self, score, expected_level):
        assert HRRules.get_risk_level(score)["level"] == expected_level

    def test_returns_level_metadata(self):
        level = HRRules.get_risk_level(0.85)
        assert "threshold" in level
        assert "color" in level
        assert "label" in level


# ---- should_generate_alert ----

class TestShouldGenerateAlert:
    def test_high_sensitivity_low_threshold(self):
        config = {"sensitivity": "high", "focus_topics": []}
        assert HRRules.should_generate_alert(0.35, "culture", config) is True

    def test_low_sensitivity_high_threshold(self):
        config = {"sensitivity": "low", "focus_topics": []}
        assert HRRules.should_generate_alert(0.65, "culture", config) is False
        assert HRRules.should_generate_alert(0.75, "culture", config) is True

    def test_focus_topic_lowers_threshold(self):
        config_focus = {"sensitivity": "medium", "focus_topics": ["layoffs"]}
        config_no_focus = {"sensitivity": "medium", "focus_topics": []}
        # 0.4 is below medium threshold (0.5) for non-focus, but focus drops threshold to 0.35.
        assert HRRules.should_generate_alert(0.4, "layoffs", config_focus) is True
        assert HRRules.should_generate_alert(0.4, "layoffs", config_no_focus) is False

    def test_unknown_sensitivity_defaults_to_medium(self):
        config = {"sensitivity": "bogus", "focus_topics": []}
        # Medium threshold is 0.5.
        assert HRRules.should_generate_alert(0.55, "culture", config) is True
        assert HRRules.should_generate_alert(0.45, "culture", config) is False


# ---- detect_anomaly ----

class TestDetectAnomaly:
    def test_not_enough_history_returns_not_anomaly(self):
        result = HRRules.detect_anomaly(0.9, [{"value": 0.5}])
        assert result["is_anomaly"] is False
        assert result["deviation"] == 0

    def test_anomaly_up(self):
        historical = [{"value": 0.3}] * 10
        result = HRRules.detect_anomaly(0.9, historical)
        assert result["is_anomaly"] is True
        assert result["direction"] == "up"

    def test_anomaly_down(self):
        historical = [{"value": 0.8}] * 10
        result = HRRules.detect_anomaly(0.3, historical)
        assert result["is_anomaly"] is True
        assert result["direction"] == "down"

    def test_value_within_threshold_is_not_anomaly(self):
        historical = [{"value": 0.5}] * 10
        result = HRRules.detect_anomaly(0.55, historical)
        # 10% deviation < 30% threshold.
        assert result["is_anomaly"] is False

    def test_zero_average_handled_safely(self):
        historical = [{"value": 0.0}] * 10
        result = HRRules.detect_anomaly(0.5, historical)
        assert result["is_anomaly"] is False
        assert result["deviation"] == 0


# ---- prioritize_insight ----

class TestPrioritizeInsight:
    def test_critical_immediate_gets_max_priority(self):
        insight = {"risk_level": "critical", "urgency": "immediate"}
        assert HRRules.prioritize_insight(insight, "analyst") == 100

    def test_low_month_gets_base_priority(self):
        insight = {"risk_level": "low", "urgency": "month"}
        priority = HRRules.prioritize_insight(insight, "analyst")
        # base 50 + 0 (low) + 5 (month) = 55
        assert priority == 55

    def test_priority_is_bounded_at_100(self):
        insight = {"risk_level": "critical", "urgency": "immediate"}
        assert HRRules.prioritize_insight(insight, "analyst") <= 100

    def test_unknown_fields_default_to_zero_impact(self):
        insight = {"risk_level": "unknown", "urgency": "whenever"}
        # base 50 + 0 + 0
        assert HRRules.prioritize_insight(insight, "analyst") == 50


# ---- get_topic_trend_summary ----

class TestTopicTrendSummary:
    def test_empty_data_returns_stable(self):
        summary = HRRules.get_topic_trend_summary([])
        assert summary["direction"] == "stable"

    def test_single_point_returns_stable(self):
        summary = HRRules.get_topic_trend_summary([{"value": 0.5}])
        assert summary["direction"] == "stable"

    def test_rising_trend(self):
        data = [{"value": 0.2}] * 5 + [{"value": 0.8}] * 5
        summary = HRRules.get_topic_trend_summary(data)
        assert summary["direction"] == "up"
        assert summary["change"] > 10

    def test_falling_trend(self):
        data = [{"value": 0.8}] * 5 + [{"value": 0.2}] * 5
        summary = HRRules.get_topic_trend_summary(data)
        assert summary["direction"] == "down"
        assert summary["change"] < -10

    def test_stable_trend(self):
        data = [{"value": 0.5}] * 10
        summary = HRRules.get_topic_trend_summary(data)
        assert summary["direction"] == "stable"
