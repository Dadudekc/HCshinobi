import unittest
import os
import sys
from unittest.mock import patch, MagicMock
import pytest
from unittest import mock
import logging

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # tests/strategies
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Modules/Classes to test or use
# Need to handle potential import errors if NLTK isn't installed/downloaded
try:
    from core.strategies.twitter_strategy import TwitterStrategy
    from core.strategies.reddit_strategy import RedditStrategy
    from core.utils.sentiment_analyzer import analyze_sentiment # Assuming location
    # Attempt to instantiate analyzer to trigger potential NLTK download check early
    _analyzer_test_instance = analyze_sentiment()
    _SENTIMENT_READY = True
except ImportError as e:
    print(f"[TestSentimentAnalysis] Warning: Failed to import modules or init SentimentAnalyzer ({e}). Skipping tests.")
    _SENTIMENT_READY = False
except Exception as nltk_e: # Catch potential NLTK download errors
    print(f"[TestSentimentAnalysis] Warning: Failed during SentimentAnalyzer init (NLTK download issue? {nltk_e}). Skipping tests.")
    _SENTIMENT_READY = False

# Define Benchmark Data and Expected Ranges
# (Sentence, expected_compound_range, expected_dominant_category)
# Ranges are approximate and depend heavily on VADER's scoring.
BENCHMARK_DATA = [
    ("This is a great and wonderful day!", (0.7, 1.0), 'pos'),
    ("I love this product, it's amazing.", (0.6, 1.0), 'pos'),
    ("What a horrible, terrible, awful experience.", (-1.0, -0.6), 'neg'),
    ("I hate waiting in line, it's the worst.", (-1.0, -0.5), 'neg'),
    ("The weather is okay today.", (-0.2, 0.4), 'neu'), # Neutral can be tricky
    ("This document contains facts.", (-0.1, 0.1), 'neu'),
    ("It was not bad, but not great either.", (-0.4, 0.5), 'neu'), # Mixed sentiment
    ("I am uncertain about the future.", (-0.5, 0.1), 'neu'), # Negative leaning neutral
    ("Sunshine and rainbows, pure joy!", (0.8, 1.0), 'pos'),
    ("This is utterly disgusting and repulsive.", (-1.0, -0.7), 'neg'),
]

@unittest.skipUnless(_SENTIMENT_READY, "Sentiment analysis dependencies not ready")
class TestSentimentAnalysisIntegration(unittest.TestCase):

    def setUp(self):
        """Instantiate analyzer for tests."""
        # Use the class directly for Reddit-like tests
        self.analyzer = analyze_sentiment()
        
        # Mock dependencies for TwitterStrategy instantiation
        self.mock_config = {"common_settings": {}}
        self.mock_driver = MagicMock()
        # Patch logger within the TwitterStrategy module if necessary
        with patch('core.strategies.twitter_strategy.log_event'):
             self.twitter_strategy = TwitterStrategy(self.mock_config, self.mock_driver)
        # Ensure the analyzer exists on the strategy instance
        self.assertIsNotNone(self.twitter_strategy.sentiment_analyzer, "TwitterStrategy should have a sentiment analyzer")

    def test_direct_sentiment_analysis_benchmarks(self):
        """Test SentimentAnalyzer directly against benchmarks."""
        for text, (min_compound, max_compound), expected_category in BENCHMARK_DATA:
            with self.subTest(text=text):
                scores = self.analyzer.analyze(text)
                self.assertIsNotNone(scores, f"Analyzer returned None for: {text}")
                self.assertIsInstance(scores, dict)
                self.assertIn('compound', scores)
                self.assertIn('pos', scores)
                self.assertIn('neu', scores)
                self.assertIn('neg', scores)
                
                # Check compound score range
                self.assertGreaterEqual(scores['compound'], min_compound, f"Compound score {scores['compound']} below range for: {text}")
                self.assertLessEqual(scores['compound'], max_compound, f"Compound score {scores['compound']} above range for: {text}")
                
                # Check dominant category (simple version)
                # This is a basic check, real sentiment might be more nuanced
                dominant_score = max(scores['pos'], scores['neu'], scores['neg'])
                dominant_cat = 'neu' # Default to neutral
                if scores['pos'] == dominant_score and scores['pos'] > 0.1:
                    dominant_cat = 'pos'
                elif scores['neg'] == dominant_score and scores['neg'] > 0.1:
                    dominant_cat = 'neg'
                
                # Allow some flexibility for neutral range, especially if compound is near zero
                if expected_category == 'neu' and abs(scores['compound']) < 0.2:
                     pass # Accept if compound score is close to zero for expected neutral
                else:
                     self.assertEqual(dominant_cat, expected_category, f"Dominant category mismatch for: {text} (Got {dominant_cat}, Expected {expected_category}, Scores: {scores})")

    def test_twitter_strategy_sentiment_integration(self):
        """Test sentiment analysis as used within TwitterStrategy parsing."""
        # We call _parse_tweet_article, mocking the element finding
        for text, (min_compound, max_compound), _ in BENCHMARK_DATA:
             with self.subTest(text=text):
                 # Mock the article element and its find_element results
                 mock_article = MagicMock()
                 mock_text_element = MagicMock()
                 mock_text_element.text = text
                 
                 # Simulate finding necessary elements (URL, Author, Text, Time)
                 mock_url_link = MagicMock()
                 mock_url_link.get_attribute.return_value = f"https://twitter.com/user/status/123?text={text[:10]}" # Include text snippet for debug
                 mock_author_link = MagicMock()
                 mock_author_link.get_attribute.return_value = "https://twitter.com/testuser"
                 mock_time_element = MagicMock()
                 mock_time_element.get_attribute.return_value = "2023-01-01T12:00:00Z"

                 # Configure find_element mock based on selector tuple
                 def find_element_side_effect(*args):
                     selector_tuple = args[0] # Selector is the first argument
                     # Use string representation for easier matching if needed
                     # selector_str = str(selector_tuple)
                     if selector_tuple == self.twitter_strategy.selectors.TWEET_URL_LINK:
                         return mock_url_link
                     elif selector_tuple == self.twitter_strategy.selectors.TWEET_AUTHOR_LINK:
                         return mock_author_link
                     elif selector_tuple == self.twitter_strategy.selectors.TWEET_TEXT_DIV:
                         return mock_text_element
                     elif selector_tuple == self.twitter_strategy.selectors.TWEET_TIMESTAMP:
                         return mock_time_element
                     else:
                         raise unittest.mock.Mock.failure(f"Unexpected find_element call with: {selector_tuple}")
                 mock_article.find_element = MagicMock(side_effect=find_element_side_effect)

                 # Call the parsing method
                 with patch('core.strategies.twitter_strategy.log_event'): # Mock logging within parse
                      parsed_data = self.twitter_strategy._parse_tweet_article(mock_article)
                 
                 self.assertIsNotNone(parsed_data, f"Parsing failed for text: {text}")
                 self.assertIn('sentiment', parsed_data)
                 scores = parsed_data['sentiment']
                 self.assertIsNotNone(scores)
                 self.assertGreaterEqual(scores['compound'], min_compound, f"Compound score {scores['compound']} below range for: {text}")
                 self.assertLessEqual(scores['compound'], max_compound, f"Compound score {scores['compound']} above range for: {text}")

    # Note: RedditStrategy test is covered by test_direct_sentiment_analysis_benchmarks
    # as it uses SentimentAnalyzer directly in the current implementation.
    # If RedditStrategy were to embed the logic differently, a separate test like
    # test_twitter_strategy_sentiment_integration would be needed.

if __name__ == '__main__':
    unittest.main() 