"""
Consolidated test utilities and mock classes.
"""

from typing import Any, List, Optional, Dict
from unittest.mock import Mock
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from core.strategies.base_strategy import BaseSocialStrategy
from datetime import datetime
import pytest
import unittest
from unittest.mock import MagicMock, patch
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

class MockWebDriver:
    """Mock Selenium WebDriver for testing."""
    
    def __init__(self, current_url: str = "https://example.com"):
        self.current_url = current_url
        self.page_source = "<html><body>Mock page</body></html>"
        self.title = "Mock Page"
        self._mock_elements: List[MockElement] = []
        
    def get(self, url: str) -> None:
        """Mock navigation to URL."""
        self.current_url = url
        
    def find_element(self, by: str, value: str) -> Any:
        """Mock finding a single element."""
        if not self._mock_elements:
            return MockElement()
        return self._mock_elements[0]
        
    def find_elements(self, by: str, value: str) -> List[Any]:
        """Mock finding multiple elements."""
        return self._mock_elements or [MockElement()]
        
    def add_mock_element(self, element: 'MockElement') -> None:
        """Add a mock element to be returned by find operations."""
        self._mock_elements.append(element)
        
    def clear_mock_elements(self) -> None:
        """Clear all mock elements."""
        self._mock_elements.clear()
        
    def quit(self) -> None:
        """Mock driver cleanup."""
        pass

class MockElement:
    """Mock Selenium WebElement for testing."""
    
    def __init__(
        self,
        text: str = "",
        is_displayed: bool = True,
        attributes: Optional[dict] = None
    ):
        self.text = text
        self._is_displayed = is_displayed
        self._attributes = attributes or {}
        self.click_count = 0
        self.sent_keys: List[str] = []
        
    def click(self) -> None:
        """Mock element click."""
        self.click_count += 1
        
    def send_keys(self, *args) -> None:
        """Mock sending keys to element."""
        self.sent_keys.extend(args)
        
    def is_displayed(self) -> bool:
        """Mock element visibility check."""
        return self._is_displayed
        
    def get_attribute(self, name: str) -> str:
        """Mock getting element attribute."""
        return self._attributes.get(name, "")
        
    def clear(self) -> None:
        """Mock clearing element content."""
        self.text = ""
        self.sent_keys.clear()

class MockResponse:
    """Mock requests.Response for testing."""
    
    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[dict] = None,
        text: str = ""
    ):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        
    def json(self) -> dict:
        """Mock response JSON data."""
        return self._json_data
        
    def raise_for_status(self) -> None:
        """Mock response status check."""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

def create_mock_strategy_config() -> dict:
    """Create a mock configuration for social media strategies."""
    return {
        "username": "test_user",
        "password": "test_pass",
        "api_key": "test_key",
        "api_secret": "test_secret",
        "access_token": "test_token",
        "access_token_secret": "test_token_secret",
        "timeout": 5,
        "max_retries": 2
    }

def simulate_timeout_exception() -> None:
    """Simulate a Selenium TimeoutException."""
    raise TimeoutException("Element not found")

def setup_driver():
    """Create a Chrome WebDriver instance with common options for testing/demos."""
    logging.info("Setting up WebDriver for demo/test...")
    options = webdriver.ChromeOptions()
    # --- Common Options ---
    # options.add_argument("--headless") # Uncomment for headless execution
    options.add_argument("--no-sandbox") # Required for running as root/in containers
    options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems
    options.add_argument("--start-maximized") # Start maximized to ensure elements are visible
    options.add_argument("--disable-blink-features=AutomationControlled") # Helps avoid bot detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # --------------------
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        # Mitigate detection
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        })
        logging.info(f"WebDriver Info: {driver.capabilities['browserName']} {driver.capabilities['browserVersion']}")
        logging.info("WebDriver setup complete.")
        return driver
    except Exception as e:
        logging.error(f"WebDriver setup failed: {e}", exc_info=True)
        raise 

