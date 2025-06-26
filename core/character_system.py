"""Character management with JSON persistence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .character import Character


class CharacterSystem:
    """Manage player characters stored as JSON files."""

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir) / "characters"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.characters: Dict[str, Character] = {}

    async def create_character(self, user_id: int | str, name: str, clan: str) -> Character:
        char = Character(id=str(user_id), name=name)
        char.clan = clan  # type: ignore[attr-defined]
        self.characters[str(user_id)] = char
        await self.save_character(char)
        return char

    async def get_character(self, user_id: int | str) -> Optional[Character]:
        uid = str(user_id)
        if uid in self.characters:
            return self.characters[uid]
        return await self._load_character(uid)

    async def delete_character(self, user_id: int | str) -> bool:
        uid = str(user_id)
        self.characters.pop(uid, None)
        file = self.data_dir / f"{uid}.json"
        if file.exists():
            file.unlink()
            return True
        return False

    async def save_character(self, character: Character) -> None:
        file = self.data_dir / f"{character.id}.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump(character.to_dict(), f, indent=2)

    async def _load_character(self, user_id: str) -> Optional[Character]:
        file = self.data_dir / f"{user_id}.json"
        if not file.exists():
            return None
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        char = Character.from_dict(data)
        self.characters[user_id] = char
        return char
