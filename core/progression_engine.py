"""Minimal progression engine used in tests."""
from __future__ import annotations


class ShinobiProgressionEngine:
    async def award_battle_experience(self, player_id: str, exp: int) -> None:
        # In a real implementation this would update the character.
        return None

    async def award_mission_experience(self, player_id: str, exp: int) -> None:
        """Award experience for completing missions."""
        return None
