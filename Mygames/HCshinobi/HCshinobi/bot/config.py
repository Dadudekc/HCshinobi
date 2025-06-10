"""
Configuration module for HCShinobi bot.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any
import json
from ..utils.file_io import ensure_directory, load_json, save_json
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Load .env file from the project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

def find_env_file() -> Optional[str]:
    """Find the .env file by checking multiple possible locations."""
    current_dir = os.getcwd()
    logger.info(f"Current directory: {current_dir}")
    
    # List of potential .env file locations
    potential_paths = [
        os.path.join(current_dir, '.env'),  # Current directory
        os.path.join(current_dir, '..', '.env'),  # One level up
        os.path.join(current_dir, '..', '..', '.env'),  # Two levels up
    ]
    
    for path in potential_paths:
        abs_path = os.path.abspath(path)
        logger.info(f"Checking for .env file at: {abs_path}")
        if os.path.isfile(abs_path):
            logger.info(f"Found .env file at: {abs_path}")
            return abs_path
            
    return None

def load_env_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """Load a value from environment variables.
    
    Args:
        key: The environment variable key
        default: Default value if not found
        
    Returns:
        The value from environment or default
    """
    return os.getenv(key, default)

def convert_to_int(value: Optional[str], key: str) -> Optional[int]:
    """Convert string value to integer.
    
    Args:
        value: String value to convert
        key: Key name for error message
        
    Returns:
        Integer value or None
        
    Raises:
        ValueError: If value cannot be converted to int
    """
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Invalid {key}")

@dataclass
class BotConfig:
    """Configuration class for the bot."""
    # Required fields
    token: str
    guild_id: int
    battle_channel_id: int
    online_channel_id: int
    data_dir: str
    application_id: int
    
    # Optional fields with defaults
    announcement_channel_id: Optional[int] = None
    jutsu_shop_channel_id: Optional[int] = None
    equipment_shop_channel_id: Optional[int] = None
    command_prefix: str = "!"
    webhook_url: Optional[str] = None
    log_level: str = "INFO"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    openai_api_key: Optional[str] = None
    openai_target_url: Optional[str] = None
    openai_headless: bool = False
    version: str = "1.0.0"

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()

    def _validate_config(self):
        """Validate configuration values."""
        # Validate numeric fields are positive
        if self.guild_id <= 0:
            raise ValueError("guild_id must be positive")
        if self.battle_channel_id <= 0:
            raise ValueError("battle_channel_id must be positive")
        if self.online_channel_id <= 0:
            raise ValueError("online_channel_id must be positive")
        if self.announcement_channel_id is not None and self.announcement_channel_id <= 0:
            raise ValueError("announcement_channel_id must be positive")
        if self.application_id <= 0:
            raise ValueError("application_id must be positive")
        if self.jutsu_shop_channel_id is not None and self.jutsu_shop_channel_id <= 0:
            raise ValueError("jutsu_shop_channel_id must be positive")
        if self.equipment_shop_channel_id is not None and self.equipment_shop_channel_id <= 0:
            raise ValueError("equipment_shop_channel_id must be positive")

        # Validate URLs, only if they are provided
        if self.webhook_url and not self._is_valid_url(self.webhook_url):
            raise ValueError(f"Invalid webhook URL: {self.webhook_url}")
        if self.ollama_base_url and not self._is_valid_url(self.ollama_base_url):
            raise ValueError(f"Invalid Ollama base URL: {self.ollama_base_url}")
        # Allow openai_target_url to be None
        if self.openai_target_url and not self._is_valid_url(self.openai_target_url):
            raise ValueError(f"Invalid OpenAI target URL: {self.openai_target_url}")

        # Validate log level
        try:
            logging.getLevelName(self.log_level.upper())
        except ValueError:
            raise ValueError(f"Invalid log level: {self.log_level}")

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if a URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Create configuration from environment variables."""
        required_fields = {
            "token": os.getenv("DISCORD_BOT_TOKEN"),
            "guild_id": os.getenv("DISCORD_GUILD_ID"),
            # Use DISCORD_ prefix for channel IDs
            "battle_channel_id": os.getenv("DISCORD_BATTLE_CHANNEL_ID"),
            "online_channel_id": os.getenv("DISCORD_ONLINE_CHANNEL_ID"),
            "data_dir": os.getenv("DATA_DIR"),
            "application_id": os.getenv("APPLICATION_ID")
        }

        # Check for missing required fields
        missing = [k for k, v in required_fields.items() if not v]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        # Convert numeric fields
        try:
            guild_id = int(required_fields["guild_id"])
            battle_channel_id = int(required_fields["battle_channel_id"])
            online_channel_id = int(required_fields["online_channel_id"])
            application_id = int(required_fields["application_id"])
            # Use DISCORD_ prefix
            raw_announcement_id = os.getenv("DISCORD_ANNOUNCEMENT_CHANNEL_ID")
            announcement_channel_id = int(raw_announcement_id) if raw_announcement_id else None
            raw_jutsu_shop_id = os.getenv("DISCORD_JUTSU_SHOP_CHANNEL_ID")
            jutsu_shop_channel_id = int(raw_jutsu_shop_id) if raw_jutsu_shop_id else None
            raw_equipment_shop_id = os.getenv("DISCORD_EQUIPMENT_SHOP_CHANNEL_ID")
            equipment_shop_channel_id = int(raw_equipment_shop_id) if raw_equipment_shop_id else None
        except ValueError as e:
            raise ValueError(f"Invalid numeric value in configuration: {str(e)}")

        # Get optional fields with defaults
        optional_fields = {
            "announcement_channel_id": announcement_channel_id,
            "jutsu_shop_channel_id": jutsu_shop_channel_id,
            "equipment_shop_channel_id": equipment_shop_channel_id,
            "command_prefix": os.getenv("DISCORD_COMMAND_PREFIX", "!"),
            "webhook_url": os.getenv("DISCORD_WEBHOOK_URL"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "llama2"),
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "openai_target_url": os.getenv("OPENAI_TARGET_URL"), # Allow None, validation handles it
            "openai_headless": os.getenv("OPENAI_HEADLESS", "false").lower() == "true",
            "version": os.getenv("BOT_VERSION", "1.0.0")  # Added version from env with default
        }

        # Create and return config instance
        return cls(
            token=required_fields["token"],
            guild_id=guild_id,
            battle_channel_id=battle_channel_id,
            online_channel_id=online_channel_id,
            data_dir=required_fields["data_dir"],
            application_id=application_id,
            **optional_fields
        )

def load_config() -> BotConfig:
    """Load bot configuration.
    
    Returns:
        BotConfig instance
        
    Raises:
        ValueError: If required settings are missing
    """
    return BotConfig.from_env() 