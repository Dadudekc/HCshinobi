"""Simplified battle lifecycle manager."""
from __future__ import annotations

from typing import Optional

from .state import BattleState
from .persistence import BattlePersistence
from ..character_system import CharacterSystem
from ..progression_engine import ShinobiProgressionEngine


class BattleLifecycle:
    def __init__(
        self,
        character_system: CharacterSystem,
        persistence: BattlePersistence,
        progression_engine: ShinobiProgressionEngine,
        battle_timeout: int = 60,
    ) -> None:
        self.character_system = character_system
        self.persistence = persistence
        self.progression_engine = progression_engine
        self.battle_timeout = battle_timeout

    async def handle_battle_end(self, state: BattleState, battle_id: str) -> None:
        await self.persistence.add_battle_to_history(battle_id, state)
        await self.persistence.remove_active_battle(battle_id)
        if state.winner_id:
            char = state.attacker.character if state.winner_id == state.attacker.id else state.defender.character
            await self.progression_engine.award_battle_experience(char, state.turn_number)
