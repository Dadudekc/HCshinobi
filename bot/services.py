"""Container for core services used by the bot."""
from __future__ import annotations

import asyncio
from typing import Optional

from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.token_system import TokenSystem
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.training_system import TrainingSystem
from HCshinobi.core.battle.persistence import BattlePersistence
from HCshinobi.core.battle.lifecycle import BattleLifecycle
from HCshinobi.core.progression_engine import ShinobiProgressionEngine


class ServiceContainer:
    def __init__(self, config) -> None:
        data_dir = getattr(config, "data_dir", "data")
        self.character_system = CharacterSystem(data_dir)
        self.clan_system = ClanSystem(data_dir)
        self.clan_assignment_engine = ClanAssignmentEngine(self.clan_system)
        self.currency_system = CurrencySystem(data_dir)
        self.token_system = TokenSystem(data_dir)
        self.progression_engine = ShinobiProgressionEngine()
        self.mission_system = MissionSystem(
            data_dir,
            currency_system=self.currency_system,
            progression_engine=self.progression_engine,
        )
        self.training_system = TrainingSystem(data_dir)
        self.battle_persistence = BattlePersistence(data_dir)
        self.battle_lifecycle = BattleLifecycle(self.character_system, self.battle_persistence, self.progression_engine)

    async def initialize(self, bot=None) -> None:
        self.battle_lifecycle.bot = bot

    async def shutdown(self) -> None:
        await self.battle_lifecycle.shutdown()
        await self.battle_persistence.save_active_battles()
