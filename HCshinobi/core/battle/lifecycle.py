import asyncio
from datetime import datetime, timezone
from .state import BattleState

class BattleLifecycle:
    def __init__(self, character_system, persistence, progression_engine, battle_timeout: int = 5):
        self.character_system = character_system
        self.persistence = persistence
        self.progression_engine = progression_engine
        self.battle_timeout = battle_timeout
        self.battle_tasks = {}
        self.bot = None

    async def handle_battle_end(self, battle_state: BattleState, battle_id: str):
        await self.persistence.add_battle_to_history(battle_id, battle_state)
        await self.persistence.remove_active_battle(battle_id)
        if battle_state.winner_id:
            exp = self._calculate_exp_gain(battle_state)
            await self.progression_engine.award_battle_experience(battle_state.winner_id, exp)

    def _calculate_exp_gain(self, battle_state: BattleState) -> int:
        return 100

    async def cleanup_inactive_battles(self):
        to_remove = []
        for bid, state in list(self.persistence.active_battles.items()):
            if (datetime.now(timezone.utc) - state.last_action).total_seconds() > self.battle_timeout:
                state.is_active = False
                state.end_reason = "timeout"
                to_remove.append((bid, state))
        for bid, state in to_remove:
            await self.handle_battle_end(state, bid)

    async def notify_players_battle_timeout(self, attacker_id: str, defender_id: str):
        if not self.bot:
            return
        for pid in [attacker_id, defender_id]:
            user = await self.bot.fetch_user(pid)
            await user.send("Your battle timed out.")

    async def _battle_timeout_check(self):
        while True:
            await self.cleanup_inactive_battles()
            await asyncio.sleep(self.battle_timeout)

    async def shutdown(self):
        for task in self.battle_tasks.values():
            task.cancel()
        await self.persistence.save_active_battles()
        await self.persistence.save_battle_history()
