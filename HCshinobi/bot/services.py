"""Provide core game services for the bot."""
from __future__ import annotations

from typing import Optional

from .config import BotConfig
from ..core.character_system import CharacterSystem
from ..core.clan_system import ClanSystem
from ..core.battle_system import BattleSystem
from ..core.mission_system import MissionSystem


class ServiceContainer:
    """Lazily initialized service container."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.character_system: Optional[CharacterSystem] = None
        self.clan_system: Optional[ClanSystem] = None
        self.mission_system: Optional[MissionSystem] = None
        self.battle_system: Optional[BattleSystem] = None
        # Additional placeholder attributes
        self.currency_system = None
        self.token_system = None
        self.training_system = None
        self.jutsu_shop_system = None
        self.equipment_shop_system = None
        self.clan_data = None
        self.clan_missions = None
        self.ollama_client = None

    async def initialize(self, bot) -> None:
        """Create service instances."""
        self.character_system = CharacterSystem()
        self.clan_system = ClanSystem()
        self.mission_system = MissionSystem()
        self.battle_system = BattleSystem()

    async def shutdown(self) -> None:
        """Shutdown services if necessary."""
        pass
