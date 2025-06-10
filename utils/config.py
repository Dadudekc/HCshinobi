"""Configuration management utilities."""
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CONFIG_PATH = Path("config/config.json")
DEFAULT_CLANS_PATH = Path("data/clans/clans.json")
DEFAULT_CHARACTERS_PATH = Path("data/characters")
DEFAULT_MODIFIERS_PATH = Path("data/modifiers.json")

def load_env(env_path: Optional[str] = None) -> None:
    """Load environment variables from .env file.
    
    Args:
        env_path: Optional path to .env file. If not provided, searches in default locations.
    """
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Try common locations
        paths = [
            ".env",
            "../.env",
            "../../.env",
            os.path.expanduser("~/.env")
        ]
        
        for path in paths:
            if os.path.exists(path):
                load_dotenv(path)
                logger.info(f"Loaded environment variables from {path}")
                return
                
        logger.warning("No .env file found in common locations")

def load_config(config_path: Union[str, Path] = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load configuration from JSON file.
    
    Args:
        config_path: Path to config JSON file
        
    Returns:
        Dict containing configuration values
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    config_path = Path(config_path)
    
    try:
        with open(config_path) as f:
            config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in config file {config_path}")
        raise

def save_config(config: Dict[str, Any], config_path: Union[str, Path] = DEFAULT_CONFIG_PATH) -> None:
    """Save configuration to JSON file.
    
    Args:
        config: Configuration dictionary to save
        config_path: Path to save config JSON file
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
        logger.info(f"Saved configuration to {config_path}")

def get_required_env(key: str) -> str:
    """Get a required environment variable.
    
    Args:
        key: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(key)
    if value is None:
        logger.error(f"Required environment variable {key} not set")
        raise ValueError(f"Required environment variable {key} not set")
    return value

def get_optional_env(key: str, default: Any = None) -> Any:
    """Get an optional environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)

def load_clans(clans_path: Union[str, Path] = DEFAULT_CLANS_PATH) -> Dict[str, Any]:
    """Load clan data from JSON file.
    
    Args:
        clans_path: Path to clans JSON file
        
    Returns:
        Dict containing clan data
    """
    clans_path = Path(clans_path)
    
    try:
        with open(clans_path) as f:
            clans = json.load(f)
            logger.info(f"Loaded {len(clans)} clans from {clans_path}")
            return clans
    except FileNotFoundError:
        logger.error(f"Clans file not found at {clans_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in clans file {clans_path}")
        raise

def load_modifiers(modifiers_path: Union[str, Path] = DEFAULT_MODIFIERS_PATH) -> Dict[str, Any]:
    """Load personality modifiers from JSON file.
    
    Args:
        modifiers_path: Path to modifiers JSON file
        
    Returns:
        Dict containing modifier data
    """
    modifiers_path = Path(modifiers_path)
    
    try:
        with open(modifiers_path) as f:
            modifiers = json.load(f)
            logger.info(f"Loaded personality modifiers from {modifiers_path}")
            return modifiers
    except FileNotFoundError:
        logger.warning(f"Modifiers file not found at {modifiers_path}, creating default")
        default_modifiers = {
            "personality_traits": {},
            "response_templates": {},
            "behavior_rules": {}
        }
        save_modifiers(default_modifiers, modifiers_path)
        return default_modifiers
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in modifiers file {modifiers_path}")
        raise

def save_modifiers(
    modifiers: Dict[str, Any],
    modifiers_path: Union[str, Path] = DEFAULT_MODIFIERS_PATH
) -> None:
    """Save personality modifiers to JSON file.
    
    Args:
        modifiers: Modifiers dictionary to save
        modifiers_path: Path to save modifiers JSON file
    """
    modifiers_path = Path(modifiers_path)
    modifiers_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(modifiers_path, 'w') as f:
        json.dump(modifiers, f, indent=2)
        logger.info(f"Saved personality modifiers to {modifiers_path}")

def get_character_path(character_id: str) -> Path:
    """Get the path for a character's JSON file.
    
    Args:
        character_id: Character's unique ID
        
    Returns:
        Path to character JSON file
    """
    return Path(DEFAULT_CHARACTERS_PATH) / f"{character_id}.json"

def load_character(character_id: str) -> Dict[str, Any]:
    """Load character data from JSON file.
    
    Args:
        character_id: Character's unique ID
        
    Returns:
        Dict containing character data
        
    Raises:
        FileNotFoundError: If character file doesn't exist
    """
    char_path = get_character_path(character_id)
    
    try:
        with open(char_path) as f:
            character = json.load(f)
            logger.info(f"Loaded character data for {character_id}")
            return character
    except FileNotFoundError:
        logger.error(f"Character file not found for ID {character_id}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in character file for ID {character_id}")
        raise

def save_character(character_id: str, character_data: Dict[str, Any]) -> None:
    """Save character data to JSON file.
    
    Args:
        character_id: Character's unique ID
        character_data: Character data to save
    """
    char_path = get_character_path(character_id)
    char_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(char_path, 'w') as f:
        json.dump(character_data, f, indent=2)
        logger.info(f"Saved character data for {character_id}")

def get_data_dir() -> Path:
    """Get the data directory path.
    
    Returns:
        Path to data directory
    """
    return Path("data") 