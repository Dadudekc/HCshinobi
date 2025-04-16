"""Tests for the configuration service module."""

import json
import yaml
import pytest
from pathlib import Path
from typing import Generator
from core.coordination.config_service import ConfigService, ConfigFormat, ConfigSource

@pytest.fixture
def config_dir(tmp_path) -> Generator[Path, None, None]:
    """Fixture that provides a temporary directory for config files."""
    config_path = tmp_path / "config"
    config_path.mkdir()
    yield config_path

@pytest.fixture
def config_service(config_dir: Path) -> ConfigService:
    """Fixture that provides a configured ConfigService instance."""
    return ConfigService(config_dir)

@pytest.fixture
def sample_configs(config_dir: Path) -> dict[str, Path]:
    """Fixture that creates sample config files in different formats."""
    # JSON config
    json_config = config_dir / "config.json"
    json_data = {
        "database": {
            "host": "localhost",
            "port": 5432
        },
        "api": {
            "url": "http://api.example.com",
            "timeout": 30
        }
    }
    json_config.write_text(json.dumps(json_data))
    
    # YAML config
    yaml_config = config_dir / "config.yaml"
    yaml_data = {
        "logging": {
            "level": "INFO",
            "file": "app.log"
        },
        "cache": {
            "enabled": True,
            "ttl": 3600
        }
    }
    yaml_config.write_text(yaml.dump(yaml_data))
    
    # ENV config
    env_config = config_dir / ".env"
    env_data = """
    APP_NAME=TestApp
    DEBUG=true
    PORT=8080
    """
    env_config.write_text(env_data.strip())
    
    return {
        "json": json_config,
        "yaml": yaml_config,
        "env": env_config
    }

def test_config_source_creation():
    """Test that ConfigSource objects are created correctly."""
    source = ConfigSource(
        path=Path("/tmp/config.json"),
        format=ConfigFormat.JSON,
        required=True,
        namespace="app"
    )
    
    assert source.path == Path("/tmp/config.json")
    assert source.format == ConfigFormat.JSON
    assert source.required is True
    assert source.namespace == "app"

def test_add_source(config_service: ConfigService, sample_configs: dict[str, Path]):
    """Test adding configuration sources."""
    # Add JSON source
    config_service.add_source(
        sample_configs["json"],
        ConfigFormat.JSON,
        namespace="main"
    )
    
    # Add YAML source
    config_service.add_source(
        sample_configs["yaml"],
        ConfigFormat.YAML,
        namespace="logging"
    )
    
    # Verify sources were added
    assert len(config_service._sources) == 2
    assert config_service._sources[0].format == ConfigFormat.JSON
    assert config_service._sources[1].format == ConfigFormat.YAML

def test_load_json_config(config_service: ConfigService, sample_configs: dict[str, Path]):
    """Test loading JSON configuration."""
    config_service.add_source(sample_configs["json"], ConfigFormat.JSON)
    config_service.load()
    
    assert config_service.get("database.host") == "localhost"
    assert config_service.get("api.timeout") == 30

def test_load_yaml_config(config_service: ConfigService, sample_configs: dict[str, Path]):
    """Test loading YAML configuration."""
    config_service.add_source(sample_configs["yaml"], ConfigFormat.YAML)
    config_service.load()
    
    assert config_service.get("logging.level") == "INFO"
    assert config_service.get("cache.enabled") is True

def test_load_env_config(config_service: ConfigService, sample_configs: dict[str, Path]):
    """Test loading environment variables."""
    config_service.add_source(sample_configs["env"], ConfigFormat.ENV)
    config_service.load()
    
    assert config_service.get("APP_NAME") == "TestApp"
    assert config_service.get("PORT") == "8080"

def test_config_namespaces(config_service: ConfigService, sample_configs: dict[str, Path]):
    """Test configuration namespacing."""
    config_service.add_source(
        sample_configs["json"],
        ConfigFormat.JSON,
        namespace="app"
    )
    config_service.add_source(
        sample_configs["yaml"],
        ConfigFormat.YAML,
        namespace="system"
    )
    config_service.load()
    
    # Test namespace access
    app_config = config_service.get_namespace("app")
    assert app_config["database"]["host"] == "localhost"
    
    system_config = config_service.get_namespace("system")
    assert system_config["logging"]["level"] == "INFO"

def test_config_save(config_service: ConfigService, config_dir: Path):
    """Test saving configuration to file."""
    # Set some config values
    config_service.set("database.host", "localhost")
    config_service.set("database.port", 5432)
    
    # Save as JSON
    json_path = config_dir / "saved_config.json"
    config_service.save(json_path, ConfigFormat.JSON)
    
    # Verify saved file
    assert json_path.exists()
    saved_data = json.loads(json_path.read_text())
    assert saved_data["database"]["host"] == "localhost"
    assert saved_data["database"]["port"] == 5432

def test_missing_required_config(config_service: ConfigService, config_dir: Path):
    """Test handling of missing required configuration."""
    config_service.add_source(
        config_dir / "nonexistent.json",
        ConfigFormat.JSON,
        required=True
    )
    
    with pytest.raises(FileNotFoundError):
        config_service.load()

def test_missing_optional_config(config_service: ConfigService, config_dir: Path):
    """Test handling of missing optional configuration."""
    config_service.add_source(
        config_dir / "nonexistent.json",
        ConfigFormat.JSON,
        required=False
    )
    
    # Should not raise an error
    config_service.load()

def test_get_with_default(config_service: ConfigService):
    """Test getting configuration with default values."""
    assert config_service.get("nonexistent.key", default="default") == "default"
    assert config_service.get("another.missing.key", default=42) == 42 