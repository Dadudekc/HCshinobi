from __future__ import annotations
from typing import Optional
from discord.ext import commands

from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.mission_system import MissionSystem

from .config import BotConfig


class ServiceContainer:
    """Container for all core systems used by the bot."""

    def __init__(self, config: Optional[BotConfig] = None, data_dir: Optional[str] = None) -> None:
        self.config = config or BotConfig()
        self.data_dir = data_dir or self.config.data_dir

        self.character_system = CharacterSystem()
        self.battle_system = BattleSystem()
        self.clan_system = ClanSystem()
        self.mission_system = MissionSystem()

        self.currency_system = None
        self.token_system = None
        self.training_system = None
        self.jutsu_shop_system = None
        self.equipment_shop_system = None
        self.clan_data = None
        self.clan_missions = None
        self.ollama_client = None

        self._initialized = False
        self.bot: Optional[commands.Bot] = None

    async def initialize(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._initialized = True

    async def shutdown(self) -> None:
        self._initialized = False

    async def run_ready_hooks(self) -> None:
        return
