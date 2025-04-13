"""Sentiment analysis utility for social media content."""

from typing import Dict, Any, List, Tuple
import re
from collections import Counter

class SentimentAnalyzer:
    """Utility class for analyzing sentiment in text content."""

    def __init__(self):
        """Initialize sentiment analyzer."""
        # Basic sentiment word lists
        self.positive_words = {
            "good", "great", "excellent", "amazing", "wonderful", "fantastic",
            "awesome", "perfect", "love", "like", "enjoy", "happy", "joy",
            "pleasure", "delight", "satisfied", "impressed", "recommend"
        }
        self.negative_words = {
            "bad", "terrible", "awful", "horrible", "disappointing", "poor",
            "worst", "hate", "dislike", "unhappy", "sad", "angry", "frustrated",
            "annoyed", "upset", "disgusted", "regret", "avoid"
        }
        self.intensifiers = {
            "very", "extremely", "really", "so", "too", "quite", "rather",
            "absolutely", "completely", "totally", "utterly", "incredibly"
        }
        self.negators = {
            "not", "never", "no", "none", "nothing", "nobody", "nowhere",
            "neither", "nor", "hardly", "scarcely", "barely", "seldom"
        }

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text content."""
        try:
            # Clean text
            cleaned_text = self._clean_text(text)
            
            # Get word counts
            words = cleaned_text.lower().split()
            word_counts = Counter(words)
            
            # Calculate sentiment scores
            positive_score = self._calculate_positive_score(words)
            negative_score = self._calculate_negative_score(words)
            overall_score = positive_score - negative_score
            
            # Get sentiment category
            sentiment = self._get_sentiment_category(overall_score)
            
            # Get key phrases
            key_phrases = self._extract_key_phrases(cleaned_text)
            
            return {
                "sentiment": sentiment,
                "score": overall_score,
                "positive_score": positive_score,
                "negative_score": negative_score,
                "key_phrases": key_phrases,
                "word_counts": dict(word_counts)
            }
        except Exception as e:
            return {
                "sentiment": "neutral",
                "score": 0,
                "positive_score": 0,
                "negative_score": 0,
                "key_phrases": [],
                "word_counts": {},
                "error": str(e)
            }

    def _clean_text(self, text: str) -> str:
        """Clean text for analysis."""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def _calculate_positive_score(self, words: List[str]) -> float:
        """Calculate positive sentiment score."""
        score = 0.0
        for i, word in enumerate(words):
            if word in self.positive_words:
                # Check for intensifiers
                if i > 0 and words[i-1] in self.intensifiers:
                    score += 2.0
                # Check for negators
                elif i > 0 and words[i-1] in self.negators:
                    score -= 1.0
                else:
                    score += 1.0
        return score

    def _calculate_negative_score(self, words: List[str]) -> float:
        """Calculate negative sentiment score."""
        score = 0.0
        for i, word in enumerate(words):
            if word in self.negative_words:
                # Check for intensifiers
                if i > 0 and words[i-1] in self.intensifiers:
                    score += 2.0
                # Check for negators
                elif i > 0 and words[i-1] in self.negators:
                    score -= 1.0
                else:
                    score += 1.0
        return score

    def _get_sentiment_category(self, score: float) -> str:
        """Get sentiment category based on score."""
        if score > 0.0:
            return "positive"
        elif score < 0.0:
            return "negative"
        else:
            return "neutral"

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text."""
        # Simple implementation - can be enhanced with more sophisticated methods
        words = text.split()
        phrases = []
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if any(word in phrase for word in self.positive_words | self.negative_words):
                phrases.append(phrase)
        return phrases

    def analyze_comments(self, comments: List[str]) -> Dict[str, Any]:
        """Analyze sentiment of multiple comments."""
        try:
            results = [self.analyze_text(comment) for comment in comments]
            
            # Calculate aggregate scores
            total_score = sum(result["score"] for result in results)
            avg_score = total_score / len(comments) if comments else 0
            
            # Count sentiment categories
            sentiment_counts = Counter(result["sentiment"] for result in results)
            
            # Get most common key phrases
            all_phrases = [phrase for result in results for phrase in result["key_phrases"]]
            common_phrases = Counter(all_phrases).most_common(5)
            
            return {
                "total_comments": len(comments),
                "average_score": avg_score,
                "sentiment_distribution": dict(sentiment_counts),
                "most_common_phrases": common_phrases,
                "individual_results": results
            }
        except Exception as e:
            return {
                "total_comments": 0,
                "average_score": 0,
                "sentiment_distribution": {},
                "most_common_phrases": [],
                "individual_results": [],
                "error": str(e)
            } 