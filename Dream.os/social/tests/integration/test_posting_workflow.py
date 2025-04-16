import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, call, ANY
import pytest

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # tests/integration
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) 
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Import the class to test and dependencies to mock
try:
    from core.agents.social_media_agent import SocialMediaAgent, AGENT_ID
    from utils.mailbox_handler import MailboxHandler 
    from core.strategies.base_strategy import BaseSocialStrategy
    # Import exceptions for testing error cases
    from core.strategies.strategy_exceptions import PostError, AuthenticationError
    from core.devlog_processor import DevLogPost, ContentBlock
    from core.strategy_loader import load_strategies
    _imports_ok = True
except ImportError as e:
    print(f"Error importing modules for Posting Workflow test: {e}")
    _imports_ok = False

# Mock config for the agent
MOCK_CONFIG = {
    "common_settings": {"timeout_seconds": 10},
    "twitter": {"username": "test_twitter", "password": "pass"},
    "reddit": {"username": "test_reddit", "password": "pass"},
    "linkedin": {"username": "test_linkedin", "password": "pass"}
    # Add other platforms if their posting is tested
}

# Mock Base Strategy focused on posting
class MockPostingStrategy(BaseSocialStrategy):
    def __init__(self, config, driver, platform_name="mock"):
        super().__init__(config, driver)
        self._platform = platform_name
        self.post_should_succeed = True
        self.post_should_raise = None # Exception class to raise, or None
        self.last_post_args = None
        self.last_post_kwargs = None

    def get_platform_name(self): return self._platform
    def login(self): return True # Assume login works for posting tests
    def post(self, *args, **kwargs):
        self.last_post_args = args
        self.last_post_kwargs = kwargs
        if self.post_should_raise:
            raise self.post_should_raise(f"Simulated post error on {self._platform}", platform=self._platform)
        return self.post_should_succeed
    def check_login_status(self): return True
    # Add other methods as needed by agent interactions during post
    def quit(self): pass

