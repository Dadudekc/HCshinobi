import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, call, ANY
import time # Import time if we decide to test sleep/backoff
import threading # For testing loop interruption
import logging

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # tests/integration
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) 
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Import the class to test and dependencies to mock
try:
    from core.agents.social_media_agent import SocialMediaAgent, AGENT_ID
    from core.utils.mailbox_handler import MailboxHandler
    from core.strategies.base_strategy import BaseSocialStrategy
    _imports_ok = True
except ImportError as e:
    print(f"Error importing modules for SocialAgent integration test: {e}")
    _imports_ok = False

# Mock config for the agent
MOCK_CONFIG = {
    "common_settings": {"timeout_seconds": 10},
    "twitter": {"username": "testuser", "password": "testpass"}, 
    "reddit": {}, # Add other platforms if needed for tests
    "linkedin": {}
}

# Mock Base Strategy for simplified testing
class MockStrategy(BaseSocialStrategy):
    def __init__(self, config, driver, platform_name="mock"):
        super().__init__(config, driver)
        self._platform = platform_name
        self.login_result = True
        self.post_result = True
        self.check_login_status_result = True
        self.scrape_mentions_result = []
        self.scrape_trends_result = []
        self.scrape_community_result = []
        self.quit_called = False
        self.logged_in = True

    def get_platform_name(self): return self._platform
    def login(self): return self.login_result
    def post(self, text, image_path=None, **kwargs): return self.post_result
    def check_login_status(self): return self.check_login_status_result
    def scrape_mentions(self, max_mentions): return self.scrape_mentions_result
    def scrape_trends(self, **kwargs): return self.scrape_trends_result
    def scrape_community(self, **kwargs): return self.scrape_community_result
    def quit(self): self.quit_called = True


