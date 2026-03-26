
"""
Trend and anomaly analysis module using GigaChat.
"""
from src.api.gigachat import gigachat_client
from src.agent.rules import hr_rules


def analyze_content(item: dict, historical: list) -> dict:
    """Analyze content for trends and anomalies."""
    result = {
        "trend_analysis": None,
        "anomaly_detection": None,
        "risk_assessment": None
    }
    
    # Get trend analysis from GigaChat
    if historical:
        try:
            trend = gigachat_client.analyze_trend(historical, item)
            result["trend_analysis"] = trend
        except Exception as e:
            print(f"Trend analysis error: {e}")
    
    # Detect anomalies using rules
    risk_score = item.get("risk_score", 0.5)
    anomaly = hr_rules.detect_anomaly(risk_score, historical)
    result["anomaly_detection"] = anomaly
    
    # Risk assessment
    result["risk_assessment"] = hr_rules.get_risk_level(risk_score)
    
    return result

