#!/usr/bin/env python3
# autoblogger/cli/extract_devlogs.py

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from autoblogger.agents.devlog_extractor import DevlogExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Extract devlogs from ChatGPT history")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/devlogs",
        help="Directory to save devlogs (default: output/devlogs)",
    )
    parser.add_argument(
        "--max-chats",
        type=int,
        default=5,
        help="Maximum number of chats to process (default: 5)",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=3,
        help="Wait time in seconds between requests (default: 3)",
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode"
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    try:
        args = parse_args()

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting devlog extraction to {output_dir}")
        logger.info(f"Processing up to {args.max_chats} chats")
        logger.info(f"Rate limit: {args.rate_limit} seconds")
        logger.info(f"Headless mode: {'enabled' if args.headless else 'disabled'}")

        # Initialize extractor
        extractor = DevlogExtractor(
            output_dir=output_dir,
            max_chats=args.max_chats,
            rate_limit=args.rate_limit,
            headless=args.headless,
        )

        # Run extraction
        extractor.run()

        logger.info("Devlog extraction completed successfully")

    except KeyboardInterrupt:
        logger.info("Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
