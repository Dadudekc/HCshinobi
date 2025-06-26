"""Assign clans randomly with optional weighting."""
from __future__ import annotations

import random
from typing import Dict, Optional


class ClanAssignmentEngine:
    def __init__(self, clan_system) -> None:
        self.clan_system = clan_system

    async def assign_clan(self, user_id: int | str) -> Dict[str, str]:
        clans = self.clan_system.list_clans()
        if not clans:
            return {"assigned_clan": ""}
        clan = random.choice(clans)
        return {"assigned_clan": clan["name"], "clan_rarity": clan.get("rarity", "Common")}

    def get_player_clan(self, user_id: int | str) -> Optional[str]:
        # This simple implementation doesn't track assignments.
        return None
