from dataclasses import dataclass, field
from typing import Set

@dataclass
class Character:
    """Minimal representation of a player character."""

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
    intelligence: int = 5
    willpower: int = 5
    chakra_control: int = 5
    xp: int = 0

    completed_missions: Set[str] = field(default_factory=set)
    achievements: Set[str] = field(default_factory=set)
