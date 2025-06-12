#!/usr/bin/env python3
# autoblogger/scrapers/chatgpt.py

import os
import logging
from typing import Optional, Dict, Any, List, Tuple, Union
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
)
import openai
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import time
import json
import pickle
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re
import shutil
import sys
from webdriver_manager.chrome import ChromeDriverManager
from autoblogger.core.profile import check_selenium_profile_ready

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def is_real_profile(profile_path: str) -> bool:
    """Check if the given profile path is a real Chrome user profile."""
    path = Path(profile_path).expanduser().resolve()
    return (
        "Default" in path.name
        or "Profile" in path.name
        or "User Data" in str(path)
        or str(path).lower().endswith("default")
    )


@dataclass
class ChatMetadata:
    """Metadata for a ChatGPT conversation."""

    title: str
    url: str
    created_at: datetime
    last_modified: datetime
    message_count: int
    topics: List[str]
    technologies: List[str]
    project_context: Optional[str] = None


class ChatGPTScraper:
    """Scrapes ChatGPT conversations and generates devlogs from them."""

    def __init__(self, headless: bool = True):
        """Initialize the scraper with browser settings."""
        self.logger = logging.getLogger(__name__)

        # Configure Chrome options
        options = uc.ChromeOptions()

        # Use a dedicated automation profile
        self.profile_path = str(
            Path.home()
            / "AppData"
            / "Local"
            / "Google"
            / "Chrome"
            / "User Data"
            / "SeleniumProfile"
        )
        options.add_argument(f"--user-data-dir={self.profile_path}")

        # Enable headless mode for automation profile
        if headless:
            options.add_argument("--headless=new")
            self.logger.info("✅ Using automation profile with headless mode")

        # Additional options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")

        self.options = options
        self.driver = None
        self.wait = None
        self.cookies_path = Path("cookies/chatgpt_cookies.pkl")

        self.logger.info(f"🧠 Using automation profile: {self.profile_path}")

    def start(self):
        """Start the browser session and load cookies."""
        # Check if profile is ready
        if not check_selenium_profile_ready(self.profile_path):
            self.logger.error("❌ Automation profile not ready. Please run setup first:")
            self.logger.error("python -m autoblogger.scripts.setup_automation_profile")
            raise Exception("Profile not ready")

        self.driver = uc.Chrome(
            options=self.options, driver_executable_path=ChromeDriverManager().install()
        )

        self.wait = WebDriverWait(self.driver, 10)

        # Navigate to ChatGPT
        self.driver.get("https://chat.openai.com/")
        time.sleep(3)  # Give it a moment to load

        # Verify login
        if not self._is_logged_in():
            self.logger.error("Not logged into ChatGPT. Please run setup again:")
            self.logger.error("python -m autoblogger.scripts.setup_automation_profile")
            raise Exception("Authentication failed")

        self.logger.info("Successfully authenticated with existing Chrome profile")

    def _is_logged_in(self) -> bool:
        """Check if we're logged in by looking for chat elements."""
        try:
            return (
                "chat" in self.driver.current_url
                or "gpt" in self.driver.page_source.lower()
                or len(self.driver.find_elements(By.CSS_SELECTOR, "nav a[href^='/c/']"))
                > 0
            )
        except:
            return False

    def close(self):
        """Close the browser session."""
        if self.driver:
            self.driver.quit()

    def extract_chat_list(self) -> List[ChatMetadata]:
        """
        Extract detailed chat history from the sidebar.

        Returns:
            List of ChatMetadata objects containing chat information
        """
        try:
            # Wait for chat list to load
            chat_links = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "nav a[href^='/c/']")
                )
            )

            chats = []
            for link in chat_links:
                try:
                    # Extract basic info
                    title = link.text.strip()
                    url = link.get_attribute("href")

                    if not (title and url):
                        continue

                    # Get chat metadata
                    metadata = self._extract_chat_metadata(url)
                    if metadata:
                        chats.append(metadata)

                except Exception as e:
                    self.logger.warning(f"Failed to extract chat info: {str(e)}")
                    continue

            return chats

        except Exception as e:
            self.logger.error(f"Failed to get chat history: {str(e)}")
            return []

    def _extract_chat_metadata(self, chat_url: str) -> Optional[ChatMetadata]:
        """
        Extract detailed metadata from a chat conversation.

        Args:
            chat_url: URL of the chat to analyze

        Returns:
            ChatMetadata object or None if extraction fails
        """
        try:
            # Navigate to chat
            self.driver.get(chat_url)

            # Wait for chat to load
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-message-author-role]")
                )
            )

            # Extract metadata from page
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Get message count
            messages = soup.find_all("div", {"data-message-author-role": True})
            message_count = len(messages)

            # Extract dates (if available)
            created_at = datetime.now()  # Default to now if not found
            last_modified = created_at

            # Extract topics and technologies
            topics = []
            technologies = []

            # Look for common tech stack mentions
            tech_keywords = [
                "python",
                "javascript",
                "react",
                "node",
                "docker",
                "kubernetes",
            ]
            for msg in messages:
                text = msg.get_text().lower()
                for tech in tech_keywords:
                    if tech in text and tech not in technologies:
                        technologies.append(tech)

            # Try to identify project context
            project_context = None
            first_message = messages[0].get_text() if messages else ""
            if "project" in first_message.lower():
                project_context = first_message[:200]  # First 200 chars as context

            return ChatMetadata(
                title=soup.title.string if soup.title else "Untitled Chat",
                url=chat_url,
                created_at=created_at,
                last_modified=last_modified,
                message_count=message_count,
                topics=topics,
                technologies=technologies,
                project_context=project_context,
            )

        except Exception as e:
            self.logger.error(f"Failed to extract chat metadata: {str(e)}")
            return None

    def generate_devlog(self, chat_url: str) -> Optional[str]:
        """
        Generate a devlog by asking ChatGPT to summarize its own conversation.

        Args:
            chat_url: URL of the chat to process

        Returns:
            str: Generated devlog content or None if failed
        """
        try:
            # Navigate to chat
            self.driver.get(chat_url)

            # Wait for chat to load
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-message-author-role]")
                )
            )

            # Find input box
            input_box = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "textarea[data-id='root']")
                )
            )

            # Inject the summary prompt
            prompt = (
                "Can you summarize this entire conversation into a devlog-style blog post? "
                "Please highlight:\n"
                "1. Key decisions made\n"
                "2. Technical challenges encountered\n"
                "3. Breakthrough moments\n"
                "4. Lessons learned\n\n"
                "Format it as a proper blog post with sections and a conclusion."
            )

            # Clear any existing text and send prompt
            input_box.clear()
            input_box.send_keys(prompt)

            # Submit prompt
            submit_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-testid='send-button']")
                )
            )
            submit_btn.click()

            # Wait for response (with timeout)
            try:
                response = self.wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div[data-message-author-role='assistant']:last-child",
                        )
                    )
                )
                return response.text
            except TimeoutException:
                self.logger.error("Timeout waiting for ChatGPT response")
                return None

        except Exception as e:
            self.logger.error(f"Failed to generate devlog: {str(e)}")
            return None

    def process_chat_history(self, max_chats: int = 10) -> List[Dict[str, Any]]:
        """
        Process recent chats and generate devlogs for each.

        Args:
            max_chats: Maximum number of chats to process

        Returns:
            List of dictionaries containing chat metadata and generated devlog
        """
        try:
            # Get list of chats
            chats = self.extract_chat_list()
            if not chats:
                return []

            # Process up to max_chats
            results = []
            for chat in chats[:max_chats]:
                try:
                    # Generate devlog
                    devlog_content = self.generate_devlog(chat.url)
                    if devlog_content:
                        results.append(
                            {
                                "title": chat.title,
                                "url": chat.url,
                                "created_at": chat.created_at,
                                "devlog": devlog_content,
                            }
                        )
                        # Small delay between chats
                        time.sleep(2)
                except Exception as e:
                    self.logger.error(f"Failed to process chat {chat.url}: {str(e)}")
                    continue

            return results

        except Exception as e:
            self.logger.error(f"Failed to process chat history: {str(e)}")
            return []

    def save_devlog(self, chat_info: ChatMetadata, content: str) -> bool:
        """
        Save the generated devlog to a file.

        Args:
            chat_info: ChatMetadata object with chat information
            content: Devlog content to save

        Returns:
            bool: True if successful
        """
        try:
            # Create output directory
            output_dir = Path("output/devlogs")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from chat title
            safe_title = "".join(c if c.isalnum() else "_" for c in chat_info.title)
            filename = f"devlog_{safe_title}.md"
            output_path = output_dir / filename

            # Add metadata
            metadata = {
                "title": chat_info.title,
                "source_chat": chat_info.url,
                "generated_at": datetime.now().isoformat(),
                "message_count": chat_info.message_count,
                "technologies": chat_info.technologies,
                "project_context": chat_info.project_context,
            }

            # Write file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                for key, value in metadata.items():
                    if value:  # Only write non-empty values
                        f.write(f"{key}: {value}\n")
                f.write("---\n\n")
                f.write(content)

            return True

        except Exception as e:
            self.logger.error(f"Failed to save devlog: {str(e)}")
            return False


# ---------------------------
# Hybrid Response Handler Class
# ---------------------------
class HybridResponseHandler:
    """
    Parses a hybrid response that includes both narrative text and a MEMORY_UPDATE JSON block.
    Returns a tuple of (text_part, memory_update_json).
    """

    def parse_hybrid_response(self, raw_response: str) -> Tuple[str, dict]:
        """Extract text and structured JSON data from a hybrid response."""
        logger.info("Parsing hybrid response for narrative text and MEMORY_UPDATE JSON")

        # Regex to capture JSON block between ```json and ```
        json_pattern = r"""```json(.*?)```"""
        match = re.search(json_pattern, raw_response, re.DOTALL)

        if match:
            json_content = match.group(1).strip()
            try:
                memory_update = json.loads(json_content)
                logger.info("Successfully parsed MEMORY_UPDATE JSON")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                memory_update = {}
        else:
            logger.info("No JSON block found in the response")
            memory_update = {}

        # Remove the JSON block from the raw response to extract pure narrative text
        text_part = re.sub(json_pattern, "", raw_response, flags=re.DOTALL).strip()

        return text_part, memory_update