@unittest.skipUnless(_imports_ok, "SocialAgent dependencies not met, skipping integration test")
class TestSocialAgentLoop(unittest.TestCase):

    # Patch MailboxHandler globally for the class if preferred, or per method
    @patch('core.agents.social_media_agent.MailboxHandler') 
    @patch('core.agents.social_media_agent.log_event')
    @patch('core.agents.social_media_agent.get_undetected_driver') # Prevent actual driver init
    @patch('core.agents.social_media_agent.importlib.import_module') # Control strategy loading
    def setUp(self, mock_import_module, mock_get_driver, mock_log_event, mock_mailbox_handler_cls):
        """Set up the agent instance with mocked dependencies."""
        # Mock MailboxHandler instance
        self.mock_mailbox_handler = MagicMock(spec=MailboxHandler)
        mock_mailbox_handler_cls.return_value = self.mock_mailbox_handler
        
        # Prevent driver initialization unless specifically needed
        mock_get_driver.return_value = None 

        # Store mock log_event for assertions
        self.mock_log_event = mock_log_event
        
        # Setup mock strategies
        self.mock_twitter_strategy = MockStrategy(MOCK_CONFIG, None, "twitter")
        # Mock import_module to return our mock strategy class/instance
        def side_effect_import(module_path):
            mock_module = MagicMock()
            if module_path.endswith("twitter_strategy"):
                mock_module.TwitterStrategy = MagicMock(return_value=self.mock_twitter_strategy)
            # Add other platforms if needed
            # elif module_path.endswith("reddit_strategy"):
            #     mock_module.RedditStrategy = MagicMock(return_value=MockStrategy(MOCK_CONFIG, None, "reddit"))
            else:
                raise ModuleNotFoundError(f"No mock for {module_path}")
            return mock_module
        mock_import_module.side_effect = side_effect_import

        # Patch the config loading within the agent's init
        with patch('core.agents.social_media_agent.SocialMediaAgent._load_config') as mock_load_config:
            mock_load_config.return_value = MOCK_CONFIG
            self.agent = SocialMediaAgent(mailbox_base_dir="mock/path") # Path doesn't matter due to mocked handler
            self.agent.driver = None # Ensure driver is None initially
            # Mock shutdown specifically for loop tests
            self.agent.shutdown = MagicMock()
            # Add flag to easily check if original shutdown was called (if not mocking)
            self.agent.shutdown_called = False 
            original_shutdown = self.agent.shutdown
            def shutdown_wrapper():
                 self.agent.shutdown_called = True
                 original_shutdown() # Call the mocked/original shutdown
            self.agent.shutdown = shutdown_wrapper 

        # Reset mocks before each test (optional, good practice)
        self.mock_mailbox_handler.reset_mock()
        self.mock_log_event.reset_mock()
        # Reset strategy mocks if state needs cleaning between tests
        # self.mock_twitter_strategy = MockStrategy(MOCK_CONFIG, None, "twitter") 
        

    def test_01_process_valid_post_message(self):
        """Test processing a valid 'post' command message."""
        # Arrange
        msg_id = "msg-post-123"
        command_msg = {
            "message_id": msg_id,
            "command": "post",
            "platform": "twitter",
            "details": {"text": "Test tweet"}
        }
        self.mock_mailbox_handler.check_for_messages.return_value = [command_msg] # Simulate one message
        self.mock_mailbox_handler.send_message.return_value = True
        self.mock_twitter_strategy.post_result = True # Simulate successful post

        # Act
        self.agent.process_incoming_message(command_msg)

        # Assert
        # Verify agent called the correct strategy method
        # (Need to access the instance loaded by the agent, which is tricky with current setup)
        # Instead, we check the response sent back, assuming strategy success
        
        # Verify response sent via mailbox handler
        self.mock_mailbox_handler.send_message.assert_called_once()
        call_args, call_kwargs = self.mock_mailbox_handler.send_message.call_args
        sent_response = call_args[0]
        self.assertEqual(sent_response['type'], "RESPONSE")
        self.assertEqual(sent_response['response_to'], msg_id)
        self.assertEqual(sent_response['payload']['status'], "completed")
        self.assertIsNone(sent_response['payload'].get('error_details'))
        
        # Verify logging (basic checks)
        self.mock_log_event.assert_any_call("AGENT_INFO", AGENT_ID, ANY) # Check for processing log
        self.mock_log_event.assert_any_call("PLATFORM_POST", AGENT_ID, ANY) # Check for post log

    def test_02_process_valid_scrape_message(self):
        """Test processing a valid 'scrape_mentions' command."""
        # Arrange
        msg_id = "msg-scrape-456"
        command_msg = {
            "message_id": msg_id,
            "command": "scrape_mentions",
            "platform": "twitter",
            "details": {"max_mentions": 5}
        }
        simulated_mentions = [
            {'author': '@user1', 'text': 'mention 1'},
            {'author': '@user2', 'text': 'mention 2'}
        ]
        self.mock_mailbox_handler.check_for_messages.return_value = [command_msg]
        self.mock_mailbox_handler.send_message.return_value = True
        self.mock_twitter_strategy.scrape_mentions_result = simulated_mentions # Simulate successful scrape
        
        # Act
        self.agent.process_incoming_message(command_msg)

        # Assert
        self.mock_mailbox_handler.send_message.assert_called_once()
        call_args, call_kwargs = self.mock_mailbox_handler.send_message.call_args
        sent_response = call_args[0]
        self.assertEqual(sent_response['payload']['status'], "completed")
        self.assertEqual(sent_response['payload']['results']['mention_count'], 2)
        self.assertEqual(sent_response['payload']['results']['mentions'], simulated_mentions)
        
        self.mock_log_event.assert_any_call("PLATFORM_SCRAPE", AGENT_ID, ANY) 

    def test_03_process_message_strategy_fails(self):
        """Test processing a command where the strategy method fails."""
        # Arrange
        msg_id = "msg-post-fail-789"
        command_msg = {
            "message_id": msg_id,
            "command": "post",
            "platform": "twitter",
            "details": {"text": "This will fail"}
        }
        self.mock_mailbox_handler.check_for_messages.return_value = [command_msg]
        self.mock_mailbox_handler.send_message.return_value = True
        self.mock_twitter_strategy.post_result = False # Simulate strategy failure

        # Act
        self.agent.process_incoming_message(command_msg)

        # Assert
        self.mock_mailbox_handler.send_message.assert_called_once()
        call_args, call_kwargs = self.mock_mailbox_handler.send_message.call_args
        sent_response = call_args[0]
        self.assertEqual(sent_response['payload']['status'], "failed")
        # Strategy log should indicate failure, agent response reflects it.
        self.mock_log_event.assert_any_call("PLATFORM_POST", AGENT_ID, {
                "platform": "twitter", 
                "success": False, # Check that failure is logged
                "text_length": len("This will fail"), 
                "image_provided": False,
                "governance_context_used": False,
                "context_details": None, 
                "strategy_kwargs": {}
            })

    def test_04_process_invalid_command(self):
        """Test processing a message with an unknown command."""
        # Arrange
        msg_id = "msg-invalid-cmd-000"
        command_msg = {
            "message_id": msg_id,
            "command": "fly_to_moon", # Invalid command
            "platform": "twitter"
        }
        self.mock_mailbox_handler.check_for_messages.return_value = [command_msg]
        self.mock_mailbox_handler.send_message.return_value = True

        # Act
        self.agent.process_incoming_message(command_msg)

        # Assert
        self.mock_mailbox_handler.send_message.assert_called_once()
        call_args, call_kwargs = self.mock_mailbox_handler.send_message.call_args
        sent_response = call_args[0]
        self.assertEqual(sent_response['payload']['status'], "error")
        self.assertIn("Unknown command", sent_response['payload']['error_details'])
        
        self.mock_log_event.assert_any_call("AGENT_WARNING", AGENT_ID, {"warning": "Unknown mailbox command", "command": "fly_to_moon", "message_content": command_msg})

    def test_05_process_post_not_logged_in(self):
        """Test processing a post command when the agent is not logged in."""
        # Arrange
        msg_id = "msg-post-nologin-111"
        command_msg = {
            "message_id": msg_id,
            "command": "post",
            "platform": "twitter",
            "details": {"text": "Should fail"}
        }
        # Ensure agent state reflects not logged in for the strategy
        self.mock_twitter_strategy.logged_in = False 
        self.mock_mailbox_handler.check_for_messages.return_value = [command_msg]
        self.mock_mailbox_handler.send_message.return_value = True

        # Act
        self.agent.process_incoming_message(command_msg)

        # Assert
        # Verify strategy's post method was NOT called
        # We check this by ensuring the PLATFORM_POST log didn't happen
        # and the response indicates failure without specific strategy error
        
        self.mock_mailbox_handler.send_message.assert_called_once()
        call_args, call_kwargs = self.mock_mailbox_handler.send_message.call_args
        sent_response = call_args[0]
        # Expecting 'failed' because the *agent* failed the precondition, not an internal error
        self.assertEqual(sent_response['payload']['status'], "failed") 
        self.assertIsNone(sent_response['payload'].get('error_details')) # No specific error message here
        
        # Verify specific log event for this failure isn't explicitly defined, 
        # but PLATFORM_POST should NOT have been called.
        platform_post_called = any(
            call_args[0] == "PLATFORM_POST" 
            for call_args, _ in self.mock_log_event.call_args_list
        )
        self.assertFalse(platform_post_called, "PLATFORM_POST should not be logged if not logged in")

    @patch('core.agents.social_media_agent.SocialMediaAgent._generate_post_content')
    def test_06_process_post_with_governance_context(self, mock_generate_content):
        """Test processing a post using generated governance context."""
        # Arrange
        msg_id = "msg-post-gov-222"
        command_msg = {
            "message_id": msg_id,
            "command": "post",
            "platform": "twitter",
            "details": {"use_governance_context": True} # Trigger context gen
        }
        generated_text = "Generated content from governance event."
        mock_generate_content.return_value = (generated_text, {"event_type": "TEST_EVENT"})
        self.mock_mailbox_handler.check_for_messages.return_value = [command_msg]
        self.mock_mailbox_handler.send_message.return_value = True
        self.mock_twitter_strategy.post_result = True # Simulate successful post
        self.mock_twitter_strategy.logged_in = True # Ensure logged in

        # Act
        self.agent.process_incoming_message(command_msg)

        # Assert
        mock_generate_content.assert_called_once_with("twitter")
        
        # Verify response sent via mailbox handler
        self.mock_mailbox_handler.send_message.assert_called_once()
        call_args, call_kwargs = self.mock_mailbox_handler.send_message.call_args
        sent_response = call_args[0]
        self.assertEqual(sent_response['payload']['status'], "completed")
        
        # Verify logging indicates context was used and includes details
        self.mock_log_event.assert_any_call("PLATFORM_POST", AGENT_ID, {
                "platform": "twitter", 
                "success": True, 
                "text_length": len(generated_text), 
                "image_provided": False,
                "governance_context_used": True,
                "context_details": {"event_type": "TEST_EVENT"}, # Check context logged 
                "strategy_kwargs": {}
            })

    # --- New Tests for run_operational_loop (Task TODO) ---
    
    @patch('time.sleep', return_value=None) # Mock time.sleep
    def test_07_loop_runs_multiple_cycles_empty_inbox(self, mock_sleep):
        """Test the loop runs multiple times when inbox is empty."""
        # Arrange
        self.mock_mailbox_handler.check_for_messages.side_effect = [
            [], # First call: empty
            [], # Second call: empty
            KeyboardInterrupt # Third call: stop the loop
        ]
        interval = 0.1 # Small interval for test

        # Act
        try:
            self.agent.run_operational_loop(interval_seconds=interval)
        except KeyboardInterrupt:
            pass # Expected exit

        # Assert
        # Check that check_for_messages was called 3 times
        self.assertEqual(self.mock_mailbox_handler.check_for_messages.call_count, 3)
        # Check that sleep was called twice (after empty checks)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(interval)
        # Check start/stop logs
        self.mock_log_event.assert_any_call("AGENT_START", AGENT_ID, ANY)
        self.mock_log_event.assert_any_call("AGENT_STOP", AGENT_ID, {"reason": "KeyboardInterrupt"})
        self.mock_log_event.assert_any_call("AGENT_LOOP_CYCLE", AGENT_ID, {"event": "start", "timestamp": ANY})
        self.mock_log_event.assert_any_call("AGENT_LOOP_CYCLE", AGENT_ID, {"event": "end", "sleep_duration": interval})
        # Ensure shutdown was called after loop exit
        self.assertTrue(self.agent.shutdown_called) # Assuming shutdown sets a flag or mock it

    @patch('time.sleep', return_value=None) # Mock time.sleep
    def test_08_loop_processes_message_then_empty(self, mock_sleep):
        """Test loop processing one message then finding empty inbox."""
        # Arrange
        msg_id = "loop-msg-1"
        command_msg = {"message_id": msg_id, "command": "agent_status", "platform": None}
        self.mock_mailbox_handler.check_for_messages.side_effect = [
            [command_msg], # First call: one message
            [],            # Second call: empty
            KeyboardInterrupt # Stop loop
        ]
        self.mock_mailbox_handler.send_message.return_value = True # Mock response sending
        interval = 0.1

        # Act
        try:
            self.agent.run_operational_loop(interval_seconds=interval)
        except KeyboardInterrupt:
            pass

        # Assert
        self.assertEqual(self.mock_mailbox_handler.check_for_messages.call_count, 3)
        # Check response was sent for the message
        self.mock_mailbox_handler.send_message.assert_called_once()
        call_args, _ = self.mock_mailbox_handler.send_message.call_args
        self.assertEqual(call_args[0]['response_to'], msg_id)
        self.assertEqual(call_args[0]['payload']['status'], "completed")
        # Check sleep was called twice
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(interval)
        self.assertTrue(self.agent.shutdown_called)

    @patch('time.sleep', return_value=None) # Mock time.sleep
    def test_09_loop_handles_check_messages_error(self, mock_sleep):
        """Test loop continues after MailboxHandler raises error, with backoff."""
        # Arrange
        mailbox_error = OSError("Cannot access inbox")
        self.mock_mailbox_handler.check_for_messages.side_effect = [
            mailbox_error,   # First call: error
            [],              # Second call: empty (loop continues)
            KeyboardInterrupt # Stop loop
        ]
        interval = 0.1
        expected_backoff_sleep = interval * self.agent.ERROR_BACKOFF_MULTIPLIER # Use agent's constant

        # Act
        try:
            self.agent.run_operational_loop(interval_seconds=interval)
        except KeyboardInterrupt:
            pass

        # Assert
        self.assertEqual(self.mock_mailbox_handler.check_for_messages.call_count, 3)
        # Verify critical error logged
        self.mock_log_event.assert_any_call("AGENT_CRITICAL", AGENT_ID, {
             "error": "Operational loop failure", 
             "details": str(mailbox_error), 
             "traceback": ANY
             })
        # Check sleep calls: one for backoff, one for normal interval
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_has_calls([
            call(expected_backoff_sleep), 
            call(interval)
        ], any_order=False) # Ensure backoff happens first
        self.assertTrue(self.agent.shutdown_called)

    def test_10_loop_shutdown_called_on_interrupt(self):
        """Test that shutdown is called when KeyboardInterrupt occurs."""
        # Arrange
        # Simulate the loop running and then receiving interrupt
        self.mock_mailbox_handler.check_for_messages.side_effect = KeyboardInterrupt
        interval = 0.1
        # Mock agent's shutdown method to check if it's called
        self.agent.shutdown = MagicMock()

        # Act
        try:
            self.agent.run_operational_loop(interval_seconds=interval)
        except KeyboardInterrupt:
            pass # Expected

        # Assert
        self.agent.shutdown.assert_called_once()
        self.mock_log_event.assert_any_call("AGENT_STOP", AGENT_ID, {"reason": "KeyboardInterrupt"})

    # Removed TODO as tests were added above
    # TODO: Add tests for:
    # - Error during message processing within the loop (process_incoming_message fails)
    # - Shutdown behavior when loop exits normally (if possible without interrupt)


if __name__ == '__main__':
    unittest.main() 