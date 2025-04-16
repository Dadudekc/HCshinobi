"""
Base test classes and utilities for social media strategy testing.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from strategies.base_strategy import BaseStrategy
from utils.logging_utils import log_event

# Import test utilities if needed
from tests.utils.test_utils import MockWebDriver, MockElement

class MockWebDriver:
    """Mock Selenium WebDriver for testing."""
    def __init__(self):
        self.current_url = "https://example.com"
        self.page_source = "<html><body>Mock page</body></html>"
        
    def find_element(self, *args, **kwargs):
        return Mock()
        
    def find_elements(self, *args, **kwargs):
        return [Mock()]
        
    def get(self, url: str) -> None:
        self.current_url = url
        
    def quit(self) -> None:
        pass

class MockElement:
    """Mock Selenium WebElement for testing."""
    def __init__(self, text: str = "", is_displayed: bool = True):
        self.text = text
        self._is_displayed = is_displayed
        
    def click(self) -> None:
        pass
        
    def send_keys(self, *args) -> None:
        pass
        
    def is_displayed(self) -> bool:
        return self._is_displayed
        
    def get_attribute(self, name: str) -> str:
        return ""

class BaseStrategyTest(unittest.TestCase):
    """Base test class for all social media strategy tests."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.driver = MockWebDriver()
        self.config = {
            'username': 'test_user',
            'password': 'test_pass',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'access_token': 'test_token',
            'access_token_secret': 'test_secret'
        }
        
        # Create strategy instance - override in subclass
        self.strategy = None
        
        # Common test data
        self.test_post = {
            'content': 'Test post content',
            'media': [],
            'tags': ['test', 'automation'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Start patches
        self.patches = [
            patch('selenium.webdriver.common.by.By'),
            patch('selenium.webdriver.support.ui.WebDriverWait'),
            patch('selenium.webdriver.support.expected_conditions'),
            patch('utils.common.log_event')
        ]
        self.mocks = [p.start() for p in self.patches]
        
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        for p in self.patches:
            p.stop()
            
        if self.driver:
            self.driver.quit()
            
    def assert_logged_event(self, event_type: str, message: Optional[str] = None) -> None:
        """Assert that a specific event was logged."""
        log_event_mock = self.mocks[-1]  # Last mock is log_event
        log_event_mock.assert_called()
        if message:
            log_event_mock.assert_any_call(event_type, message, ANY)
        else:
            any_matching_call = any(
                call[0][0] == event_type 
                for call in log_event_mock.call_args_list
            )
            self.assertTrue(any_matching_call)
            
    def simulate_element_present(self, locator: tuple, text: str = "") -> None:
        """Simulate an element being present on the page."""
        element = MockElement(text)
        self.mocks[1].return_value.until.return_value = element
        
    def simulate_element_not_found(self, locator: tuple) -> None:
        """Simulate an element not being found on the page."""
        self.mocks[1].return_value.until.side_effect = TimeoutException()
        
    def simulate_login_success(self) -> None:
        """Simulate successful login flow."""
        self.simulate_element_present(('id', 'username'))
        self.simulate_element_present(('id', 'password'))
        self.simulate_element_present(('id', 'login-button'))
        
    def simulate_login_failure(self, error_message: str) -> None:
        """Simulate login failure with error message."""
        self.simulate_element_present(('id', 'error'), error_message)
        
    def simulate_post_success(self) -> None:
        """Simulate successful post creation."""
        self.simulate_element_present(('id', 'post-button'))
        self.simulate_element_present(('id', 'post-success'))
        
    def simulate_post_failure(self, error_message: str) -> None:
        """Simulate post creation failure."""
        self.simulate_element_present(('id', 'error'), error_message) 