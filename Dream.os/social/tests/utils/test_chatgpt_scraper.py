"""Tests for the ChatGPT web scraper."""
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException
)
from utils.chatgpt_scraper import ChatGPTScraper, CHATGPT_URL

@pytest.fixture
def mock_driver():
    """Fixture providing a mock Selenium WebDriver."""
    driver = MagicMock()
    driver.get_cookies.return_value = [{"name": "test", "value": "test"}]
    return driver

@pytest.fixture
def mock_webdriver():
    """Fixture providing a mock undetected-chromedriver."""
    with patch('utils.chatgpt_scraper.uc') as mock_uc:
        mock_uc.Chrome.return_value = mock_driver()
        yield mock_uc

@pytest.fixture
def temp_cookie_file(tmp_path):
    """Fixture providing a temporary cookie file path."""
    return str(tmp_path / "test_cookies.json")

@pytest.fixture
def valid_cookies():
    """Fixture providing valid cookie data."""
    return [
        {
            "name": "session",
            "value": "test_session",
            "domain": ".chat.openai.com",
            "sameSite": "None"
        }
    ]

class TestChatGPTScraper:
    def test_initialization(self, temp_cookie_file):
        """Test scraper initialization."""
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        assert scraper.cookie_file == temp_cookie_file
        assert not scraper.headless
        assert scraper.driver is None
        assert scraper.wait is None
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_initialization"})

    def test_context_manager(self, mock_webdriver, temp_cookie_file):
        """Test context manager functionality."""
        with ChatGPTScraper(cookie_file=temp_cookie_file) as scraper:
            assert scraper.driver is not None
            assert scraper.wait is not None
        # Should call cleanup
        scraper.driver.quit.assert_called_once()
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_context_manager"})

    def test_setup_browser_success(self, mock_webdriver, temp_cookie_file):
        """Test successful browser setup."""
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.setup_browser()
        
        assert scraper.driver is not None
        assert scraper.wait is not None
        mock_webdriver.Chrome.assert_called_once()
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_setup_browser_success"})

    def test_setup_browser_failure(self, mock_webdriver, temp_cookie_file):
        """Test browser setup failure."""
        mock_webdriver.Chrome.side_effect = WebDriverException("Failed to start")
        
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        with pytest.raises(WebDriverException):
            scraper.setup_browser()
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_setup_browser_failure"})

    def test_cleanup_success(self, mock_driver, temp_cookie_file):
        """Test successful cleanup."""
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        scraper.cleanup()
        mock_driver.quit.assert_called_once()
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_cleanup_success"})

    def test_cleanup_failure(self, mock_driver, temp_cookie_file):
        """Test cleanup with driver error."""
        mock_driver.quit.side_effect = WebDriverException("Quit failed")
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        scraper.cleanup()  # Should handle error gracefully
        mock_driver.quit.assert_called_once()
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_cleanup_failure"})

    def test_save_cookies_success(self, mock_driver, temp_cookie_file, valid_cookies):
        """Test successful cookie saving."""
        mock_driver.get_cookies.return_value = valid_cookies
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.save_cookies()
        
        assert success
        assert os.path.exists(temp_cookie_file)
        with open(temp_cookie_file) as f:
            saved_cookies = json.load(f)
            assert saved_cookies == valid_cookies
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_save_cookies_success"})

    def test_save_cookies_failure(self, mock_driver, temp_cookie_file):
        """Test cookie saving failure."""
        mock_driver.get_cookies.side_effect = WebDriverException("Failed to get cookies")
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.save_cookies()
        
        assert not success
        assert not os.path.exists(temp_cookie_file)
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_save_cookies_failure"})

    def test_load_cookies_success(self, mock_driver, temp_cookie_file, valid_cookies):
        """Test successful cookie loading."""
        # Create cookie file
        os.makedirs(os.path.dirname(temp_cookie_file), exist_ok=True)
        with open(temp_cookie_file, 'w') as f:
            json.dump(valid_cookies, f)
            
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.load_cookies()
        
        assert success
        mock_driver.add_cookie.assert_called()
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_load_cookies_success"})

    def test_load_cookies_missing_file(self, mock_driver, temp_cookie_file):
        """Test cookie loading with missing file."""
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.load_cookies()
        
        assert not success
        mock_driver.add_cookie.assert_not_called()
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_load_cookies_missing_file"})

    def test_inject_jquery_success(self, mock_driver, temp_cookie_file):
        """Test successful jQuery injection."""
        mock_driver.execute_script.side_effect = [None, True]  # Script injection, jQuery check
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.inject_jquery()
        
        assert success
        assert mock_driver.execute_script.call_count == 2
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_inject_jquery_success"})

    def test_inject_jquery_failure(self, mock_driver, temp_cookie_file):
        """Test jQuery injection failure."""
        mock_driver.execute_script.side_effect = WebDriverException("Script error")
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.inject_jquery()
        
        assert not success
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_inject_jquery_failure"})

    def test_scroll_and_capture_chats_success(self, mock_driver, temp_cookie_file):
        """Test successful chat capture."""
        mock_tiles = [
            Mock(text="Chat 1", find_element=Mock(return_value=Mock(
                get_attribute=Mock(side_effect=["url1", "timestamp1"])
            ))),
            Mock(text="Chat 2", find_element=Mock(return_value=Mock(
                get_attribute=Mock(side_effect=["url2", "timestamp2"])
            )))
        ]
        mock_driver.find_elements.return_value = mock_tiles
        mock_driver.execute_script.return_value = True
        
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        chats = scraper.scroll_and_capture_chats()
        
        assert len(chats) == 2
        assert all(c["title"] in ["Chat 1", "Chat 2"] for c in chats)
        assert all(c["url"] in ["url1", "url2"] for c in chats)
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_scroll_and_capture_chats_success"})

    def test_scroll_and_capture_chats_empty(self, mock_driver, temp_cookie_file):
        """Test chat capture with no chats found."""
        mock_driver.find_elements.return_value = []
        mock_driver.execute_script.return_value = True
        
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        chats = scraper.scroll_and_capture_chats()
        
        assert len(chats) == 0
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_scroll_and_capture_chats_empty"})

    def test_run_scraper_success(self, mock_driver, temp_cookie_file):
        """Test successful scraper run."""
        mock_driver.get.return_value = None
        mock_driver.find_elements.return_value = [
            Mock(text="Chat 1", find_element=Mock(return_value=Mock(
                get_attribute=Mock(side_effect=["url1", "timestamp1"])
            )))
        ]
        
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.run_scraper(output_file=str(temp_cookie_file).replace("cookies", "chats"))
        
        assert success
        mock_driver.get.assert_called_once_with(CHATGPT_URL)
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_run_scraper_success"})

    def test_run_scraper_navigation_error(self, mock_driver, temp_cookie_file):
        """Test scraper run with navigation error."""
        mock_driver.get.side_effect = WebDriverException("Navigation failed")
        
        scraper = ChatGPTScraper(cookie_file=temp_cookie_file)
        scraper.driver = mock_driver
        
        success = scraper.run_scraper()
        
        assert not success
        mock_driver.get.assert_called_once_with(CHATGPT_URL)
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_run_scraper_navigation_error"})

    @pytest.mark.integration
    def test_integration_full_workflow(self, mock_webdriver, temp_cookie_file):
        """Integration test for full scraper workflow."""
        with ChatGPTScraper(cookie_file=temp_cookie_file) as scraper:
            mock_driver = scraper.driver
            mock_driver.find_elements.return_value = [
                Mock(text="Chat 1", find_element=Mock(return_value=Mock(
                    get_attribute=Mock(side_effect=["url1", "timestamp1"])
                )))
            ]
            
            success = scraper.run_scraper(
                model_append="?model=gpt-4",
                output_file=str(temp_cookie_file).replace("cookies", "chats")
            )
            
            assert success
            mock_driver.get.assert_called_once_with(CHATGPT_URL + "?model=gpt-4")
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_integration_full_workflow"})

if __name__ == '__main__':
    pytest.main([__file__]) 