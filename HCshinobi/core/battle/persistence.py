"""Placeholder persistence manager."""
from typing import Dict

from .state import BattleState


class BattlePersistence:
    def __init__(self) -> None:
        self.active: Dict[str, BattleState] = {}
        self.history: Dict[str, BattleState] = {}

    async def add_battle_to_history(self, battle_id: str, state: BattleState) -> None:
        self.history[battle_id] = state

    async def remove_active_battle(self, battle_id: str) -> None:
        self.active.pop(battle_id, None)

    async def save_active_battles(self) -> None:
        pass

    async def save_battle_history(self) -> None:
        pass
