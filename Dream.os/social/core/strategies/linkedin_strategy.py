"""
LinkedIn Strategy - Handles publishing content to LinkedIn using their API.
"""

import json
import logging
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException

from .base_strategy import BaseSocialStrategy
from core.exceptions.strategy_exceptions import LoginError, PostError, ScrapeError
from utils.logging_utils import setup_logging
from utils.browser_utils import wait_and_click, wait_and_send_keys
from utils.selenium_utils import wait_for_element, safe_click, safe_send_keys, navigate_to
from utils.logging_utils import log_event, get_logger
from tests.utils.test_utils import setup_driver

# Configure logger using the consolidated utility
logger = get_logger(__name__)

# Centralized Selectors for LinkedInStrategy
SELECTORS = {
    "username_input": (By.ID, "username"),
    "password_input": (By.ID, "password"),
    "signin_button": (By.CSS_SELECTOR, '[data-litms-control-urn="login-submit"]'), # Or type="submit"
    "start_post_button": (By.CSS_SELECTOR, 'button.share-box__open'), # Example, verify this
    "post_textarea": (By.CSS_SELECTOR, '.ql-editor[contenteditable="true"]'), # Example, verify this
    "post_button": (By.CSS_SELECTOR, 'button.share-actions__primary-action'), # Example, verify this
    "analytics_impressions": (By.CSS_SELECTOR, '[data-test-id="impression-count"]'), # Example
    "analytics_reactions": (By.CSS_SELECTOR, '[data-test-id="social-actions-reactions"]'), # Example
    "analytics_comments": (By.CSS_SELECTOR, '[data-test-id="social-actions-comments"]'), # Example
    "analytics_shares": (By.CSS_SELECTOR, '[data-test-id="social-actions-shares"]') # Example
}

