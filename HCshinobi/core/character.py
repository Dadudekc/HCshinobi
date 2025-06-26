"""Data model for Shinobi characters."""
from dataclasses import dataclass


@dataclass
class Character:
    id: int
    name: str
    clan: str = ""
    level: int = 1
    hp: int = 100
    max_hp: int = 100
    chakra: int = 50
    max_chakra: int = 50
    stamina: int = 50
    max_stamina: int = 50
    strength: int = 10
    speed: int = 10
    defense: int = 10
    willpower: int = 10
    chakra_control: int = 10
    intelligence: int = 10
    xp: int = 0
    rank: str = "Genin"
