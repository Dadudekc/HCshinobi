import pytest
import os
import json
import time
from unittest.mock import patch, MagicMock, call

# Updated import path
# from social_media_agent import SocialMediaAgent
from core.agents.social_media_agent import SocialMediaAgent
# Import exceptions used by the agent
# from strategy_exceptions import (
#     StrategyError, LoginError, PostError, ScrapeError, AuthenticationError, RateLimitError, ContentError
# )
from core.exceptions.strategy_exceptions import (
    StrategyError, LoginError, PostError, ScrapeError, AuthenticationError, RateLimitError, ContentError
)

# Assuming constants are moved
# from constants import AGENT_ID, DEFAULT_MAILBOX_BASE_DIR_NAME
from core.constants import AGENT_ID_SOCIAL_MEDIA as AGENT_ID, DEFAULT_MAILBOX_BASE_DIR_NAME

import unittest
from unittest.mock import patch, MagicMock
import sys

# Add project root to sys.path to allow importing social_media_agent
script_dir = os.path.dirname(__file__) # tests/
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels to D:/Dream.os/
# Check if the path is already there to avoid duplicates
if project_root not in sys.path:
    # Find the 'social' directory specifically if nested deeper
    # This assumes 'social' is directly under project_root
    social_dir = os.path.join(project_root, 'social')
    if os.path.isdir(social_dir) and social_dir not in sys.path:
         sys.path.insert(0, social_dir) # Add social directory first
    # Add the main project root if needed for other imports like governance
    if project_root not in sys.path:
         sys.path.insert(0, project_root) # Then add project root


# Dynamically determine the import path based on directory structure
# Assuming this test file is in /d:/Dream.os/social/tests/
# And the agent is in /d:/Dream.os/social/
try:
    from social_media_agent import SocialMediaAgent
except ImportError:
    # If the direct import fails (e.g., due to complex paths or workspace structure)
    # Fallback or raise an error
    print("Error: Could not import SocialMediaAgent. Check sys.path and file locations.")
    # As a simple fallback, try relative if structure allows, but direct is preferred
    # from ..social_media_agent import SocialMediaAgent # Example relative import
    sys.exit(1) # Exit if import fails, tests cannot run


