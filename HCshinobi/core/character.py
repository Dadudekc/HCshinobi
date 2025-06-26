from dataclasses import dataclass, field
from typing import List, Dict, Set

@dataclass
class Character:
    id: str
    name: str
    clan: str = ""
    level: int = 1
    rank: str = "Genin"
    hp: int = 100
    max_hp: int = 100
    chakra: int = 50
    max_chakra: int = 50
    stamina: int = 50
    max_stamina: int = 50
    strength: int = 10
    defense: int = 5
    speed: int = 5
    ninjutsu: int = 5
    genjutsu: int = 5
    taijutsu: int = 5
    wins: int = 0
    losses: int = 0
    draws: int = 0
    wins_against_rank: Dict[str, int] = field(default_factory=dict)
