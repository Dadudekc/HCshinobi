"""Tests for Twitter platform strategy."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException
import time
import asyncio
import aiohttp
from contextlib import asynccontextmanager
import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.exceptions import (
    MissingCredentialsError,
    RateLimitError,
    AuthenticationError,
    LoginError,
    PostError,
    ScrapeError,
    NetworkError,
    SessionError
)
from core.strategies.twitter_strategy import TwitterStrategy
from core.services.feedback_engine import FeedbackEngine
from tests.social.strategies.base_strategy_test import BaseStrategyTest

# Test configuration
@pytest.fixture
def mock_config():
    """Fixture for valid Twitter configuration."""
    return {
        "credentials": {
            "twitter": {
                "api_key": "test_key",
                "api_secret": "test_secret",
                "access_token": "test_token",
                "access_token_secret": "test_token_secret"
            }
        }
    }

@pytest.fixture
def mock_api():
    """Fixture for mocked Twitter API client."""
    return Mock()

@pytest.fixture
def strategy(mock_config, mock_api):
    """Fixture for initialized TwitterStrategy."""
    strategy = TwitterStrategy(mock_config)
    strategy.api = mock_api
    return strategy

@pytest.fixture
def snapshot_dir(request):
    """Fixture for snapshot directory."""
    return os.path.join(os.path.dirname(__file__), "snapshots")

def save_snapshot(snapshot_dir, name, data):
    """Save snapshot data to file."""
    os.makedirs(snapshot_dir, exist_ok=True)
    path = os.path.join(snapshot_dir, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_snapshot(snapshot_dir, name):
    """Load snapshot data from file."""
    path = os.path.join(snapshot_dir, f"{name}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def test_init_with_valid_credentials(mock_config):
    """Test successful initialization with valid credentials."""
    strategy = TwitterStrategy(mock_config)
    assert strategy.config == mock_config
    assert isinstance(strategy.feedback_engine, FeedbackEngine)

def test_init_with_missing_credentials():
    """Test initialization fails with missing credentials."""
    invalid_config = {"credentials": {"twitter": {}}}
    with pytest.raises(MissingCredentialsError) as exc_info:
        TwitterStrategy(invalid_config)
    assert "Missing required Twitter credentials" in str(exc_info.value)

class TestTwitterStrategy(BaseStrategyTest):
    """Test suite for Twitter platform strategy."""
    
    strategy_class = TwitterStrategy
    platform_name = "twitter"
    required_credentials = [
        "api_key",
        "api_secret",
        "access_token",
        "access_token_secret"
    ]

    def test_post_tweet_success(self, strategy):
        """Test successful tweet posting."""
        expected_response = {"id": "123", "text": "Test tweet"}
        strategy.api.create_tweet.return_value = expected_response
        
        result = strategy.post_tweet("Test tweet")
        
        strategy.api.create_tweet.assert_called_once_with(text="Test tweet")
        assert result == expected_response

    def test_post_tweet_rate_limit(self, strategy):
        """Test handling of rate limit error during tweet posting."""
        strategy.api.create_tweet.side_effect = Exception("Rate limit exceeded")
        
        with pytest.raises(RateLimitError) as exc_info:
            strategy.post_tweet("Test tweet")
        
        assert "Rate limit exceeded" in str(exc_info.value)

    def test_post_reply_success(self, strategy):
        """Test successful reply posting."""
        expected_response = {"id": "456", "text": "Test reply"}
        strategy.api.create_reply.return_value = expected_response
        
        result = strategy.post_reply("123", "Test reply")
        
        strategy.api.create_reply.assert_called_once_with(tweet_id="123", text="Test reply")
        assert result == expected_response

    @patch('core.strategies.twitter_strategy.analyze')
    def test_analyze_tweet_sentiment(self, mock_analyze, strategy):
        """Test sentiment analysis of tweet text."""
        mock_analyze.return_value = 0.8
        
        result = strategy.analyze_tweet_sentiment("Great tweet!")
        
        mock_analyze.assert_called_once_with("Great tweet!")
        assert result == 0.8

    def test_detect_and_handle_intermediate_screens_phone(self, strategy):
        """Test detection of phone number verification screen."""
        mock_screen = Mock()
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_screen.find_element.return_value = mock_element
        
        result = strategy._detect_and_handle_intermediate_screens(mock_screen)
        
        assert result is True
        mock_screen.find_element.assert_called_with("name", "phone_number")

    def test_detect_and_handle_intermediate_screens_email(self, strategy):
        """Test detection of email verification screen."""
        mock_screen = Mock()
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_screen.find_element.side_effect = [
            Exception("No phone field"),  # First call fails
            mock_element  # Second call succeeds
        ]
        
        result = strategy._detect_and_handle_intermediate_screens(mock_screen)
        
        assert result is True
        assert mock_screen.find_element.call_args_list[1] == [("name", "email")]

    def test_detect_and_handle_intermediate_screens_no_screens(self, strategy):
        """Test when no intermediate screens are present."""
        mock_screen = Mock()
        mock_screen.find_element.side_effect = Exception("No elements found")
        
        result = strategy._detect_and_handle_intermediate_screens(mock_screen)
        
        assert result is False

    def test_render_tweet_template(self, strategy, snapshot_dir):
        """Test rendering tweet content from template."""
        template_data = {
            "content": "Hello Twitter!",
            "hashtags": ["#python", "#testing"]
        }
        
        self.verify_template_rendering(
            strategy=strategy,
            template_data=template_data,
            snapshot_name="tweet_template",
            snapshot_dir=snapshot_dir
        )

    def test_render_tweet_template_no_hashtags(self, strategy, snapshot_dir):
        """Test rendering tweet content without hashtags."""
        template_data = {
            "content": "Hello Twitter!"
        }
        
        self.verify_template_rendering(
            strategy=strategy,
            template_data=template_data,
            snapshot_name="tweet_template_no_hashtags",
            snapshot_dir=snapshot_dir
        )

    def test_render_tweet_template_empty_content(self, strategy):
        """Test rendering tweet template with empty content."""
        template_data = {
            "content": "",
            "hashtags": ["#test"]
        }
        
        result = strategy.render_tweet_template(template_data)
        assert result == "\n\n#test"

    def test_render_tweet_template_missing_content(self, strategy):
        """Test rendering tweet template with missing content key."""
        template_data = {
            "hashtags": ["#test"]
        }
        
        with pytest.raises(KeyError) as exc_info:
            strategy.render_tweet_template(template_data)
        assert "content" in str(exc_info.value)

    def test_post_tweet_with_max_length(self, strategy):
        """Test posting tweet with maximum allowed length."""
        long_text = "x" * 280  # Twitter's max length
        strategy.api.create_tweet.return_value = {"id": "123", "text": long_text}
        
        result = strategy.post_tweet(long_text)
        assert result["text"] == long_text
        strategy.api.create_tweet.assert_called_once_with(text=long_text)

def test_feedback_on_rate_limit(strategy):
    """Test feedback is properly recorded on rate limit."""
    strategy.api.create_tweet.side_effect = Exception("Rate limit exceeded")
    
    try:
        strategy.post_tweet("Test tweet")
    except RateLimitError:
        pass
    
    feedback_data = strategy.feedback_engine.feedback_data
    assert len(feedback_data) == 1
    assert feedback_data[0]["strategy"] == "twitter"
    assert feedback_data[0]["severity"] == "high"
    assert feedback_data[0]["message"] == "Rate limit exceeded" 