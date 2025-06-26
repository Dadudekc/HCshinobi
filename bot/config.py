"""Simple configuration dataclass for tests."""
from dataclasses import dataclass


@dataclass
class BotConfig:
    command_prefix: str = "!"
    application_id: int = 0
    guild_id: int = 0
    battle_channel_id: int = 0
    online_channel_id: int = 0
    log_level: str = "INFO"
    token: str = ""
    data_dir: str = "data"
    database_url: str = "sqlite:///bot.db"
