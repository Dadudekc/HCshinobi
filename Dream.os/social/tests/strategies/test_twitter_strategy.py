"""Tests for Twitter platform strategy."""

import pytest
import unittest.mock as mock
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException
)
from datetime import datetime, timezone
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from core.strategies.twitter_strategy import TwitterStrategy
from core.exceptions.strategy_exceptions import MissingCredentialsError, RateLimitError
from tests.strategies.base_strategy_test import BaseStrategyTest

class TestTwitterStrategy(BaseStrategyTest):
    """Test cases for TwitterStrategy."""

    @pytest.fixture
    def strategy(self, mock_driver, mock_config) -> TwitterStrategy:
        """Fixture for TwitterStrategy instance."""
        return TwitterStrategy(mock_driver, mock_config)

    def test_validate_api_credentials_success(self, strategy: TwitterStrategy):
        """Test API credential validation with valid credentials."""
        strategy._validate_api_credentials()  # Should not raise

    def test_validate_api_credentials_missing(self, mock_driver, mock_config):
        """Test API credential validation with missing credentials."""
        mock_config["credentials"]["twitter"] = {}
        strategy = TwitterStrategy(mock_driver, mock_config)
        with pytest.raises(MissingCredentialsError):
            strategy._validate_api_credentials()

    def test_login_success(self, strategy: TwitterStrategy, mock_driver: mock.Mock):
        """Test successful login flow."""
        # Mock successful element interactions
        strategy._safe_send_keys = mock.Mock(return_value=True)
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._wait_for_element = mock.Mock(return_value=True)
        
        assert strategy.login()
        
        # Verify correct sequence of actions
        assert mock_driver.get.called_with("https://twitter.com/login")
        assert strategy._safe_send_keys.call_count == 2  # username and password
        assert strategy._safe_click.call_count == 2  # next and login buttons
        assert strategy._wait_for_element.called_once_with(
            By.CSS_SELECTOR, "[data-testid='SideNav_NewTweet_Button']"
        )

    def test_login_failure_username(self, strategy: TwitterStrategy, mock_driver: mock.Mock):
        """Test login failure at username step."""
        strategy._safe_send_keys = mock.Mock(return_value=False)
        assert not strategy.login()
        assert strategy._safe_send_keys.call_count == 1

    def test_login_failure_password(self, strategy: TwitterStrategy, mock_driver: mock.Mock):
        """Test login failure at password step."""
        strategy._safe_send_keys = mock.Mock(side_effect=[True, False])
        strategy._safe_click = mock.Mock(return_value=True)
        assert not strategy.login()
        assert strategy._safe_send_keys.call_count == 2

    def test_post_content_success(self, strategy: TwitterStrategy):
        """Test successful content posting."""
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._safe_send_keys = mock.Mock(return_value=True)
        
        assert strategy.post_content("Test tweet")
        
        assert strategy._safe_click.call_count == 2  # new tweet and post buttons
        assert strategy._safe_send_keys.call_count == 1  # tweet text

    def test_post_content_with_media(self, strategy: TwitterStrategy, tmp_path):
        """Test content posting with media files."""
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._safe_send_keys = mock.Mock(return_value=True)
        
        # Create test media file
        media_file = tmp_path / "test.jpg"
        media_file.write_text("test")
        
        assert strategy.post_content("Test tweet", [str(media_file)])
        
        assert strategy._safe_click.call_count == 2  # new tweet and post buttons
        assert strategy._safe_send_keys.call_count == 2  # tweet text and media

    def test_post_content_rate_limit(self, strategy: TwitterStrategy):
        """Test rate limit handling during posting."""
        strategy._safe_click = mock.Mock(side_effect=WebDriverException("rate limit exceeded"))
        
        with pytest.raises(RateLimitError):
            strategy.post_content("Test tweet")

    def test_scrape_mentions_success(self, strategy: TwitterStrategy, mock_driver: mock.Mock):
        """Test successful mention scraping."""
        # Mock tweet elements
        mock_tweets = [
            mock.Mock(
                find_element=mock.Mock(side_effect=lambda by, value: mock.Mock(
                    text="Test Author" if "User-Name" in value else "Test Tweet",
                    get_attribute=lambda x: "2024-01-01T00:00:00Z" if x == "datetime" else "123"
                ))
            )
            for _ in range(2)
        ]
        mock_driver.find_elements.return_value = mock_tweets
        
        mentions = strategy.scrape_mentions()
        
        assert len(mentions) == 2
        assert mentions[0]["author"] == "Test Author"
        assert mentions[0]["text"] == "Test Tweet"
        assert mentions[0]["tweet_id"] == "123"

    def test_scrape_mentions_with_since(self, strategy: TwitterStrategy, mock_driver: mock.Mock):
        """Test mention scraping with time filter."""
        # Mock tweet elements with different timestamps
        mock_tweets = [
            mock.Mock(
                find_element=mock.Mock(side_effect=lambda by, value: mock.Mock(
                    text="Author",
                    get_attribute=lambda x: ts if x == "datetime" else "id"
                ))
            )
            for ts in ["2024-01-01T00:00:00Z", "2023-12-31T00:00:00Z"]
        ]
        mock_driver.find_elements.return_value = mock_tweets
        
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mentions = strategy.scrape_mentions(since)
        
        assert len(mentions) == 1
        assert mentions[0]["timestamp"] == "2024-01-01T00:00:00Z"

    def test_scrape_mentions_empty(self, strategy: TwitterStrategy, mock_driver: mock.Mock):
        """Test mention scraping with no results."""
        mock_driver.find_elements.return_value = []
        mentions = strategy.scrape_mentions()
        assert len(mentions) == 0

    def test_post_reply_success(self, strategy: TwitterStrategy):
        """Test successful reply posting."""
        strategy.api = mock.Mock()
        strategy.api.create_reply.return_value = {"id": "123"}
        
        result = strategy.post_reply("456", "Test reply")
        
        assert result["id"] == "123"
        strategy.api.create_reply.assert_called_once_with(
            tweet_id="456",
            text="Test reply"
        )

    def test_analyze_tweet_sentiment(self, strategy: TwitterStrategy):
        """Test tweet sentiment analysis."""
        with mock.patch("social.strategies.twitter_strategy.analyze") as mock_analyze:
            mock_analyze.return_value = 0.8
            sentiment = strategy.analyze_tweet_sentiment("Great tweet!")
            assert sentiment == 0.8
            mock_analyze.assert_called_once_with("Great tweet!")

    def test_detect_and_handle_intermediate_screens(self, strategy: TwitterStrategy):
        """Test intermediate screen detection and handling."""
        # Test phone verification screen
        mock_screen = mock.Mock()
        mock_screen.find_element.return_value = mock.Mock(is_displayed=mock.Mock(return_value=True))
        
        assert strategy._detect_and_handle_intermediate_screens(mock_screen)
        mock_screen.find_element.assert_called_with("name", "phone_number")

        # Test email verification screen
        mock_screen.find_element.side_effect = [
            WebDriverException(),  # phone field not found
            Mock(is_displayed=Mock(return_value=True))  # email field found
        ]
        assert strategy._detect_and_handle_intermediate_screens(mock_screen)

    def test_render_tweet_template(self, strategy: TwitterStrategy):
        """Test tweet template rendering."""
        template_data = {
            "content": "Test tweet",
            "hashtags": ["#test", "#tweet"]
        }
        
        rendered = strategy.render_tweet_template(template_data)
        assert rendered == "Test tweet\n\n#test #tweet" 