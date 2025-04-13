import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

class ConfigBase:
    """
    Base configuration class that handles environment variables and configuration files.
    """

    def __init__(self):
        self.env_vars = {}
        self.config_data = {}
        self.path_manager = PathManager()
        self._load_env()
        self._load_config()

    def _load_env(self):
        """Load environment variables."""
        self.env_vars = dict(os.environ)

    def _load_config(self):
        """Load configuration from JSON file."""
        config_path = self.path_manager.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
                self.config_data = {}
        else:
            logger.warning(f"No config file found at {config_path}")
            self.config_data = {}

    def get_env(self, key: str, default: Any = None) -> Any:
        """Get environment variable value."""
        return self.env_vars.get(key, default)

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config_data.get(key, default)

    def _validate_required_keys(self, required_keys: List[str]):
        """Validate that required environment variables are present."""
        missing_keys = [key for key in required_keys if key not in self.env_vars]
        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")


class PathManager:
    """
    Manages paths for configuration files and other resources.
    """

    def __init__(self):
        self.base_dir = self._get_base_dir()

    def _get_base_dir(self) -> Path:
        """Get the base directory for the application."""
        return Path(os.getcwd())

    def get_config_path(self) -> str:
        """Get the path to the configuration file."""
        return str(self.base_dir / "config.json")

    def get_rate_limit_state_path(self) -> str:
        """Get the path to the rate limit state file."""
        return str(self.base_dir / "rate_limit_state.json")

    def get_chrome_profile_path(self) -> str:
        """Get the path to Chrome profiles."""
        return str(self.base_dir / "chrome_profiles") 