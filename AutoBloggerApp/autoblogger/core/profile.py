#!/usr/bin/env python3
# autoblogger/utils/profile_checker.py

import os
import json
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from autoblogger.core.logging import get_logger

logger = get_logger(__name__)


def get_profile_config_path() -> Path:
    """Get the path to the profile configuration file."""
    return Path.home() / ".autoblogger" / "profile_config.json"


def reset_profile(profile_path: str) -> bool:
    """
    Reset the Chrome profile by removing it and its config.

    Args:
        profile_path: Path to the Chrome user data directory

    Returns:
        bool: True if successful
    """
    try:
        path = Path(profile_path)
        if path.exists():
            logger.info(f"🧹 Resetting Chrome profile: {profile_path}")
            shutil.rmtree(path)

            # Also remove config
            config_path = get_profile_config_path()
            if config_path.exists():
                config_path.unlink()
                logger.info("🧹 Removed profile configuration")

            return True
        else:
            logger.warning(f"⚠️ No profile found to reset at: {profile_path}")
            return False

    except Exception as e:
        logger.error(f"❌ Error resetting profile: {e}")
        return False


def check_selenium_profile_ready(profile_path: str) -> bool:
    """
    Check if the Selenium profile is ready for automation.

    Args:
        profile_path: Path to the Chrome user data directory

    Returns:
        bool: True if profile is ready, False otherwise
    """
    try:
        path = Path(profile_path)
        if not path.exists():
            logger.warning(f"❌ Profile directory not found: {profile_path}")
            return False

        # Check for essential files
        required_files = [
            "Default/Cookies",
            "Default/Login Data",
            "Default/Preferences",
        ]

        for file in required_files:
            file_path = path / file
            if not file_path.exists():
                logger.warning(f"❌ Missing required file: {file}")
                return False
            else:
                logger.debug(f"✅ Found required file: {file}")

        # Check config file for explicit ready flag
        config = load_profile_config()
        if config and config.get("selenium_profile_ready"):
            logger.info("✅ Profile marked as ready in config")
            return True

        logger.info("✅ Profile files present but not marked as ready")
        return True  # If all files exist, consider it ready

    except Exception as e:
        logger.error(f"❌ Error checking profile: {e}")
        return False


def save_profile_config(config: Dict[str, Any]) -> bool:
    """
    Save profile configuration to disk.

    Args:
        config: Configuration dictionary to save

    Returns:
        bool: True if successful
    """
    try:
        config_path = get_profile_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"✅ Saved profile configuration to: {config_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Error saving profile config: {e}")
        return False


def load_profile_config() -> Optional[Dict[str, Any]]:
    """
    Load profile configuration from disk.

    Returns:
        Optional[Dict[str, Any]]: Configuration dictionary or None if not found
    """
    try:
        config_path = get_profile_config_path()
        if not config_path.exists():
            logger.debug("No profile configuration found")
            return None

        with open(config_path, "r") as f:
            config = json.load(f)
            logger.debug(f"Loaded profile configuration: {config}")
            return config

    except Exception as e:
        logger.error(f"❌ Error loading profile config: {e}")
        return None


def mark_profile_ready(profile_path: str) -> bool:
    """
    Mark the Selenium profile as ready for automation.

    Args:
        profile_path: Path to the Chrome user data directory

    Returns:
        bool: True if successful
    """
    try:
        config = load_profile_config() or {}
        config.update(
            {
                "selenium_profile_ready": True,
                "profile_path": profile_path,
                "last_verified": str(Path(profile_path).stat().st_mtime),
            }
        )

        success = save_profile_config(config)
        if success:
            logger.info("✅ Profile marked as ready for automation")
        return success

    except Exception as e:
        logger.error(f"❌ Error marking profile ready: {e}")
        return False
