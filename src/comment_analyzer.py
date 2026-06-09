import logging
from textblob import TextBlob
from config import FAMILY_KEYWORDS, BOT_KEYWORDS

logger = logging.getLogger(__name__)


class CommentAnalyzer:
    def __init__(self):
        self.repeat_commenters = set()

    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of comment text using TextBlob"""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity

            if polarity > 0.1:
                return "positive"
            elif polarity < -0.1:
                return "negative"
            else:
                return "neutral"

        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return "neutral"

    def classify_audience(self, author: str, text: str, is_repeat: bool) -> str:
        """Classify audience type based on comment characteristics"""
        text_lower = text.lower()

        # Check for bot patterns
        for keyword in BOT_KEYWORDS:
            if keyword in text_lower:
                return "bot"

        # Check for family/friend patterns
        for keyword in FAMILY_KEYWORDS:
            if keyword in text_lower:
                return "family_friend"

        # Check if repeat commenter
        if is_repeat:
            return "repeat_fan"

        # Default to new audience
        return "new_audience"

    def aggregate_audience_types(self, comments: list) -> dict:
        """Aggregate audience types into percentages"""
        if not comments:
            return {}

        type_counts = {}
        for comment in comments:
            audience_type = comment.get("audience_type", "unknown")
            type_counts[audience_type] = type_counts.get(audience_type, 0) + 1

        total = len(comments)
        percentages = {
            k: round((v / total) * 100, 2) for k, v in type_counts.items()
        }

        return percentages
