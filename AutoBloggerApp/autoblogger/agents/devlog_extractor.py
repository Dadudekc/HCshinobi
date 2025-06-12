#!/usr/bin/env python3
# autoblogger/agents/devlog_extractor.py

import os
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from autoblogger.scrapers.chatgpt import ChatGPTScraper
from autoblogger.services.devlog_service import DevlogService
from autoblogger.services.vector_db import VectorDB

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ChatHistory:
    """Data class for chat history entries."""

    chat_id: str
    title: str
    messages: List[dict]
    timestamp: datetime = datetime.now()


class DevlogExtractor:
    """Agent for extracting devlogs from ChatGPT history."""

    def __init__(
        self,
        output_dir: Path,
        max_chats: int = 5,
        rate_limit: int = 3,
        headless: bool = False,
    ):
        """
        Initialize the devlog extractor.

        Args:
            output_dir: Directory to save extracted devlogs
            max_chats: Maximum number of chats to process
            rate_limit: Seconds to wait between requests
            headless: Whether to run browser in headless mode
        """
        self.output_dir = Path(output_dir)
        self.max_chats = max_chats
        self.rate_limit = rate_limit
        self.headless = headless

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize services
        self.scraper = ChatGPTScraper(headless=headless)
        self.devlog_service = DevlogService(self.scraper)
        self.vector_db = VectorDB()

        logger.info(f"Initialized DevlogExtractor with output_dir={output_dir}")
        logger.info(f"Max chats: {max_chats}, Rate limit: {rate_limit}s")
        logger.info(f"Headless mode: {'enabled' if headless else 'disabled'}")

    def run(self):
        """Run the devlog extraction process."""
        try:
            logger.info("Starting devlog extraction process")

            # Extract chat history
            chat_history = self.extract_chat_history()
            logger.info(f"Extracted {len(chat_history)} chats")

            # Process each chat
            for chat in chat_history:
                try:
                    logger.info(f"Processing chat: {chat.title}")
                    self.process_chat(chat)
                    time.sleep(self.rate_limit)
                except Exception as e:
                    logger.error(f"Error processing chat {chat.chat_id}: {e}")
                    continue

            logger.info("Devlog extraction completed")

        except Exception as e:
            logger.error(f"Error in extraction process: {e}")
            raise
        finally:
            self.cleanup()

    def extract_chat_history(self) -> List[ChatHistory]:
        """Extract chat history from ChatGPT interface."""
        try:
            logger.info("Navigating to ChatGPT interface")
            self.scraper.driver.get("https://chat.openai.com")

            # Wait for chat list to load
            logger.info("Waiting for chat list to load")
            WebDriverWait(self.scraper.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-testid='conversation-turn-2']")
                )
            )

            # Get chat elements
            chat_elements = self.scraper.driver.find_elements(
                By.CSS_SELECTOR, "[data-testid='conversation-turn-2']"
            )[: self.max_chats]

            chat_history = []
            for element in chat_elements:
                try:
                    chat_id = element.get_attribute("data-conversation-id")
                    title = element.find_element(
                        By.CSS_SELECTOR, ".conversation-title"
                    ).text

                    # Get messages
                    messages = []
                    message_elements = element.find_elements(
                        By.CSS_SELECTOR, ".message"
                    )

                    for msg in message_elements:
                        role = msg.get_attribute("data-role")
                        content = msg.find_element(
                            By.CSS_SELECTOR, ".message-content"
                        ).text
                        messages.append({"role": role, "content": content})

                    chat_history.append(
                        ChatHistory(chat_id=chat_id, title=title, messages=messages)
                    )

                except Exception as e:
                    logger.error(f"Error extracting chat: {e}")
                    continue

            return chat_history

        except Exception as e:
            logger.error(f"Error extracting chat history: {e}")
            raise

    def process_chat(self, chat: ChatHistory):
        """Process a single chat into a devlog entry."""
        try:
            logger.info(f"Processing chat: {chat.title}")

            # Generate summary
            summary_prompt = (
                f"Summarize this ChatGPT conversation as a devlog entry:\n\n"
                f"Title: {chat.title}\n\n"
                f"Messages:\n"
                + "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat.messages)
            )

            summary = self.scraper.query_ai(summary_prompt)

            # Create devlog entry
            entry = {
                "chat_id": chat.chat_id,
                "title": chat.title,
                "timestamp": chat.timestamp.isoformat(),
                "messages": chat.messages,
                "summary": summary,
            }

            # Save to file
            output_file = self.output_dir / f"{chat.chat_id}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2)

            # Store in vector DB
            self.vector_db.store_document(
                doc_id=chat.chat_id,
                content=summary,
                metadata={"title": chat.title, "timestamp": chat.timestamp.isoformat()},
            )

            logger.info(f"Saved devlog entry to {output_file}")

        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            raise

    def cleanup(self):
        """Clean up resources."""
        try:
            logger.info("Cleaning up resources")
            self.scraper.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point."""
    try:
        extractor = DevlogExtractor(
            output_dir="output/devlogs", max_chats=5, rate_limit=3, headless=False
        )
        extractor.run()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
