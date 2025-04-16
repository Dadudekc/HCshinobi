"""Base test class for strategy tests."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from typing import Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

from core.strategies.base_strategy import BaseSocialStrategy as BaseStrategy
from core.exceptions.strategy_exceptions import StrategyError

class MockStrategy(BaseStrategy):
    """Mock strategy for testing base functionality."""
    
    def login(self) -> bool:
        return True
        
    def post_content(self, content: str, media_files=None) -> bool:
        return True
        
    def scrape_mentions(self, since=None):
        return []

class BaseStrategyTest:
    """Base test class for all strategy tests."""
    
    @pytest.fixture
    def mock_config(self) -> Dict[str, Any]:
        """Fixture for mock configuration."""
        return {
            "username": "test_user",
            "password": "test_pass",
            "timeout": 5,
            "max_retries": 2,
            "credentials": {
                "twitter": {
                    "api_key": "test_key",
                    "api_secret": "test_secret",
                    "access_token": "test_token",
                    "access_token_secret": "test_token_secret"
                },
                "facebook": {
                    "app_id": "test_app_id",
                    "app_secret": "test_app_secret",
                    "access_token": "test_token"
                },
                "linkedin": {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "access_token": "test_token"
                }
            }
        }

    @pytest.fixture
    def mock_driver(self) -> Mock:
        """Fixture for mock WebDriver."""
        driver = Mock(spec=WebDriver)
        driver.find_element.return_value = Mock()
        driver.find_elements.return_value = []
        return driver

    @pytest.fixture
    def strategy(self, mock_driver: Mock, mock_config: Dict[str, Any]) -> BaseStrategy:
        """Fixture for strategy instance."""
        return MockStrategy(mock_driver, mock_config)

    def test_init_with_valid_config(self, strategy: BaseStrategy):
        """Test strategy initialization with valid config."""
        assert strategy.driver is not None
        assert strategy.config is not None
        assert strategy.timeout == 5
        assert strategy.max_retries == 2

    def test_init_with_missing_config(self, mock_driver: Mock):
        """Test strategy initialization with missing config."""
        with pytest.raises(StrategyError):
            MockStrategy(mock_driver, {})

    def test_validate_media_files_success(self, strategy: BaseStrategy, tmp_path):
        """Test media file validation with valid files."""
        # Create temp test files
        file1 = tmp_path / "test1.jpg"
        file2 = tmp_path / "test2.png"
        file1.write_text("test1")
        file2.write_text("test2")
        
        files = [str(file1), str(file2)]
        valid_files = strategy._validate_media_files(files)
        assert valid_files == files

    def test_validate_media_files_missing(self, strategy: BaseStrategy):
        """Test media file validation with missing files."""
        with pytest.raises(StrategyError):
            strategy._validate_media_files(["nonexistent.jpg"])

    def test_wait_for_element_success(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test successful element wait."""
        mock_driver.find_element.return_value = Mock()
        assert strategy._wait_for_element(By.ID, "test_id")

    def test_wait_for_element_timeout(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test element wait timeout."""
        mock_driver.find_element.side_effect = TimeoutException()
        assert not strategy._wait_for_element(By.ID, "test_id")

    def test_safe_click_success(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test successful element click."""
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        assert strategy._safe_click(By.ID, "test_id")
        mock_element.click.assert_called_once()

    def test_safe_click_retry_success(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test successful click after retry."""
        mock_element = Mock()
        mock_element.click.side_effect = [WebDriverException(), None]
        mock_driver.find_element.return_value = mock_element
        assert strategy._safe_click(By.ID, "test_id")
        assert mock_element.click.call_count == 2

    def test_safe_click_failure(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test click failure after max retries."""
        mock_element = Mock()
        mock_element.click.side_effect = WebDriverException()
        mock_driver.find_element.return_value = mock_element
        assert not strategy._safe_click(By.ID, "test_id")
        assert mock_element.click.call_count == strategy.max_retries

    def test_safe_send_keys_success(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test successful key sending."""
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        assert strategy._safe_send_keys(By.ID, "test_id", "test_text")
        mock_element.send_keys.assert_called_once_with("test_text")

    def test_safe_send_keys_retry_success(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test successful key sending after retry."""
        mock_element = Mock()
        mock_element.send_keys.side_effect = [WebDriverException(), None]
        mock_driver.find_element.return_value = mock_element
        assert strategy._safe_send_keys(By.ID, "test_id", "test_text")
        assert mock_element.send_keys.call_count == 2

    def test_safe_send_keys_failure(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test key sending failure after max retries."""
        mock_element = Mock()
        mock_element.send_keys.side_effect = WebDriverException()
        mock_driver.find_element.return_value = mock_element
        assert not strategy._safe_send_keys(By.ID, "test_id", "test_text")
        assert mock_element.send_keys.call_count == strategy.max_retries

    def test_extract_error_details_success(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test successful error details extraction."""
        mock_driver.title = "Error Page"
        mock_driver.current_url = "https://test.com/error"
        mock_driver.page_source = "<html>Error message</html>"
        mock_driver.find_elements.return_value = [
            Mock(text="Error 1"),
            Mock(text="Error 2")
        ]
        
        message, details = strategy._extract_error_details()
        assert "Error 1 | Error 2" == message
        assert "Error Page" == details["title"]
        assert "https://test.com/error" == details["url"]
        assert len(details["error_messages"]) == 2

    def test_extract_error_details_failure(self, strategy: BaseStrategy, mock_driver: Mock):
        """Test error details extraction with WebDriver exception."""
        mock_driver.title.side_effect = WebDriverException("Driver error")
        message, details = strategy._extract_error_details()
        assert "Driver error" == message
        assert "traceback" in details 