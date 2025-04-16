"""
ChatGPT Web Scraper - Automated chat history extraction tool.
Uses undetected-chromedriver to avoid detection and provides robust session management.
"""
import os
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException
)
import undetected_chromedriver as uc
from utils.retry_utils import retry_selenium_action

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ChatGPTScraper')

# Constants
COOKIE_FILE = "chatgpt_cookies.json"
CHATGPT_URL = "https://chat.openai.com"
JQUERY_URL = "https://code.jquery.com/jquery-3.6.0.min.js"
WAIT_TIMEOUT = 30

class ChatGPTScraper:
    """Manages ChatGPT web scraping operations with session persistence."""
    
    def __init__(self, cookie_file: str = COOKIE_FILE, headless: bool = False):
        """
        Initialize the scraper with configuration.
        
        Args:
            cookie_file: Path to store/load cookies
            headless: Whether to run in headless mode
        """
        self.cookie_file = cookie_file
        self.headless = headless
        self.driver = None
        self.wait = None
        logger.info("Initializing ChatGPT Scraper")

    def __enter__(self):
        """Context manager entry."""
        self.setup_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        if exc_type:
            logger.error(f"Error during execution: {exc_type.__name__}: {exc_val}")
            return False
        return True

    @retry_selenium_action(max_attempts=3)
    def setup_browser(self) -> None:
        """Initialize and configure the browser with retry mechanism."""
        try:
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--start-maximized")

            self.driver = uc.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, WAIT_TIMEOUT)
            logger.info("Browser setup completed successfully")
        except WebDriverException as e:
            logger.error(f"Failed to setup browser: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser cleanup completed")
            except WebDriverException as e:
                logger.error(f"Error during browser cleanup: {str(e)}")

    def save_cookies(self) -> bool:
        """
        Save current session cookies to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cookies = self.driver.get_cookies()
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "w") as f:
                json.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_file}")
            return True
        except (IOError, WebDriverException) as e:
            logger.error(f"Failed to save cookies: {str(e)}")
            return False

    def load_cookies(self) -> bool:
        """
        Load cookies from file to restore session.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(self.cookie_file):
            logger.info("No cookie file found")
            return False
        
        try:
            with open(self.cookie_file, "r") as f:
                cookies = json.load(f)
            for cookie in cookies:
                if "sameSite" in cookie and cookie["sameSite"] == "None":
                    cookie["sameSite"] = "Strict"
                self.driver.add_cookie(cookie)
            logger.info("Cookies loaded successfully")
            return True
        except (IOError, WebDriverException, json.JSONDecodeError) as e:
            logger.error(f"Failed to load cookies: {str(e)}")
            return False

    @retry_selenium_action(max_attempts=3)
    def inject_jquery(self) -> bool:
        """
        Inject jQuery into the page for enhanced DOM manipulation.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.driver.execute_script(f'''
                if (typeof jQuery === 'undefined') {{
                    var script = document.createElement("script");
                    script.src = "{JQUERY_URL}";
                    document.head.appendChild(script);
                }}
            ''')
            time.sleep(1)  # Wait for jQuery to load
            # Verify jQuery loaded
            jquery_loaded = self.driver.execute_script("return typeof jQuery !== 'undefined';")
            if jquery_loaded:
                logger.info("jQuery injected successfully")
                return True
            else:
                logger.error("jQuery injection failed")
                return False
        except WebDriverException as e:
            logger.error(f"Error injecting jQuery: {str(e)}")
            return False

    @retry_selenium_action(max_attempts=3)
    def scroll_and_capture_chats(self) -> List[Dict[str, str]]:
        """
        Scroll through chat history and capture all chat metadata.
        
        Returns:
            List[Dict[str, str]]: List of chat metadata dictionaries
        """
        if not self.inject_jquery():
            logger.error("Failed to inject jQuery, proceeding with basic scrolling")

        logger.info("Starting chat capture")
        chats_data = []
        
        try:
            # Scroll chat sidebar
            self.driver.execute_script("""
                async function scrollChats() {
                    let container = document.querySelector('[aria-label="Chat history"]');
                    if (!container) return;
                    let prevScroll = -1;
                    while (container.scrollTop !== prevScroll) {
                        prevScroll = container.scrollTop;
                        container.scrollTo(0, container.scrollHeight);
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                }
                scrollChats();
            """)
            time.sleep(5)  # Wait for content load

            chat_tiles = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="conversation-item"]')
            logger.info(f"Found {len(chat_tiles)} chat tiles")

            for tile in chat_tiles:
                try:
                    title = tile.text.strip()
                    link_elem = tile.find_element(By.TAG_NAME, 'a')
                    url = link_elem.get_attribute('href')
                    timestamp = link_elem.get_attribute('data-timestamp') or ""
                    
                    chat_data = {
                        "title": title,
                        "url": url,
                        "timestamp": timestamp,
                        "captured_at": datetime.now().isoformat()
                    }
                    chats_data.append(chat_data)
                except (NoSuchElementException, StaleElementReferenceException) as e:
                    logger.warning(f"Failed to capture chat tile: {str(e)}")
                    continue

            logger.info(f"Successfully captured {len(chats_data)} chats")
            return chats_data
        except WebDriverException as e:
            logger.error(f"Error during chat capture: {str(e)}")
            return []

    def run_scraper(self, model_append: str = "", output_file: str = "chatgpt_chats.json") -> bool:
        """
        Main scraping workflow.
        
        Args:
            model_append: URL parameter to specify ChatGPT model
            output_file: Path to save captured chat data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.driver.get(CHATGPT_URL + model_append)
            logger.info("Navigated to ChatGPT")

            if not self.load_cookies():
                logger.info("Waiting for manual login (30s)...")
                time.sleep(30)  # Allow time for manual login
                self.save_cookies()

            # Refresh to apply cookies/ensure logged in state
            self.driver.refresh()
            time.sleep(5)

            chats = self.scroll_and_capture_chats()
            if not chats:
                logger.error("No chats captured")
                return False

            # Save captured data
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, "w") as f:
                    json.dump(chats, f, indent=2)
                logger.info(f"Chats saved to {output_file}")
                return True
            except IOError as e:
                logger.error(f"Failed to save chat data: {str(e)}")
                return False

        except WebDriverException as e:
            logger.error(f"Scraper execution failed: {str(e)}")
            return False

def main():
    """CLI entry point."""
    with ChatGPTScraper() as scraper:
        success = scraper.run_scraper(model_append="?model=gpt-4")
        if success:
            logger.info("Scraping completed successfully")
        else:
            logger.error("Scraping failed")
            return 1
    return 0

if __name__ == "__main__":
    exit(main()) 