class LinkedInStrategy(BaseSocialStrategy):
    """Strategy for interacting with LinkedIn platform."""
    
    def __init__(self, driver, config):
        """Initialize LinkedIn strategy."""
        super().__init__(driver, config)
        self.base_url = "https://linkedin.com"
        self.login_url = f"{self.base_url}/login"
        self.api_url = "https://api.linkedin.com/v2"
        self.selectors = SELECTORS
        
    def login(self) -> bool:
        """Log into LinkedIn account."""
        try:
            if not navigate_to(self.driver, self.login_url, source=self._source):
                return False
                
            # Enter email
            if not safe_send_keys(
                self.driver,
                self.selectors["username_input"],
                self.config["username"],
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
                
            # Click sign in
            if not safe_click(
                self.driver,
                self.selectors["signin_button"],
                source=self._source
            ):
                return False
                
            return self.check_login_status()
            
        except Exception as e:
            log_event("error", f"Login failed: {str(e)}", {"source": self._source})
            return False
            
    def create_post(self, content: Dict[str, Any]) -> bool:
        """Create a new LinkedIn post."""
        try:
            # Click start post button
            if not safe_click(
                self.driver,
                self.selectors["start_post_button"],
                source=self._source
            ):
                return False
                
            # Enter post text
            if not safe_send_keys(
                self.driver,
                self.selectors["post_textarea"],
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
                 if not self.add_tags(tags, self.selectors["post_textarea"]):
                    return False
                    
            # Schedule post - LinkedIn UI scheduling might be complex/premium
            if schedule_time := content.get("schedule_time"):
                 log_event("warning", "Scheduling via UI not directly supported in this base implementation.", {"source": self._source})
                 # Add LinkedIn-specific scheduling logic if available
                 # if not self.schedule_post(schedule_time): return False
                    
            # Click post button
            if not safe_click(
                self.driver,
                self.selectors["post_button"],
                source=self._source
            ):
                return False
                
            log_event("post", "LinkedIn post created successfully", {"source": self._source})
            return True
            
        except Exception as e:
            log_event("error", f"Failed to create post: {str(e)}", {"source": self._source})
            return False
            
    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get analytics for a specific LinkedIn post."""
        # Note: LinkedIn analytics via Selenium might require navigating specific analytics pages.
        try:
            # Example URL, likely needs adjustment
            analytics_url = f"{self.base_url}/analytics/post/{post_id}"
            if not navigate_to(self.driver, analytics_url, source=self._source):
                return {}
                
            metrics = {}
            
            # Get impression count
            impressions = wait_for_element(self.driver, self.selectors["analytics_impressions"], source=self._source)
            if impressions:
                metrics["impressions"] = int(impressions.text.replace(",", ""))
                
            # Get engagement metrics
            engagement_selectors = {
                "reactions": self.selectors["analytics_reactions"],
                "comments": self.selectors["analytics_comments"],
                "shares": self.selectors["analytics_shares"]
            }
            
            for metric, selector in engagement_selectors.items():
                element = wait_for_element(self.driver, selector, source=self._source)
                if element:
                    # Parsing might be needed if text includes labels e.g., "15 reactions"
                    try: 
                        metrics[metric] = int(element.text.split()[0].replace(",", ""))
                    except (ValueError, IndexError): 
                         log_event("warning", f"Could not parse int from analytics element {metric}: {element.text}", {"source": self._source})
            
            if metrics:                
                log_event("analytics", f"Retrieved analytics for post {post_id}", {"source": self._source})
            else:
                log_event("warning", f"Could not find any analytics elements for post {post_id}", {"source": self._source})
                
            return metrics
            
        except Exception as e:
            log_event("error", f"Failed to get post analytics: {str(e)}", {"source": self._source})
            return {}
    
    def post_update(self, content: str) -> bool:
        """
        Post a text update to LinkedIn.
        
        Args:
            content: The content to post
            
        Returns:
            bool: True if successful
        """
        try:
            # Prepare the post data
            post_data = {
                "author": f"urn:li:person:{self._get_user_id()}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Make the API request
            response = requests.post(
                f"{self.api_url}/ugcPosts",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                },
                json=post_data
            )
            
            if response.status_code == 201:
                logger.info("Successfully posted update to LinkedIn")
                return True
            else:
                logger.error(f"Failed to post update: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting update to LinkedIn: {str(e)}")
            return False
    
    def post_article(self, content: str, title: Optional[str] = None) -> bool:
        """
        Post an article to LinkedIn.
        
        Args:
            content: The article content
            title: Optional article title
            
        Returns:
            bool: True if successful
        """
        try:
            # Prepare the article data
            article_data = {
                "author": f"urn:li:person:{self._get_user_id()}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content[:1300]  # LinkedIn has a character limit
                        },
                        "shareMediaCategory": "ARTICLE",
                        "media": [{
                            "status": "READY",
                            "description": {
                                "text": content[:200]  # Short description
                            },
                            "originalUrl": self._get_blog_url(),
                            "title": {
                                "text": title or "Development Log"
                            }
                        }]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Make the API request
            response = requests.post(
                f"{self.api_url}/ugcPosts",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0"
                },
                json=article_data
            )
            
            if response.status_code == 201:
                logger.info("Successfully posted article to LinkedIn")
                return True
            else:
                logger.error(f"Failed to post article: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting article to LinkedIn: {str(e)}")
            return False
    
    def _get_user_id(self) -> str:
        """Get the current user's LinkedIn ID."""
        try:
            response = requests.get(
                f"{self.api_url}/me",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Restli-Protocol-Version": "2.0.0"
                }
            )
            
            if response.status_code == 200:
                return response.json().get("id")
            else:
                raise Exception(f"Failed to get user ID: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting user ID: {str(e)}")
            raise
    
    def _get_blog_url(self) -> str:
        """Get the blog URL for article links."""
        return "https://blog.dream.os"  # Replace with your actual blog URL 

if __name__ == "__main__":
    # Example usage: Run & Debug
    import os
    from datetime import datetime, timedelta
    import json
    import logging
    from tests.utils.test_utils import setup_driver
    try:
        from config import settings
        settings_available = True
    except ImportError:
        settings_available = False
        settings = None # Define settings as None if import fails
        logging.warning("config.settings not found, using os.getenv/defaults for demo.")

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    def demo_linkedin_capabilities():
        """Demonstrate LinkedIn-specific capabilities."""
        print("\n=== LinkedIn Strategy Capability Demo ===")
        driver = setup_driver()
        
        # Get config, prioritizing settings -> os.getenv -> defaults
        def _get_demo_config(key, env_var, default):
            if settings_available and hasattr(settings, 'LINKEDIN_CONFIG') and key in settings.LINKEDIN_CONFIG:
                return settings.LINKEDIN_CONFIG[key]
            return os.getenv(env_var, default)

        config_dict = {
            "username": _get_demo_config("username", "LINKEDIN_USERNAME", "test_user"),
            "password": _get_demo_config("password", "LINKEDIN_PASSWORD", "test_pass"),
            "api_key": _get_demo_config("api_key", "LINKEDIN_API_KEY", "test_key"), # Assumes these keys exist in settings.LINKEDIN_CONFIG
            "api_secret": _get_demo_config("api_secret", "LINKEDIN_API_SECRET", "test_secret"),
            "access_token": _get_demo_config("access_token", "LINKEDIN_ACCESS_TOKEN", "test_token"),
            "timeout": 15, # Example demo timeout
            "max_retries": 2 # Example demo retries
        }
        
        try:
            strategy = LinkedInStrategy(driver, config_dict)
            print("✓ Initialized LinkedIn Strategy")
            
            # 1. Browser-based Operations
            print("\n1. Testing Browser-based Operations:")
            
            # Test login
            if strategy.login():
                print("  ✓ Login successful")
            else:
                print("  ✗ Login failed")
                return
            
            # Test post creation with rich content
            post_content = {
                "text": "Check out our latest development update! #tech #innovation",
                "media": ["path/to/feature_demo.gif"],
                "tags": ["tech", "innovation", "development"],
                "schedule_time": datetime.now() + timedelta(hours=2)
            }
            
            if strategy.create_post(post_content):
                print("  ✓ Rich post created successfully")
            else:
                print("  ✗ Rich post creation failed")
            
            # 2. API-based Operations
            print("\n2. Testing API-based Operations:")
            
            # Test simple text update
            update_text = "Quick update: Just shipped a new feature! 🚀"
            if strategy.post_update(update_text):
                print("  ✓ Text update posted via API")
            else:
                print("  ✗ Text update failed")
            
            # Test article posting
            article_content = {
                "title": "Implementing Social Media Automation",
                "content": """
                In this article, we'll explore best practices for social media automation.
                
                Key points:
                1. Choose the right tools
                2. Maintain authentic engagement
                3. Monitor performance metrics
                
                Read more on our blog!
                """
            }
            
            if strategy.post_article(article_content["content"], article_content["title"]):
                print("  ✓ Article posted successfully")
            else:
                print("  ✗ Article posting failed")
            
            # 3. Analytics
            print("\n3. Testing Analytics Retrieval:")
            
            # Get analytics for a test post
            test_post_id = "123456789"
            analytics = strategy.get_analytics(test_post_id)
            if analytics:
                print("  ✓ Analytics retrieved successfully:")
                print(json.dumps(analytics, indent=2))
            else:
                print("  ✗ Analytics retrieval failed")
            
        except Exception as e:
            print(f"✗ Error during demo: {str(e)}")
            
        finally:
            driver.quit()
            print("\n=== Demo Complete ===\n")
    
    # Run the demo
    demo_linkedin_capabilities() 