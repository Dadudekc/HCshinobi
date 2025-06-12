#!/usr/bin/env python3
"""
Script to manually log into ChatGPT and save cookies for future sessions.
"""

import os
import pickle
import logging
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
COOKIES_DIR = Path("cookies")
COOKIES_PATH = COOKIES_DIR / "chatgpt_cookies.pkl"
USER_DATA_DIR = Path("selenium_session")


def main():
    """Main function to handle login and cookie saving."""
    # Create directories
    COOKIES_DIR.mkdir(exist_ok=True)
    USER_DATA_DIR.mkdir(exist_ok=True)

    # Configure Chrome options
    options = Options()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--start-maximized")

    # Initialize driver
    logger.info("Starting Chrome browser...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    try:
        # Navigate to ChatGPT
        logger.info("Navigating to ChatGPT...")
        driver.get("https://chat.openai.com/")

        # Wait for manual login
        logger.info("❗ Please log in manually...")
        input("✅ Press [ENTER] after you've fully logged in and can see your chats.\n")

        # Verify login
        if "chat" in driver.current_url or "gpt" in driver.page_source.lower():
            logger.info("✅ Login confirmed!")

            # Save cookies
            logger.info("Saving cookies...")
            with open(COOKIES_PATH, "wb") as f:
                pickle.dump(driver.get_cookies(), f)
            logger.info(f"✅ Cookies saved to: {COOKIES_PATH}")
        else:
            logger.error("❌ Login not confirmed - please try again")

    except Exception as e:
        logger.error(f"Error during login process: {str(e)}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
