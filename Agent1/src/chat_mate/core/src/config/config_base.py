import os
import json
import logging
from datetime import datetime, UTC
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ConfigBase:
    """Base configuration class with shared functionality."""
    
    def __init__(self, path_manager: Optional[Any] = None):
        """
        Initialize the config base.
        
        Args:
            path_manager: Optional path manager instance. If not provided,
                        will use environment-based path resolution.
        """
        self.env = os.environ
        self.path_manager = path_manager
        self._load_env()
        
    def _load_env(self) -> None:
        """Load environment variables using calculated project root."""
        try:
            if self.path_manager:
                dotenv_path = self.path_manager.get_project_root() / ".env"
            else:
                # Fallback to direct path calculation
                project_root = Path(__file__).resolve().parent.parent.parent 
                dotenv_path = project_root / ".env"
            
            if dotenv_path.exists():
                load_dotenv(dotenv_path, override=False)
                logger.info(f"Loaded .env file from: {dotenv_path}")
            else:
                logger.warning(f".env file not found at: {dotenv_path}")
                
        except Exception as e:
            logger.error(f"Error loading .env file: {e}", exc_info=True)

    def get_env(self, key: str, default: Any = None) -> Any:
        """Get environment variable value."""
        return self.env.get(key, default)
        
    def get_path(self, key: str, default: Optional[Path] = None) -> Optional[Path]:
        """Get a path using the path manager if available."""
        if self.path_manager:
            return self.path_manager.get_path(key)
        return Path(self.get_env(key, str(default))) if default else None
        
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback to environment variables."""
        return self.get_env(key, default)
        
    def set_path_manager(self, path_manager: Any) -> None:
        """Set the path manager after initialization if needed."""
        self.path_manager = path_manager

    def _validate_required_keys(self, required_keys):
        """Validate required environment variables exist."""
        missing = [key for key in required_keys if not self.get_env(key)]
        if missing:
            logger.warning(f"Missing required env vars: {missing}")
            return False
        return True
