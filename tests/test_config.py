"""Tests for the configuration module."""

import pytest
import os
from HCshinobi.bot.config import BotConfig

@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "123456789")
    monkeypatch.setenv("DISCORD_BATTLE_CHANNEL_ID", "987654321")
    monkeypatch.setenv("DISCORD_ONLINE_CHANNEL_ID", "987654322")
    monkeypatch.setenv("DATA_DIR", "test_data")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("OPENAI_TARGET_URL", "http://localhost:8000")
    monkeypatch.setenv("OPENAI_HEADLESS", "true")
    monkeypatch.setenv("DISCORD_COMMAND_PREFIX", "!")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123456789/test_token")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

def test_config_initialization():
    """Test direct initialization of BotConfig."""
    config = BotConfig(
        token="test_token",
        guild_id=123456789,
        battle_channel_id=987654321,
        online_channel_id=123789456,
        announcement_channel_id=777888999,
        data_dir="test_data",
        command_prefix="!",
        webhook_url="https://discord.com/api/webhooks/test",
        log_level="INFO",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama2",
        openai_api_key="test_key",
        openai_target_url="https://api.openai.com/v1",
        openai_headless=True
    )
    
    assert config.token == "test_token"
    assert config.guild_id == 123456789
    assert config.battle_channel_id == 987654321
    assert config.online_channel_id == 123789456
    assert config.announcement_channel_id == 777888999
    assert config.data_dir == "test_data"
    assert config.command_prefix == "!"
    assert config.webhook_url == "https://discord.com/api/webhooks/test"
    assert config.log_level == "INFO"
    assert config.ollama_base_url == "http://localhost:11434"
    assert config.ollama_model == "llama2"
    assert config.openai_api_key == "test_key"
    assert config.openai_target_url == "https://api.openai.com/v1"
    assert config.openai_headless is True

def test_config_from_env(monkeypatch):
    """Test creating config from environment variables."""
    # Set environment variables
    env_vars = {
        "DISCORD_BOT_TOKEN": "test_token",
        "DISCORD_GUILD_ID": "123456789",
        "DISCORD_BATTLE_CHANNEL_ID": "987654321",
        "DISCORD_ONLINE_CHANNEL_ID": "123789456",
        "DISCORD_ANNOUNCEMENT_CHANNEL_ID": "777888999",
        "DATA_DIR": "test_data",
        "DISCORD_COMMAND_PREFIX": "!",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        "LOG_LEVEL": "INFO",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama2",
        "OPENAI_API_KEY": "test_key",
        "OPENAI_TARGET_URL": "https://api.openai.com/v1",
        "OPENAI_HEADLESS": "true"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    # Create config from environment
    config = BotConfig.from_env()
    
    # Verify values
    assert config.token == "test_token"
    assert config.guild_id == 123456789
    assert config.battle_channel_id == 987654321
    assert config.online_channel_id == 123789456
    assert config.announcement_channel_id == 777888999
    assert config.data_dir == "test_data"
    assert config.command_prefix == "!"
    assert config.webhook_url == "https://discord.com/api/webhooks/test"
    assert config.log_level == "INFO"
    assert config.ollama_base_url == "http://localhost:11434"
    assert config.ollama_model == "llama2"
    assert config.openai_api_key == "test_key"
    assert config.openai_target_url == "https://api.openai.com/v1"
    assert config.openai_headless is True

def test_config_missing_required(monkeypatch):
    """Test that missing required fields raise ValueError."""
    # Set only optional variables
    env_vars = {
        "DISCORD_COMMAND_PREFIX": "!",
        "LOG_LEVEL": "INFO",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "llama2",
        "OPENAI_HEADLESS": "true"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    # Verify ValueError is raised
    with pytest.raises(ValueError) as exc_info:
        BotConfig.from_env()
    assert "Missing required configuration" in str(exc_info.value)

def test_config_invalid_values(monkeypatch):
    """Test that invalid values raise ValueError."""
    # Set invalid values
    env_vars = {
        "DISCORD_BOT_TOKEN": "test_token",
        "DISCORD_GUILD_ID": "invalid",  # Should be numeric
        "DISCORD_BATTLE_CHANNEL_ID": "987654321",
        "DISCORD_ONLINE_CHANNEL_ID": "123789456",
        "DATA_DIR": "test_data",
        "DISCORD_COMMAND_PREFIX": "!",
        "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
        "LOG_LEVEL": "INVALID",  # Invalid log level
        "OLLAMA_BASE_URL": "not_a_url",  # Invalid URL
        "OLLAMA_MODEL": "llama2",
        "OPENAI_API_KEY": "test_key",
        "OPENAI_TARGET_URL": "not_a_url",  # Invalid URL
        "OPENAI_HEADLESS": "not_bool"  # Invalid boolean
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    # Verify ValueError is raised
    with pytest.raises(ValueError) as exc_info:
        BotConfig.from_env()
    assert "Invalid numeric value in configuration" in str(exc_info.value) 