@unittest.skipUnless(_imports_ok, "SocialAgent dependencies not met, skipping posting workflow test")
class TestPostingWorkflow(unittest.TestCase):

    @patch('core.agents.social_media_agent.MailboxHandler') 
    @patch('core.agents.social_media_agent.log_event')
    @patch('core.agents.social_media_agent.get_undetected_driver') 
    @patch('core.agents.social_media_agent.importlib.import_module') 
    def setUp(self, mock_import_module, mock_get_driver, mock_log_event, mock_mailbox_handler_cls):
        """Set up the agent instance with mocked dependencies for posting tests."""
        self.mock_mailbox_handler = MagicMock(spec=MailboxHandler)
        mock_mailbox_handler_cls.return_value = self.mock_mailbox_handler
        mock_get_driver.return_value = None 
        self.mock_log_event = mock_log_event
        
        # Setup mock strategies
        self.mock_strategies = {
            "twitter": MockPostingStrategy(MOCK_CONFIG, None, "twitter"),
            "reddit": MockPostingStrategy(MOCK_CONFIG, None, "reddit"),
            "linkedin": MockPostingStrategy(MOCK_CONFIG, None, "linkedin")
        }

        def side_effect_import(module_path):
            mock_module = MagicMock()
            platform_name = module_path.split('.')[-1].replace("_strategy", "")
            strategy_class_name = f"{platform_name.capitalize()}Strategy"
            if platform_name in self.mock_strategies:
                # Return a mock class that returns the specific instance
                setattr(mock_module, strategy_class_name, MagicMock(return_value=self.mock_strategies[platform_name]))
            else:
                raise ModuleNotFoundError(f"No mock for {module_path}")
            return mock_module
        mock_import_module.side_effect = side_effect_import

        with patch('core.agents.social_media_agent.SocialMediaAgent._load_config') as mock_load_config:
            mock_load_config.return_value = MOCK_CONFIG
            self.agent = SocialMediaAgent(mailbox_base_dir="mock/posting/path")
            self.agent.driver = None 

        # Reset mocks
        self.mock_mailbox_handler.reset_mock()
        self.mock_log_event.reset_mock()
        for strategy in self.mock_strategies.values():
            strategy.last_post_args = None
            strategy.last_post_kwargs = None
            strategy.post_should_succeed = True
            strategy.post_should_raise = None

    def _create_post_message(self, msg_id="msg-post-test", platform="twitter", text="Default text", image=None, **details):
        """Helper to create a post command message."""
        post_details = {"text": text}
        if image:
            post_details["image_path"] = image
        post_details.update(details)
        return {
            "message_id": msg_id,
            "command": "post",
            "platform": platform,
            "details": post_details
        }

    def test_post_twitter_success(self):
        """Test successful posting to Twitter via mailbox message."""
        platform = "twitter"
        msg_id = "msg-tw-post-01"
        post_text = "Hello Twitter!"
        command_msg = self._create_post_message(msg_id, platform, post_text)
        
        self.agent.process_incoming_message(command_msg)
        
        mock_strategy = self.mock_strategies[platform]
        self.assertIsNotNone(mock_strategy.last_post_kwargs, "Strategy post method not called")
        self.assertEqual(mock_strategy.last_post_kwargs.get('text'), post_text)
        
        self.mock_mailbox_handler.send_message.assert_called_once()
        response = self.mock_mailbox_handler.send_message.call_args[0][0]
        self.assertEqual(response['response_to'], msg_id)
        self.assertEqual(response['payload']['status'], "completed")

    def test_post_reddit_success(self):
        """Test successful posting to Reddit via mailbox message."""
        platform = "reddit"
        msg_id = "msg-rd-post-02"
        post_title = "Reddit Title"
        post_body = "Reddit body text."
        subreddit = "testsubreddit"
        command_msg = self._create_post_message(msg_id, platform, text=None, title=post_title, body=post_body, subreddit=subreddit)
        
        self.agent.process_incoming_message(command_msg)
        
        mock_strategy = self.mock_strategies[platform]
        self.assertIsNotNone(mock_strategy.last_post_kwargs, "Strategy post method not called")
        # Reddit strategy post takes specific args
        self.assertEqual(mock_strategy.last_post_kwargs.get('title'), post_title)
        self.assertEqual(mock_strategy.last_post_kwargs.get('body'), post_body)
        self.assertEqual(mock_strategy.last_post_kwargs.get('subreddit'), subreddit)
        
        self.mock_mailbox_handler.send_message.assert_called_once()
        response = self.mock_mailbox_handler.send_message.call_args[0][0]
        self.assertEqual(response['response_to'], msg_id)
        self.assertEqual(response['payload']['status'], "completed")

    def test_post_linkedin_success(self):
        """Test successful posting to LinkedIn via mailbox message."""
        platform = "linkedin"
        msg_id = "msg-li-post-03"
        post_text = "Professional thoughts on LinkedIn."
        command_msg = self._create_post_message(msg_id, platform, post_text)
        
        self.agent.process_incoming_message(command_msg)
        
        mock_strategy = self.mock_strategies[platform]
        self.assertIsNotNone(mock_strategy.last_post_kwargs, "Strategy post method not called")
        # LinkedIn post might take content or content_prompt
        self.assertTrue('content' in mock_strategy.last_post_kwargs or 'content_prompt' in mock_strategy.last_post_kwargs)
        self.assertEqual(mock_strategy.last_post_kwargs.get('content') or mock_strategy.last_post_kwargs.get('content_prompt'), post_text)
        
        self.mock_mailbox_handler.send_message.assert_called_once()
        response = self.mock_mailbox_handler.send_message.call_args[0][0]
        self.assertEqual(response['response_to'], msg_id)
        self.assertEqual(response['payload']['status'], "completed")

    def test_post_strategy_returns_false(self):
        """Test posting when the strategy's post method returns False."""
        platform = "twitter"
        msg_id = "msg-tw-post-fail-04"
        command_msg = self._create_post_message(msg_id, platform, "This post fails")
        
        self.mock_strategies[platform].post_should_succeed = False # Simulate failure
        
        self.agent.process_incoming_message(command_msg)
        
        self.assertIsNotNone(self.mock_strategies[platform].last_post_kwargs, "Strategy post method should still be called")
        self.mock_mailbox_handler.send_message.assert_called_once()
        response = self.mock_mailbox_handler.send_message.call_args[0][0]
        self.assertEqual(response['response_to'], msg_id)
        self.assertEqual(response['payload']['status'], "failed")
        self.assertIn("Strategy returned unsuccessful", response['payload']['error_details'])

    def test_post_strategy_raises_post_error(self):
        """Test posting when the strategy's post method raises PostError."""
        platform = "twitter"
        msg_id = "msg-tw-post-err-05"
        error_message = "Simulated post error on twitter"
        command_msg = self._create_post_message(msg_id, platform, "This post raises error")
        
        self.mock_strategies[platform].post_should_raise = PostError # Simulate exception
        
        self.agent.process_incoming_message(command_msg)
        
        self.assertIsNotNone(self.mock_strategies[platform].last_post_kwargs, "Strategy post method should still be called")
        self.mock_mailbox_handler.send_message.assert_called_once()
        response = self.mock_mailbox_handler.send_message.call_args[0][0]
        self.assertEqual(response['response_to'], msg_id)
        self.assertEqual(response['payload']['status'], "error") # Agent should report error status
        self.assertIn(error_message, response['payload']['error_details'])
        self.assertIn("PostError", response['payload']['error_details'])

    def test_post_strategy_raises_auth_error(self):
        """Test posting when the strategy's post method raises AuthenticationError."""
        platform = "twitter"
        msg_id = "msg-tw-post-auth-err-06"
        error_message = "Simulated auth error during post"
        command_msg = self._create_post_message(msg_id, platform, "This post raises auth error")
        
        self.mock_strategies[platform].post_should_raise = AuthenticationError(error_message, platform=platform)
        
        self.agent.process_incoming_message(command_msg)
        
        self.assertIsNotNone(self.mock_strategies[platform].last_post_kwargs, "Strategy post method should still be called")
        self.mock_mailbox_handler.send_message.assert_called_once()
        response = self.mock_mailbox_handler.send_message.call_args[0][0]
        self.assertEqual(response['response_to'], msg_id)
        self.assertEqual(response['payload']['status'], "error")
        self.assertIn(error_message, response['payload']['error_details'])
        self.assertIn("AuthenticationError", response['payload']['error_details'])

    def test_post_with_image(self):
        """Test posting with an image path."""
        platform = "twitter"
        msg_id = "msg-tw-post-img-07"
        image_path = "path/to/image.jpg"
        command_msg = self._create_post_message(msg_id, platform, "Post with image", image=image_path)
        
        self.agent.process_incoming_message(command_msg)
        
        mock_strategy = self.mock_strategies[platform]
        self.assertIsNotNone(mock_strategy.last_post_kwargs, "Strategy post method not called")
        self.assertEqual(mock_strategy.last_post_kwargs.get('image_path'), image_path)
        
        self.mock_mailbox_handler.send_message.assert_called_once()
        response = self.mock_mailbox_handler.send_message.call_args[0][0]
        self.assertEqual(response['payload']['status'], "completed")

if __name__ == '__main__':
    unittest.main() 