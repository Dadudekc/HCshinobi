"""
Configuration management for Trinity Core
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TrinityConfig(BaseModel):
    """Configuration model for Trinity Core"""
    project_name: str = Field(default="chat_mate")
    version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    base_path: Optional[str] = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True

class ConfigManager:
    """Configuration manager for Trinity Core"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 'config.json'
        )
        self.config = self._load_config()
    
    def _load_config(self) -> TrinityConfig:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = {}
        
        # Set base_path if not provided
        if 'base_path' not in config_data:
            config_data['base_path'] = str(Path(__file__).parent.parent)
        
        return TrinityConfig(**config_data)
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        config_data = self.config.dict()
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def update_config(self, **kwargs) -> None:
        """Update configuration with new values"""
        config_data = self.config.dict()
        config_data.update(kwargs)
        self.config = TrinityConfig(**config_data)
        self.save_config()
    
    def get_config(self) -> TrinityConfig:
        """Get current configuration"""
        return self.config 