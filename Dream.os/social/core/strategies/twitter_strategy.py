"""
Twitter Strategy - Handles publishing content to Twitter using their API.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import requests
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
import time

# Use updated import paths
from .base_strategy import BaseSocialStrategy
# from strategy_exceptions import LoginError, PostError, ScrapeError, RateLimitError, AuthenticationError
from core.exceptions.strategy_exceptions import LoginError, PostError, ScrapeError, RateLimitError, AuthenticationError
# from utils import retry_on_stale_element, setup_logging, wait_and_click, wait_and_send_keys
from utils.retry_utils import retry_on_stale_element
from utils.logging_utils import setup_logging
from utils.browser_utils import wait_and_click, wait_and_send_keys

# Configure logging
logger = logging.getLogger(__name__)

# Centralized Selectors for TwitterStrategy
SELECTORS = {
    "username_input": (By.NAME, "text"),
    "next_button": (By.CSS_SELECTOR, '[data-testid="next"]'),
    "password_input": (By.NAME, "password"),
    "login_button": (By.CSS_SELECTOR, '[data-testid="LoginForm_Login_Button"]'),
    "compose_button": (By.CSS_SELECTOR, '[data-testid="SideNav_NewTweet_Button"]'),
    "tweet_textarea": (By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'),
    "tweet_button": (By.CSS_SELECTOR, '[data-testid="tweetButton"]'),
    "analytics_impressions": (By.CSS_SELECTOR, '[data-testid="impressions"]'),
    "analytics_likes": (By.CSS_SELECTOR, '[data-testid="like_count"]'),
    "analytics_retweets": (By.CSS_SELECTOR, '[data-testid="retweet_count"]'),
    "analytics_replies": (By.CSS_SELECTOR, '[data-testid="reply_count"]'
    )
    # Add other selectors used in BaseSocialStrategy common methods if needed (e.g., profile, media upload)
}

class TwitterStrategy(BaseSocialStrategy):
    """Strategy for interacting with Twitter platform."""
    
    def __init__(self, driver, config):
        """Initialize Twitter strategy.
        
        Args:
            driver: Selenium WebDriver instance
            config: Configuration with Twitter credentials
        """
        super().__init__(driver, config)
        self.base_url = "https://twitter.com"
        self.login_url = f"{self.base_url}/login"
        self.api_url = "https://api.twitter.com/2"
        self.selectors = SELECTORS # Make selectors available instance-wide if needed, or use directly
        
        logger.info("Initialized Twitter Strategy")
    
    def login(self) -> bool:
        """Log into Twitter account.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            if not navigate_to(self.driver, self.login_url, source=self._source):
                return False
                
            # Enter username
            if not safe_send_keys(
                self.driver,
                self.selectors["username_input"],
                self.config["username"],
                source=self._source
            ):
                return False
                
            # Click next
            if not safe_click(
                self.driver,
                self.selectors["next_button"],
                source=self._source
            ):
                return False
                
            # Enter password
            if not safe_send_keys(
                self.driver,
                self.selectors["password_input"],
                self.config["password"],
                source=self._source
            ):
                return False
                
            # Click login
            if not safe_click(
                self.driver,
                self.selectors["login_button"],
                source=self._source
            ):
                return False
                
            return self.check_login_status()
            
        except Exception as e:
            log_event("error", f"Login failed: {str(e)}", {"source": self._source})
            return False
            
    def create_post(self, content: Dict[str, Any]) -> bool:
        """Create a new tweet.
        
        Args:
            content: Dictionary containing tweet content and metadata
                text: Main tweet text
                media: Optional list of media file paths
                tags: Optional list of hashtags
                schedule_time: Optional datetime for scheduled posting
                
        Returns:
            bool: True if tweet posted successfully, False otherwise
        """
        try:
            # Click compose button
            if not safe_click(
                self.driver,
                self.selectors["compose_button"],
                source=self._source
            ):
                return False
                
            # Enter tweet text
            if not safe_send_keys(
                self.driver,
                self.selectors["tweet_textarea"],
                content["text"],
                source=self._source
            ):
                return False
                
            # Handle media uploads
            if media_files := content.get("media"):
                if not self.upload_media(media_files):
                    return False
                    
            # Add hashtags
            if tags := content.get("tags"):
                if not self.add_tags(tags, self.selectors["tweet_textarea"]):
                    return False
                    
            # Schedule post
            if schedule_time := content.get("schedule_time"):
                if not self.schedule_post(schedule_time):
                    return False
                    
            # Post tweet
            if not safe_click(
                self.driver,
                self.selectors["tweet_button"],
                source=self._source
            ):
                return False
                
            log_event("post", "Tweet created successfully", {"source": self._source})
            return True
            
        except Exception as e:
            log_event("error", f"Failed to create tweet: {str(e)}", {"source": self._source})
            return False
            
    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get analytics for a specific tweet.
        
        Args:
            post_id: Twitter post ID
            
        Returns:
            dict: Analytics data including impressions, engagements, etc.
        """
        try:
            analytics_url = f"{self.base_url}/analytics/tweet/{post_id}"
            if not navigate_to(self.driver, analytics_url, source=self._source):
                return {}
                
            metrics = {}
            
            # Get impression count
            impressions = wait_for_element(
                self.driver,
                self.selectors["analytics_impressions"],
                source=self._source
            )
            if impressions:
                metrics["impressions"] = int(impressions.text.replace(",", ""))
                
            # Get engagement metrics
            engagement_selectors = {
                "likes": self.selectors["analytics_likes"],
                "retweets": self.selectors["analytics_retweets"],
                "replies": self.selectors["analytics_replies"]
            }
            
            for metric, selector in engagement_selectors.items():
                element = wait_for_element(
                    self.driver,
                    selector,
                    source=self._source
                )
                if element:
                    metrics[metric] = int(element.text.replace(",", ""))
                    
            log_event("analytics", f"Retrieved analytics for tweet {post_id}", 
                     {"source": self._source})
            return metrics
            
        except Exception as e:
            log_event("error", f"Failed to get tweet analytics: {str(e)}", 
                     {"source": self._source})
            return {}
    
    def post_update(self, content: str) -> bool:
        """
        Post a tweet.
        
        Args:
            content: The tweet content
            
        Returns:
            bool: True if successful
        """
        try:
            # Ensure content is within Twitter's character limit
            if len(content) > 280:
                content = content[:277] + "..."
            
            # Prepare the tweet data
            tweet_data = {
                "text": content
            }
            
            # Make the API request
            response = requests.post(
                f"{self.api_url}/tweets",
                headers={
                    "Authorization": f"Bearer {self._get_bearer_token()}",
                    "Content-Type": "application/json"
                },
                json=tweet_data
            )
            
            if response.status_code == 201:
                logger.info("Successfully posted tweet")
                return True
            else:
                logger.error(f"Failed to post tweet: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting tweet: {str(e)}")
            return False
    
    def post_thread(self, content: str) -> bool:
        """
        Post a thread of tweets.
        
        Args:
            content: The thread content
            
        Returns:
            bool: True if successful
        """
        try:
            # Split content into tweet-sized chunks
            tweets = self._split_into_tweets(content)
            
            # Post the first tweet
            response = requests.post(
                f"{self.api_url}/tweets",
                headers={
                    "Authorization": f"Bearer {self._get_bearer_token()}",
                    "Content-Type": "application/json"
                },
                json={"text": tweets[0]}
            )
            
            if response.status_code != 201:
                logger.error(f"Failed to post first tweet: {response.text}")
                return False
            
            # Get the ID of the first tweet
            first_tweet_id = response.json()["data"]["id"]
            
            # Post the rest of the thread in reply to the previous tweet
            previous_tweet_id = first_tweet_id
            for tweet in tweets[1:]:
                response = requests.post(
                    f"{self.api_url}/tweets",
                    headers={
                        "Authorization": f"Bearer {self._get_bearer_token()}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": tweet,
                        "reply": {
                            "in_reply_to_tweet_id": previous_tweet_id
                        }
                    }
                )
                
                if response.status_code != 201:
                    logger.error(f"Failed to post thread tweet: {response.text}")
                    return False
                
                previous_tweet_id = response.json()["data"]["id"]
            
            logger.info("Successfully posted thread")
            return True
            
        except Exception as e:
            logger.error(f"Error posting thread: {str(e)}")
            return False
    
    def _get_bearer_token(self) -> str:
        """Get a bearer token for API requests."""
        try:
            response = requests.post(
                "https://api.twitter.com/oauth2/token",
                auth=(self.config["api_key"], self.config["api_secret"]),
                data={"grant_type": "client_credentials"}
            )
            
            if response.status_code == 200:
                return response.json()["access_token"]
            else:
                raise Exception(f"Failed to get bearer token: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting bearer token: {str(e)}")
            raise
    
    def _split_into_tweets(self, content: str) -> List[str]:
        """Split content into tweet-sized chunks."""
        tweets = []
        words = content.split()
        current_tweet = ""
        
        for word in words:
            # Check if adding the word would exceed Twitter's limit
            if len(current_tweet) + len(word) + 1 <= 280:
                current_tweet += " " + word if current_tweet else word
            else:
                # Save current tweet and start a new one
                tweets.append(current_tweet)
                current_tweet = word
        
        # Add the last tweet
        if current_tweet:
            tweets.append(current_tweet)
        
        return tweets 