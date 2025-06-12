#!/usr/bin/env python3
"""
Script to set up a dedicated Chrome profile for automation and log into ChatGPT.
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from autoblogger.core.logging import get_logger
from autoblogger.core.profile import (
    check_selenium_profile_ready,
    reset_profile,
    mark_profile_ready,
)
from autoblogger.core.chrome import ensure_chrome_clean
from selenium.common.exceptions import WebDriverException

logger = get_logger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Setup Chrome automation profile")
    parser.add_argument(
        "--reset", action="store_true", help="Reset the automation profile"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check if profile is ready"
    )
    return parser.parse_args()


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info("Received interrupt signal. Cleaning up...")
    if "driver" in globals():
        driver.quit()
    sys.exit(0)


def get_chrome_options(profile_path: str) -> webdriver.ChromeOptions:
    """Get configured Chrome options."""
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--start-maximized")

    # Stability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    # Performance options
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-breakpad")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")

    return options


def main():
    """Main setup function."""
    args = parse_args()

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get profile path
    profile_path = str(
        Path.home()
        / "AppData"
        / "Local"
        / "Google"
        / "Chrome"
        / "User Data"
        / "SeleniumProfile"
    )
    logger.info(f"Using automation profile at: {profile_path}")

    # Handle reset flag
    if args.reset:
        logger.info("Resetting Chrome profile...")
        if reset_profile(profile_path):
            logger.info("Profile reset successful")
        else:
            logger.warning("Profile reset failed or profile not found")

    # Handle check flag
    if args.check:
        if check_selenium_profile_ready(profile_path):
            logger.info("Profile is ready")
            return True
        else:
            logger.warning("Profile is not ready")
            return False

    # Ensure Chrome is clean before starting
    if not ensure_chrome_clean():
        logger.error("Failed to clean up Chrome processes")
        return False

    driver = None
    try:
        # Create profile directory
        Path(profile_path).mkdir(parents=True, exist_ok=True)

        # Get Chrome options
        options = get_chrome_options(profile_path)

        # Start Chrome
        logger.info("Starting Chrome browser...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

        # Set page load timeout
        driver.set_page_load_timeout(30)

        # Navigate to ChatGPT
        driver.get("https://chat.openai.com/")

        # Wait for user to log in
        logger.info("Please log in to ChatGPT in the browser window...")
        logger.info("Waiting for login to complete...")

        # Wait for login to complete with retries and longer timeouts
        max_retries = 5  # Increased from 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Check if browser is still alive
                if not driver.window_handles:
                    logger.error("Browser window was closed")
                    return False

                # Try to find login success indicators
                wait = WebDriverWait(driver, 60)  # 1 minute per attempt
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "nav a[href^='/c/']")
                    )
                )

                # Additional verification
                if "chat" in driver.current_url or "gpt" in driver.page_source.lower():
                    logger.info("Login successful!")
                    mark_profile_ready(profile_path)
                    return True

            except WebDriverException as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise
                logger.warning(
                    f"Login check failed, retrying ({retry_count}/{max_retries})..."
                )
                time.sleep(10)  # Increased from 5

        logger.error("Login verification failed after all retries")
        return False

    except Exception as e:
        logger.error(f"Error during setup: {e}")
        return False

    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"Error while quitting driver: {e}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
