
"""
Proactive insight generation - the core agent intelligence.
"""
from datetime import datetime
from src.api.gigachat import gigachat_client
from config.settings import HR_TOPICS, USER_ROLES


class InsightGenerator:
    """
    Generates proactive HR insights.
    
    This is what makes this an AGENT, not a chatbot:
    - Insights are generated without user queries
    - Based on detected patterns and anomalies
    - Tailored to user role and preferences
    """
    
    def generate(self, item: dict, historical: list, user_config: dict) -> dict:
        """Generate insight for an item."""
        topic = item.get("classification", {}).get("topic", "culture")
        topic_name = HR_TOPICS.get(topic, topic)
        
        # Build context for GigaChat
        context = self._build_context(item, historical, user_config)
        
        # Prepare data summary
        data_summary = {
            "topic": topic_name,
            "title": item.get("title", ""),
            "content_preview": item.get("translated_content", "")[:500],
            "risk_score": item.get("risk_score", 0.5),
            "source": item.get("source", "Unknown"),
            "anomaly": item.get("anomaly", {}),
            "trend_points": len(historical)
        }
        
        # Generate insight using GigaChat
        try:
            insight = gigachat_client.generate_insight(data_summary, context)
        except Exception as e:
            print(f"Insight generation error: {e}")
            insight = self._fallback_insight(data_summary)
        
        # Enhance insight with metadata
        insight["topic"] = topic
        insight["topic_name"] = topic_name
        insight["source"] = item.get("source", "")
        insight["source_title"] = item.get("title", "")
        
        return insight
    
    def _build_context(self, item: dict, historical: list, user_config: dict) -> str:
        """Build context string for insight generation."""
        role = user_config.get("role", "analyst")
        role_name = USER_ROLES.get(role, {}).get("name", "HR-специалист")
        focus = user_config.get("focus_topics", [])
        focus_names = [HR_TOPICS.get(t, t) for t in focus]
        
        context_parts = [
            f"Роль пользователя: {role_name}",
            f"Приоритетные темы: {', '.join(focus_names)}",
            f"Количество исторических наблюдений: {len(historical)}",
        ]
        
        # Add anomaly context if present
        if item.get("anomaly", {}).get("is_anomaly"):
            anomaly = item["anomaly"]
            context_parts.append(
                f"ОБНАРУЖЕНА АНОМАЛИЯ: отклонение {anomaly['deviation']:.1%} "
                f"({anomaly['direction']})"
            )
        
        return " | ".join(context_parts)
    
    def _fallback_insight(self, data: dict) -> dict:
        """Generate fallback insight when GigaChat API fails."""
        return {
            "what_changed": f"Обнаружена новая информация по теме: {data['topic']}",
            "why_important": "Данные требуют внимания HR-специалиста",
            "recommendation": "Рекомендуется провести детальный анализ источника",
            "risk_level": "medium" if data["risk_score"] >= 0.5 else "low",
            "urgency": "week"
        }
