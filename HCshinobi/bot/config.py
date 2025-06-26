from dataclasses import dataclass
from typing import Optional

@dataclass
class BotConfig:
    """Configuration options for HCBot."""

    token: str = ""
    command_prefix: str = "!"
    application_id: int = 0
    guild_id: int = 0
    battle_channel_id: int = 0
    online_channel_id: int = 0
    announcement_channel_id: int = 0
    equipment_shop_channel_id: int = 0
    log_level: str = "INFO"
    data_dir: str = "data"
    database_url: str = "sqlite:///hcshinobi.db"
    webhook_url: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_target_url: Optional[str] = None
    openai_headless: bool = False
