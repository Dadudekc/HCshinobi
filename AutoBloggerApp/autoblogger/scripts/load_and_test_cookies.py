#!/usr/bin/env python3
"""
Script to test cookie-based authentication with ChatGPT.
"""

import os
import pickle
import logging
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
COOKIES_PATH = Path("cookies/chatgpt_cookies.pkl")
USER_DATA_DIR = Path("selenium_session")


def main():
    """Main function to test cookie-based authentication."""
    if not COOKIES_PATH.exists():
        logger.error(
            "❌ No saved cookies found. Please run login_and_save_cookies.py first."
        )
        return

    # Configure Chrome options
    options = Options()
    options.add_argument("--headless")
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")

    # Initialize driver
    logger.info("Starting Chrome browser...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    try:
        # Load cookies
        logger.info("Loading cookies...")
        with open(COOKIES_PATH, "rb") as f:
            cookies = pickle.load(f)

        # Navigate to ChatGPT
        logger.info("Navigating to ChatGPT...")
        driver.get("https://chat.openai.com/")

        # Add cookies
        for cookie in cookies:
            driver.add_cookie(cookie)

        # Refresh page
        logger.info("Refreshing page with cookies...")
        driver.refresh()
        time.sleep(3)

        # Verify login
        if "chat" in driver.current_url or "gpt" in driver.page_source.lower():
            logger.info("✅ Login confirmed using cookies!")

            # Test chat list access
            logger.info("Testing chat list access...")
            chat_links = driver.find_elements("css selector", "nav a[href^='/c/']")
            if chat_links:
                logger.info(f"✅ Found {len(chat_links)} chats!")
            else:
                logger.warning("⚠️ No chats found - may need to refresh cookies")
        else:
            logger.error("❌ Login failed - cookies may be expired")

    except Exception as e:
        logger.error(f"Error during cookie test: {str(e)}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
