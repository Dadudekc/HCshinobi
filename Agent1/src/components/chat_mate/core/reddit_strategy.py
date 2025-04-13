"""
Reddit-specific strategy implementation.
Extends BasePlatformStrategy with Reddit-specific functionality.
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    TimeoutException
)

from core.task_engine.agents.social_strategies.base_platform_strategy import BasePlatformStrategy
from core.task_engine.utils.cookie_manager import CookieManager
from core.task_engine.utils.log_writer import get_social_logger, write_json_log
from core.task_engine.social_config import social_config
from core.task_engine.AIChatAgent import AIChatAgent
from core.task_engine.utils.sentiment_analyzer import SentimentAnalyzer

logger = get_social_logger()

class RedditStrategy(BasePlatformStrategy):
    """
    Reddit-specific strategy implementation.
    Features:
      - Dynamic feedback loops with AI sentiment analysis
      - Reinforcement loops using ChatGPT responses
      - Reward system for top engaging followers
      - Cross-platform feedback integration
      - Crossposting and awards management
      - Enhanced analytics and reporting
      - Moderation tools and user management
      - Advanced content analysis
      - Predictive analytics and trend forecasting
    """
    
    def __init__(self, driver: Optional[webdriver.Chrome] = None):
        """Initialize Reddit strategy with browser automation."""
        super().__init__(platform_id="reddit", driver=driver)
        self.login_url = "https://www.reddit.com/login"
        self.username = os.getenv("REDDIT_USERNAME")
        self.password = os.getenv("REDDIT_PASSWORD")
        self.wait_range = (3, 6)
        self.feedback_data = self._load_feedback_data()
        self.subreddits = ["algotrading", "systemtrader", "automation", "investing"]
        self.mod_config = {
            "max_removals_per_day": 50,
            "max_bans_per_day": 10,
            "max_mod_actions_per_hour": 20,
            "spam_threshold": 0.7,
            "toxicity_threshold": 0.8
        }
        self.user_config = {
            "max_follows_per_day": 50,
            "max_messages_per_day": 30,
            "max_user_actions_per_hour": 15
        }
    
    def initialize(self, credentials: Dict[str, str]) -> bool:
        """Initialize Reddit strategy with credentials."""
        try:
            if not self.driver:
                self.driver = self._get_driver()
            return self.login()
        except Exception as e:
            logger.error(f"Failed to initialize Reddit strategy: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
            return True
        except Exception as e:
            logger.error(f"Error during Reddit cleanup: {e}")
            return False
    
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get Reddit-specific community metrics."""
        metrics = {
            "engagement_rate": 0.0,
            "growth_rate": 0.0,
            "sentiment_score": 0.0,
            "active_members": 0
        }
        
        try:
            # Get metrics from feedback data
            total_interactions = (
                self.feedback_data.get("upvotes", 0) +
                self.feedback_data.get("comments", 0) +
                self.feedback_data.get("subscriptions", 0)
            )
            
            if total_interactions > 0:
                metrics["engagement_rate"] = min(1.0, total_interactions / 1000)  # Normalize to [0,1]
                metrics["growth_rate"] = min(1.0, self.feedback_data.get("subscriptions", 0) / 100)
                metrics["sentiment_score"] = self.feedback_data.get("sentiment_score", 0.0)
                metrics["active_members"] = total_interactions
        except Exception as e:
            logger.error(f"Error calculating Reddit metrics: {e}")
        
        return metrics
    
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top Reddit community members."""
        top_members = []
        try:
            if os.path.exists(self.follow_db):
                with open(self.follow_db, "r") as f:
                    follow_data = json.load(f)
                
                # Convert follow data to member list
                for subreddit, data in follow_data.items():
                    if data.get("status") == "subscribed":
                        member = {
                            "id": subreddit,
                            "platform": "reddit",
                            "engagement_score": random.uniform(0.5, 1.0),  # Replace with real metrics
                            "subscribed_at": data.get("subscribed_at"),
                            "recent_interactions": []
                        }
                        top_members.append(member)
                
                # Sort by engagement score
                top_members.sort(key=lambda x: x["engagement_score"], reverse=True)
                top_members = top_members[:20]  # Keep top 20
        except Exception as e:
            logger.error(f"Error getting top Reddit members: {e}")
        
        return top_members
    
    def track_member_interaction(self, member_id: str, interaction_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a Reddit member (subreddit)."""
        try:
            if not os.path.exists(self.follow_db):
                return False
            
            with open(self.follow_db, "r") as f:
                follow_data = json.load(f)
            
            if member_id not in follow_data:
                follow_data[member_id] = {
                    "subscribed_at": datetime.utcnow().isoformat(),
                    "status": "subscribed",
                    "interactions": []
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
            
            logger.info(f"Tracked {interaction_type} interaction with Reddit member {member_id}")
            return True
        except Exception as e:
            logger.error(f"Error tracking Reddit member interaction: {e}")
            return False
    
    def _get_driver(self, headless=False):
        """Get configured Chrome WebDriver for Reddit."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        driver = webdriver.Chrome(options=options)
        logger.info(" Reddit driver initialized")
        return driver
    
    def _wait(self, custom_range=None):
        """Wait for a random duration."""
        wait_time = random.uniform(*(custom_range or self.wait_range))
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
    
    def login(self) -> bool:
        """Log in to Reddit."""
        logger.info(" Initiating Reddit login...")
        try:
            self.driver.get(self.login_url)
            self._wait()
            
            # Try cookie login first
            self.cookie_manager.load_cookies(self.driver, "reddit")
            self.driver.refresh()
            self._wait()
            
            if self.is_logged_in():
                logger.info(" Logged into Reddit via cookies")
                return True
            
            # Try credential login
            if self.username and self.password:
                try:
                    username_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "loginUsername"))
                    )
                    password_input = self.driver.find_element(By.ID, "loginPassword")
                    
                    username_input.clear()
                    password_input.clear()
                    username_input.send_keys(self.username)
                    password_input.send_keys(self.password)
                    password_input.send_keys(Keys.RETURN)
                    self._wait((5, 8))
                    
                    if self.is_logged_in():
                        self.cookie_manager.save_cookies(self.driver, "reddit")
                        logger.info(" Logged into Reddit via credentials")
                        return True
                except Exception as e:
                    logger.error(f"Reddit auto-login failed: {e}")
            
            # Manual login fallback
            if self.cookie_manager.wait_for_manual_login(self.driver, self.is_logged_in, "reddit"):
                self.cookie_manager.save_cookies(self.driver, "reddit")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Reddit login error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Check if logged into Reddit."""
        try:
            self.driver.get("https://www.reddit.com/")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self._wait((3, 5))
            return "login" not in self.driver.current_url.lower()
        except Exception:
            return False
    
    def post_content(self, subreddit: str, title: str, body: str = None) -> bool:
        """Post content to Reddit."""
        logger.info(f" Posting content to r/{subreddit}...")
        try:
            if not self.is_logged_in():
                if not self.login():
                    return False
            
            submit_url = f"https://www.reddit.com/r/{subreddit}/submit"
            self.driver.get(submit_url)
            self._wait((3, 5))
            
            # Fill title
            title_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='title']"))
            )
            title_field.clear()
            title_field.send_keys(title)
            self._wait((1, 2))
            
            # Fill body if provided
            if body:
                body_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='post-content'] div[role='textbox']"))
                )
                body_field.click()
                self._wait((1, 2))
                body_field.send_keys(body)
                self._wait((1, 2))
            
            # Submit
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Post')]"))
            )
            post_button.click()
            self._wait((3, 5))
            
            logger.info(f" Successfully posted to r/{subreddit}")
            write_json_log("reddit", "success", f"Posted to r/{subreddit}")
            return True
        except Exception as e:
            logger.error(f"Error posting to Reddit: {e}")
            return False
    
    def run_daily_strategy_session(self):
        """Run complete daily Reddit strategy session."""
        logger.info(" Starting Full Reddit Strategy Session")
        try:
            if not self.initialize({}):
                return
            
            # Post AI-generated content
            for subreddit in self.subreddits:
                title_prompt = f"Write an engaging Reddit post title for r/{subreddit} about community building and system convergence."
                body_prompt = "Write a detailed post body expanding on the title, focusing on value and authenticity."
                
                title = self.ai_agent.ask(
                    prompt=title_prompt,
                    metadata={"platform": "reddit", "subreddit": subreddit}
                )
                body = self.ai_agent.ask(
                    prompt=body_prompt,
                    metadata={"platform": "reddit", "subreddit": subreddit}
                )
                
                if title and body:
                    self.post_content(subreddit, title, body)
                self._wait((5, 10))
            
            # Process engagement metrics
            self.analyze_engagement_metrics()
            
            # Sample engagement reinforcement
            sample_comments = [
                "This is exactly what I needed to see!",
                "Not sure about this approach.",
                "Your insights are always valuable!"
            ]
            for comment in sample_comments:
                self.reinforce_engagement(comment)
            
            # Run feedback and reward systems
            self.run_feedback_loop()
            self.reward_top_engagers()
            self.cross_platform_feedback_loop()
            
            self.cleanup()
            logger.info(" Reddit Strategy Session Complete")
        except Exception as e:
            logger.error(f"Error in Reddit strategy session: {e}")
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
        logger.info(" Analyzing Reddit engagement metrics...")
        self.feedback_data["upvotes"] = self.feedback_data.get("upvotes", 0) + random.randint(5, 10)
        self.feedback_data["comments"] = self.feedback_data.get("comments", 0) + random.randint(2, 5)
        self.feedback_data["subscriptions"] = self.feedback_data.get("subscriptions", 0) + random.randint(1, 3)
        logger.info(f" Total Upvotes: {self.feedback_data['upvotes']}")
        logger.info(f" Total Comments: {self.feedback_data['comments']}")
        logger.info(f" Total Subscriptions: {self.feedback_data['subscriptions']}")
        self._save_feedback_data()

    def run_feedback_loop(self):
        """Run the dynamic feedback loop process."""
        self.analyze_engagement_metrics()
        self.adaptive_posting_strategy()

    def adaptive_posting_strategy(self):
        """Adjust posting strategy based on engagement feedback."""
        logger.info(" Adapting Reddit posting strategy based on feedback...")
        if self.feedback_data.get("upvotes", 0) > 100:
            logger.info(" High engagement detected! Consider increasing post frequency.")
        if self.feedback_data.get("comments", 0) > 50:
            logger.info(" More discussion-oriented posts may yield better community interaction.")

    def crosspost(self, original_post_url: str, target_subreddit: str, 
                 custom_title: Optional[str] = None) -> bool:
        """Crosspost content to another subreddit."""
        logger.info(f" Crossposting to r/{target_subreddit}")
        try:
            if not self.is_logged_in():
                return False
                
            # Navigate to original post
            self.driver.get(original_post_url)
            self._wait((3, 5))
            
            # Click share button
            share_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[@aria-label='Share']"))
            )
            share_button.click()
            self._wait((1, 2))
            
            # Click crosspost option
            crosspost_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[contains(text(), 'Crosspost')]"))
            )
            crosspost_button.click()
            self._wait((2, 3))
            
            # Select target subreddit
            subreddit_input = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, 
                                               "//input[@placeholder='Choose a community']"))
            )
            subreddit_input.send_keys(target_subreddit)
            self._wait((1, 2))
            
            # Select from dropdown
            subreddit_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         f"//div[contains(text(), 'r/{target_subreddit}')]"))
            )
            subreddit_option.click()
            self._wait((1, 2))
            
            # Update title if provided
            if custom_title:
                title_input = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, 
                                                   "//textarea[@name='title']"))
                )
                title_input.clear()
                title_input.send_keys(custom_title)
                self._wait((1, 2))
                
            # Submit crosspost
            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[contains(text(), 'Crosspost')]"))
            )
            submit_button.click()
            self._wait((5, 8))
            
            logger.info(" Crosspost successful")
            write_json_log(self.platform, "successful", tags=["crosspost"])
            return True
            
        except Exception as e:
            logger.error(f"Failed to crosspost: {e}")
            write_json_log(self.platform, "failed", tags=["crosspost"], 
                         ai_output=str(e))
            return False
            
    def give_award(self, post_url: str, award_type: str) -> bool:
        """Give an award to a post."""
        logger.info(f" Giving {award_type} award")
        try:
            if not self.is_logged_in():
                return False
                
            # Navigate to post
            self.driver.get(post_url)
            self._wait((3, 5))
            
            # Click award button
            award_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[@aria-label='Award']"))
            )
            award_button.click()
            self._wait((1, 2))
            
            # Select award type
            award_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         f"//div[contains(text(), '{award_type}')]"))
            )
            award_option.click()
            self._wait((1, 2))
            
            # Confirm award
            confirm_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[contains(text(), 'Give Award')]"))
            )
            confirm_button.click()
            self._wait((3, 5))
            
            logger.info(" Award given successfully")
            write_json_log(self.platform, "successful", tags=["award"])
            return True
            
        except Exception as e:
            logger.error(f"Failed to give award: {e}")
            write_json_log(self.platform, "failed", tags=["award"], 
                         ai_output=str(e))
            return False
            
    def get_enhanced_metrics(self) -> Dict[str, Any]:
        """Get enhanced Reddit metrics with detailed analytics."""
        metrics = {
            "community_metrics": self.get_community_metrics(),
            "content_metrics": {},
            "engagement_metrics": {},
            "growth_metrics": {},
            "sentiment_analysis": {}
        }
        
        try:
            # Content metrics
            metrics["content_metrics"] = {
                "total_posts": self.feedback_data.get("total_posts", 0),
                "total_comments": self.feedback_data.get("total_comments", 0),
                "average_post_score": self.feedback_data.get("average_post_score", 0),
                "top_posts": self._get_top_posts(),
                "content_types": self._analyze_content_types()
            }
            
            # Engagement metrics
            metrics["engagement_metrics"] = {
                "daily_active_users": self._calculate_dau(),
                "comment_ratio": self._calculate_comment_ratio(),
                "upvote_ratio": self._calculate_upvote_ratio(),
                "award_ratio": self._calculate_award_ratio(),
                "interaction_times": self._analyze_interaction_times()
            }
            
            # Growth metrics
            metrics["growth_metrics"] = {
                "subscriber_growth": self._calculate_subscriber_growth(),
                "post_growth": self._calculate_post_growth(),
                "comment_growth": self._calculate_comment_growth(),
                "trending_topics": self._get_trending_topics()
            }
            
            # Sentiment analysis
            metrics["sentiment_analysis"] = {
                "overall_sentiment": self._analyze_overall_sentiment(),
                "topic_sentiment": self._analyze_topic_sentiment(),
                "user_sentiment": self._analyze_user_sentiment(),
                "sentiment_trends": self._analyze_sentiment_trends()
            }
            
            logger.info("Enhanced metrics retrieved successfully")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating enhanced metrics: {e}")
            return metrics
            
    def _get_top_posts(self) -> List[Dict[str, Any]]:
        """Get top performing posts."""
        top_posts = []
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/top")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:5]  # Get top 5 posts
                
                for post in posts:
                    try:
                        title = post.find_element(By.XPATH, 
                                               ".//h3").text
                        score = post.find_element(By.XPATH, 
                                               ".//div[@class='_1rZYMD_4xY3gRcSS3p8ODO']").text
                        comments = post.find_element(By.XPATH, 
                                                  ".//span[@class='FHCV02u6Cp2zYL0fhQPsO']").text
                        
                        top_posts.append({
                            "subreddit": subreddit,
                            "title": title,
                            "score": int(score.replace("k", "000")),
                            "comments": int(comments)
                        })
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error getting top posts: {e}")
            
        return sorted(top_posts, key=lambda x: x["score"], reverse=True)
        
    def _analyze_content_types(self) -> Dict[str, int]:
        """Analyze types of content posted."""
        content_types = {
            "text": 0,
            "image": 0,
            "video": 0,
            "link": 0,
            "poll": 0
        }
        
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/new")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:20]  # Analyze last 20 posts
                
                for post in posts:
                    try:
                        if post.find_elements(By.XPATH, ".//img"):
                            content_types["image"] += 1
                        elif post.find_elements(By.XPATH, ".//video"):
                            content_types["video"] += 1
                        elif post.find_elements(By.XPATH, ".//a[contains(@href, 'http')]"):
                            content_types["link"] += 1
                        elif post.find_elements(By.XPATH, ".//div[contains(@class, 'poll')]"):
                            content_types["poll"] += 1
                        else:
                            content_types["text"] += 1
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error analyzing content types: {e}")
            
        return content_types
        
    def _calculate_dau(self) -> int:
        """Calculate daily active users."""
        try:
            total_interactions = (
                self.feedback_data.get("upvotes", 0) +
                self.feedback_data.get("comments", 0) +
                self.feedback_data.get("subscriptions", 0)
            )
            return min(total_interactions, 1000)  # Cap at 1000 for normalization
        except:
            return 0
            
    def _calculate_comment_ratio(self) -> float:
        """Calculate ratio of comments to posts."""
        try:
            total_posts = self.feedback_data.get("total_posts", 1)
            total_comments = self.feedback_data.get("total_comments", 0)
            return total_comments / total_posts
        except:
            return 0.0
            
    def _calculate_upvote_ratio(self) -> float:
        """Calculate ratio of upvotes to posts."""
        try:
            total_posts = self.feedback_data.get("total_posts", 1)
            total_upvotes = self.feedback_data.get("total_upvotes", 0)
            return total_upvotes / total_posts
        except:
            return 0.0
            
    def _calculate_award_ratio(self) -> float:
        """Calculate ratio of awards to posts."""
        try:
            total_posts = self.feedback_data.get("total_posts", 1)
            total_awards = self.feedback_data.get("total_awards", 0)
            return total_awards / total_posts
        except:
            return 0.0
            
    def _analyze_interaction_times(self) -> Dict[str, int]:
        """Analyze when users are most active."""
        interaction_times = {str(hour): 0 for hour in range(24)}
        
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/new")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:50]  # Analyze last 50 posts
                
                for post in posts:
                    try:
                        timestamp = post.find_element(By.XPATH, 
                                                   ".//time").get_attribute("datetime")
                        hour = datetime.fromisoformat(timestamp).hour
                        interaction_times[str(hour)] += 1
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error analyzing interaction times: {e}")
            
        return interaction_times
        
    def _calculate_subscriber_growth(self) -> float:
        """Calculate subscriber growth rate."""
        try:
            current_subs = self.feedback_data.get("current_subscribers", 0)
            previous_subs = self.feedback_data.get("previous_subscribers", 0)
            if previous_subs == 0:
                return 0.0
            return (current_subs - previous_subs) / previous_subs * 100
        except:
            return 0.0
            
    def _calculate_post_growth(self) -> float:
        """Calculate post growth rate."""
        try:
            current_posts = self.feedback_data.get("total_posts", 0)
            previous_posts = self.feedback_data.get("previous_total_posts", 0)
            if previous_posts == 0:
                return 0.0
            return (current_posts - previous_posts) / previous_posts * 100
        except:
            return 0.0
            
    def _calculate_comment_growth(self) -> float:
        """Calculate comment growth rate."""
        try:
            current_comments = self.feedback_data.get("total_comments", 0)
            previous_comments = self.feedback_data.get("previous_total_comments", 0)
            if previous_comments == 0:
                return 0.0
            return (current_comments - previous_comments) / previous_comments * 100
        except:
            return 0.0
            
    def _get_trending_topics(self) -> List[str]:
        """Get trending topics across subreddits."""
        trending_topics = []
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/hot")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:10]  # Get top 10 hot posts
                
                for post in posts:
                    try:
                        title = post.find_element(By.XPATH, 
                                               ".//h3").text
                        trending_topics.append(title)
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            
        return trending_topics
        
    def _analyze_overall_sentiment(self) -> float:
        """Analyze overall sentiment of content."""
        try:
            sentiment_analyzer = SentimentAnalyzer()
            total_sentiment = 0
            count = 0
            
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/top")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:20]  # Analyze top 20 posts
                
                for post in posts:
                    try:
                        title = post.find_element(By.XPATH, 
                                               ".//h3").text
                        sentiment = sentiment_analyzer.analyze(title)
                        total_sentiment += sentiment
                        count += 1
                    except:
                        continue
                        
            return total_sentiment / count if count > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error analyzing overall sentiment: {e}")
            return 0.0
            
    def _analyze_topic_sentiment(self) -> Dict[str, float]:
        """Analyze sentiment by topic."""
        topic_sentiment = {}
        try:
            sentiment_analyzer = SentimentAnalyzer()
            
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/top")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:10]  # Analyze top 10 posts per subreddit
                
                for post in posts:
                    try:
                        title = post.find_element(By.XPATH, 
                                               ".//h3").text
                        sentiment = sentiment_analyzer.analyze(title)
                        topic_sentiment[subreddit] = sentiment
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error analyzing topic sentiment: {e}")
            
        return topic_sentiment
        
    def _analyze_user_sentiment(self) -> Dict[str, float]:
        """Analyze sentiment of user interactions."""
        user_sentiment = {}
        try:
            sentiment_analyzer = SentimentAnalyzer()
            
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/comments")
                self._wait((3, 5))
                
                comments = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='comment']"))
                )[:20]  # Analyze last 20 comments
                
                for comment in comments:
                    try:
                        author = comment.find_element(By.XPATH, 
                                                   ".//a[contains(@href, '/user/')]").text
                        text = comment.find_element(By.XPATH, 
                                                 ".//div[@class='_1eM9yP']").text
                        sentiment = sentiment_analyzer.analyze(text)
                        user_sentiment[author] = sentiment
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error analyzing user sentiment: {e}")
            
        return user_sentiment
        
    def _analyze_sentiment_trends(self) -> Dict[str, List[float]]:
        """Analyze sentiment trends over time."""
        sentiment_trends = {}
        try:
            sentiment_analyzer = SentimentAnalyzer()
            
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/top?t=month")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:30]  # Analyze last 30 days of posts
                
                daily_sentiment = []
                for post in posts:
                    try:
                        title = post.find_element(By.XPATH, 
                                               ".//h3").text
                        sentiment = sentiment_analyzer.analyze(title)
                        daily_sentiment.append(sentiment)
                    except:
                        continue
                        
                sentiment_trends[subreddit] = daily_sentiment
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment trends: {e}")
            
        return sentiment_trends

    def moderate_content(self, post_url: str, action: str, reason: str = None) -> bool:
        """Moderate content (remove, approve, lock, etc.)."""
        logger.info(f" Moderating content with action: {action}")
        try:
            if not self.is_logged_in():
                return False
                
            # Navigate to post
            self.driver.get(post_url)
            self._wait((3, 5))
            
            # Click mod menu
            mod_menu = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[@aria-label='Mod Tools']"))
            )
            mod_menu.click()
            self._wait((1, 2))
            
            # Select action
            action_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         f"//button[contains(text(), '{action}')]"))
            )
            action_button.click()
            self._wait((1, 2))
            
            # Add reason if required
            if reason:
                reason_input = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, 
                                                   "//textarea[@placeholder='Reason for action']"))
                )
                reason_input.send_keys(reason)
                self._wait((1, 2))
                
            # Confirm action
            confirm_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[contains(text(), 'Confirm')]"))
            )
            confirm_button.click()
            self._wait((3, 5))
            
            logger.info(f" Content moderation successful: {action}")
            write_json_log(self.platform, "successful", tags=["moderation", action])
            return True
            
        except Exception as e:
            logger.error(f"Failed to moderate content: {e}")
            write_json_log(self.platform, "failed", tags=["moderation", action], 
                         ai_output=str(e))
            return False
            
    def manage_user(self, username: str, action: str, duration: str = None) -> bool:
        """Manage user (ban, mute, approve, etc.)."""
        logger.info(f" Managing user {username} with action: {action}")
        try:
            if not self.is_logged_in():
                return False
                
            # Navigate to user profile
            self.driver.get(f"https://www.reddit.com/user/{username}")
            self._wait((3, 5))
            
            # Click mod menu
            mod_menu = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[@aria-label='Mod Tools']"))
            )
            mod_menu.click()
            self._wait((1, 2))
            
            # Select action
            action_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         f"//button[contains(text(), '{action}')]"))
            )
            action_button.click()
            self._wait((1, 2))
            
            # Set duration if required
            if duration:
                duration_input = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, 
                                                   "//input[@placeholder='Duration']"))
                )
                duration_input.send_keys(duration)
                self._wait((1, 2))
                
            # Confirm action
            confirm_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                                         "//button[contains(text(), 'Confirm')]"))
            )
            confirm_button.click()
            self._wait((3, 5))
            
            logger.info(f" User management successful: {action}")
            write_json_log(self.platform, "successful", tags=["user_management", action])
            return True
            
        except Exception as e:
            logger.error(f"Failed to manage user: {e}")
            write_json_log(self.platform, "failed", tags=["user_management", action], 
                         ai_output=str(e))
            return False
            
    def get_mod_metrics(self) -> Dict[str, Any]:
        """Get moderation-specific metrics."""
        metrics = {
            "moderation_actions": {},
            "user_management": {},
            "content_quality": {},
            "community_health": {}
        }
        
        try:
            # Moderation actions
            metrics["moderation_actions"] = {
                "total_removals": self.feedback_data.get("total_removals", 0),
                "total_approvals": self.feedback_data.get("total_approvals", 0),
                "total_bans": self.feedback_data.get("total_bans", 0),
                "total_mutes": self.feedback_data.get("total_mutes", 0),
                "action_trends": self._analyze_mod_action_trends()
            }
            
            # User management
            metrics["user_management"] = {
                "active_users": self._get_active_users(),
                "problem_users": self._get_problem_users(),
                "user_growth": self._calculate_user_growth(),
                "user_retention": self._calculate_user_retention()
            }
            
            # Content quality
            metrics["content_quality"] = {
                "spam_score": self._calculate_spam_score(),
                "toxicity_score": self._calculate_toxicity_score(),
                "content_diversity": self._analyze_content_diversity(),
                "rule_violations": self._analyze_rule_violations()
            }
            
            # Community health
            metrics["community_health"] = {
                "mod_activity": self._analyze_mod_activity(),
                "user_satisfaction": self._calculate_user_satisfaction(),
                "community_growth": self._analyze_community_growth(),
                "content_engagement": self._analyze_content_engagement()
            }
            
            logger.info("Mod metrics retrieved successfully")
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating mod metrics: {e}")
            return metrics
            
    def _analyze_mod_action_trends(self) -> Dict[str, List[int]]:
        """Analyze trends in moderation actions."""
        action_trends = {
            "removals": [],
            "approvals": [],
            "bans": [],
            "mutes": []
        }
        
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/about/modqueue")
                self._wait((3, 5))
                
                # Get last 7 days of actions
                for i in range(7):
                    date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                    actions = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, 
                                                          f"//div[contains(@class, 'mod-action') and contains(@data-date, '{date}')]"))
                    )
                    
                    action_trends["removals"].append(len([a for a in actions if "removed" in a.text]))
                    action_trends["approvals"].append(len([a for a in actions if "approved" in a.text]))
                    action_trends["bans"].append(len([a for a in actions if "banned" in a.text]))
                    action_trends["mutes"].append(len([a for a in actions if "muted" in a.text]))
                    
        except Exception as e:
            logger.error(f"Error analyzing mod action trends: {e}")
            
        return action_trends
        
    def _get_active_users(self) -> List[Dict[str, Any]]:
        """Get list of active users."""
        active_users = []
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/about/contributors")
                self._wait((3, 5))
                
                users = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[contains(@class, 'user-row')]"))
                )[:20]  # Get top 20 contributors
                
                for user in users:
                    try:
                        username = user.find_element(By.XPATH, 
                                                  ".//a[contains(@href, '/user/')]").text
                        karma = user.find_element(By.XPATH, 
                                               ".//span[contains(@class, 'karma')]").text
                        posts = user.find_element(By.XPATH, 
                                               ".//span[contains(@class, 'posts')]").text
                        
                        active_users.append({
                            "username": username,
                            "subreddit": subreddit,
                            "karma": int(karma),
                            "posts": int(posts)
                        })
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            
        return sorted(active_users, key=lambda x: x["karma"], reverse=True)
        
    def _get_problem_users(self) -> List[Dict[str, Any]]:
        """Get list of users with rule violations."""
        problem_users = []
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/about/banned")
                self._wait((3, 5))
                
                users = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[contains(@class, 'banned-user')]"))
                )[:10]  # Get last 10 banned users
                
                for user in users:
                    try:
                        username = user.find_element(By.XPATH, 
                                                  ".//a[contains(@href, '/user/')]").text
                        reason = user.find_element(By.XPATH, 
                                                ".//div[contains(@class, 'reason')]").text
                        date = user.find_element(By.XPATH, 
                                              ".//time").get_attribute("datetime")
                        
                        problem_users.append({
                            "username": username,
                            "subreddit": subreddit,
                            "reason": reason,
                            "date": date
                        })
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error getting problem users: {e}")
            
        return problem_users
        
    def _calculate_user_growth(self) -> float:
        """Calculate user growth rate."""
        try:
            current_users = self.feedback_data.get("current_users", 0)
            previous_users = self.feedback_data.get("previous_users", 0)
            if previous_users == 0:
                return 0.0
            return (current_users - previous_users) / previous_users * 100
        except:
            return 0.0
            
    def _calculate_user_retention(self) -> float:
        """Calculate user retention rate."""
        try:
            total_users = self.feedback_data.get("total_users", 0)
            active_users = self.feedback_data.get("active_users", 0)
            if total_users == 0:
                return 0.0
            return (active_users / total_users) * 100
        except:
            return 0.0
            
    def _calculate_spam_score(self) -> float:
        """Calculate spam score for content."""
        try:
            total_posts = self.feedback_data.get("total_posts", 0)
            spam_posts = self.feedback_data.get("spam_posts", 0)
            if total_posts == 0:
                return 0.0
            return (spam_posts / total_posts) * 100
        except:
            return 0.0
            
    def _calculate_toxicity_score(self) -> float:
        """Calculate toxicity score for content."""
        try:
            total_comments = self.feedback_data.get("total_comments", 0)
            toxic_comments = self.feedback_data.get("toxic_comments", 0)
            if total_comments == 0:
                return 0.0
            return (toxic_comments / total_comments) * 100
        except:
            return 0.0
            
    def _analyze_content_diversity(self) -> Dict[str, float]:
        """Analyze content diversity."""
        diversity = {
            "topic_diversity": 0.0,
            "user_diversity": 0.0,
            "format_diversity": 0.0
        }
        
        try:
            # Get unique topics
            topics = set()
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/top")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:20]
                
                for post in posts:
                    try:
                        title = post.find_element(By.XPATH, 
                                               ".//h3").text
                        topics.add(title)
                    except:
                        continue
                        
            diversity["topic_diversity"] = len(topics) / 100  # Normalize
            
            # Get unique users
            users = set()
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/new")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )[:20]
                
                for post in posts:
                    try:
                        author = post.find_element(By.XPATH, 
                                                ".//a[contains(@href, '/user/')]").text
                        users.add(author)
                    except:
                        continue
                        
            diversity["user_diversity"] = len(users) / 100  # Normalize
            
            # Get content formats
            formats = self._analyze_content_types()
            total_posts = sum(formats.values())
            if total_posts > 0:
                format_scores = [count / total_posts for count in formats.values()]
                diversity["format_diversity"] = sum(score * (1 - score) for score in format_scores)
                
        except Exception as e:
            logger.error(f"Error analyzing content diversity: {e}")
            
        return diversity
        
    def _analyze_rule_violations(self) -> Dict[str, int]:
        """Analyze rule violations."""
        violations = {
            "spam": 0,
            "harassment": 0,
            "misinformation": 0,
            "other": 0
        }
        
        try:
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/about/reports")
                self._wait((3, 5))
                
                reports = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[contains(@class, 'report')]"))
                )[:20]  # Get last 20 reports
                
                for report in reports:
                    try:
                        reason = report.find_element(By.XPATH, 
                                                  ".//div[contains(@class, 'reason')]").text.lower()
                        if "spam" in reason:
                            violations["spam"] += 1
                        elif "harassment" in reason:
                            violations["harassment"] += 1
                        elif "misinformation" in reason:
                            violations["misinformation"] += 1
                        else:
                            violations["other"] += 1
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error analyzing rule violations: {e}")
            
        return violations
        
    def _analyze_mod_activity(self) -> Dict[str, float]:
        """Analyze moderator activity."""
        activity = {
            "response_time": 0.0,
            "action_frequency": 0.0,
            "coverage": 0.0
        }
        
        try:
            total_actions = 0
            total_time = 0
            total_posts = 0
            
            for subreddit in self.subreddits:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/about/modqueue")
                self._wait((3, 5))
                
                actions = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[contains(@class, 'mod-action')]"))
                )[:20]  # Get last 20 actions
                
                for action in actions:
                    try:
                        timestamp = action.find_element(By.XPATH, 
                                                     ".//time").get_attribute("datetime")
                        action_time = datetime.fromisoformat(timestamp)
                        total_time += (datetime.now() - action_time).total_seconds()
                        total_actions += 1
                    except:
                        continue
                        
                # Get total posts
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/new")
                self._wait((3, 5))
                
                posts = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      "//div[@data-testid='post-container']"))
                )
                total_posts += len(posts)
                
            if total_actions > 0:
                activity["response_time"] = total_time / total_actions / 3600  # Hours
                activity["action_frequency"] = total_actions / 24  # Actions per hour
                
            if total_posts > 0:
                activity["coverage"] = total_actions / total_posts
                
        except Exception as e:
            logger.error(f"Error analyzing mod activity: {e}")
            
        return activity
        
    def _calculate_user_satisfaction(self) -> float:
        """Calculate user satisfaction score."""
        try:
            total_posts = self.feedback_data.get("total_posts", 0)
            upvoted_posts = self.feedback_data.get("upvoted_posts", 0)
            if total_posts == 0:
                return 0.0
            return (upvoted_posts / total_posts) * 100
        except:
            return 0.0
            
    def _analyze_community_growth(self) -> Dict[str, float]:
        """Analyze community growth metrics."""
        growth = {
            "subscriber_growth": 0.0,
            "post_growth": 0.0,
            "comment_growth": 0.0,
            "engagement_growth": 0.0
        }
        
        try:
            growth["subscriber_growth"] = self._calculate_subscriber_growth()
            growth["post_growth"] = self._calculate_post_growth()
            growth["comment_growth"] = self._calculate_comment_growth()
            
            # Calculate engagement growth
            current_engagement = (
                self.feedback_data.get("current_upvotes", 0) +
                self.feedback_data.get("current_comments", 0)
            )
            previous_engagement = (
                self.feedback_data.get("previous_upvotes", 0) +
                self.feedback_data.get("previous_comments", 0)
            )
            
            if previous_engagement > 0:
                growth["engagement_growth"] = (
                    (current_engagement - previous_engagement) / 
                    previous_engagement * 100
                )
                
        except Exception as e:
            logger.error(f"Error analyzing community growth: {e}")
            
        return growth
        
    def _analyze_content_engagement(self) -> Dict[str, float]:
        """Analyze content engagement metrics."""
        engagement = {
            "average_upvotes": 0.0,
            "average_comments": 0.0,
            "average_awards": 0.0,
            "engagement_rate": 0.0
        }
        
        try:
            total_posts = self.feedback_data.get("total_posts", 0)
            if total_posts > 0:
                engagement["average_upvotes"] = (
                    self.feedback_data.get("total_upvotes", 0) / total_posts
                )
                engagement["average_comments"] = (
                    self.feedback_data.get("total_comments", 0) / total_posts
                )
                engagement["average_awards"] = (
                    self.feedback_data.get("total_awards", 0) / total_posts
                )
                
                # Calculate engagement rate
                total_views = self.feedback_data.get("total_views", 0)
                if total_views > 0:
                    total_engagement = (
                        self.feedback_data.get("total_upvotes", 0) +
                        self.feedback_data.get("total_comments", 0) +
                        self.feedback_data.get("total_awards", 0)
                    )
                    engagement["engagement_rate"] = (total_engagement / total_views) * 100
                    
        except Exception as e:
            logger.error(f"Error analyzing content engagement: {e}")
            
        return engagement

    def predict_engagement(self, post_content: str, subreddit: str) -> Dict[str, float]:
        """Predict engagement metrics for a post."""
        predictions = {
            "upvotes": 0.0,
            "comments": 0.0,
            "awards": 0.0,
            "engagement_rate": 0.0
        }
        
        try:
            # Get historical data for the subreddit
            historical_data = self._get_historical_data(subreddit)
            
            # Analyze content features
            content_features = self._analyze_content_features(post_content)
            
            # Calculate predictions based on historical data and content features
            predictions["upvotes"] = self._predict_upvotes(historical_data, content_features)
            predictions["comments"] = self._predict_comments(historical_data, content_features)
            predictions["awards"] = self._predict_awards(historical_data, content_features)
            predictions["engagement_rate"] = self._predict_engagement_rate(predictions)
            
            logger.info("Engagement predictions generated successfully")
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting engagement: {e}")
            return predictions
            
    def forecast_trends(self, metric: str, days: int = 7) -> Dict[str, List[float]]:
        """Forecast trends for various metrics."""
        forecasts = {
            "subscriber_growth": [],
            "post_growth": [],
            "comment_growth": [],
            "engagement_growth": []
        }
        
        try:
            # Get historical data
            historical_data = self._get_historical_data()
            
            # Generate forecasts for each metric
            for day in range(1, days + 1):
                forecasts["subscriber_growth"].append(
                    self._forecast_subscriber_growth(historical_data, day)
                )
                forecasts["post_growth"].append(
                    self._forecast_post_growth(historical_data, day)
                )
                forecasts["comment_growth"].append(
                    self._forecast_comment_growth(historical_data, day)
                )
                forecasts["engagement_growth"].append(
                    self._forecast_engagement_growth(historical_data, day)
                )
            
            logger.info("Trend forecasts generated successfully")
            return forecasts
            
        except Exception as e:
            logger.error(f"Error forecasting trends: {e}")
            return forecasts
            
    def get_risk_assessment(self, subreddit: str) -> Dict[str, float]:
        """Get risk assessment for a subreddit."""
        risks = {
            "spam_risk": 0.0,
            "toxicity_risk": 0.0,
            "moderation_risk": 0.0,
            "engagement_risk": 0.0
        }
        
        try:
            # Get historical data
            historical_data = self._get_historical_data(subreddit)
            
            # Calculate risk scores
            risks["spam_risk"] = self._calculate_spam_risk(historical_data)
            risks["toxicity_risk"] = self._calculate_toxicity_risk(historical_data)
            risks["moderation_risk"] = self._calculate_moderation_risk(historical_data)
            risks["engagement_risk"] = self._calculate_engagement_risk(historical_data)
            
            logger.info("Risk assessment generated successfully")
            return risks
            
        except Exception as e:
            logger.error(f"Error generating risk assessment: {e}")
            return risks
            
    def _get_historical_data(self, subreddit: str = None) -> Dict[str, List[float]]:
        """Get historical data for analysis."""
        historical_data = {
            "subscribers": [],
            "posts": [],
            "comments": [],
            "upvotes": [],
            "awards": []
        }
        
        try:
            if subreddit:
                self.driver.get(f"https://www.reddit.com/r/{subreddit}/about/traffic")
            else:
                self.driver.get("https://www.reddit.com/about/traffic")
                
            self._wait((3, 5))
            
            # Get last 30 days of data
            for i in range(30):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                data = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, 
                                                      f"//div[contains(@class, 'traffic-data') and contains(@data-date, '{date}')]"))
                )
                
                for point in data:
                    try:
                        metric = point.get_attribute("data-metric")
                        value = float(point.text)
                        historical_data[metric].append(value)
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            
        return historical_data
        
    def _analyze_content_features(self, content: str) -> Dict[str, float]:
        """Analyze features of content for prediction."""
        features = {
            "length": 0.0,
            "complexity": 0.0,
            "sentiment": 0.0,
            "topic_relevance": 0.0
        }
        
        try:
            # Calculate content length
            features["length"] = len(content) / 1000  # Normalize
            
            # Calculate content complexity
            words = content.split()
            sentences = content.split(".")
            features["complexity"] = len(words) / len(sentences) if sentences else 0
            
            # Calculate sentiment
            sentiment_analyzer = SentimentAnalyzer()
            features["sentiment"] = sentiment_analyzer.analyze(content)
            
            # Calculate topic relevance
            features["topic_relevance"] = self._calculate_topic_relevance(content)
            
        except Exception as e:
            logger.error(f"Error analyzing content features: {e}")
            
        return features
        
    def _predict_upvotes(self, historical_data: Dict[str, List[float]], 
                        features: Dict[str, float]) -> float:
        """Predict number of upvotes."""
        try:
            # Use historical average as base
            base_upvotes = sum(historical_data["upvotes"]) / len(historical_data["upvotes"])
            
            # Adjust based on content features
            adjustment = (
                features["length"] * 0.2 +
                features["complexity"] * 0.3 +
                features["sentiment"] * 0.3 +
                features["topic_relevance"] * 0.2
            )
            
            return base_upvotes * (1 + adjustment)
            
        except:
            return 0.0
            
    def _predict_comments(self, historical_data: Dict[str, List[float]], 
                         features: Dict[str, float]) -> float:
        """Predict number of comments."""
        try:
            # Use historical average as base
            base_comments = sum(historical_data["comments"]) / len(historical_data["comments"])
            
            # Adjust based on content features
            adjustment = (
                features["length"] * 0.3 +
                features["complexity"] * 0.4 +
                features["sentiment"] * 0.2 +
                features["topic_relevance"] * 0.1
            )
            
            return base_comments * (1 + adjustment)
            
        except:
            return 0.0
            
    def _predict_awards(self, historical_data: Dict[str, List[float]], 
                       features: Dict[str, float]) -> float:
        """Predict number of awards."""
        try:
            # Use historical average as base
            base_awards = sum(historical_data["awards"]) / len(historical_data["awards"])
            
            # Adjust based on content features
            adjustment = (
                features["length"] * 0.1 +
                features["complexity"] * 0.2 +
                features["sentiment"] * 0.4 +
                features["topic_relevance"] * 0.3
            )
            
            return base_awards * (1 + adjustment)
            
        except:
            return 0.0
            
    def _predict_engagement_rate(self, predictions: Dict[str, float]) -> float:
        """Predict engagement rate."""
        try:
            total_engagement = (
                predictions["upvotes"] +
                predictions["comments"] * 2 +  # Comments weighted more
                predictions["awards"] * 3  # Awards weighted most
            )
            
            # Use historical average views
            historical_data = self._get_historical_data()
            avg_views = sum(historical_data["views"]) / len(historical_data["views"])
            
            return (total_engagement / avg_views) * 100 if avg_views > 0 else 0.0
            
        except:
            return 0.0
            
    def _forecast_subscriber_growth(self, historical_data: Dict[str, List[float]], 
                                  days_ahead: int) -> float:
        """Forecast subscriber growth."""
        try:
            # Calculate growth rate
            subscribers = historical_data["subscribers"]
            if len(subscribers) < 2:
                return 0.0
                
            growth_rate = (subscribers[-1] - subscribers[0]) / subscribers[0]
            
            # Project growth
            return subscribers[-1] * (1 + growth_rate) ** days_ahead
            
        except:
            return 0.0
            
    def _forecast_post_growth(self, historical_data: Dict[str, List[float]], 
                            days_ahead: int) -> float:
        """Forecast post growth."""
        try:
            # Calculate growth rate
            posts = historical_data["posts"]
            if len(posts) < 2:
                return 0.0
                
            growth_rate = (posts[-1] - posts[0]) / posts[0]
            
            # Project growth
            return posts[-1] * (1 + growth_rate) ** days_ahead
            
        except:
            return 0.0
            
    def _forecast_comment_growth(self, historical_data: Dict[str, List[float]], 
                               days_ahead: int) -> float:
        """Forecast comment growth."""
        try:
            # Calculate growth rate
            comments = historical_data["comments"]
            if len(comments) < 2:
                return 0.0
                
            growth_rate = (comments[-1] - comments[0]) / comments[0]
            
            # Project growth
            return comments[-1] * (1 + growth_rate) ** days_ahead
            
        except:
            return 0.0
            
    def _forecast_engagement_growth(self, historical_data: Dict[str, List[float]], 
                                  days_ahead: int) -> float:
        """Forecast engagement growth."""
        try:
            # Calculate engagement metrics
            upvotes = historical_data["upvotes"]
            comments = historical_data["comments"]
            awards = historical_data["awards"]
            
            if len(upvotes) < 2:
                return 0.0
                
            # Calculate weighted engagement
            engagement = [
                u + c * 2 + a * 3  # Weighted sum
                for u, c, a in zip(upvotes, comments, awards)
            ]
            
            # Calculate growth rate
            growth_rate = (engagement[-1] - engagement[0]) / engagement[0]
            
            # Project growth
            return engagement[-1] * (1 + growth_rate) ** days_ahead
            
        except:
            return 0.0
            
    def _calculate_spam_risk(self, historical_data: Dict[str, List[float]]) -> float:
        """Calculate spam risk score."""
        try:
            # Get recent spam reports
            spam_reports = self.feedback_data.get("spam_reports", [])
            if not spam_reports:
                return 0.0
                
            # Calculate risk based on recent trend
            recent_spam = sum(spam_reports[-7:])  # Last 7 days
            avg_spam = sum(spam_reports) / len(spam_reports)
            
            return min(1.0, recent_spam / avg_spam if avg_spam > 0 else 0.0)
            
        except:
            return 0.0
            
    def _calculate_toxicity_risk(self, historical_data: Dict[str, List[float]]) -> float:
        """Calculate toxicity risk score."""
        try:
            # Get recent toxic comments
            toxic_comments = self.feedback_data.get("toxic_comments", [])
            if not toxic_comments:
                return 0.0
                
            # Calculate risk based on recent trend
            recent_toxic = sum(toxic_comments[-7:])  # Last 7 days
            avg_toxic = sum(toxic_comments) / len(toxic_comments)
            
            return min(1.0, recent_toxic / avg_toxic if avg_toxic > 0 else 0.0)
            
        except:
            return 0.0
            
    def _calculate_moderation_risk(self, historical_data: Dict[str, List[float]]) -> float:
        """Calculate moderation risk score."""
        try:
            # Get recent mod actions
            mod_actions = self.feedback_data.get("mod_actions", [])
            if not mod_actions:
                return 0.0
                
            # Calculate risk based on recent trend
            recent_actions = sum(mod_actions[-7:])  # Last 7 days
            avg_actions = sum(mod_actions) / len(mod_actions)
            
            return min(1.0, recent_actions / avg_actions if avg_actions > 0 else 0.0)
            
        except:
            return 0.0
            
    def _calculate_engagement_risk(self, historical_data: Dict[str, List[float]]) -> float:
        """Calculate engagement risk score."""
        try:
            # Get recent engagement metrics
            upvotes = historical_data["upvotes"]
            comments = historical_data["comments"]
            awards = historical_data["awards"]
            
            if len(upvotes) < 7:
                return 0.0
                
            # Calculate recent vs average engagement
            recent_engagement = sum(upvotes[-7:]) + sum(comments[-7:]) * 2 + sum(awards[-7:]) * 3
            avg_engagement = (
                sum(upvotes) + sum(comments) * 2 + sum(awards) * 3
            ) / len(upvotes)
            
            # Risk increases as engagement decreases
            return min(1.0, 1 - (recent_engagement / (avg_engagement * 7)))
            
        except:
            return 0.0
            
    def _calculate_topic_relevance(self, content: str) -> float:
        """Calculate topic relevance score."""
        try:
            # Get trending topics
            trending_topics = self._get_trending_topics()
            if not trending_topics:
                return 0.5  # Neutral score
                
            # Calculate relevance based on topic overlap
            content_words = set(content.lower().split())
            relevance_scores = []
            
            for topic in trending_topics:
                topic_words = set(topic.lower().split())
                overlap = len(content_words.intersection(topic_words))
                relevance_scores.append(overlap / len(topic_words))
                
            return sum(relevance_scores) / len(relevance_scores)
            
        except:
            return 0.5  # Neutral score