class TestSocialMediaAgent(unittest.TestCase):

    @patch('social_media_agent.MailboxHandler') # Patch MailboxHandler where it's used in social_media_agent.py
    @patch('social_media_agent._load_config') # Mock config loading
    @patch('social_media_agent.log_event') # Mock governance logging
    def setUp(self, mock_log_event, mock_load_config, MockMailboxHandler):
        """Set up test environment before each test."""
        # Configure the mock config
        self.mock_config_data = {
            "platforms": {
                "twitter": {
                    "enabled": True,
                    # Add other necessary mock config details if needed by agent init
                }
            },
            "common_settings": {
                "timeout_seconds": 10
            }
        }
        mock_load_config.return_value = self.mock_config_data

        # Configure the mock MailboxHandler instance
        self.mock_mailbox_instance = MockMailboxHandler.return_value
        self.mock_mailbox_instance.get_message.return_value = None # Default: no messages
        self.mock_mailbox_instance.send_response.return_value = True # Assume sending is successful

        # Store mock constructor for assertions
        self.MockMailboxHandler = MockMailboxHandler
        
        # Use a temporary directory for user_data_dir if needed, or mock its usage
        self.test_user_data_dir = "test_chrome_data" 
        self.test_mailbox_base = "test_mailbox"

        # Create the agent instance
        # The MailboxHandler import within SocialMediaAgent will now use the mock
        self.agent = SocialMediaAgent(
            config_path="dummy_config.json", 
            user_data_dir=self.test_user_data_dir,
            mailbox_base_dir=self.test_mailbox_base
        )
        
        # Store mocks for potential use in tests
        self.mock_log_event = mock_log_event
        self.mock_load_config = mock_load_config


    def test_agent_initialization_loads_config(self):
        """Test that the agent loads configuration during initialization."""
        # Check if _load_config was called by __init__
        self.mock_load_config.assert_called_once_with("dummy_config.json")
        self.assertEqual(self.agent.config, self.mock_config_data)

    def test_agent_initialization_initializes_mailbox(self):
        """Test that the agent initializes MailboxHandler during __init__."""
        # Check if MailboxHandler was instantiated
        self.MockMailboxHandler.assert_called_once()
        
        # Check if it was called with the correct base paths derived from mailbox_base_dir
        expected_inbox = os.path.join(self.test_mailbox_base, "inbox")
        expected_outbox = os.path.join(self.test_mailbox_base, "outbox")
        self.MockMailboxHandler.assert_called_once_with(expected_inbox, expected_outbox)

        # Check if the agent stored the instance
        self.assertEqual(self.agent.mailbox_handler, self.mock_mailbox_instance)

    def test_process_incoming_message_valid_login(self):
        """Test processing a valid LOGIN command."""
        # Mock the agent's login method
        self.agent.login = MagicMock(return_value=True) 
        
        # Create a sample message
        test_message = {
            "message_id": "test-msg-001",
            "sender": "SupervisorTest",
            "command": "login",
            "platform": "twitter"
        }
        
        # Process the message
        self.agent.process_incoming_message(test_message)
        
        # Assertions
        self.agent.login.assert_called_once_with("twitter")
        # Check that send_response was called with 'completed'
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['type'], "RESPONSE")
        self.assertEqual(response_message['payload']['status'], "completed")
        self.assertEqual(response_message['payload']['original_command'], "login")
        self.assertEqual(response_message['payload']['original_platform'], "twitter")
        self.assertEqual(response_message['response_to'], "test-msg-001")
        self.mock_log_event.assert_not_called() # No error logging expected

    def test_process_incoming_message_unknown_command(self):
        """Test processing a message with an unknown command."""
        # Create a sample message
        test_message = {
            "message_id": "test-msg-002",
            "sender": "SupervisorTest",
            "command": "fly_to_moon",
            "platform": "rocket"
        }
        
        # Process the message
        self.agent.process_incoming_message(test_message)
        
        # Assertions
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "error")
        self.assertIn("Unknown command: fly_to_moon", response_message['payload']['error_details'])
        self.assertEqual(response_message['response_to'], "test-msg-002")
        
        # Check that an error/warning was logged
        self.mock_log_event.assert_called()
        log_call_args, _ = self.mock_log_event.call_args
        self.assertIn("AGENT_WARNING", log_call_args) # Check event type
        self.assertIn("Unknown mailbox command", log_call_args[2].get("warning")) # Check details
        self.assertEqual(log_call_args[2].get("command"), "fly_to_moon")

    def test_process_incoming_message_valid_post(self):
        """Test processing a valid POST command with text."""
        # Mock the agent's post method
        self.agent.post = MagicMock(return_value=True)

        # Create a sample message
        test_message = {
            "message_id": "test-msg-003",
            "sender": "SupervisorTest",
            "command": "post",
            "platform": "twitter",
            "details": {
                "text": "Hello World!"
            }
        }

        # Process the message
        self.agent.process_incoming_message(test_message)

        # Assertions
        self.agent.post.assert_called_once_with(
            "twitter", 
            text="Hello World!", 
            image_path=None, 
            use_governance_context=False, 
            # We expect empty kwargs if none provided in message
        )
        # Check that send_response was called with 'completed'
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "completed")
        self.assertEqual(response_message['response_to'], "test-msg-003")
        self.mock_log_event.assert_not_called() # No warning/error logs expected

    def test_process_incoming_message_missing_command(self):
        """Test processing a message that is missing the 'command' field."""
        # Create a malformed message
        test_message = {
            "message_id": "test-msg-004",
            "sender": "SupervisorTest",
            # No 'command' field
            "platform": "twitter",
            "details": {
                "text": "This message is broken"
            }
        }

        # Process the message
        self.agent.process_incoming_message(test_message)

        # Assertions
        # Should not attempt any agent actions like post/login
        self.agent.post.assert_not_called()
        self.agent.login.assert_not_called()
        
        # Check that send_response was called with 'error'
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "error")
        self.assertIn("Message missing 'command' field", response_message['payload']['error_details'])
        self.assertEqual(response_message['response_to'], "test-msg-004")
        
        # Check that a warning was logged
        self.mock_log_event.assert_called()
        log_call_args, _ = self.mock_log_event.call_args
        self.assertIn("AGENT_WARNING", log_call_args)
        self.assertIn("Received message missing command", log_call_args[2].get("warning"))

    def test_process_incoming_message_scrape_mentions(self):
        """Test processing a valid SCRAPE_MENTIONS command."""
        # Mock the agent's scrape_mentions method
        mock_mention_results = [
            {"id": "m1", "text": "Mention 1", "author": "userA"},
            {"id": "m2", "text": "Mention 2", "author": "userB"}
        ]
        self.agent.scrape_mentions = MagicMock(return_value=mock_mention_results)

        # Create a sample message
        test_message = {
            "message_id": "test-msg-005",
            "sender": "AnalyzerAgent",
            "command": "scrape_mentions",
            "platform": "twitter",
            "details": {
                "max_mentions": 15 # Example detail
            }
        }

        # Process the message
        self.agent.process_incoming_message(test_message)

        # Assertions
        self.agent.scrape_mentions.assert_called_once_with("twitter", max_mentions=15)
        
        # Check that send_response was called with 'completed' and results
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "completed")
        self.assertEqual(response_message['payload']['original_command'], "scrape_mentions")
        self.assertIn('results', response_message['payload'])
        self.assertEqual(response_message['payload']['results']['mention_count'], 2)
        self.assertEqual(response_message['payload']['results']['mentions'], mock_mention_results)
        self.assertEqual(response_message['response_to'], "test-msg-005")
        self.mock_log_event.assert_not_called() # No warning/error logs expected

    def test_process_incoming_message_check_login_status(self):
        """Test processing a valid CHECK_LOGIN_STATUS command."""
        # Mock the agent's check_login_status method
        self.agent.check_login_status = MagicMock(return_value=True) # Simulate logged in

        # Create a sample message
        test_message = {
            "message_id": "test-msg-006",
            "sender": "MonitorAgent",
            "command": "check_login_status",
            "platform": "twitter"
        }

        # Process the message
        self.agent.process_incoming_message(test_message)

        # Assertions
        self.agent.check_login_status.assert_called_once_with("twitter")
        
        # Check response
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "completed")
        self.assertEqual(response_message['payload']['original_command'], "check_login_status")
        self.assertIn('results', response_message['payload'])
        self.assertEqual(response_message['payload']['results'], {"logged_in": True})
        self.assertEqual(response_message['response_to'], "test-msg-006")
        self.mock_log_event.assert_not_called()

    def test_process_incoming_message_scrape_trends(self):
        """Test processing a valid SCRAPE_TRENDS command."""
        # Mock the agent's scrape_trends method
        mock_trend_results = [
            {"name": "#TestTrend", "volume": "10K Posts"},
            {"name": "#AnotherTrend", "volume": "5.2K Tweets"}
        ]
        self.agent.scrape_trends = MagicMock(return_value=mock_trend_results)

        # Create a sample message
        test_message = {
            "message_id": "test-msg-007",
            "sender": "MarketAnalyzer",
            "command": "scrape_trends",
            "platform": "twitter",
            "details": {
                "region": "UK" # Example detail
            }
        }

        # Process the message
        self.agent.process_incoming_message(test_message)

        # Assertions
        self.agent.scrape_trends.assert_called_once_with("twitter", region="UK")
        
        # Check response
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "completed")
        self.assertEqual(response_message['payload']['original_command'], "scrape_trends")
        self.assertIn('results', response_message['payload'])
        self.assertEqual(response_message['payload']['results']['trend_count'], 2)
        self.assertEqual(response_message['payload']['results']['trends'], mock_trend_results)
        self.assertEqual(response_message['payload']['results']['region'], "UK")
        self.assertEqual(response_message['response_to'], "test-msg-007")
        self.mock_log_event.assert_not_called()

    def test_process_incoming_message_scrape_community(self):
        """Test processing a valid SCRAPE_COMMUNITY command."""
        # Mock the agent's scrape_community method
        mock_community_posts = [
            {"id": "p1", "text": "Post 1 in community", "author": "userC"},
            {"id": "p2", "text": "Post 2...", "author": "userD"}
        ]
        self.agent.scrape_community = MagicMock(return_value=mock_community_posts)

        # Create a sample message
        test_message = {
            "message_id": "test-msg-008",
            "sender": "CommunityMonitor",
            "command": "scrape_community",
            "platform": "reddit", # Example platform
            "details": {
                "community_id": "r/DreamOS",
                "max_posts": 50
            }
        }

        # Process the message
        self.agent.process_incoming_message(test_message)

        # Assertions
        self.agent.scrape_community.assert_called_once_with("reddit", community_id="r/DreamOS", max_posts=50)
        
        # Check response
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "completed")
        self.assertEqual(response_message['payload']['original_command'], "scrape_community")
        self.assertIn('results', response_message['payload'])
        self.assertEqual(response_message['payload']['results']['post_count'], 2)
        self.assertEqual(response_message['payload']['results']['posts'], mock_community_posts)
        self.assertEqual(response_message['payload']['results']['community_id'], "r/DreamOS")
        self.assertEqual(response_message['payload']['results']['max_posts'], 50)
        self.assertEqual(response_message['response_to'], "test-msg-008")
        self.mock_log_event.assert_not_called()

    def test_process_incoming_message_agent_status(self):
        """Test processing the AGENT_STATUS command."""
        # Preload a mock strategy to test status reporting
        self.agent.strategies['twitter'] = MagicMock() # Add a mock strategy instance

        # Create a sample message
        test_message = {
            "message_id": "test-msg-009",
            "sender": "Supervisor",
            "command": "agent_status",
            # No platform needed for this command
        }

        # Process the message
        self.agent.process_incoming_message(test_message)

        # Assertions
        # Check response
        self.mock_mailbox_instance.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_instance.send_message.call_args
        response_message = call_args[0]
        self.assertEqual(response_message['payload']['status'], "completed")
        self.assertEqual(response_message['payload']['original_command'], "agent_status")
        self.assertIn('results', response_message['payload'])
        results = response_message['payload']['results']
        self.assertEqual(results['agent_id'], self.agent.agent_id)
        self.assertIn('twitter', results['loaded_strategies']) # Check if preloaded strategy is listed
        self.assertEqual(response_message['response_to'], "test-msg-009")
        self.mock_log_event.assert_not_called()

    # --- Tests for internal methods like driver init, strategy loading ---

    @patch('social_media_agent.get_undetected_driver')
    def test_initialize_driver_success(self, mock_get_driver):
        """Test successful initialization of the Selenium driver."""
        mock_driver_instance = MagicMock()
        mock_get_driver.return_value = mock_driver_instance
        
        # Reset agent's driver state for this test
        self.agent.driver = None 
        
        # Call the internal method
        driver = self.agent._initialize_driver()
        
        self.assertEqual(driver, mock_driver_instance)
        self.assertEqual(self.agent.driver, mock_driver_instance)
        mock_get_driver.assert_called_once_with(user_data_dir=self.agent.user_data_dir)
        self.mock_log_event.assert_not_called() # No errors expected

    @patch('social_media_agent.get_undetected_driver')
    def test_initialize_driver_failure(self, mock_get_driver):
        """Test handling failure during driver initialization."""
        # Simulate get_undetected_driver raising an exception
        mock_get_driver.side_effect = Exception("WebDriver Error")
        
        # Reset agent's driver state
        self.agent.driver = None

        # Call the internal method and expect it to raise
        with self.assertRaises(Exception) as cm:
            self.agent._initialize_driver()
            
        self.assertIn("WebDriver Error", str(cm.exception))
        self.assertIsNone(self.agent.driver) # Driver should remain None
        # Check that the error was logged
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertIn("AGENT_ERROR", call_args)
        self.assertIn("Driver initialization failed", call_args[2].get("error"))

    @patch('social_media_agent.importlib.import_module')
    @patch('social_media_agent.SocialMediaAgent._initialize_driver') # Mock driver init within strategy load
    def test_get_or_load_strategy_success_first_time(self, mock_init_driver, mock_import_module):
        """Test successfully loading a strategy for the first time."""
        platform = "twitter"
        mock_driver_instance = MagicMock()
        mock_init_driver.return_value = mock_driver_instance
        
        # Mock the strategy class and its instantiation
        mock_strategy_instance = MagicMock()
        mock_strategy_class = MagicMock(return_value=mock_strategy_instance)
        # Configure import_module to return a module containing the mock class
        mock_module = MagicMock()
        mock_module.TwitterStrategy = mock_strategy_class # Class name must match expected
        mock_import_module.return_value = mock_module

        # Ensure strategy is not already loaded
        self.agent.strategies = {}

        # Call the method
        strategy = self.agent._get_or_load_strategy(platform)

        # Assertions
        self.assertEqual(strategy, mock_strategy_instance)
        self.assertIn(platform, self.agent.strategies)
        self.assertEqual(self.agent.strategies[platform], mock_strategy_instance)
        # Verify import_module was called correctly
        expected_module_path = f"social.strategies.{platform}_strategy"
        mock_import_module.assert_called_once_with(expected_module_path)
        # Verify strategy class was instantiated with config and driver
        mock_strategy_class.assert_called_once_with(self.agent.config, mock_driver_instance)
        # Verify driver was initialized
        mock_init_driver.assert_called_once()
        # Verify logging
        self.mock_log_event.assert_called_with("STRATEGY_LOADED", self.agent.agent_id, {"platform": platform})

    def test_get_or_load_strategy_already_loaded(self):
        """Test getting a strategy that has already been loaded."""
        platform = "twitter"
        # Pre-load a mock strategy instance
        mock_existing_instance = MagicMock()
        self.agent.strategies[platform] = mock_existing_instance

        # Mock import_module to ensure it's NOT called
        with patch('social_media_agent.importlib.import_module') as mock_import_module:
            # Call the method
            strategy = self.agent._get_or_load_strategy(platform)
            
            # Assertions
            self.assertEqual(strategy, mock_existing_instance)
            mock_import_module.assert_not_called()
            # Ensure driver init is also not called again
            with patch('social_media_agent.SocialMediaAgent._initialize_driver') as mock_init_driver:
                 self.agent._get_or_load_strategy(platform) # Call again to check driver init
                 mock_init_driver.assert_not_called()
            self.mock_log_event.assert_not_called() # No loading logs expected

    @patch('social_media_agent.importlib.import_module')
    def test_get_or_load_strategy_module_not_found(self, mock_import_module):
        """Test handling ModuleNotFoundError when loading a strategy."""
        platform = "nonexistent"
        # Configure import_module to raise ModuleNotFoundError
        mock_import_module.side_effect = ModuleNotFoundError(f"No module named '{platform}'")

        # Ensure strategy is not already loaded
        self.agent.strategies = {}
        
        # Call the method
        strategy = self.agent._get_or_load_strategy(platform)
        
        # Assertions
        self.assertIsNone(strategy)
        self.assertNotIn(platform, self.agent.strategies)
        mock_import_module.assert_called_once()
        # Verify error logging
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertIn("AGENT_ERROR", call_args)
        self.assertIn("Strategy module not found", call_args[2].get("error"))
        self.assertEqual(call_args[2].get("platform"), platform)

    # --- Tests for Agent facade methods (calling strategies) ---

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_post_method_success(self, mock_get_strategy):
        """Test the agent's top-level post method successfully calls the strategy."""
        platform = "twitter"
        mock_strategy = MagicMock()
        mock_strategy.post.return_value = True # Simulate successful strategy post
        mock_get_strategy.return_value = mock_strategy
        
        post_text = "Agent Post Test"
        post_image = "path/to/image.jpg"
        post_kwargs = {"extra_arg": "value"}
        
        # Call the agent's post method
        success = self.agent.post(platform, text=post_text, image_path=post_image, **post_kwargs)
        
        self.assertTrue(success)
        # Verify strategy was loaded/retrieved
        mock_get_strategy.assert_called_once_with(platform)
        # Verify the strategy's post method was called with correct args
        mock_strategy.post.assert_called_once_with(
            text=post_text, 
            image_path=post_image, 
            use_governance_context=False, # Default unless specified
            extra_arg="value" # Check kwargs are passed
        )
        # Verify logging
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "PLATFORM_POST")
        self.assertEqual(call_args[2]["platform"], platform)
        self.assertTrue(call_args[2]["success"])
        self.assertEqual(call_args[2]["strategy_kwargs"], post_kwargs)

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_post_method_strategy_load_fails(self, mock_get_strategy):
        """Test agent post method when strategy loading fails."""
        platform = "twitter"
        mock_get_strategy.return_value = None # Simulate failure to load strategy
        
        success = self.agent.post(platform, text="Test")
        
        self.assertFalse(success)
        mock_get_strategy.assert_called_once_with(platform)
        # Verify error logging for failed strategy load
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "AGENT_ERROR")
        self.assertEqual(call_args[2]["error"], "Failed to load strategy for post")
        self.assertEqual(call_args[2]["platform"], platform)

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_post_method_strategy_post_fails(self, mock_get_strategy):
        """Test agent post method when the strategy's post action fails."""
        platform = "twitter"
        mock_strategy = MagicMock()
        mock_strategy.post.side_effect = Exception("API Error") # Simulate strategy error
        mock_get_strategy.return_value = mock_strategy
        
        with self.assertLogs(level='ERROR') as log_cm: # Optional: Check print output
            success = self.agent.post(platform, text="Test")

        self.assertFalse(success)
        mock_get_strategy.assert_called_once_with(platform)
        mock_strategy.post.assert_called_once()
        # Verify error logging for the post failure
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "AGENT_ERROR")
        self.assertEqual(call_args[2]["error"], "Post method failed")
        self.assertEqual(call_args[2]["platform"], platform)
        self.assertIn("API Error", call_args[2]["details"])

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_scrape_mentions_success(self, mock_get_strategy):
        """Test the agent's scrape_mentions method successfully calls the strategy."""
        platform = "twitter"
        mock_strategy = MagicMock()
        mock_mention_data = [{"id": "m1"}]
        # Ensure the mock strategy HAS the method
        mock_strategy.scrape_mentions = MagicMock(return_value=mock_mention_data)
        mock_get_strategy.return_value = mock_strategy
        
        max_m = 10
        mentions = self.agent.scrape_mentions(platform, max_mentions=max_m)
        
        self.assertEqual(mentions, mock_mention_data)
        mock_get_strategy.assert_called_once_with(platform)
        mock_strategy.scrape_mentions.assert_called_once_with(max_m)
        # Verify logging
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "PLATFORM_SCRAPE")
        self.assertEqual(call_args[2]["platform"], platform)
        self.assertEqual(call_args[2]["type"], "mentions")
        self.assertEqual(call_args[2]["count"], 1)

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_scrape_mentions_strategy_missing_method(self, mock_get_strategy):
        """Test agent scrape_mentions when the strategy doesn't support it."""
        platform = "facebook" # Assume facebook strategy exists but lacks scrape_mentions
        mock_strategy = MagicMock()
        # Explicitly delete the method from the mock instance
        del mock_strategy.scrape_mentions 
        mock_get_strategy.return_value = mock_strategy
        
        mentions = self.agent.scrape_mentions(platform)
        
        self.assertEqual(mentions, []) # Should return empty list
        mock_get_strategy.assert_called_once_with(platform)
        # Verify warning logged
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "AGENT_WARNING")
        self.assertEqual(call_args[2]["warning"], "Scrape mentions not supported")
        self.assertEqual(call_args[2]["platform"], platform)

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_scrape_mentions_strategy_fails(self, mock_get_strategy):
        """Test agent scrape_mentions when the strategy method raises an error."""
        platform = "twitter"
        mock_strategy = MagicMock()
        mock_strategy.scrape_mentions.side_effect = Exception("Scraping Error")
        mock_get_strategy.return_value = mock_strategy
        
        mentions = self.agent.scrape_mentions(platform)
        
        self.assertEqual(mentions, []) # Should return empty list on error
        mock_get_strategy.assert_called_once_with(platform)
        mock_strategy.scrape_mentions.assert_called_once()
        # Verify error logging
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "AGENT_ERROR")
        self.assertEqual(call_args[2]["error"], "Scrape mentions failed")
        self.assertIn("Scraping Error", call_args[2]["details"])

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_scrape_trends_success(self, mock_get_strategy):
        """Test the agent's scrape_trends method successfully calls the strategy."""
        platform = "twitter"
        mock_strategy = MagicMock()
        mock_trend_data = [{"name": "#Trend1"}]
        mock_strategy.scrape_trends = MagicMock(return_value=mock_trend_data)
        mock_get_strategy.return_value = mock_strategy
        
        kwargs = {"region": "US"}
        trends = self.agent.scrape_trends(platform, **kwargs)
        
        self.assertEqual(trends, mock_trend_data)
        mock_get_strategy.assert_called_once_with(platform)
        mock_strategy.scrape_trends.assert_called_once_with(**kwargs)
        # Verify logging
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "PLATFORM_SCRAPE")
        self.assertEqual(call_args[2]["type"], "trends")
        self.assertEqual(call_args[2]["count"], 1)
        self.assertEqual(call_args[2]["kwargs"], kwargs)

    @patch('social_media_agent.SocialMediaAgent._get_or_load_strategy')
    def test_agent_scrape_community_success(self, mock_get_strategy):
        """Test the agent's scrape_community method successfully calls the strategy."""
        platform = "reddit"
        mock_strategy = MagicMock()
        mock_post_data = [{"id": "p1"}]
        mock_strategy.scrape_community = MagicMock(return_value=mock_post_data)
        mock_get_strategy.return_value = mock_strategy
        
        kwargs = {"community_id": "r/test", "max_posts": 5}
        posts = self.agent.scrape_community(platform, **kwargs)
        
        self.assertEqual(posts, mock_post_data)
        mock_get_strategy.assert_called_once_with(platform)
        mock_strategy.scrape_community.assert_called_once_with(**kwargs)
        # Verify logging
        self.mock_log_event.assert_called_once()
        call_args, _ = self.mock_log_event.call_args
        self.assertEqual(call_args[0], "PLATFORM_SCRAPE")
        self.assertEqual(call_args[2]["type"], "community")
        self.assertEqual(call_args[2]["count"], 1)
        self.assertEqual(call_args[2]["community_id"], "r/test") # Check kwargs logged
        self.assertEqual(call_args[2]["max_posts"], 5)


    # --- Placeholder for future tests ---


if __name__ == '__main__':
    unittest.main() 