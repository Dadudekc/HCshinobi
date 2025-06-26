from dataclasses import dataclass, field
from typing import Dict

@dataclass
class Character:
    id: int | str
    name: str
    clan: str = ""
    level: int = 1
    rank: str = "Genin"
    hp: int = 100
    max_hp: int = 100
    chakra: int = 50
    max_chakra: int = 50
    strength: int = 10
    defense: int = 10
    speed: int = 10
    ninjutsu: int = 0
    genjutsu: int = 0
    taijutsu: int = 0
    inventory: Dict[str, int] = field(default_factory=dict)
