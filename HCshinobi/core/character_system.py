from typing import Dict, Optional
from .character import Character

class CharacterSystem:
    def __init__(self) -> None:
        self.characters: Dict[str, Character] = {}

    async def create_character(self, user_id: int, name: str, clan: str = "") -> Character:
        char = Character(id=str(user_id), name=name, clan=clan)
        self.characters[str(user_id)] = char
        return char

    async def get_character(self, user_id: int) -> Optional[Character]:
        return self.characters.get(str(user_id))

    async def delete_character(self, user_id: int) -> None:
        self.characters.pop(str(user_id), None)

    async def save_character(self, char: Character) -> None:
        self.characters[str(char.id)] = char
