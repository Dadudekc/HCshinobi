from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Character:
    """Basic representation of a player's character."""
    id: str
    name: str
    level: int = 1
    rank: str = "Genin"
    hp: int = 100
    max_hp: int = 100
    chakra: int = 50
    max_chakra: int = 50
    strength: int = 5
    defense: int = 5
    speed: int = 5
    ninjutsu: int = 0
    genjutsu: int = 0
    taijutsu: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        return cls(**data)
