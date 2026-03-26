
"""
HR topic classification using GigaChat.
"""
from src.api.gigachat import gigachat_client
from config.settings import HR_TOPICS


def classify_content(text: str) -> dict:
    """Classify content into HR topics using GigaChat."""
    if not text:
        return {"topic": "culture", "confidence": 0.5, "keywords": []}

    try:
        result = gigachat_client.classify_hr_topic(text)

        # Validate topic
        if result.get("topic") not in HR_TOPICS:
            result["topic"] = "culture"

        return result
    except Exception as e:
        print(f"Classification error: {e}")
        return {"topic": "culture", "confidence": 0.5, "keywords": []}
