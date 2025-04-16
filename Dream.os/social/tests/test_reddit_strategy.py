import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import pytest
from unittest import mock
import logging

# Add project root to sys.path
script_dir = os.path.dirname(__file__) # tests/
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels to D:/Dream.os/
social_dir = os.path.join(project_root, 'social')
if os.path.isdir(social_dir) and social_dir not in sys.path:
     sys.path.insert(0, social_dir)
if project_root not in sys.path:
     sys.path.insert(0, project_root)

# Updated import path
# from strategies.reddit_strategy import RedditStrategy
# from strategy_exceptions import LoginError, ScrapeError, PostError, RateLimitError

# Assuming RedditStrategy exists in core.strategies
from core.strategies.reddit_strategy import RedditStrategy
from core.exceptions.strategy_exceptions import LoginError, ScrapeError, PostError, RateLimitError

# Mock setup_logging
@pytest.fixture(autouse=True)
def mock_setup_logging():
    pass # Fixture needs a body

# Mock PRAW library itself if it's imported at the module level in reddit_strategy
# Alternatively, patch the specific praw.Reddit() instantiation within the strategy methods
@patch('praw.Reddit') # Adjust target if praw is imported differently
@unittest.skipIf(RedditStrategy is None, "RedditStrategy could not be imported.")
class TestRedditStrategy(unittest.TestCase):

    def setUp(self, MockPrawReddit):
        """Set up common resources for Reddit tests."""
        self.MockPrawReddit = MockPrawReddit # Store mock constructor
        self.mock_praw_instance = MockPrawReddit.return_value # Mock instance

        # Mock configuration data
        self.mock_config = {
            "reddit": {
                "client_id": "test_reddit_client_id",
                "client_secret": "test_reddit_secret",
                "user_agent": "test_agent/1.0",
                "username": "test_user",
                "password": "test_password",
                "target_subreddits": ["testsub1", "testsub2"]
            },
            "common_settings": {"timeout_seconds": 10}
        }
        # Reddit strategy doesn't need a Selenium driver
        self.mock_driver = None 
        
        # Instantiate the strategy
        # The __init__ might try to instantiate praw.Reddit, which is now mocked
        self.strategy = RedditStrategy(self.mock_config, self.mock_driver)

        # --- Configure Mock PRAW Instance Behavior --- 
        # Mock user object and username for login check
        mock_user = MagicMock()
        mock_user.me.return_value = self.mock_config['reddit']['username'] # Simulate successful login check
        self.mock_praw_instance.user = mock_user
        
        # Mock subreddit object for posting
        self.mock_subreddit = MagicMock()
        self.mock_subreddit.submit.return_value = MagicMock(id="test_submission_id") # Simulate successful submission
        self.mock_praw_instance.subreddit.return_value = self.mock_subreddit
        
        # Mock inbox for scraping mentions
        mock_mention = MagicMock()
        mock_mention.id = "mention1"
        mock_mention.author = MagicMock(name="mentioner_user")
        mock_mention.body = "This is a test mention."
        mock_mention.created_utc = 1678886400 # Example timestamp
        mock_mention.context = "/r/testsub1/comments/xyz/post_title/comment_id"
        self.mock_praw_instance.inbox.mentions.return_value = [mock_mention] # Simulate one mention
        self.mock_praw_instance.inbox.mark_read.return_value = None # Mock mark_read

    def test_login_success(self):
        """Test successful login (checks user via PRAW)."""
        # Login might be implicit in __init__ or a separate method
        # If explicit login method exists:
        # result = self.strategy.login()
        # self.assertTrue(result)
        # If implicit, check PRAW was instantiated and user checked
        self.MockPrawReddit.assert_called_once() # Check praw.Reddit was called
        self.mock_praw_instance.user.me.assert_called_once() # Check login verification occurred
        # Check internal logged_in flag if exists
        self.assertTrue(self.strategy.logged_in) 

    def test_post_text_success(self):
        """Test posting text to a subreddit."""
        target_subreddit = "testsub1"
        post_title = "Test Post Title"
        post_text = "This is the body of the test post."
        
        result = self.strategy.post(text=post_text, title=post_title, subreddit=target_subreddit)
        
        self.assertTrue(result) # Should return True on success
        # Verify praw.subreddit(target).submit(...) was called correctly
        self.mock_praw_instance.subreddit.assert_called_once_with(target_subreddit)
        self.mock_subreddit.submit.assert_called_once_with(title=post_title, selftext=post_text)

    def test_scrape_mentions_success(self):
        """Test scraping mentions from the inbox."""
        max_mentions = 5
        mentions = self.strategy.scrape_mentions(max_mentions=max_mentions)
        
        self.assertIsInstance(mentions, list)
        self.assertEqual(len(mentions), 1)
        mention = mentions[0]
        self.assertEqual(mention['id'], "mention1")
        self.assertEqual(mention['text'], "This is a test mention.")
        self.assertEqual(mention['author'], "mentioner_user")
        self.assertIn("/r/testsub1/comments/xyz/post_title/comment_id", mention['url']) # Check context mapping to URL
        
        # Verify PRAW methods were called
        self.mock_praw_instance.inbox.mentions.assert_called_once_with(limit=max_mentions)
        self.mock_praw_instance.inbox.mark_read.assert_called_once()

    # --- Add tests for error handling --- 
    
    def test_post_praw_api_exception(self):
        """Test handling PRAW API exception during post."""
        # Import PRAW exception type (adjust if specific exception needed)
        try:
            from prawcore.exceptions import PrawcoreException 
        except ImportError:
            PrawcoreException = Exception # Fallback

        # Configure the mock subreddit submit method to raise an error
        self.mock_subreddit.submit.side_effect = PrawcoreException("Reddit API Error")
        
        target_subreddit = "testsub1"
        post_title = "Error Post"
        post_text = "This post will fail"
        
        # Call post and expect it to fail gracefully
        result = self.strategy.post(text=post_text, title=post_title, subreddit=target_subreddit)
        
        self.assertFalse(result)
        # Verify submit was still called
        self.mock_praw_instance.subreddit.assert_called_once_with(target_subreddit)
        self.mock_subreddit.submit.assert_called_once_with(title=post_title, selftext=post_text)
        # Optionally verify logging if implemented in strategy error handling
        # Example: self.mock_log_event.assert_called_with(..., error="PRAW API Error", ...)

    def test_scrape_mentions_no_mentions(self):
        """Test scraping mentions when the inbox is empty."""
        # Configure mock PRAW mentions to return an empty list
        self.mock_praw_instance.inbox.mentions.return_value = []
        
        mentions = self.strategy.scrape_mentions()
        
        self.assertEqual(mentions, []) # Expect empty list
        # Verify mentions was called, but mark_read should not be called if list is empty
        self.mock_praw_instance.inbox.mentions.assert_called_once()
        self.mock_praw_instance.inbox.mark_read.assert_not_called()

    # - Posting to invalid subreddit
    # - API errors during post/scrape (e.g., PRAW exceptions)
    # - Login failures

if __name__ == '__main__':
    unittest.main() 