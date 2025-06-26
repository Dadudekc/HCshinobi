"""Minimal battle state representations."""
from dataclasses import dataclass
from typing import Optional

from ..character import Character


@dataclass
class BattleParticipant:
    id: str
    character: Character

    @classmethod
    def from_character(cls, char: Character) -> 'BattleParticipant':
        return cls(id=str(char.id), character=char)


@dataclass
class BattleState:
    attacker: BattleParticipant
    defender: BattleParticipant
    current_turn_player_id: str
    winner_id: Optional[str] = None
    turn_number: int = 0
