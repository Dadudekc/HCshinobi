"""Simple in-memory character management."""

from typing import Dict, Optional

from .character import Character

class CharacterSystem:
    def __init__(self) -> None:
        self.characters: Dict[int, Character] = {}

    async def create_character(self, user_id: int, name: str, clan: str) -> Character:
        char = Character(id=user_id, name=name, clan=clan)
        self.characters[user_id] = char
        return char

    async def get_character(self, user_id: int) -> Optional[Character]:
        return self.characters.get(user_id)

    async def delete_character(self, user_id: int) -> None:
        self.characters.pop(user_id, None)
