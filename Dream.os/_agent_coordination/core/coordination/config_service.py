from typing import Dict, Any, Optional, Union, List
import os
import json
import yaml
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum
import dotenv

logger = logging.getLogger(__name__)

class ConfigFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    ENV = "env"

@dataclass
class ConfigSource:
    path: Path
    format: ConfigFormat
    required: bool = True
    namespace: Optional[str] = None

class ConfigService:
    """Unified configuration management service."""
    
    def __init__(self, root_path: Union[str, Path]):
        self.root = Path(root_path).resolve()
        self._config: Dict[str, Any] = {}
        self._sources: List[ConfigSource] = []
        self._env_loaded = False
        
    def add_source(self, path: Union[str, Path], 
                  format: ConfigFormat,
                  required: bool = True,
                  namespace: Optional[str] = None) -> None:
        """Add a configuration source."""
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = self.root / config_path
            
        source = ConfigSource(
            path=config_path,
            format=format,
            required=required,
            namespace=namespace
        )
        self._sources.append(source)
        
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON config {path}: {e}")
            raise
            
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading YAML config {path}: {e}")
            raise
            
    def _load_env(self, path: Path) -> Dict[str, Any]:
        """Load environment variables from .env file."""
        try:
            env_vars = dotenv.dotenv_values(path)
            # Also load into actual environment
            dotenv.load_dotenv(path)
            return dict(env_vars)
        except Exception as e:
            logger.error(f"Error loading .env file {path}: {e}")
            raise
            
    def _merge_config(self, base: Dict[str, Any], 
                     update: Dict[str, Any],
                     namespace: Optional[str] = None) -> None:
        """Merge configuration dictionaries."""
        if namespace:
            if namespace not in base:
                base[namespace] = {}
            base[namespace].update(update)
        else:
            base.update(update)
            
    def load(self) -> None:
        """Load all configuration sources."""
        config: Dict[str, Any] = {}
        
        for source in self._sources:
            try:
                if not source.path.exists():
                    if source.required:
                        raise FileNotFoundError(f"Required config file not found: {source.path}")
                    logger.warning(f"Optional config file not found: {source.path}")
                    continue
                    
                if source.format == ConfigFormat.JSON:
                    data = self._load_json(source.path)
                elif source.format == ConfigFormat.YAML:
                    data = self._load_yaml(source.path)
                elif source.format == ConfigFormat.ENV:
                    data = self._load_env(source.path)
                    self._env_loaded = True
                else:
                    raise ValueError(f"Unsupported config format: {source.format}")
                    
                self._merge_config(config, data, source.namespace)
                logger.info(f"Loaded config from {source.path}")
                
            except Exception as e:
                if source.required:
                    raise
                logger.warning(f"Error loading optional config {source.path}: {e}")
                
        self._config = config
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        try:
            value = self._config
            for part in key.split('.'):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        parts = key.split('.')
        config = self._config
        
        # Navigate to the correct nested level
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
            
        # Set the value
        config[parts[-1]] = value
        
    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        """Get all configuration values in a namespace."""
        return self._config.get(namespace, {})
        
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration."""
        return self._config.copy()
        
    def save(self, path: Union[str, Path], 
            format: ConfigFormat = ConfigFormat.JSON) -> None:
        """Save current configuration to file."""
        save_path = Path(path)
        if not save_path.is_absolute():
            save_path = self.root / save_path
            
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == ConfigFormat.JSON:
                with open(save_path, 'w') as f:
                    json.dump(self._config, f, indent=2)
            elif format == ConfigFormat.YAML:
                with open(save_path, 'w') as f:
                    yaml.dump(self._config, f)
            elif format == ConfigFormat.ENV:
                with open(save_path, 'w') as f:
                    for key, value in self._config.items():
                        if isinstance(value, (str, int, float, bool)):
                            f.write(f"{key}={value}\n")
            else:
                raise ValueError(f"Unsupported save format: {format}")
                
            logger.info(f"Saved config to {save_path}")
            
        except Exception as e:
            logger.error(f"Error saving config to {save_path}: {e}")
            raise 