"""Environment fixer script for HCShinobi project.

This script validates and fixes the project environment by:
1. Checking for required dependencies
2. Validating .env file and configuration
3. Setting up required directories
4. Checking data files and seeding if needed
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REQUIRED_DIRS = [
    "data",
    "data/characters",
    "data/clans",
    "data/missions",
    "data/npcs",
    "logs",
    "reports"
]

REQUIRED_ENV_VARS = [
    "DISCORD_TOKEN",
    "OPENAI_API_KEY",  # If using AI features
    "DEBUG_MODE",
    "GUILD_ID",  # For development/testing
]

EXAMPLE_ENV = """# Discord Bot Configuration
DISCORD_TOKEN=your_token_here
GUILD_ID=your_guild_id_here

# OpenAI Configuration (if using AI features)
OPENAI_API_KEY=your_openai_key_here

# Debug Configuration
DEBUG_MODE=True

# Data Directories
DATA_DIR=./data
CHARACTER_DATA_DIR=./data/characters
CLAN_DATA_DIR=./data/clans
MISSION_DATA_DIR=./data/missions
NPC_DATA_DIR=./data/npcs
"""

EXAMPLE_CLANS = [
    {
        "name": "Uchiha",
        "rarity": "Legendary",
        "lore": "A clan known for their powerful Sharingan and exceptional combat abilities.",
        "special_ability": "Sharingan",
        "stat_bonuses": {"ninjutsu": 5, "genjutsu": 5}
    },
    {
        "name": "Hyuga",
        "rarity": "Rare",
        "lore": "Masters of the Gentle Fist and wielders of the Byakugan.",
        "special_ability": "Byakugan",
        "stat_bonuses": {"taijutsu": 5, "chakra_control": 5}
    }
]


def check_python_version() -> bool:
    """Check if Python version meets requirements."""
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < required_version:
        logger.error(
            f"Python {required_version[0]}.{required_version[1]} or higher required. "
            f"Current version: {current_version[0]}.{current_version[1]}"
        )
        return False
    
    logger.info(f"Python version check passed: {sys.version}")
    return True


def install_dependencies() -> bool:
    """Install or update project dependencies."""
    try:
        logger.info("Installing dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        logger.info("Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False


def check_create_directories() -> bool:
    """Check and create required directories."""
    try:
        for directory in REQUIRED_DIRS:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Directory verified: {directory}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        return False


def check_env_file() -> bool:
    """Check and create .env file if needed."""
    env_path = Path(".env")
    
    # Check if .env exists
    if not env_path.exists():
        logger.warning(".env file not found, creating example .env")
        with open(env_path, "w") as f:
            f.write(EXAMPLE_ENV)
        logger.info("Created example .env file - please update with your actual values")
        return False
    
    # Read existing .env
    with open(env_path) as f:
        env_contents = f.read()
    
    # Check for required variables
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if var not in env_contents:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info(".env file check passed")
    return True


def seed_example_data() -> bool:
    """Seed example data files if they don't exist."""
    try:
        # Seed clans
        clans_file = Path("data/clans/clans.json")
        if not clans_file.exists():
            logger.info("Seeding example clan data...")
            clans_file.parent.mkdir(exist_ok=True)
            with open(clans_file, "w") as f:
                json.dump(EXAMPLE_CLANS, f, indent=2)
        
        # Add more data seeding as needed
        # TODO: Add example characters, missions, NPCs
        
        logger.info("Data seeding complete")
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed data: {e}")
        return False


def check_discord_bot() -> bool:
    """Check if Discord bot can be imported and initialized."""
    try:
        # Try importing the bot module
        from HCshinobi.bot import bot
        logger.info("Discord bot module check passed")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import bot module: {e}")
        return False


def main():
    """Run environment fixes and checks."""
    logger.info("Starting environment check...")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", install_dependencies),
        ("Directories", check_create_directories),
        ("Environment File", check_env_file),
        ("Example Data", seed_example_data),
        ("Discord Bot", check_discord_bot)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        logger.info(f"\nRunning check: {check_name}")
        if not check_func():
            failed_checks.append(check_name)
    
    if failed_checks:
        logger.error("\n❌ Environment check failed!")
        logger.error(f"Failed checks: {', '.join(failed_checks)}")
        logger.error("\nPlease fix the above issues and run the script again.")
        sys.exit(1)
    else:
        logger.info("\n✅ Environment check passed!")
        logger.info("Your development environment is ready.")
        sys.exit(0)


if __name__ == "__main__":
    main() 