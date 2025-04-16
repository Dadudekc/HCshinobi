import pytest
import os
import time
from unittest.mock import patch, MagicMock

# Updated import path
# from social.utils.browser_utils import get_undetected_driver, wait_and_click, wait_and_send_keys
from core.utils.browser_utils import get_undetected_driver, wait_and_click, wait_and_send_keys # Updated

# Mock selenium imports if needed, or assume they are installed
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from social.utils.browser_utils import get_undetected_driver

@pytest.fixture
def mock_uc():
    """Mock undetected_chromedriver."""
    with patch('social.utils.browser_utils.uc') as mock:
        mock.Chrome = MagicMock()
        yield mock

@pytest.fixture
def mock_options():
    """Mock Chrome options."""
    with patch('social.utils.browser_utils.Options') as mock:
        yield mock

def test_get_undetected_driver_headless(mock_uc, mock_options):
    """Test getting headless browser driver."""
    driver = get_undetected_driver(headless=True)
    
    assert driver is not None
    mock_options().add_argument.assert_called_with('--headless')
    mock_uc.Chrome.assert_called_once()

def test_get_undetected_driver_with_proxy(mock_uc, mock_options):
    """Test getting driver with proxy configuration."""
    proxy = "socks5://localhost:9050"
    driver = get_undetected_driver(proxy=proxy)
    
    assert driver is not None
    mock_options().add_argument.assert_called_with(f'--proxy-server={proxy}')
    mock_uc.Chrome.assert_called_once()

def test_get_undetected_driver_with_user_agent(mock_uc, mock_options):
    """Test getting driver with custom user agent."""
    user_agent = "Mozilla/5.0 Test Agent"
    driver = get_undetected_driver(user_agent=user_agent)
    
    assert driver is not None
    mock_options().add_argument.assert_called_with(f'user-agent={user_agent}')
    mock_uc.Chrome.assert_called_once()

def test_get_undetected_driver_all_options(mock_uc, mock_options):
    """Test getting driver with all options configured."""
    proxy = "socks5://localhost:9050"
    user_agent = "Mozilla/5.0 Test Agent"
    driver = get_undetected_driver(
        headless=True,
        proxy=proxy,
        user_agent=user_agent
    )
    
    assert driver is not None
    mock_options().add_argument.assert_any_call('--headless')
    mock_options().add_argument.assert_any_call(f'--proxy-server={proxy}')
    mock_options().add_argument.assert_any_call(f'user-agent={user_agent}')
    mock_uc.Chrome.assert_called_once()

def test_get_undetected_driver_import_error():
    """Test handling of missing undetected_chromedriver package."""
    with patch('social.utils.browser_utils.uc', None):
        driver = get_undetected_driver()
        assert driver is None

def test_get_undetected_driver_chrome_error(mock_uc, mock_options):
    """Test handling of Chrome driver initialization error."""
    mock_uc.Chrome.side_effect = Exception("Chrome error")
    driver = get_undetected_driver()
    assert driver is None

def test_get_undetected_driver_options_error(mock_options):
    """Test handling of Chrome options initialization error."""
    mock_options.side_effect = Exception("Options error")
    driver = get_undetected_driver()
    assert driver is None 