"""
Base class for all social media platform strategies.
Provides common functionality and interface for platform-specific implementations.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from abc import ABC, abstractmethod

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.task_engine.utils.log_writer import get_social_logger, write_json_log
from core.task_engine.utils.cookie_manager import CookieManager
from core.task_engine.utils.sentiment_analyzer import SentimentAnalyzer

logger = get_social_logger()

class BasePlatformStrategy(ABC):
    """Base class for all social media platform strategies."""

    def __init__(self, driver: webdriver.Remote):
        """Initialize base strategy with browser automation."""
        self.driver = driver
        self.platform_id = None
        self.login_url = None
        self.config = {}
        self.feedback_data = {}
        self.cookie_manager = CookieManager()
        self.feedback_db = Path("data/feedback") / f"{self.platform_id}_feedback.json"
        self.follow_db = Path("data/follows") / f"{self.platform_id}_follows.json"
        
    @abstractmethod
    def _login(self) -> bool:
        """Perform login to the platform."""
        pass

    @abstractmethod
    def execute(self) -> None:
        """Execute the platform strategy."""
        pass

    def _load_feedback_data(self) -> Dict:
        """Load feedback data for the platform."""
        try:
            if os.path.exists(self.feedback_db):
                with open(self.feedback_db, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"Error loading feedback data: {str(e)}")
            return {}
        
    def _save_feedback_data(self):
        """Save updated feedback data."""
        os.makedirs(self.feedback_db.parent, exist_ok=True)
        with open(self.feedback_db, "w") as f:
            json.dump(self.feedback_data, f, indent=4)
            
    def _wait(self, custom_range: Optional[tuple] = None):
        """Wait for a random duration."""
        import random
        import time
        wait_range = custom_range or (3, 6)
        wait_time = random.uniform(*wait_range)
        logger.debug(f"⏳ Waiting for {round(wait_time, 2)} seconds...")
        time.sleep(wait_time)
        
    def get_community_metrics(self) -> Dict[str, Any]:
        """Get platform-specific community metrics."""
        raise NotImplementedError
        
    def get_top_members(self) -> List[Dict[str, Any]]:
        """Get list of top community members."""
        raise NotImplementedError
        
    def track_member_interaction(self, member_id: str, 
                               interaction_type: str,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Track an interaction with a community member."""
        raise NotImplementedError
        
    def run_daily_strategy_session(self):
        """Run complete daily strategy session."""
        raise NotImplementedError