class MockBaseSocialStrategy(BaseSocialStrategy):
    """Mock implementation of BaseSocialStrategy for testing purposes."""

    def __init__(self, driver, config_override: Dict[str, Any]):
        """Initialize the mock strategy."""
        # We don't call super().__init__ here as we are mocking, not inheriting real behavior.
        self.driver = driver # Usually a MockWebDriver instance
        self.config = config_override
        self._source = self.__class__.__name__
        self.timeout = self.config.get("timeout", 10)
        self.max_retries = self.config.get("max_retries", 2)

        # Mock control attributes
        self.mock_login_success = True
        self.mock_create_post_success = True
        self.mock_get_analytics_data = {"impressions": 100, "likes": 10}
        self.mock_check_login_status_return = True
        self.mock_upload_media_success = True
        self.mock_add_tags_success = True
        self.mock_schedule_post_success = True
        self.call_log = [] # Track method calls

        # Simulate logging if needed
        # from utils.logging_utils import log_event
        # log_event("init", f"Initialized Mock {self._source}", {"source": self._source})

    def _log_call(self, method_name: str, **kwargs):
        self.call_log.append({"method": method_name, "args": kwargs, "timestamp": datetime.now()})

    def login(self) -> bool:
        self._log_call("login")
        print(f"[MOCK {self._source}] login() called. Returning: {self.mock_login_success}")
        return self.mock_login_success

    def create_post(self, content: Dict[str, Any]) -> bool:
        self._log_call("create_post", content=content)
        print(f"[MOCK {self._source}] create_post() called with content keys: {list(content.keys())}. Returning: {self.mock_create_post_success}")
        # Simulate interaction based on content if needed
        return self.mock_create_post_success

    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        self._log_call("get_analytics", post_id=post_id)
        print(f"[MOCK {self._source}] get_analytics() called for post_id: {post_id}. Returning: {self.mock_get_analytics_data}")
        return self.mock_get_analytics_data.copy() # Return a copy

    def check_login_status(self) -> bool:
        self._log_call("check_login_status")
        print(f"[MOCK {self._source}] check_login_status() called. Returning: {self.mock_check_login_status_return}")
        return self.mock_check_login_status_return

    def upload_media(self, media_files: List[str]) -> bool:
        self._log_call("upload_media", media_files=media_files)
        print(f"[MOCK {self._source}] upload_media() called with {len(media_files)} files. Returning: {self.mock_upload_media_success}")
        return self.mock_upload_media_success

    def add_tags(self, tags: List[str], textarea_locator=None) -> bool:
        self._log_call("add_tags", tags=tags, textarea_locator=textarea_locator)
        print(f"[MOCK {self._source}] add_tags() called with {len(tags)} tags. Returning: {self.mock_add_tags_success}")
        return self.mock_add_tags_success

    def schedule_post(self, schedule_time: datetime) -> bool:
        self._log_call("schedule_post", schedule_time=schedule_time)
        print(f"[MOCK {self._source}] schedule_post() called for {schedule_time}. Returning: {self.mock_schedule_post_success}")
        return self.mock_schedule_post_success

    # --- Mock Control Methods ---
    def set_mock_login(self, success: bool):
        self.mock_login_success = success

    def set_mock_create_post(self, success: bool):
        self.mock_create_post_success = success

    def set_mock_analytics(self, data: Dict[str, Any]):
        self.mock_get_analytics_data = data

    def reset_call_log(self):
        self.call_log = []

    def get_call_log(self):
        return self.call_log 

# --- Helper Functions for Testing ---

def create_mock_agent_config(agent_id: str = "MockAgent001") -> Dict[str, Any]:
    """Creates a mock configuration dictionary suitable for agent initialization tests."""
    return {
        "agent_id": agent_id,
        "mailbox_base_dir": "./temp_test_mailboxes", # Use temp dir for isolation
        "status_dir": "./temp_test_status",
        "log_level": "DEBUG",
        # Add other relevant agent config defaults
    }

def initialize_mock_strategy(
    strategy_type: str = "twitter",
    mock_driver: Optional[MockWebDriver] = None,
    config_overrides: Optional[Dict[str, Any]] = None
) -> MockBaseSocialStrategy:
    """Initializes a MockBaseSocialStrategy with standard mock config.

    Args:
        strategy_type: Used to potentially customize mock behavior later (e.g., 'twitter', 'facebook')
        mock_driver: Optional pre-configured MockWebDriver.
        config_overrides: Optional dict to override default mock config.

    Returns:
        An instance of MockBaseSocialStrategy.
    """
    driver = mock_driver or MockWebDriver()
    base_config = create_mock_strategy_config() # Uses existing helper
    if config_overrides:
        base_config.update(config_overrides)
    
    # We use MockBaseSocialStrategy directly for simplicity in this example
    # In more complex scenarios, you might have MockTwitterStrategy(MockBaseSocialStrategy), etc.
    mock_strategy = MockBaseSocialStrategy(driver, base_config)
    mock_strategy._source = f"Mock{strategy_type.capitalize()}Strategy" # Give it a mock name
    
    print(f"[TEST HELPER] Initialized {mock_strategy._source}")
    return mock_strategy 