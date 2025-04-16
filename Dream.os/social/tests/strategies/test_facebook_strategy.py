"""Tests for Facebook platform strategy."""

import pytest
from unittest import mock
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

from core.strategies.facebook_strategy import FacebookStrategy
from core.exceptions.strategy_exceptions import MissingCredentialsError
from tests.strategies.base_strategy_test import BaseStrategyTest

# Mock setup_logging
@pytest.fixture(autouse=True)
def mock_setup_logging():
    pass

class TestFacebookStrategy(BaseStrategyTest):
    """Test cases for FacebookStrategy."""

    @pytest.fixture
    def strategy(self, mock_driver, mock_config) -> FacebookStrategy:
        """Fixture for FacebookStrategy instance."""
        return FacebookStrategy(mock_driver, mock_config)

    def test_validate_api_credentials_success(self, strategy: FacebookStrategy):
        """Test API credential validation with valid credentials."""
        strategy._validate_api_credentials()  # Should not raise

    def test_validate_api_credentials_missing(self, mock_driver, mock_config):
        """Test API credential validation with missing credentials."""
        mock_config["credentials"]["facebook"] = {}
        strategy = FacebookStrategy(mock_driver, mock_config)
        with pytest.raises(MissingCredentialsError):
            strategy._validate_api_credentials()

    def test_login_success(self, strategy: FacebookStrategy, mock_driver: mock.Mock):
        """Test successful login flow."""
        # Mock successful element interactions
        strategy._safe_send_keys = mock.Mock(return_value=True)
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._wait_for_element = mock.Mock(return_value=True)
        
        assert strategy.login()
        
        # Verify correct sequence of actions
        assert mock_driver.get.called_with("https://www.facebook.com/login")
        assert strategy._safe_send_keys.call_count == 2  # email and password
        assert strategy._safe_click.call_count == 1  # login button
        assert strategy._wait_for_element.called_once_with(
            By.CSS_SELECTOR, "[aria-label='News Feed']"
        )

    def test_login_failure_email(self, strategy: FacebookStrategy, mock_driver: mock.Mock):
        """Test login failure at email step."""
        strategy._safe_send_keys = mock.Mock(return_value=False)
        assert not strategy.login()
        assert strategy._safe_send_keys.call_count == 1

    def test_login_failure_password(self, strategy: FacebookStrategy, mock_driver: mock.Mock):
        """Test login failure at password step."""
        strategy._safe_send_keys = mock.Mock(side_effect=[True, False])
        assert not strategy.login()
        assert strategy._safe_send_keys.call_count == 2

    def test_post_content_success(self, strategy: FacebookStrategy):
        """Test successful content posting."""
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._safe_send_keys = mock.Mock(return_value=True)
        
        assert strategy.post_content("Test post")
        
        assert strategy._safe_click.call_count == 2  # create post and post buttons
        assert strategy._safe_send_keys.call_count == 1  # post text

    def test_post_content_with_media(self, strategy: FacebookStrategy, tmp_path):
        """Test content posting with media files."""
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._safe_send_keys = mock.Mock(return_value=True)
        
        # Create test media file
        media_file = tmp_path / "test.jpg"
        media_file.write_text("test")
        
        assert strategy.post_content("Test post", [str(media_file)])
        
        assert strategy._safe_click.call_count == 3  # create post, photo/video, and post buttons
        assert strategy._safe_send_keys.call_count == 2  # post text and media

    def test_post_content_failure(self, strategy: FacebookStrategy):
        """Test content posting failure."""
        strategy._safe_click = mock.Mock(return_value=False)
        assert not strategy.post_content("Test post")
        assert strategy._safe_click.call_count == 1

    def test_scrape_mentions_success(self, strategy: FacebookStrategy, mock_driver: mock.Mock):
        """Test successful mention scraping."""
        # Mock notification elements
        mock_notifications = [
            mock.Mock(
                find_element=mock.Mock(side_effect=lambda by, value: mock.Mock(
                    text="Test Author" if "link" in value else "Test Post",
                    get_attribute=lambda x: "1704067200" if x == "data-utime" else "123"
                ))
            )
            for _ in range(2)
        ]
        mock_driver.find_elements.return_value = mock_notifications
        
        mentions = strategy.scrape_mentions()
        
        assert len(mentions) == 2
        assert mentions[0]["author"] == "Test Author"
        assert mentions[0]["text"] == "Test Post"
        assert mentions[0]["post_id"] == "123"

    def test_scrape_mentions_with_since(self, strategy: FacebookStrategy, mock_driver: mock.Mock):
        """Test mention scraping with time filter."""
        # Mock notification elements with different timestamps
        mock_notifications = [
            mock.Mock(
                find_element=mock.Mock(side_effect=lambda by, value: mock.Mock(
                    text="Author",
                    get_attribute=lambda x: ts if x == "data-utime" else "id"
                ))
            )
            for ts in ["1704067200", "1703980800"]  # 2024-01-01, 2023-12-31
        ]
        mock_driver.find_elements.return_value = mock_notifications
        
        since = datetime(2024, 1, 1)
        mentions = strategy.scrape_mentions(since)
        
        assert len(mentions) == 1
        assert datetime.fromtimestamp(int(mentions[0]["timestamp"])) >= since

    def test_scrape_mentions_empty(self, strategy: FacebookStrategy, mock_driver: mock.Mock):
        """Test mention scraping with no results."""
        mock_driver.find_elements.return_value = []
        mentions = strategy.scrape_mentions()
        assert len(mentions) == 0

    def test_post_reply_success(self, strategy: FacebookStrategy):
        """Test successful reply posting."""
        strategy.api = mock.Mock()
        strategy.api.post_comment.return_value = {"id": "123"}
        
        result = strategy.post_reply("456", "Test reply")
        
        assert result["id"] == "123"
        strategy.api.post_comment.assert_called_once_with(
            post_id="456",
            message="Test reply"
        )

    def test_analyze_post_sentiment(self, strategy: FacebookStrategy):
        """Test post sentiment analysis."""
        with mock.patch("social.strategies.facebook_strategy.analyze") as mock_analyze:
            mock_analyze.return_value = 0.8
            sentiment = strategy.analyze_post_sentiment("Great post!")
            assert sentiment == 0.8
            mock_analyze.assert_called_once_with("Great post!")

    def test_calculate_engagement_reward(self, strategy: FacebookStrategy):
        """Test engagement reward calculation."""
        engagement_data = {
            "likes": 100,
            "comments": 50,
            "shares": 25,
            "other": 10
        }
        
        reward = strategy.calculate_engagement_reward(engagement_data)
        expected = 100 * 1.0 + 50 * 2.0 + 25 * 3.0 + 10 * 1.0
        assert reward == expected

    def test_render_post_template(self, strategy: FacebookStrategy):
        """Test post template rendering."""
        template_data = {
            "content": "Test post",
            "company_mention": "@testcompany",
            "hashtags": ["#test", "#post"]
        }
        
        rendered = strategy.render_post_template(template_data)
        
        assert '<article class="facebook-post">' in rendered
        assert "Test post" in rendered
        assert "@testcompany" in rendered
        assert "#test #post" in rendered 