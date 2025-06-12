import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import json
import sys

from autoblogger.scrapers.athlea.athlea_scraper import AthleaScraper
from autoblogger.scrapers.athlea.memory import Memory, Quest, MemoryBank


def setup_logging():
    """Configure logging for the test script"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,  # Ensure output goes to console
    )
    return logging.getLogger(__name__)


def test_single_chat():
    """Test processing a single chat"""
    logger = setup_logging()
    logger.info("Starting single chat test")

    scraper = AthleaScraper()
    try:
        # Initialize the scraper
        logger.info("Initializing scraper...")
        scraper.start()

        if not scraper._is_logged_in():
            logger.error(
                "Not logged into ChatGPT. Please run login_and_save_cookies.py first"
            )
            return

        # Process a single chat
        chat_url = (
            "https://chat.openai.com/c/1234567890"  # Replace with your actual chat URL
        )
        logger.info(f"Processing chat: {chat_url}")

        devlog, memory = scraper.generate_devlog(chat_url)

        if devlog and memory:
            logger.info("Successfully generated devlog and memory")
            logger.info(f"Devlog length: {len(devlog)} chars")
            logger.info(f"Memory keys: {memory.keys()}")

            # Save devlog to file
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            devlog_path = output_dir / f"devlog_{timestamp}.md"
            memory_path = output_dir / f"memory_{timestamp}.json"

            with open(devlog_path, "w", encoding="utf-8") as f:
                f.write(devlog)

            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2)

            logger.info(f"Saved devlog to {devlog_path}")
            logger.info(f"Saved memory to {memory_path}")
        else:
            logger.error("Failed to generate devlog or memory")

    except Exception as e:
        logger.error(
            f"Error in test: {str(e)}", exc_info=True
        )  # Added exc_info for full traceback
    finally:
        scraper.close()


def test_chat_history():
    """Test processing multiple chats"""
    logger = setup_logging()
    logger.info("Starting chat history test")

    scraper = AthleaScraper()
    try:
        # Initialize the scraper
        logger.info("Initializing scraper...")
        scraper.start()

        if not scraper._is_logged_in():
            logger.error(
                "Not logged into ChatGPT. Please run login_and_save_cookies.py first"
            )
            return

        # Process up to 3 recent chats
        results = scraper.process_chat_history(max_chats=3)

        if results:
            logger.info(f"Successfully processed {len(results)} chats")

            # Save results
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for i, result in enumerate(results):
                # Save devlog
                devlog_path = output_dir / f"devlog_{timestamp}_{i}.md"
                with open(devlog_path, "w", encoding="utf-8") as f:
                    f.write(result["devlog"])

                # Save memory
                memory_path = output_dir / f"memory_{timestamp}_{i}.json"
                with open(memory_path, "w", encoding="utf-8") as f:
                    json.dump(result["memory"], f, indent=2)

                logger.info(f"Saved chat {i+1} to {devlog_path} and {memory_path}")
        else:
            logger.error("No chats were processed")

    except Exception as e:
        logger.error(
            f"Error in test: {str(e)}", exc_info=True
        )  # Added exc_info for full traceback
    finally:
        scraper.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        test_chat_history()
    else:
        test_single_chat()
