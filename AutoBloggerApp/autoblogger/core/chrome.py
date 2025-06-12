#!/usr/bin/env python3
# autoblogger/utils/chrome_utils.py

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)


def kill_chrome_processes() -> bool:
    """Kill all Chrome and chromedriver processes."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/f", "/im", "chromedriver.exe"],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["taskkill", "/f", "/im", "chrome.exe"],
                capture_output=True,
                check=False,
            )
        else:
            subprocess.run(
                ["pkill", "-f", "chromedriver"], capture_output=True, check=False
            )
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True, check=False)
        return True
    except Exception as e:
        logger.error(f"Failed to kill Chrome processes: {e}")
        return False


def clean_chromedriver_cache() -> bool:
    """Clean the webdriver-manager cache directory."""
    try:
        cache_dir = Path.home() / ".wdm" / "drivers" / "chromedriver"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            logger.info("Cleaned chromedriver cache")
        return True
    except Exception as e:
        logger.error(f"Failed to clean chromedriver cache: {e}")
        return False


def ensure_chrome_clean() -> bool:
    """Kill Chrome processes and clean chromedriver cache."""
    killed = kill_chrome_processes()
    cleaned = clean_chromedriver_cache()
    return killed and cleaned
