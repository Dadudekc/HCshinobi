#!/usr/bin/env python3
# autoblogger/utils/logger.py

import logging
import sys
import os
from pathlib import Path
from datetime import datetime


def strip_emoji(text: str) -> str:
    """Strip emoji characters from text."""
    return text.encode("ascii", "ignore").decode()


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance with consistent formatting.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Create logs directory
    log_dir = Path.home() / ".autoblogger" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create formatters
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if os.name == "nt":  # Windows
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        # Strip emoji for Windows console
        original_emit = console_handler.emit

        def emit_without_emoji(record):
            record.msg = strip_emoji(str(record.msg))
            original_emit(record)

        console_handler.emit = emit_without_emoji
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    logger.addHandler(console_handler)

    # File handler
    log_file = log_dir / f"autoblogger_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger
