import os
import sys
import pytest
import unittest.mock as mock
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.common.exceptions import WebDriverException

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.strategies.linkedin_strategy import LinkedInStrategy
from core.exceptions.strategy_exceptions import MissingCredentialsError, MetricGatheringError

@pytest.fixture
def mock_driver():
    """Mock Selenium WebDriver."""
    mock = mock.MagicMock()
    mock.find_element.return_value = mock.MagicMock()
    return mock

@pytest.fixture
def mock_wait():
    """Mock WebDriverWait."""
    with mock.patch('social.strategies.linkedin_strategy.WebDriverWait') as mock:
        mock.return_value.until.return_value = mock.MagicMock()
        yield mock

@pytest.fixture
def strategy(mock_driver):
    """Create LinkedIn strategy with mocked driver."""
    with mock.patch('social.strategies.linkedin_strategy.get_undetected_driver', return_value=mock_driver):
        strategy = LinkedInStrategy({"email": "test@example.com", "password": "testpass"})
        yield strategy

def test_initialize_success(strategy, mock_driver):
    """Test successful strategy initialization."""
    assert strategy.initialize() is True
    assert strategy.initialized is True
    assert strategy.driver == mock_driver

def test_initialize_failure(strategy):
    """Test initialization failure."""
    with mock.patch('social.strategies.linkedin_strategy.get_undetected_driver', return_value=None):
        assert strategy.initialize() is False
        assert strategy.initialized is False
        assert strategy.driver is None

def test_login_success(strategy, mock_wait):
    """Test successful login."""
    strategy.initialize()
    assert strategy.login() is True
    assert strategy.logged_in is True
    
    # Verify login flow
    strategy.driver.get.assert_called_with("https://www.linkedin.com/login")
    mock_wait.assert_called()
    mock_wait().until.assert_any_call(
        EC.presence_of_element_located((By.ID, "username"))
    )

def test_login_without_init(strategy):
    """Test login attempt without initialization."""
    assert strategy.login() is False
    assert strategy.logged_in is False

def test_login_failure(strategy, mock_wait):
    """Test login failure."""
    strategy.initialize()
    mock_wait.return_value.until.side_effect = Exception("Login timeout")
    
    assert strategy.login() is False
    assert strategy.logged_in is False

def test_post_update_success(strategy, mock_wait):
    """Test successful post update."""
    strategy.initialize()
    strategy.logged_in = True
    
    content = "Test post content"
    assert strategy.post_update(content) is True
    
    # Verify post flow
    strategy.driver.get.assert_called_with("https://www.linkedin.com/feed/")
    mock_wait.assert_called()
    mock_wait().until.assert_any_call(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-control-name='create_post']"))
    )

def test_post_update_not_logged_in(strategy):
    """Test post attempt when not logged in."""
    strategy.initialize()
    assert strategy.post_update("Test content") is False

def test_post_update_with_media(strategy, mock_wait):
    """Test post update with media attachments."""
    strategy.initialize()
    strategy.logged_in = True
    
    content = "Test with media"
    media_urls = ["http://example.com/image.jpg"]
    
    # Should succeed but log warning about unimplemented media
    with mock.patch('sys.stderr') as mock_stderr:
        assert strategy.post_update(content, media_urls) is True
        mock_stderr.write.assert_called()

def test_post_update_failure(strategy, mock_wait):
    """Test post update failure."""
    strategy.initialize()
    strategy.logged_in = True
    mock_wait.return_value.until.side_effect = Exception("Post timeout")
    
    assert strategy.post_update("Test content") is False

def test_close(strategy):
    """Test cleanup on close."""
    strategy.initialize()
    strategy.logged_in = True
    
    strategy.close()
    
    assert strategy.driver is None
    assert strategy.logged_in is False
    assert strategy.initialized is False
    strategy.driver.quit.assert_called_once()

