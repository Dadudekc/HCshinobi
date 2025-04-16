import os
import sys
import pytest
from unittest.mock import patch, mock_open, MagicMock

# Add project root to path once at the test suite level
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

@pytest.fixture
def mock_log_event():
    """Shared fixture for mocking log_event function."""
    with patch('dreamforge.core.governance_memory_engine.log_event') as mock:
        yield mock

@pytest.fixture
def mock_file_ops():
    """Shared fixture for mocking file operations."""
    mock_open_fn = mock_open()
    with patch('builtins.open', mock_open_fn):
        with patch('os.makedirs') as mock_makedirs:
            with patch('os.path.exists', return_value=True):
                yield {
                    'open': mock_open_fn,
                    'makedirs': mock_makedirs
                }

@pytest.fixture
def mock_web_driver():
    """Shared fixture for mocking Selenium WebDriver."""
    mock = MagicMock()
    mock.find_element.return_value = MagicMock()
    with patch('social.utils.browser_utils.uc') as mock_uc:
        mock_uc.Chrome = MagicMock(return_value=mock)
        yield mock

@pytest.fixture
def mock_wait():
    """Shared fixture for mocking WebDriverWait."""
    with patch('selenium.webdriver.support.ui.WebDriverWait') as mock:
        mock.return_value.until.return_value = MagicMock()
        yield mock

# Common test data
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpass"
TEST_PROXY = "socks5://localhost:9050"
TEST_USER_AGENT = "Mozilla/5.0 Test Agent"

# Common assertion helpers
def assert_event_structure(event, event_type, source, data):
    """Helper to verify event structure."""
    assert event["type"] == event_type
    assert event["source"] == source
    assert event["data"] == data
    assert "id" in event
    assert "timestamp" in event

# Common test fixtures that can be shared across test files
@pytest.fixture
def test_data_dir():
    """Returns path to test data directory."""
    return os.path.join(os.path.dirname(__file__), 'data')

@pytest.fixture
def snapshot_dir():
    """Returns path to snapshot directory."""
    return os.path.join(os.path.dirname(__file__), 'snapshots') 