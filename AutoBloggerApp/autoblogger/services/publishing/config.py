import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv


class PublisherConfig:
    """Manages publisher credentials and configuration."""

    def __init__(self, config_dir: str = None):
        """
        Initialize the publisher configuration manager.

        Args:
            config_dir: Directory to store configuration files. Defaults to ~/.autoblogger
        """
        # Load environment variables
        load_dotenv()

        # Setup config directory
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".autoblogger"

        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Setup encryption
        self.key_file = self.config_dir / ".key"
        self._setup_encryption()

        # Load configuration
        self.config_file = self.config_dir / "publishers.json"
        self.config = self._load_config()

    def _setup_encryption(self):
        """Setup encryption key for secure credential storage."""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
        else:
            with open(self.key_file, "rb") as f:
                key = f.read()

        self.cipher = Fernet(key)

    def _load_config(self) -> Dict[str, Any]:
        """Load publisher configuration from file."""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, "r") as f:
                encrypted_data = f.read()
                if encrypted_data:
                    decrypted_data = self.cipher.decrypt(encrypted_data.encode())
                    return json.loads(decrypted_data)
                return {}
        except Exception as e:
            logging.error(f"Error loading publisher config: {e}")
            return {}

    def _save_config(self):
        """Save publisher configuration to file."""
        try:
            encrypted_data = self.cipher.encrypt(json.dumps(self.config).encode())
            with open(self.config_file, "w") as f:
                f.write(encrypted_data.decode())
        except Exception as e:
            logging.error(f"Error saving publisher config: {e}")

    def get_credentials(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get credentials for a specific platform.

        Args:
            platform: Platform identifier (e.g., 'wordpress', 'medium')

        Returns:
            Optional[Dict[str, Any]]: Platform credentials or None if not found
        """
        return self.config.get(platform)

    def set_credentials(self, platform: str, credentials: Dict[str, Any]):
        """
        Set credentials for a platform.

        Args:
            platform: Platform identifier
            credentials: Platform-specific credentials
        """
        self.config[platform] = credentials
        self._save_config()

    def remove_credentials(self, platform: str) -> bool:
        """
        Remove credentials for a platform.

        Args:
            platform: Platform identifier

        Returns:
            bool: True if credentials were removed
        """
        if platform in self.config:
            del self.config[platform]
            self._save_config()
            return True
        return False

    def list_platforms(self) -> List[str]:
        """Get list of configured platforms."""
        return list(self.config.keys())

    def clear_all(self):
        """Remove all stored credentials."""
        self.config.clear()
        self._save_config()
