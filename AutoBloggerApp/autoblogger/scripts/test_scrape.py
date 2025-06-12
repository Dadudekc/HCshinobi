#!/usr/bin/env python3
# autoblogger/scripts/quick_scrape_test.py

import sys
import logging
from pathlib import Path
from autoblogger.core.logging import get_logger
from autoblogger.core.profile import check_selenium_profile_ready
from autoblogger.scrapers.chatgpt import ChatGPTScraper

# Configure root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = get_logger(__name__)


def run_quick_test():
    """Run a quick test of the ChatGPT scraper."""
    logger.info("Starting quick test...")

    # Get profile path
    profile_path = str(
        Path.home()
        / "AppData"
        / "Local"
        / "Google"
        / "Chrome"
        / "User Data"
        / "Default"
    )
    logger.info(f"Using Chrome profile at: {profile_path}")

    # Check if profile is ready
    if not check_selenium_profile_ready(profile_path):
        logger.error("Profile not ready. Please run setup first:")
        logger.error("python -m autoblogger.scripts.setup_automation_profile")
        return False

    try:
        # Initialize scraper
        logger.info("Initializing ChatGPT scraper...")
        scraper = ChatGPTScraper(headless=False)  # Keep visible for debugging

        # Start browser
        logger.info("Starting browser session...")
        scraper.start()

        # Get chat list
        logger.info("Fetching chat list...")
        chats = scraper.extract_chat_list()

        if not chats:
            logger.warning("No chats found. This might be a new account.")
        else:
            logger.info(f"Found {len(chats)} chats")
            for chat in chats[:3]:  # Show first 3 chats
                logger.info(f"- {chat.title} ({chat.message_count} messages)")

        # Try to generate a devlog from the first chat
        if chats:
            logger.info("Testing devlog generation...")
            first_chat = chats[0]
            devlog = scraper.generate_devlog(first_chat.url)

            if devlog:
                logger.info("Devlog generation successful!")
                logger.info(f"Generated {len(devlog)} characters")
            else:
                logger.warning("Devlog generation failed")

        logger.info("Quick test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

    finally:
        if "scraper" in locals():
            scraper.close()


if __name__ == "__main__":
    success = run_quick_test()
    sys.exit(0 if success else 1)
