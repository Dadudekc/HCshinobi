"""
DevLog Dispatcher - Autonomous content publishing agent that watches for new content
and dispatches it to various platforms using the appropriate strategies.
"""

import os
import json
import time
import logging
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from queue import Queue
from threading import Thread

from config import settings
from strategies import TwitterStrategy, LinkedInStrategy
from utils.devlog_generator import DevLogPost
from utils.devlog_analyzer import DevLogAnalyzer
from utils.logging_utils import get_logger

# Configure logging using the consolidated utility
logger = get_logger(__name__)

class ContentHandler(FileSystemEventHandler):
    """Handles file system events for new content."""
    
    def __init__(self, dispatcher: 'DevLogDispatcher'):
        self.dispatcher = dispatcher
        
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.md'):
            logger.info(f"New blog post detected: {event.src_path}")
            self.dispatcher.handle_new_blog_post(event.src_path)
        elif event.src_path.endswith('-posts.json'):
            logger.info(f"New social content detected: {event.src_path}")
            self.dispatcher.handle_new_social_content(event.src_path)

class DevLogDispatcher:
    """
    Autonomous agent that watches for new content and publishes it
    to appropriate platforms using configured strategies.
    """
    
    def __init__(self, content_queue: Queue):
        """
        Initialize the dispatcher.
        
        Args:
            content_queue: Queue containing generated content payloads.
        """
        self.content_queue = content_queue
        self.strategies = self._initialize_strategies()
        self.running = False
        self.thread: Optional[Thread] = None
        
        logger.info(f"Initialized DevLog Dispatcher with strategies for: {list(self.strategies.keys())}")
    
    def _initialize_strategies(self) -> Dict[str, object]:
        """Initialize strategy instances based on configuration."""
        strategies = {}
        # Use settings from config.settings
        # Check if required keys are present before initializing
        if settings.TWITTER_CONFIG.get('api_key') and settings.TWITTER_CONFIG.get('api_secret'):
            try:
                strategies['twitter'] = TwitterStrategy(**settings.TWITTER_CONFIG)
                logger.info("TwitterStrategy initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize TwitterStrategy: {e}", exc_info=True)

        if settings.LINKEDIN_CONFIG.get('client_id') and settings.LINKEDIN_CONFIG.get('client_secret'):
            try:
                strategies['linkedin'] = LinkedInStrategy(**settings.LINKEDIN_CONFIG)
                logger.info("LinkedInStrategy initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize LinkedInStrategy: {e}", exc_info=True)

        # Add other platform strategies here based on settings
        # e.g., if settings.FACEBOOK_CONFIG.get(...):
        #           strategies['facebook'] = FacebookStrategy(**settings.FACEBOOK_CONFIG)

        if not strategies:
            logger.warning("No social media strategies were configured or initialized successfully.")

        return strategies
    
    def start(self):
        """Start watching for new content."""
        # Watch posts directory
        self.observer.schedule(self.handler, str(self.posts_dir), recursive=False)
        # Watch social content directories
        self.observer.schedule(self.handler, str(self.social_dir), recursive=True)
        
        self.observer.start()
        logger.info(f"Started watching {self.content_dir} for new content")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.scheduler.shutdown()
            self.observer.join()
    
    def handle_new_blog_post(self, post_path: str):
        """
        Handle a new blog post file.
        
        Args:
            post_path: Path to the new blog post
        """
        if post_path in self.published["blog"]:
            return
            
        try:
            # Here you would implement the logic to publish to your blog
            # For example, via GitHub Pages API or WordPress API
            logger.info(f"Publishing blog post: {post_path}")
            
            # Generate post ID
            post_id = self._generate_post_id(post_path)
            
            # Track the post in analytics
            with open(post_path, 'r') as f:
                content = f.read()
            
            self.analyzer.track_post(
                post_id=post_id,
                platform="blog",
                post_type="article",
                content=content,
                tags=self._extract_tags(content),
                url=f"https://blog.dream.os/posts/{Path(post_path).stem}"
            )
            
            # Mark as published
            self.published["blog"].add(post_path)
            logger.info(f"Successfully published blog post: {post_path}")
            
        except Exception as e:
            logger.error(f"Failed to publish blog post {post_path}: {str(e)}")
    
    def handle_new_social_content(self, content_path: str):
        """
        Handle new social media content.
        
        Args:
            content_path: Path to the social content JSON file
        """
        if content_path in self.published["twitter"] and content_path in self.published["linkedin"]:
            return
            
        try:
            with open(content_path, 'r') as f:
                posts = json.load(f)
            
            platform = "twitter" if "twitter" in content_path else "linkedin"
            strategy = self.strategies.get(platform)
            
            if not strategy:
                logger.warning(f"No strategy configured for {platform}")
                return
            
            # Get optimal posting time
            best_times = self.analyzer.get_best_posting_times(platform)
            publish_time = self._get_next_optimal_time(best_times)
            
            # Schedule posts
            for post in posts:
                post_id = self._generate_post_id(content_path, post["content"])
                
                # Track the post
                self.analyzer.track_post(
                    post_id=post_id,
                    platform=platform,
                    post_type=post["type"],
                    content=post["content"],
                    tags=self._extract_tags(post["content"])
                )
                
                # Schedule the post
                self.schedule_post(
                    post_path=content_path,
                    platform=platform,
                    post_type=post["type"],
                    content=post["content"],
                    post_id=post_id,
                    publish_time=publish_time
                )
                
                # Add 15 minutes for the next post if it's a thread
                publish_time = publish_time + timedelta(minutes=15)
            
            # Mark as published
            self.published[platform].add(content_path)
            logger.info(f"Successfully scheduled {platform} content: {content_path}")
            
        except Exception as e:
            logger.error(f"Failed to handle social content {content_path}: {str(e)}")
    
    def schedule_post(
        self,
        post_path: str,
        platform: str,
        post_type: str,
        content: str,
        post_id: str,
        publish_time: datetime
    ):
        """
        Schedule a post for future publishing.
        
        Args:
            post_path: Path to the content to publish
            platform: Target platform
            post_type: Type of post (main, thread, article)
            content: Post content
            post_id: Unique post identifier
            publish_time: When to publish the content
        """
        try:
            strategy = self.strategies.get(platform)
            
            # Define the job function
            def publish_job():
                try:
                    if post_type == "main":
                        success = strategy.post_update(content)
                    elif post_type == "thread" and platform == "twitter":
                        success = strategy.post_thread(content)
                    else:
                        success = strategy.post_article(content)
                    
                    if success:
                        logger.info(f"Successfully published scheduled post: {post_id}")
                        # Initialize metrics
                        self.analyzer.update_metrics(post_id, {"views": 0, "likes": 0, "shares": 0})
                    else:
                        logger.error(f"Failed to publish scheduled post: {post_id}")
                        
                except Exception as e:
                    logger.error(f"Error in publish job for {post_id}: {str(e)}")
            
            # Schedule the job
            self.scheduler.add_job(
                publish_job,
                trigger=DateTrigger(run_date=publish_time),
                id=post_id,
                name=f"Publish {platform} {post_type}"
            )
            
            logger.info(f"Scheduled post {post_id} for {publish_time}")
            
        except Exception as e:
            logger.error(f"Failed to schedule post {post_id}: {str(e)}")
    
    def _generate_post_id(self, file_path: str, content: str = "") -> str:
        """Generate a unique post ID."""
        hash_input = f"{file_path}:{content}:{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        words = content.split()
        return [word[1:] for word in words if word.startswith("#")]
    
    def _get_next_optimal_time(self, best_times: Dict[str, List[str]]) -> datetime:
        """Get the next optimal posting time."""
        now = datetime.now()
        current_day = now.strftime("%A")
        
        # Get best hours for current day
        best_hours = best_times.get(current_day, [])
        
        if not best_hours:
            # If no optimal times, schedule for next hour
            next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            # Find the next best hour
            current_hour = now.hour
            next_hour = None
            
            for hour in best_hours:
                if int(hour) > current_hour:
                    next_hour = int(hour)
                    break
            
            if next_hour is None:
                # No more optimal times today, use first optimal time tomorrow
                tomorrow = now + timedelta(days=1)
                next_time = tomorrow.replace(
                    hour=int(best_hours[0]),
                    minute=0,
                    second=0,
                    microsecond=0
                )
            else:
                next_time = now.replace(
                    hour=next_hour,
                    minute=0,
                    second=0,
                    microsecond=0
                )
        
        return next_time

def main():
    """Main entry point for the DevLog Dispatcher."""
    # Load configuration
    twitter_config = {
        "api_key": os.getenv("TWITTER_API_KEY"),
        "api_secret": os.getenv("TWITTER_API_SECRET"),
        "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    }
    
    linkedin_config = {
        "client_id": os.getenv("LINKEDIN_CLIENT_ID"),
        "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET"),
        "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN")
    }
    
    # Initialize and start dispatcher
    dispatcher = DevLogDispatcher(
        twitter_config=twitter_config,
        linkedin_config=linkedin_config
    )
    
    dispatcher.start()

if __name__ == "__main__":
    main() 