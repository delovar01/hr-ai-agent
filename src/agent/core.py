
"""
Core agent logic - the brain of the HR AI Agent.
"""
import time
from datetime import datetime
from typing import Optional
from src.agent.state import agent_state
from src.agent.rules import hr_rules
from src.sources.rss_fetcher import RSSFetcher
from src.sources.mock_data import MockDataGenerator
from src.processing.translator import translate_if_needed
from src.processing.classifier import classify_content
from src.processing.analyzer import analyze_content
from src.insights.generator import InsightGenerator
from config.settings import HR_TOPICS, USER_ROLES, TIME_RANGES  # Добавил TIME_RANGES


class HRAgent:
    """
    Proactive HR AI Agent.
    
    This is NOT a chatbot. This agent:
    1. Monitors data sources autonomously
    2. Maintains state and memory
    3. Applies HR-specific rules
    4. Generates insights proactively
    """
    
    def __init__(self, user_config: Optional[dict] = None):
        self.user_config = user_config or self._default_config()
        self.rss_fetcher = RSSFetcher()
        self.mock_generator = MockDataGenerator()
        self.insight_generator = InsightGenerator()
        self.is_running = False
    
    def _default_config(self) -> dict:
        return {
            "role": "analyst",
            "focus_topics": ["hiring", "layoffs", "salaries"],
            "sensitivity": "medium",
            "language": "ru",
            "time_range": "24h"
        }
    
    def configure(self, role: str = None, topics: list = None, sensitivity: str = None, time_range: str = None):
        """Configure agent behavior without editing prompts."""
        if role and role in USER_ROLES:
            self.user_config["role"] = role
            self.user_config["focus_topics"] = USER_ROLES[role]["focus"]
        if topics:
            self.user_config["focus_topics"] = topics
        if sensitivity in ["low", "medium", "high"]:
            self.user_config["sensitivity"] = sensitivity
        if time_range:
            self.user_config["time_range"] = time_range
    
    def _filter_by_time_range(self, items: list) -> list:
        """Filter items by configured time range."""
        from datetime import datetime, timedelta
        from config.settings import TIME_RANGES
        
        time_range = self.user_config.get("time_range", "24h")
        
        # If "all", return everything
        if time_range == "all":
            return items
        
        # Calculate cutoff time
        range_config = TIME_RANGES.get(time_range, {"hours": 24})
        now = datetime.now()
        
        if "hours" in range_config:
            cutoff = now - timedelta(hours=range_config["hours"])
        elif "days" in range_config:
            cutoff = now - timedelta(days=range_config["days"])
        else:
            return items
        
        # Filter items
        filtered = []
        for item in items:
            published = item.get("published", "")
            if not published:
                # If no date, include it (might be fresh)
                filtered.append(item)
                continue
            
            try:
                # Parse different date formats
                from dateutil import parser
                pub_date = parser.parse(published)
                
                # Make timezone-naive for comparison
                if pub_date.tzinfo:
                    pub_date = pub_date.replace(tzinfo=None)
                
                if pub_date >= cutoff:
                    filtered.append(item)
            except:
                # If parsing fails, include it
                filtered.append(item)
        
        return filtered
    
    def run_cycle(self) -> dict:
        """
        Execute one monitoring cycle.
        """
        cycle_results = {
            "timestamp": datetime.now().isoformat(),
            "sources_checked": 0,
            "new_items": 0,
            "insights_generated": [],
            "alerts_created": [],
            "debug_info": {}  # ← Добавляем дебаг
        }
        
        # 1. Fetch from real RSS sources
        rss_items = self.rss_fetcher.fetch_all()
        mock_items = self.mock_generator.generate_batch(3)
        total_fetched = len(rss_items)

        # 2. Filter by time range
        all_items = self._filter_by_time_range(rss_items + mock_items)
        filtered_count = len(all_items)
        
        cycle_results["debug_info"] = {
            "total_fetched": total_fetched,
            "after_filter": filtered_count,
            "filtered_out": total_fetched - filtered_count,
            "time_range": self.user_config.get('time_range', '24h')
        }
        
        cycle_results["sources_checked"] = len(all_items)
        
        # 3. Process each item
        for item in all_items:
            # Skip if already processed
            url = item.get("url", item.get("id", ""))
            if agent_state.is_url_processed(url):
                continue

            cycle_results["new_items"] += 1

            # Translate if needed
            content = item.get("content", item.get("title", ""))
            translated = translate_if_needed(content, item.get("lang", "en"))
            item["translated_content"] = translated
            
            # Classify HR topic
            classification = classify_content(translated)
            item["classification"] = classification
            topic = classification.get("topic", "culture")
            
            # Calculate risk score
            risk_score = hr_rules.calculate_risk_score(translated, topic)
            item["risk_score"] = risk_score
            item["risk_level"] = hr_rules.get_risk_level(risk_score)
            
            # Add to state
            agent_state.add_observation(item)
            agent_state.add_trend_point(topic, risk_score)
            agent_state.mark_url_processed(item.get("url", item.get("id", "")))
            
            # Check for anomalies
            historical = agent_state.get_trend_data(topic)
            anomaly = hr_rules.detect_anomaly(risk_score, historical)
            
            if anomaly["is_anomaly"]:
                agent_state.record_anomaly()
                item["anomaly"] = anomaly
            
            # Generate insight if warranted
            if self._should_generate_insight(item):
                insight = self.insight_generator.generate(
                    item, 
                    historical,
                    self.user_config
                )
                if insight:
                    insight["source_item"] = {
                        "title": item.get("title", ""),
                        "topic": topic,
                        "risk_score": risk_score
                    }
                    insight["priority"] = hr_rules.prioritize_insight(
                        insight, 
                        self.user_config["role"]
                    )
                    agent_state.add_insight(insight)
                    cycle_results["insights_generated"].append(insight)
            
            # Create alert if needed
            if hr_rules.should_generate_alert(risk_score, topic, self.user_config):
                alert = {
                    "title": f"Обнаружен риск: {HR_TOPICS.get(topic, topic)}",
                    "content": translated[:200],
                    "risk_level": item["risk_level"]["level"],
                    "topic": topic,
                    "source": item.get("source", "Unknown")
                }
                agent_state.add_alert(alert)
                cycle_results["alerts_created"].append(alert)
        
        agent_state.update_last_check()
        return cycle_results
    
    def _should_generate_insight(self, item: dict) -> bool:
        """Determine if item warrants insight generation."""
        # Always generate for high risk
        if item.get("risk_score", 0) >= 0.6:
            return True
        
        # Generate for focus topics
        topic = item.get("classification", {}).get("topic", "")
        if topic in self.user_config.get("focus_topics", []):
            return True
        
        # Generate for anomalies
        if item.get("anomaly", {}).get("is_anomaly", False):
            return True
        
        return False
    
    def get_dashboard_data(self) -> dict:
        """Get data for dashboard visualization."""
        insights = agent_state.get_recent_insights(20)
        alerts = agent_state.get_unacknowledged_alerts()
        
        # Calculate trend summaries
        trends = {}
        for topic in HR_TOPICS.keys():
            trend_data = agent_state.get_trend_data(topic)
            trends[topic] = hr_rules.get_topic_trend_summary(trend_data)
            trends[topic]["data"] = trend_data[-30:]  # Last 30 points
        
        # Get metrics
        metrics = agent_state.state.get("metrics", {})
        
        return {
            "insights": insights,
            "alerts": alerts,
            "trends": trends,
            "metrics": metrics,
            "last_check": agent_state.state.get("last_check"),
            "user_config": self.user_config
        }
    
    def get_status(self) -> dict:
        """Get agent status."""
        return {
            "is_running": self.is_running,
            "last_check": agent_state.state.get("last_check"),
            "total_observations": len(agent_state.state.get("observations", [])),
            "total_insights": len(agent_state.state.get("insights", [])),
            "pending_alerts": len(agent_state.get_unacknowledged_alerts()),
            "config": self.user_config
        }


# Singleton agent instance
hr_agent = HRAgent()
