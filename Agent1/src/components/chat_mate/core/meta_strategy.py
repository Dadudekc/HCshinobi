"""
Meta Platform Strategy - Common functionality for Meta platforms (Facebook, Instagram)
"""

from typing import Dict, Any, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_platform_strategy import BasePlatformStrategy

class MetaStrategy(BasePlatformStrategy):
    """
    Base class for Meta platforms (Facebook, Instagram).
    Implements common functionality shared between Facebook and Instagram.
    """
    
    def __init__(self, platform: str, driver: Optional[webdriver.Chrome] = None):
        super().__init__(platform, driver)
        self.meta_config = {
            "login_attempts": 3,
            "post_attempts": 3,
            "engagement_attempts": 3,
            "max_daily_follows": 50,
            "max_daily_likes": 100,
            "max_daily_comments": 30
        }
        
    def login(self) -> bool:
        """Meta-specific login implementation"""
        logger.info(f" Initiating login process for {self.platform.capitalize()}.")
        self.driver.get(self.login_url)
        self._wait()
        
        # Try cookie-based login first
        self.cookie_manager.load_cookies(self.driver, self.platform)
        self.driver.refresh()
        self._wait()
        
        if self.is_logged_in():
            logger.info(f" Logged into {self.platform.capitalize()} via cookies.")
            write_json_log(self.platform, "successful", tags=["cookie_login"])
            return True
            
        # Fallback to credential login
        if not self.email or not self.password:
            logger.warning(f"️ No {self.platform} credentials provided.")
            write_json_log(self.platform, "failed", tags=["auto_login"], 
                         ai_output="Missing credentials.")
            return False
            
        try:
            # Meta platforms use similar login form structure
            username_field = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.visibility_of_element_located((By.NAME, "username"))
            )
            password_field = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.visibility_of_element_located((By.NAME, "password"))
            )
            
            username_field.clear()
            password_field.clear()
            username_field.send_keys(self.email)
            password_field.send_keys(self.password)
            password_field.send_keys(Keys.RETURN)
            
            logger.info(f" Submitted credentials for {self.platform.capitalize()}.")
            WebDriverWait(self.driver, DEFAULT_WAIT).until(EC.url_changes(self.login_url))
            self._wait((5, 10))
            
        except Exception as e:
            logger.error(f" Error during {self.platform.capitalize()} auto-login: {e}")
            write_json_log(self.platform, "failed", tags=["auto_login"], ai_output=str(e))
            
        if not self.is_logged_in():
            logger.warning(f"️ Auto-login failed for {self.platform.capitalize()}. "
                         "Awaiting manual login...")
            if self.cookie_manager.wait_for_manual_login(self.driver, 
                                                       self.is_logged_in, 
                                                       self.platform):
                write_json_log(self.platform, "successful", tags=["manual_login"])
            else:
                msg = "Manual login failed."
                logger.error(f" {msg} for {self.platform.capitalize()}.")
                write_json_log(self.platform, "failed", tags=["manual_login"], 
                             ai_output=msg)
                return False
                
        self.cookie_manager.save_cookies(self.driver, self.platform)
        logger.info(f" Logged in successfully to {self.platform.capitalize()}.")
        write_json_log(self.platform, "successful", tags=["auto_login"])
        return True
        
    def is_logged_in(self) -> bool:
        """Meta-specific login check"""
        self.driver.get(self.settings_url)
        WebDriverWait(self.driver, DEFAULT_WAIT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        self._wait((3, 5))
        if "login" not in self.driver.current_url.lower():
            logger.info(f" {self.platform.capitalize()} login confirmed via settings.")
            return True
        logger.debug(f" {self.platform.capitalize()} login check failed.")
        return False
        
    def post_content(self, content: str, **kwargs) -> bool:
        """Meta-specific post implementation"""
        logger.info(f" Attempting to post on {self.platform.capitalize()}.")
        if not self.is_logged_in():
            msg = "Not logged in."
            logger.warning(f"️ Cannot post to {self.platform.capitalize()}: {msg}")
            write_json_log(self.platform, "failed", tags=["post"], ai_output=msg)
            return False
            
        # Generate content using AI if needed
        if kwargs.get("use_ai", True):
            content = self.ai_agent.ask(
                prompt=content,
                additional_context=f"This post reflects my authentic, raw, and strategic voice.",
                metadata={"platform": self.platform.capitalize(), "persona": "Victor"}
            ) or content
            
        try:
            self.driver.get(self.post_url)
            self._wait((5, 8))
            
            # Meta platforms use similar post creation UI
            create_post_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Create a post']"))
            )
            create_post_button.click()
            self._wait((2, 3))
            
            post_box = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@role='textbox']"))
            )
            post_box.send_keys(content)
            self._wait((2, 3))
            
            post_button = WebDriverWait(self.driver, DEFAULT_WAIT).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Post']"))
            )
            post_button.click()
            self._wait((5, 8))
            
            logger.info(f" Post published on {self.platform.capitalize()}.")
            write_json_log(self.platform, "successful", tags=["post"])
            return True
            
        except Exception as e:
            logger.error(f" Failed to post on {self.platform.capitalize()}: {e}")
            write_json_log(self.platform, "failed", tags=["post"], ai_output=str(e))
            return False
            
    def like_posts(self, **kwargs) -> bool:
        """Meta-specific like implementation"""
        max_likes = kwargs.get("max_likes", self.meta_config["max_daily_likes"])
        liked = 0
        
        try:
            trending_url = social_config.get_platform_url(self.platform, "trending")
            self.driver.get(trending_url)
            self._wait((5, 8))
            
            posts = self.driver.find_elements(By.CSS_SELECTOR, 
                                           "div[data-pagelet='FeedUnit']")
            for post in posts:
                if liked >= max_likes:
                    break
                try:
                    like_button = post.find_element(By.XPATH, 
                                                  ".//div[contains(@aria-label, 'Like')]")
                    like_button.click()
                    logger.info(f"️ Liked a post on {self.platform.capitalize()}.")
                    liked += 1
                    self._wait((2, 4))
                except Exception as e:
                    logger.warning(f"️ Could not like a post: {e}")
                    
            return liked > 0
            
        except Exception as e:
            logger.error(f" Failed to like posts on {self.platform.capitalize()}: {e}")
            return False
            
    def comment_on_posts(self, comments: List[str], **kwargs) -> bool:
        """Meta-specific comment implementation"""
        max_comments = kwargs.get("max_comments", 
                                self.meta_config["max_daily_comments"])
        commented = 0
        
        try:
            trending_url = social_config.get_platform_url(self.platform, "trending")
            self.driver.get(trending_url)
            self._wait((5, 8))
            
            posts = self.driver.find_elements(By.CSS_SELECTOR, 
                                           "div[data-pagelet='FeedUnit']")
            for post in posts:
                if commented >= max_comments:
                    break
                try:
                    comment_button = post.find_element(By.XPATH, 
                                                     ".//div[contains(@aria-label, 'Comment')]")
                    comment_button.click()
                    self._wait((1, 2))
                    
                    comment_box = post.find_element(By.XPATH, 
                                                  ".//div[@role='textbox']")
                    comment = random.choice(comments)
                    comment_box.send_keys(comment)
                    comment_box.send_keys(Keys.RETURN)
                    
                    logger.info(f"️ Commented on a post on {self.platform.capitalize()}.")
                    commented += 1
                    self._wait((2, 4))
                except Exception as e:
                    logger.warning(f"️ Could not comment on a post: {e}")
                    
            return commented > 0
            
        except Exception as e:
            logger.error(f" Failed to comment on posts on {self.platform.capitalize()}: {e}")
            return False
            
    def follow_users(self, **kwargs) -> bool:
        """Meta-specific follow implementation"""
        max_follows = kwargs.get("max_follows", 
                               self.meta_config["max_daily_follows"])
        followed = 0
        
        try:
            trending_url = social_config.get_platform_url(self.platform, "trending")
            self.driver.get(trending_url)
            self._wait((5, 8))
            
            users = self.driver.find_elements(By.CSS_SELECTOR, 
                                           "div[data-pagelet='ProfileUnit']")
            for user in users:
                if followed >= max_follows:
                    break
                try:
                    follow_button = user.find_element(By.XPATH, 
                                                    ".//div[contains(@aria-label, 'Follow')]")
                    follow_button.click()
                    logger.info(f"️ Followed a user on {self.platform.capitalize()}.")
                    followed += 1
                    self._wait((2, 4))
                except Exception as e:
                    logger.warning(f"️ Could not follow user: {e}")
                    
            return followed > 0
            
        except Exception as e:
            logger.error(f" Failed to follow users on {self.platform.capitalize()}: {e}")
            return False 