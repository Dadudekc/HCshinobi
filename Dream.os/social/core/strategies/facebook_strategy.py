"""Facebook platform strategy implementation."""

from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import time
import logging

from .base_strategy import BaseSocialStrategy
from core.exceptions.strategy_exceptions import LoginError, PostError
from utils.selenium_utils import wait_for_element, safe_click, safe_send_keys, navigate_to
from utils.logging_utils import log_event, setup_logging

# Centralized Selectors for FacebookStrategy
SELECTORS = {
    "email_input": (By.ID, "email"),
    "password_input": (By.ID, "pass"),
    "login_button": (By.NAME, "login"),
    "create_post_button": (By.CSS_SELECTOR, '[aria-label="Create post"]'), # Might need refinement
    "post_textarea": (By.CSS_SELECTOR, '[aria-label="What\'s on your mind?"]'), # Might need refinement
    "post_button": (By.CSS_SELECTOR, '[aria-label="Post"]'),
    "analytics_reach": (By.CSS_SELECTOR, '[aria-label="Post reach"]'), # Example, actual selectors vary greatly
    "analytics_likes": (By.CSS_SELECTOR, '[aria-label="Like count"]'), # Example
    "analytics_comments": (By.CSS_SELECTOR, '[aria-label="Comment count"]'), # Example
    "analytics_shares": (By.CSS_SELECTOR, '[aria-label="Share count"]') # Example
}

logger = logging.getLogger(__name__)

