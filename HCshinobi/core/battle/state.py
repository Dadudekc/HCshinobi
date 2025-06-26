from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from ..character import Character

@dataclass
class BattleParticipant:
    id: str
    character: Character
    current_hp: int
    effects: List[dict] = field(default_factory=list)

    @classmethod
    def from_character(cls, character: Character) -> "BattleParticipant":
        return cls(id=str(character.id), character=character, current_hp=character.hp)

@dataclass
class BattleState:
    attacker: BattleParticipant
    defender: BattleParticipant
    current_turn_player_id: str
    turn_number: int = 1
    battle_log: List[str] = field(default_factory=list)
    last_action: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    winner_id: str | None = None
    end_reason: str | None = None
    id: str = field(default_factory=lambda: str(id(object())))
