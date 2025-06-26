"""Minimal clan data loader used in tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class ClanData:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.clans_file = self.data_dir / "clans.json"
        if not self.clans_file.exists():
            self.clans_file.write_text("[]")

    def create_default_clans(self) -> Dict[str, Dict]:
        default = {
            "Uchiha": {"name": "Uchiha", "rarity": "Legendary", "members": []},
            "Hyuga": {"name": "Hyuga", "rarity": "Rare", "members": []},
            "Nara": {"name": "Nara", "rarity": "Uncommon", "members": []},
        }
        with open(self.clans_file, "w", encoding="utf-8") as f:
            json.dump(list(default.values()), f, indent=2)
        return default

    async def get_clan_by_name(self, name: str):
        clans = await self.get_all_clans()
        for clan in clans:
            if clan.get("name") == name:
                return clan
        return None

    async def get_all_clans(self) -> List[Dict]:
        if not self.clans_file.exists():
            return []
        with open(self.clans_file, "r", encoding="utf-8") as f:
            return json.load(f)

    async def add_clan(self, clan: Dict) -> bool:
        clans = await self.get_all_clans()
        clans.append(clan)
        with open(self.clans_file, "w", encoding="utf-8") as f:
            json.dump(clans, f, indent=2)
        return True

    async def get_clan_by_member(self, member_id: str):
        clans = await self.get_all_clans()
        for clan in clans:
            if member_id in clan.get("members", []):
                return clan
        return None

    async def update_clan(self, clan: Dict) -> None:
        clans = await self.get_all_clans()
        for i, c in enumerate(clans):
            if c.get("name") == clan.get("name"):
                clans[i] = clan
        with open(self.clans_file, "w", encoding="utf-8") as f:
            json.dump(clans, f, indent=2)