class FacebookStrategy(BaseSocialStrategy):
    """Strategy for interacting with Facebook platform."""
    
    def __init__(self, driver, config):
        """Initialize Facebook strategy."""
        super().__init__(driver, config)
        self.base_url = "https://facebook.com"
        self.login_url = f"{self.base_url}/login"
        self.selectors = SELECTORS
        
    def login(self) -> bool:
        """Log into Facebook account."""
        try:
            if not navigate_to(self.driver, self.login_url, source=self._source):
                return False
                
            # Enter email
            if not safe_send_keys(
                self.driver,
                self.selectors["email_input"],
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
                
            # Click login
            if not safe_click(
                self.driver,
                self.selectors["login_button"],
                source=self._source
            ):
                return False
                
            # Note: Facebook often has intermediate steps (2FA, save browser)
            # Need robust handling here in a real scenario
            return self.check_login_status()
            
        except Exception as e:
            log_event("error", f"Login failed: {str(e)}", {"source": self._source})
            return False
            
    def create_post(self, content: Dict[str, Any]) -> bool:
        """Create a new Facebook post."""
        try:
            # Navigate/Click to open the post composer
            # Facebook's composer might be directly on the feed or require a click
            if not safe_click(
                self.driver,
                self.selectors["create_post_button"],
                source=self._source
            ):
                log_event("warning", "Could not click create post button directly, might be overlay.", {"source": self._source})
                # Add alternative ways to open composer if needed

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
                if not self.upload_media(media_files): # Uses base method
                    return False
                    
            # Add hashtags (append to text area)
            if tags := content.get("tags"):
                 if not self.add_tags(tags, self.selectors["post_textarea"]): # Pass selector
                    return False
                    
            # Schedule post (check if Facebook supports this via UI)
            if schedule_time := content.get("schedule_time"):
                 log_event("warning", "Scheduling via UI not directly supported in this base implementation.", {"source": self._source})
                 # Add Facebook-specific scheduling logic if available via UI
                 # if not self.schedule_post(schedule_time): return False
                    
            # Click post button
            if not safe_click(
                self.driver,
                self.selectors["post_button"],
                source=self._source
            ):
                return False
                
            log_event("post", "Facebook post created successfully", {"source": self._source})
            return True
            
        except Exception as e:
            log_event("error", f"Failed to create post: {str(e)}", {"source": self._source})
            return False
            
    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get analytics for a specific Facebook post (highly variable)."""
        # NOTE: Accessing Facebook post analytics via Selenium is unreliable 
        # and depends heavily on page structure (Creator Studio, Business Suite, etc.)
        # This is a basic placeholder structure.
        try:
            # Construct a plausible URL (this will likely NOT work without refinement)
            analytics_url = f"{self.base_url}/ads/manager/account_settings/information/?pid={post_id}" # Example URL pattern
            if not navigate_to(self.driver, analytics_url, source=self._source):
                 log_event("warning", f"Could not navigate to hypothetical analytics URL: {analytics_url}", {"source": self._source})
                 return {}
                
            metrics = {}
            
            # Example: Try to find reach
            reach = wait_for_element(self.driver, self.selectors["analytics_reach"], timeout=5, source=self._source)
            if reach:
                metrics["reach"] = int(reach.text.replace(",", ""))
                
            # Example: Try to find engagement metrics
            engagement_selectors = {
                "likes": self.selectors["analytics_likes"],
                "comments": self.selectors["analytics_comments"],
                "shares": self.selectors["analytics_shares"]
            }
            
            for metric, selector in engagement_selectors.items():
                element = wait_for_element(self.driver, selector, timeout=5, source=self._source)
                if element:
                    metrics[metric] = int(element.text.replace(",", ""))
                    
            if metrics:
                 log_event("analytics", f"Retrieved partial/example analytics for post {post_id}", {"source": self._source})
            else:
                 log_event("warning", f"Could not find any known analytics elements for post {post_id}", {"source": self._source})
                 
            return metrics
            
        except Exception as e:
            log_event("error", f"Failed to get post analytics: {str(e)}", {"source": self._source})
            return {}

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

    def demo_facebook_capabilities():
        """Demonstrate Facebook-specific capabilities."""
        print("\n=== Facebook Strategy Capability Demo ===")
        driver = setup_driver()

        # Get config, prioritizing settings -> os.getenv -> defaults
        def _get_demo_config(key, env_var, default):
            # Assuming facebook creds might be directly in settings or nested
            # Adjust attribute access as needed based on config/settings.py structure
            config_source = getattr(settings, 'FACEBOOK_CONFIG', {}) if settings_available else {}
            if key in config_source:
                 return config_source[key]
            # Fallback to top-level settings attributes if not nested
            if settings_available and hasattr(settings, env_var):
                 return getattr(settings, env_var)
            # Fallback to os.getenv
            return os.getenv(env_var, default)

        config_dict = {
            "username": _get_demo_config("username", "FACEBOOK_USERNAME", "test_user"),
            "password": _get_demo_config("password", "FACEBOOK_PASSWORD", "test_pass"),
            "timeout": 15, # Example demo timeout
            "max_retries": 2 # Example demo retries
        }
        
        try:
            strategy = FacebookStrategy(driver, config_dict)
            print("✓ Initialized Facebook Strategy")
            
            # 1. Authentication
            print("\n1. Testing Authentication:")
            if strategy.login():
                print("  ✓ Login successful")
            else:
                print("  ✗ Login failed")
                return
            
            # 2. Content Creation
            print("\n2. Testing Content Creation:")
            
            # Test text-only post
            text_post = {
                "text": "Exciting news! We've just released a new feature. Stay tuned for more updates!"
            }
            if strategy.create_post(text_post):
                print("  ✓ Text post created successfully")
            else:
                print("  ✗ Text post creation failed")
            
            # Test rich media post
            rich_post = {
                "text": "Check out our latest development milestone! 🎉",
                "media": ["path/to/screenshot.png", "path/to/demo.gif"],
                "tags": ["tech", "development", "innovation"],
                "schedule_time": datetime.now() + timedelta(hours=3)
            }
            
            if strategy.create_post(rich_post):
                print("  ✓ Rich media post created successfully")
            else:
                print("  ✗ Rich media post creation failed")
            
            # 3. Analytics
            print("\n3. Testing Analytics Retrieval:")
            
            # Get analytics for recent posts
            test_post_ids = ["123456789", "987654321"]
            for post_id in test_post_ids:
                print(f"\n  Retrieving analytics for post {post_id}:")
                analytics = strategy.get_analytics(post_id)
                if analytics:
                    print("    ✓ Analytics retrieved successfully:")
                    print(json.dumps(analytics, indent=4))
                else:
                    print(f"    ✗ Failed to get analytics for post {post_id}")
            
        except Exception as e:
            print(f"✗ Error during demo: {str(e)}")
            
        finally:
            driver.quit()
            print("\n=== Demo Complete ===\n")
    
    # Run the demo
    demo_facebook_capabilities() 