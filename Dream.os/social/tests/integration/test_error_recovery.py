import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import time
import logging

# --- Path Setup ---
# Assuming this script is in tests/integration/, go up two levels
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Imports for Testing ---
# Import the agent, specific strategies, and exceptions
from core.agents.social_media_agent import SocialMediaAgent
from core.utils.common import log_event
from core.strategies.strategy_exceptions import LoginError, PostError, ScrapeError, RateLimitError, AuthenticationError
# Import specific selenium/requests exceptions if mocking those
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Test Configuration ---
# Use a non-existent config to force potential loading errors or use defaults
# Or use a minimal valid config for testing specific platforms
TEST_CONFIG_PATH = os.path.join(project_root, "social", "social_config.json") # Assume default config exists
TEST_PLATFORM = "twitter" # Platform to target for most tests

# --- Fixtures --- 
@pytest.fixture(scope="function") # Recreate agent for each test function
def social_agent():
    """Provides a SocialMediaAgent instance for testing."""
    # Use default config path, potentially override mailbox dir for isolation if needed
    agent = SocialMediaAgent(config_path=TEST_CONFIG_PATH)
    # Ensure agent doesn't actually try to run its loop during tests
    yield agent
    # Teardown: Shutdown agent to close driver etc.
    try:
        agent.shutdown()
    except Exception as e:
        print(f"Warning: Error during agent shutdown in fixture: {e}")

@pytest.fixture
def mock_log_event():
    """ Mocks the log_event function to capture calls."""
    # Important: Adjust the target string based on where log_event is IMPORTED in the tested module
    # If SocialMediaAgent imports it as 'from dreamforge.core... import log_event',
    # the target should be 'social.social_media_agent.log_event'
    # If strategies import it directly, target those.
    # Patching in multiple places might be needed depending on test scope.
    with patch('social.social_media_agent.log_event') as mock_log:
        yield mock_log

# --- Test Cases for Error Recovery ---

def test_login_failure_authentication(social_agent: SocialMediaAgent, mock_log_event: MagicMock):
    """ Test recovery when strategy's login raises AuthenticationError."""
    platform = TEST_PLATFORM
    
    # Patch the specific strategy's login method to raise the error
    # Adjust the path based on where the strategy class is defined
    strategy_path = f'social.strategies.{platform}_strategy.{platform.capitalize()}Strategy.login'
    
    with patch(strategy_path, side_effect=AuthenticationError("Invalid password mock")) as mock_login_method:
        # Attempt login via the agent's helper
        success = social_agent.login(platform)
        
        # Assertions
        assert not success, "Agent login should return False on AuthenticationError"
        mock_login_method.assert_called_once()
        
        # Check if specific error logs were generated
        # This requires analyzing the calls made to the mocked log_event
        error_logged = False
        for call_args in mock_log_event.call_args_list:
            args, kwargs = call_args
            event_type = args[0] if args else None
            details = args[2] if len(args) > 2 else {}
            if event_type == "AGENT_ERROR" and details.get("error") == f"Authentication failed for login":
                error_logged = True
                assert "AuthenticationError" in details.get("exception_type", ""), "Log should mention AuthenticationError"
                break
        assert error_logged, "AGENT_ERROR event for AuthenticationError was not logged"

def test_post_failure_rate_limit(social_agent: SocialMediaAgent, mock_log_event: MagicMock):
    """ Test recovery when strategy's post raises RateLimitError."""
    platform = TEST_PLATFORM
    strategy_path = f'social.strategies.{platform}_strategy.{platform.capitalize()}Strategy.post'

    with patch(strategy_path, side_effect=RateLimitError("API rate limit hit mock")) as mock_post_method:
        success = social_agent.post(platform, text="Test post during rate limit")
        
        assert not success, "Agent post should return False on RateLimitError"
        mock_post_method.assert_called_once()
        
        # Check logs for AGENT_WARNING and RateLimitError
        warning_logged = False
        for call_args in mock_log_event.call_args_list:
            args, kwargs = call_args
            event_type = args[0] if args else None
            details = args[2] if len(args) > 2 else {}
            if event_type == "AGENT_WARNING" and "Rate limit likely hit" in details.get("warning", ""):
                warning_logged = True
                assert "RateLimitError" in details.get("exception_type", ""), "Log should mention RateLimitError"
                break
        assert warning_logged, "AGENT_WARNING event for RateLimitError was not logged"

def test_scrape_failure_timeout(social_agent: SocialMediaAgent, mock_log_event: MagicMock):
    """ Test recovery when scraping fails due to a Selenium TimeoutException."""
    platform = TEST_PLATFORM 
    # Assume scraping involves finding an element that times out
    # Need to patch a lower-level method called by the strategy, e.g., driver.find_element
    # This is more complex as the driver is accessed within the strategy.
    # We might need to mock the driver instance itself or patch find_element globally for the test.
    
    # Let's try patching find_element where it might be used in the strategy
    # NOTE: This patch path is an *assumption* and might need adjustment based on actual strategy code.
    # It assumes the strategy instance gets a driver and calls find_element on it.
    # A potentially more robust way is mocking get_undetected_driver when the agent initializes.
    find_element_path = 'selenium.webdriver.remote.webdriver.WebDriver.find_element' 
    
    with patch(find_element_path, side_effect=TimeoutException("Element not found timeout mock")) as mock_find:
        # We need to ensure the strategy is loaded and the driver is initialized *before* the patch might take effect
        # Calling a simple action first might help initialize
        try: social_agent.check_login_status(platform) 
        except: pass # Ignore potential errors during init call

        # Now attempt the scrape action that should fail
        results = social_agent.scrape_mentions(platform)
        
        # Assertions
        assert results == [], "Scrape should return an empty list on TimeoutException recovery"
        # Check if find_element was called (depends on strategy implementation)
        # mock_find.assert_called() # This might be too strict if login status check didn't call it
        
        # Check logs for AGENT_ERROR or AGENT_CRITICAL indicating scrape failure
        scrape_error_logged = False
        for call_args in mock_log_event.call_args_list:
            args, kwargs = call_args
            event_type = args[0] if args else None
            details = args[2] if len(args) > 2 else {}
            # Check for generic scrape error or specific timeout reference
            if event_type in ["AGENT_ERROR", "AGENT_CRITICAL"] and details.get("action") == "scrape_mentions":
                if "TimeoutException" in details.get("exception_type", "") or "TimeoutException" in details.get("exception", ""):
                    scrape_error_logged = True
                    break
        assert scrape_error_logged, "AGENT_ERROR/CRITICAL event for scrape_mentions TimeoutException was not logged"

# --- Add more test cases --- 
# - Test for ScrapeError (e.g., invalid CSS selector -> NoSuchElementException)
# - Test for PostError (e.g., duplicate content simulation)
# - Test for generic Exception during strategy execution
# - Test recovery when _get_or_load_strategy fails (ModuleNotFound, ClassNotFound)
# - Test agent behavior when config file is missing or invalid (might need separate fixture) 