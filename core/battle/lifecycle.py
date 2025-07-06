"""Simple battle lifecycle management."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict

from .state import BattleState
from .persistence import BattlePersistence


class BattleLifecycle:
    def __init__(self, character_system, persistence: BattlePersistence, progression_engine, battle_timeout: int = 60) -> None:
        self.character_system = character_system
        self.persistence = persistence
        self.progression_engine = progression_engine
        self.battle_timeout = battle_timeout
        self.battle_tasks: Dict[str, asyncio.Task] = {}
        self.bot = None

    async def handle_battle_end(self, state: BattleState, battle_id: str) -> None:
        await self.persistence.add_battle_to_history(battle_id, state)
        await self.persistence.remove_active_battle(battle_id)
        if state.winner_id:
            exp = self._calculate_exp_gain(state)
            await self.progression_engine.award_battle_experience(state.winner_id, exp)

    def _calculate_exp_gain(self, state: BattleState) -> int:
        base_exp = 100
        level_diff = state.defender.character.level - state.attacker.character.level
        if level_diff > 0:
            base_exp += level_diff * 10
        if state.turn_number > 5:
            base_exp -= 10
        return max(base_exp, 0)

    async def cleanup_inactive_battles(self) -> None:
        now = datetime.now(timezone.utc)
        for bid, battle in list(self.persistence.active_battles.items()):
            if (now - battle.last_action).total_seconds() > self.battle_timeout:
                battle.is_active = False
                battle.end_reason = "timeout"
                await self.handle_battle_end(battle, bid)

    async def notify_players_battle_timeout(self, attacker_id: str, defender_id: str) -> None:
        if not self.bot:
            return
        for pid in (attacker_id, defender_id):
            user = await self.bot.fetch_user(int(pid))
            await user.send("Your battle has timed out.")

    async def _battle_timeout_check(self) -> None:
        while True:
            await asyncio.sleep(self.battle_timeout)
            await self.cleanup_inactive_battles()

    async def shutdown(self) -> None:
        for task in self.battle_tasks.values():
            task.cancel()
        await self.persistence.save_active_battles()
        await self.persistence.load_battle_history()
