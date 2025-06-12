#!/usr/bin/env python3
"""
Script to generate devlogs from ChatGPT conversations.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from autoblogger.scrapers.chatgpt import ChatGPTScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to generate devlogs."""
    # Load environment variables
    load_dotenv()

    # Get credentials
    email = os.getenv("CHATGPT_EMAIL")
    password = os.getenv("CHATGPT_PASSWORD")

    if not email or not password:
        logger.error("CHATGPT_EMAIL and CHATGPT_PASSWORD must be set in .env")
        sys.exit(1)

    # Initialize scraper
    scraper = ChatGPTScraper(headless=False)  # Set to True for production
    scraper.start()

    try:
        # Login to ChatGPT
        logger.info("Logging in to ChatGPT...")
        if not scraper.login(email, password):
            logger.error("Failed to login")
            sys.exit(1)

        # Get chat history
        logger.info("Fetching chat history...")
        chats = scraper.get_chat_history()

        if not chats:
            logger.error("No chats found")
            sys.exit(1)

        logger.info(f"Found {len(chats)} chats")

        # Process each chat
        for i, chat in enumerate(chats, 1):
            logger.info(f"Processing chat {i}/{len(chats)}: {chat['title']}")

            # Generate devlog
            devlog = scraper.generate_devlog(chat["url"])

            if devlog:
                # Save devlog
                if scraper.save_devlog(chat, devlog):
                    logger.info(f"Saved devlog for: {chat['title']}")
                else:
                    logger.error(f"Failed to save devlog for: {chat['title']}")
            else:
                logger.error(f"Failed to generate devlog for: {chat['title']}")

        logger.info("Devlog generation complete!")

    except Exception as e:
        logger.error(f"Error during devlog generation: {str(e)}")
        sys.exit(1)

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
