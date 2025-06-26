"""Simplified clan assignment engine."""

class ClanAssignmentEngine:
    async def assign_clan(self, user_id: int) -> dict:
        return {"assigned_clan": "Uchiha"}

    def get_player_clan(self, user_id: int) -> str:
        return "Uchiha"
