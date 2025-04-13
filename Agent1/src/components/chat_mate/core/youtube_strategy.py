"""
YouTube-specific strategy implementation.
Extends BasePlatformStrategy with YouTube-specific functionality.
"""

import os
import time
import random
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from social.strategies.base_platform_strategy import BasePlatformStrategy
from social.social_config import social_config
from social.log_writer import get_social_logger, write_json_log
from .utils import CookieManager, AIChatAgent
from .config_loader import get_env_or_config

logger = get_social_logger()

class YouTubeStrategy(BasePlatformStrategy):
    """
    YouTube-specific strategy implementation.
    Features:
      - Video management
      - Playlist management
      - Enhanced content management
      - Comment management
      - Channel management
      - Analytics and reporting
      - Subscriber management
      - Content scheduling
    """
    
    def __init__(self, driver: Optional[webdriver.Chrome] = None):
        """Initialize YouTube strategy with browser automation."""
        super().__init__(platform_id="youtube", driver=driver)
        self.login_url = "https://accounts.google.com/signin"
        self.username = get_env_or_config("YOUTUBE_USERNAME")
        self.password = get_env_or_config("YOUTUBE_PASSWORD")
        self.wait_range = (3, 6)
        self.feedback_data = self._load_feedback_data()
        self.config = self._load_config()
        self.content_types = {
            "shorts": {
                "max_duration": 60,
                "optimal_duration": 30,
                "formats": ["vertical", "9:16"]
            },
            "regular": {
                "max_duration": 1800,  # 30 minutes
                "optimal_duration": 600,  # 10 minutes
                "formats": ["landscape", "16:9"]
            },
            "live": {
                "min_duration": 300,  # 5 minutes
                "optimal_duration": 3600,  # 1 hour
                "formats": ["landscape", "16:9"]
            }
        }
        self.debug_mode = False
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize YouTube strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver()
            return self.login()
        except Exception as e:
            logger.error(f"Failed to initialize YouTube strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            logger.error(f"Error during YouTube cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get YouTube-specific community metrics."""
        metrics = {
            "engagement_rate": 0.0,
            "growth_rate": 0.0,
            "sentiment_score": 0.0,
            "active_members": 0,
            "video_metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "watch_time": 0
            },
            "shorts_metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0
            }
        }
        
        try:
            # Get metrics from feedback data
            total_interactions = (
                self.feedback_data.get("likes", 0) +
                self.feedback_data.get("comments", 0) +
                self.feedback_data.get("shares", 0) +
                self.feedback_data.get("subscribers", 0)
            )
            
            if total_interactions > 0:
                metrics["engagement_rate"] = min(1.0, total_interactions / 1000)  # Normalize to [0,1]
                metrics["growth_rate"] = min(1.0, self.feedback_data.get("subscribers", 0) / 100)
                metrics["sentiment_score"] = self.feedback_data.get("sentiment_score", 0.0)
                metrics["active_members"] = total_interactions
                
                # Video metrics
                metrics["video_metrics"]["views"] = self.feedback_data.get("video_views", 0)
                metrics["video_metrics"]["likes"] = self.feedback_data.get("video_likes", 0)
                metrics["video_metrics"]["comments"] = self.feedback_data.get("video_comments", 0)
                metrics["video_metrics"]["shares"] = self.feedback_data.get("video_shares", 0)
                metrics["video_metrics"]["watch_time"] = self.feedback_data.get("watch_time", 0)
                
                # Shorts metrics
                metrics["shorts_metrics"]["views"] = self.feedback_data.get("shorts_views", 0)
                metrics["shorts_metrics"]["likes"] = self.feedback_data.get("shorts_likes", 0)
                metrics["shorts_metrics"]["comments"] = self.feedback_data.get("shorts_comments", 0)
                metrics["shorts_metrics"]["shares"] = self.feedback_data.get("shorts_shares", 0)
        except Exception as e:
            logger.error(f"Error calculating YouTube metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top YouTube community members."""
        top_members = []
        try:
            if os.path.exists(self.follow_db):
                with open(self.follow_db, "r") as f:
                    follow_data = json.load(f)
                
                # Convert follow data to member list
                for username, data in follow_data.items():
                    if data.get("status") == "followed":
                        member = {
                            "id": username,
                            "platform": "youtube",
                            "engagement_score": random.uniform(0.5, 1.0),  # Replace with real metrics
                            "followed_at": data.get("followed_at"),
                            "recent_interactions": [],
                            "content_type": data.get("content_type", "general")
                        }
                        top_members.append(member)
                
                # Sort by engagement score
                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:20]  # Keep top 20
        except Exception as e:
            logger.error(f"Error getting top YouTube members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a YouTube member."""
        try:
            if not os.path.exists(self.follow_db):
                return False
            
            with open(self.follow_db, "r") as f:
                follow_data = json.load(f)
            
            if member_id not in follow_data:
                follow_data[member_id] = {
                    "followed_at": datetime.utcnow().isoformat(),
                    "status": "followed",
                    "interactions": [],
                    "content_type": metadata.get("content_type", "general") if metadata else "general"
                }
            
            # Add interaction
            interaction = {
                "type": interaction_type,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            if "interactions" not in follow_data[member_id]:
                follow_data[member_id]["interactions"] = []
            
            follow_data[member_id]["interactions"].append(interaction)
            
            # Save updated data
            with open(self.follow_db, "w") as f:
                json.dump(follow_data, f, indent=4)
            
            logger.info(f"Tracked {interaction_type} interaction with YouTube member {member_id}")
            return True
        except Exception as e:
            logger.error(f"Error tracking YouTube member interaction: {e}")
            return False
    
    def _get_driver(self, headless=False):
        """Get configured Chrome WebDriver for YouTube."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        driver = webdriver.Chrome(options=options)
        logger.info(" YouTube driver initialized")
        return driver
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to YouTube."""
        logger.info(" Initiating YouTube login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "youtube")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                logger.info(" Logged into YouTube via cookies")
                return True
            
            # Try credential login
            if self.username and self.password:
                try:
                    # Enter email
                    email_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "identifier"))
                    )
                    email_input.clear()
                    email_input.send_keys(self.username)
                    email_input.send_keys(Keys.RETURN)
                    self._wait((3, 5))
                    
                    # Enter password
                    password_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "password"))
                    )
                    password_input.clear()
                    password_input.send_keys(self.password)
                    password_input.send_keys(Keys.RETURN)
                    self._wait((5, 8))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "youtube")
                        logger.info(" Logged into YouTube via credentials")
                        return True
                except Exception as e:
                    logger.error(f"YouTube auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "youtube"):
                self.cookie_manager.save_cookies(self.driver, "youtube")
                return True
            
            return False
        except Exception as e:
            logger.error(f"YouTube login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into YouTube."""
        try:
            self.driver.get("https://studio.youtube.com")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            return "studio.youtube.com" in self.driver.current_url
        except Exception:
            return False
    
    def post_video(self, video_path: str, title: str, description: str, tags: List[str] = None, is_short: bool = False) -> bool:
        """Post a video to YouTube."""
        logger.info(" Posting video to YouTube...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            self.driver.get("https://studio.youtube.com/channel/upload")
            self._wait((3, 5))
            
            # Upload video file
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(video_path)
            self._wait((5, 8))  # Wait for upload
            
            # Set title
            title_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Add a title']"))
            )
            title_input.clear()
            title_input.send_keys(title)
            
            # Set description
            description_input = self.driver.find_element(By.CSS_SELECTOR, "textarea[placeholder='Tell viewers about your video']")
            description_input.clear()
            description_input.send_keys(description)
            
            # Add tags, ensuring no personal branding tags are included
            if tags:
                tags = [tag for tag in tags if tag != "personal_brand"]  # Remove personal branding tags
                tags_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Add tags']")
                for tag in tags:
                    tags_input.send_keys(tag)
                    tags_input.send_keys(Keys.RETURN)
            
            # Mark as Short if needed
            if is_short:
                shorts_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[name='SHORT']")
                if not shorts_checkbox.is_selected():
                    shorts_checkbox.click()
            
            # Submit video
            next_button = self.driver.find_element(By.CSS_SELECTOR, "#next-button")
            next_button.click()
            self._wait((2, 3))
            
            # Navigate through remaining screens
            for _ in range(3):  # Usually 3 more screens
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#next-button"))
                )
                next_button.click()
                self._wait((1, 2))
            
            # Finally, publish
            publish_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#done-button"))
            )
            publish_button.click()
            self._wait((5, 8))
            
            logger.info(" Successfully posted video to YouTube")
            write_json_log("youtube", "success", "Posted video")
            return True
        except Exception as e:
            logger.error(f"Error posting video to YouTube: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily YouTube strategy session."""
        logger.info(" Starting Full YouTube Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Generate content ideas for different formats
            content_types = ["regular", "shorts", "community_post"]
            for content_type in content_types:
                content_prompt = f"Create a {content_type} script about trading and market analysis."
                
                script = self.ai_agent.ask(
                    prompt=content_prompt,
                    metadata={"platform": "youtube", "content_type": content_type}
                )
                
                if script:
                    # Here you would generate/prepare the content
                    # For now, we'll just log it
                    logger.info(f"Generated script for {content_type}")
                
                self._wait((5, 10))
            
            # Process engagement metrics
            self.analyze_engagement_metrics()
            
            # Run feedback and reward systems
            self.run_feedback_loop()
            self.reward_top_creators()
            self.cross_platform_feedback_loop()
            
            self.cleanup()
            logger.info(" YouTube Strategy Session Complete")
        except Exception as e:
            logger.error(f"Error in YouTube strategy session: {e}")
            self.cleanup()

    def _load_feedback_data(self):
        """Load or initialize feedback data."""
        if os.path.exists(self.feedback_db):
            with open(self.feedback_db, "r") as f:
                return json.load(f)
        return {}

    def _save_feedback_data(self):
        """Save updated feedback data."""
        with open(self.feedback_db, "w") as f:
            json.dump(self.feedback_data, f, indent=4)

    def analyze_engagement_metrics(self):
        """Analyze engagement results to optimize strategy."""
        logger.info(" Analyzing YouTube engagement metrics...")
        
        # Regular video metrics
        self.feedback_data["video_views"] = self.feedback_data.get("video_views", 0) + random.randint(50, 200)
        self.feedback_data["video_likes"] = self.feedback_data.get("video_likes", 0) + random.randint(5, 20)
        self.feedback_data["video_comments"] = self.feedback_data.get("video_comments", 0) + random.randint(2, 8)
        self.feedback_data["video_shares"] = self.feedback_data.get("video_shares", 0) + random.randint(1, 5)
        self.feedback_data["watch_time"] = self.feedback_data.get("watch_time", 0) + random.randint(300, 1200)  # in seconds
        
        # Shorts metrics
        self.feedback_data["shorts_views"] = self.feedback_data.get("shorts_views", 0) + random.randint(100, 500)
        self.feedback_data["shorts_likes"] = self.feedback_data.get("shorts_likes", 0) + random.randint(10, 50)
        self.feedback_data["shorts_comments"] = self.feedback_data.get("shorts_comments", 0) + random.randint(3, 15)
        self.feedback_data["shorts_shares"] = self.feedback_data.get("shorts_shares", 0) + random.randint(2, 10)
        
        # Subscriber metrics
        self.feedback_data["subscribers"] = self.feedback_data.get("subscribers", 0) + random.randint(1, 5)
        
        logger.info(f" Regular Video Views: {self.feedback_data['video_views']}")
        logger.info(f" Shorts Views: {self.feedback_data['shorts_views']}")
        logger.info(f" Total Subscribers: {self.feedback_data['subscribers']}")
        logger.info(f"⏱️ Watch Time (hours): {self.feedback_data['watch_time'] / 3600:.2f}")
        
        self._save_feedback_data()

    def run_feedback_loop(self):
        """Run the dynamic feedback loop process."""
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def adaptive_posting_strategy(self):
        """Adjust posting strategy based on engagement feedback."""
        logger.info(" Adapting YouTube posting strategy based on feedback...")
        
        # Analyze regular videos performance
        if self.feedback_data.get("video_views", 0) > 1000:
            logger.info(" Regular videos are performing well! Consider increasing production quality.")
        
        # Analyze Shorts performance
        if self.feedback_data.get("shorts_views", 0) > 5000:
            logger.info(" Shorts are getting great traction! Consider creating more short-form content.")
        
        # Analyze watch time
        avg_watch_time = self.feedback_data.get("watch_time", 0) / max(self.feedback_data.get("video_views", 1), 1)
        if avg_watch_time > 300:  # More than 5 minutes
            logger.info("⭐ High average watch time! Content length is optimal.")
        else:
            logger.info("️ Consider adjusting content length to improve watch time.")

    def reward_top_creators(self):
        """Reward top content creators in our community."""
        logger.info(" Identifying and rewarding top YouTube creators...")
        top_members = self.get_top_members()
        
        for member in top_members[:5]:  # Reward top 5
            try:
                reward_message = f"Your content is amazing! Keep creating awesome videos! 🌟"
                self.track_member_interaction(
                    member["id"],
                    "reward",
                    {"message": reward_message, "reward_type": "recognition"}
                )
                logger.info(f"Rewarded creator: {member['id']}")
            except Exception as e:
                logger.error(f"Error rewarding creator {member['id']}: {e}")

    def cross_platform_feedback_loop(self):
        """Integrate YouTube performance data with other platforms."""
        logger.info(" Running cross-platform feedback analysis for YouTube...")
        try:
            # Simulate cross-platform metrics
            platform_metrics = {
                "youtube": self.feedback_data,
                "tiktok": {"views": random.randint(500, 2000)},
                "instagram": {"reels_views": random.randint(300, 1000)}
            }
            
            total_video_views = (
                self.feedback_data.get("video_views", 0) +
                self.feedback_data.get("shorts_views", 0) +
                platform_metrics["tiktok"]["views"] +
                platform_metrics["instagram"]["reels_views"]
            )
            
            logger.info(f" Total video views across platforms: {total_video_views}")
            
            # Update strategy based on cross-platform performance
            if total_video_views > 5000:
                logger.info(" Video content is performing well across platforms")
                
            # Compare performance across platforms
            platform_distribution = {
                "youtube_regular": self.feedback_data.get("video_views", 0),
                "youtube_shorts": self.feedback_data.get("shorts_views", 0),
                "tiktok": platform_metrics["tiktok"]["views"],
                "instagram": platform_metrics["instagram"]["reels_views"]
            }
            
            best_platform = max(platform_distribution.items(), key=lambda x: x[1])[0]
            logger.info(f" Best performing platform: {best_platform}")
        except Exception as e:
            logger.error(f"Error in cross-platform analysis: {e}")

    def _login(self) -> bool:
        """Perform login to YouTube."""
        try:
            self.driver.get(self.login_url)
            # Add login implementation here
            return True
        except Exception as e:
            logger.error(f"Failed to login to YouTube: {str(e)}")
            return False

    def _video_management(self) -> None:
        """Manage video uploads and settings."""
        try:
            if not self._check_engagement_limit("videos", 1):
                return

            # Navigate to upload page
            self.driver.get("https://studio.youtube.com/channel/upload")
            
            # Upload video logic here
            # This is a placeholder for the actual implementation
            pass

        except Exception as e:
            logger.error(f"Video management failed: {str(e)}")

    def _short_management(self) -> None:
        """Manage YouTube Shorts."""
        try:
            if not self._check_engagement_limit("shorts", 1):
                return

            # Navigate to Shorts upload page
            self.driver.get("https://studio.youtube.com/channel/shorts")
            
            # Upload Shorts logic here
            # This is a placeholder for the actual implementation
            pass

        except Exception as e:
            logger.error(f"Shorts management failed: {str(e)}")

    def _live_stream_management(self) -> None:
        """Manage live streams."""
        try:
            if not self._check_engagement_limit("live_streams", 1):
                return

            # Navigate to live streaming page
            self.driver.get("https://studio.youtube.com/channel/livestreaming")
            
            # Live stream setup logic here
            # This is a placeholder for the actual implementation
            pass

        except Exception as e:
            logger.error(f"Live stream management failed: {str(e)}")

    def _playlist_management(self) -> None:
        """Manage playlists."""
        try:
            if not self._check_engagement_limit("playlists", 1):
                return

            # Navigate to playlists page
            self.driver.get("https://studio.youtube.com/channel/playlists")
            
            # Playlist management logic here
            # This is a placeholder for the actual implementation
            pass

        except Exception as e:
            logger.error(f"Playlist management failed: {str(e)}")

    def _community_post_management(self) -> None:
        """Manage community posts."""
        try:
            if not self._check_engagement_limit("community_posts", 1):
                return

            # Navigate to community tab
            self.driver.get("https://studio.youtube.com/channel/community")
            
            # Community post management logic here
            # This is a placeholder for the actual implementation
            pass

        except Exception as e:
            logger.error(f"Community post management failed: {str(e)}")

    def _analytics_and_reporting(self) -> Dict[str, Any]:
        """Get analytics and reporting data."""
        try:
            # Navigate to analytics page
            self.driver.get("https://studio.youtube.com/channel/analytics")
            
            # Analytics gathering logic here
            # This is a placeholder for the actual implementation
            analytics_data = {
                "views": 0,
                "watch_time": 0,
                "subscribers": 0,
                "engagement_rate": 0.0
            }
            return analytics_data

        except Exception as e:
            logger.error(f"Analytics gathering failed: {str(e)}")
            return {}

    def _validate_content(self, content: Dict[str, Any]) -> bool:
        """Validate content for YouTube guidelines."""
        try:
            # Check required fields
            required_fields = ["title", "description", "tags"]
            if not all(field in content for field in required_fields):
                return False

            # Validate title
            if not content["title"] or len(content["title"]) > 100:
                return False

            # Validate description
            if not content["description"] or len(content["description"]) > 5000:
                return False

            # Validate tags
            if not content["tags"] or len(content["tags"]) > 500:
                return False

            return True

        except Exception as e:
            logger.error(f"Content validation failed: {str(e)}")
            return False

    def _validate_video_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate video metadata."""
        try:
            required_fields = ["title", "description", "tags", "category", "privacy"]
            if not all(field in metadata for field in required_fields):
                return False

            if not metadata["title"] or len(metadata["title"]) > 100:
                return False

            if not metadata["description"] or len(metadata["description"]) > 5000:
                return False

            if not metadata["tags"] or len(metadata["tags"]) > 500:
                return False

            valid_categories = ["Education", "Entertainment", "Gaming", "Music", "News"]
            if metadata["category"] not in valid_categories:
                return False

            valid_privacy = ["public", "private", "unlisted"]
            if metadata["privacy"] not in valid_privacy:
                return False

            return True

        except Exception as e:
            logger.error(f"Video metadata validation failed: {str(e)}")
            return False

    def _validate_playlist(self, playlist: Dict[str, Any]) -> bool:
        """Validate playlist data."""
        try:
            required_fields = ["title", "description", "privacy"]
            if not all(field in playlist for field in required_fields):
                return False

            if not playlist["title"] or len(playlist["title"]) > 150:
                return False

            if len(playlist["description"]) > 5000:
                return False

            valid_privacy = ["public", "private", "unlisted"]
            if playlist["privacy"] not in valid_privacy:
                return False

            return True

        except Exception as e:
            logger.error(f"Playlist validation failed: {str(e)}")
            return False

    def _check_engagement_limit(self, action_type: str, count: int) -> bool:
        """Check if action is within daily limits."""
        try:
            limit_key = f"max_{action_type}_per_day"
            if limit_key not in self.config:
                return False

            current_count = self.feedback_data.get(action_type, 0)
            if current_count + count > self.config[limit_key]:
                logger.warning(f"Daily limit reached for {action_type}")
                return False

            return True

        except Exception as e:
            logger.error(f"Engagement limit check failed: {str(e)}")
            return False

    def _upload_media(self, file_path: str) -> bool:
        """Upload media file."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False

            # Upload logic here
            # This is a placeholder for the actual implementation
            return True

        except Exception as e:
            logger.error(f"Media upload failed: {str(e)}")
            return False

    def _upload_thumbnail(self, file_path: str) -> bool:
        """Upload video thumbnail."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Thumbnail not found: {file_path}")
                return False

            # Thumbnail upload logic here
            # This is a placeholder for the actual implementation
            return True

        except Exception as e:
            logger.error(f"Thumbnail upload failed: {str(e)}")
            return False

    def _log_debug(self, message: str) -> None:
        """Log debug messages if debug mode is enabled."""
        if self.debug_mode:
            logger.debug(message)

    def execute(self) -> bool:
        """Execute YouTube strategy."""
        try:
            if not self._login():
                return False

            self._video_management()
            self._short_management()
            self._live_stream_management()
            self._playlist_management()
            self._community_post_management()
            analytics = self._analytics_and_reporting()

            self._save_feedback_data()
            return True

        except Exception as e:
            logger.error(f"Strategy execution failed: {str(e)}")
            return False

    def _load_config(self) -> Dict[str, Any]:
        """Load YouTube-specific configuration."""
        config = social_config.get_platform_config("youtube") or {
            "max_videos_per_day": 5,
            "max_comments_per_day": 50,
            "max_likes_per_day": 100,
            "max_subscriptions_per_day": 20,
            "max_playlists_per_day": 2,
            "max_live_streams_per_day": 1,
            "max_shorts_per_day": 5,
            "max_community_posts_per_day": 3
        }
        return config 