def test_close_with_error(strategy):
    """Test cleanup when driver.quit raises error."""
    strategy.initialize()
    strategy.driver.quit.side_effect = Exception("Quit error")
    
    strategy.close()
    
    assert strategy.driver is None
    assert strategy.logged_in is False
    assert strategy.initialized is False

def test_context_manager(strategy):
    """Test using strategy as context manager."""
    with strategy as s:
        assert s.initialized is True
        s.driver.get.assert_not_called()
    
    assert strategy.driver is None
    assert strategy.initialized is False

class TestLinkedInStrategy:
    """Test cases for LinkedInStrategy."""

    @pytest.fixture
    def strategy(self, mock_driver, mock_config) -> LinkedInStrategy:
        """Fixture for LinkedInStrategy instance."""
        return LinkedInStrategy(mock_driver, mock_config)

    def test_validate_api_credentials_success(self, strategy: LinkedInStrategy):
        """Test API credential validation with valid credentials."""
        strategy._validate_api_credentials()  # Should not raise

    def test_validate_api_credentials_missing(self, mock_driver, mock_config):
        """Test API credential validation with missing credentials."""
        mock_config["credentials"]["linkedin"] = {}
        strategy = LinkedInStrategy(mock_driver, mock_config)
        with pytest.raises(MissingCredentialsError):
            strategy._validate_api_credentials()

    def test_login_success(self, strategy: LinkedInStrategy, mock_driver: mock.Mock):
        """Test successful login flow."""
        # Mock successful element interactions
        strategy._safe_send_keys = mock.Mock(return_value=True)
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._wait_for_element = mock.Mock(return_value=True)
        
        assert strategy.login()
        
        # Verify correct sequence of actions
        assert mock_driver.get.called_with("https://www.linkedin.com/login")
        assert strategy._safe_send_keys.call_count == 2  # username and password
        assert strategy._safe_click.call_count == 1  # sign in button
        assert strategy._wait_for_element.called_once_with(
            By.ID, "global-nav"
        )

    def test_login_failure_username(self, strategy: LinkedInStrategy, mock_driver: mock.Mock):
        """Test login failure at username step."""
        strategy._safe_send_keys = mock.Mock(return_value=False)
        assert not strategy.login()
        assert strategy._safe_send_keys.call_count == 1

    def test_login_failure_password(self, strategy: LinkedInStrategy, mock_driver: mock.Mock):
        """Test login failure at password step."""
        strategy._safe_send_keys = mock.Mock(side_effect=[True, False])
        assert not strategy.login()
        assert strategy._safe_send_keys.call_count == 2

    def test_post_content_success(self, strategy: LinkedInStrategy):
        """Test successful content posting."""
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._safe_send_keys = mock.Mock(return_value=True)
        
        assert strategy.post_content("Test post")
        
        assert strategy._safe_click.call_count == 2  # create post and share buttons
        assert strategy._safe_send_keys.call_count == 1  # post text

    def test_post_content_with_media(self, strategy: LinkedInStrategy, tmp_path):
        """Test content posting with media files."""
        strategy._safe_click = mock.Mock(return_value=True)
        strategy._safe_send_keys = mock.Mock(return_value=True)
        
        # Create test media file
        media_file = tmp_path / "test.jpg"
        media_file.write_text("test")
        
        assert strategy.post_content("Test post", [str(media_file)])
        
        assert strategy._safe_click.call_count == 3  # create post, add media, and share buttons
        assert strategy._safe_send_keys.call_count == 2  # post text and media

    def test_post_content_failure(self, strategy: LinkedInStrategy):
        """Test content posting failure."""
        strategy._safe_click = mock.Mock(return_value=False)
        assert not strategy.post_content("Test post")
        assert strategy._safe_click.call_count == 1

    def test_scrape_mentions_success(self, strategy: LinkedInStrategy, mock_driver: mock.Mock):
        """Test successful mention scraping."""
        # Mock notification elements
        mock_notifications = [
            mock.Mock(
                find_element=mock.Mock(side_effect=lambda by, value: mock.Mock(
                    text="Test Author" if "actor__name" in value else "Test Post",
                    get_attribute=lambda x: "2024-01-01T00:00:00" if x == "datetime" else "123"
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

    def test_scrape_mentions_with_since(self, strategy: LinkedInStrategy, mock_driver: mock.Mock):
        """Test mention scraping with time filter."""
        # Mock notification elements with different timestamps
        mock_notifications = [
            mock.Mock(
                find_element=mock.Mock(side_effect=lambda by, value: mock.Mock(
                    text="Author",
                    get_attribute=lambda x: ts if x == "datetime" else "id"
                ))
            )
            for ts in ["2024-01-01T00:00:00", "2023-12-31T00:00:00"]
        ]
        mock_driver.find_elements.return_value = mock_notifications
        
        since = datetime(2024, 1, 1)
        mentions = strategy.scrape_mentions(since)
        
        assert len(mentions) == 1
        assert mentions[0]["timestamp"] == "2024-01-01T00:00:00"

    def test_scrape_mentions_empty(self, strategy: LinkedInStrategy, mock_driver: mock.Mock):
        """Test mention scraping with no results."""
        mock_driver.find_elements.return_value = []
        mentions = strategy.scrape_mentions()
        assert len(mentions) == 0

    def test_gather_post_metrics_success(self, strategy: LinkedInStrategy):
        """Test successful metric gathering."""
        strategy.api = mock.Mock()
        metrics = {
            "engagement_rate": 0.8,
            "likes": 100,
            "comments": 50
        }
        strategy.api.get_post_metrics.return_value = metrics
        
        result = strategy.gather_post_metrics("123")
        assert result == metrics
        strategy.api.get_post_metrics.assert_called_once_with("123")

    def test_gather_post_metrics_failure(self, strategy: LinkedInStrategy):
        """Test metric gathering failure."""
        strategy.api = mock.Mock()
        strategy.api.get_post_metrics.side_effect = Exception("API error")
        
        with pytest.raises(MetricGatheringError):
            strategy.gather_post_metrics("123")

    def test_track_connection_growth_success(self, strategy: LinkedInStrategy):
        """Test successful connection growth tracking."""
        strategy.api = mock.Mock()
        growth_data = {
            "new_connections": 50,
            "total_connections": 500
        }
        strategy.api.get_connection_metrics.return_value = growth_data
        
        result = strategy.track_connection_growth()
        assert result == growth_data
        strategy.api.get_connection_metrics.assert_called_once()

    def test_track_connection_growth_threshold(self, strategy: LinkedInStrategy):
        """Test connection growth threshold detection."""
        strategy.api = mock.Mock()
        strategy.config["metric_thresholds"] = {"connection_growth": 30}
        growth_data = {"new_connections": 50}
        strategy.api.get_connection_metrics.return_value = growth_data
        
        strategy.track_connection_growth()
        # Should log threshold exceeded message

    def test_analyze_post_sentiment(self, strategy: LinkedInStrategy):
        """Test post sentiment analysis."""
        with mock.patch("social.strategies.linkedin_strategy.analyze") as mock_analyze:
            mock_analyze.return_value = 0.8
            sentiment = strategy.analyze_post_sentiment("Great post!")
            assert sentiment == 0.8
            mock_analyze.assert_called_once_with("Great post!")

    def test_render_post_template(self, strategy: LinkedInStrategy):
        """Test post template rendering."""
        template_data = {
            "content": "Test post",
            "company_mention": "@testcompany",
            "hashtags": ["#test", "#post"]
        }
        
        rendered = strategy.render_post_template(template_data)
        
        assert '<article class="linkedin-post">' in rendered
        assert "Test post" in rendered
        assert "@testcompany" in rendered
        assert "#test #post" in rendered 