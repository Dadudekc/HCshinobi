"""Battle state containers."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List
from datetime import datetime, timezone

from ..character import Character


@dataclass
class BattleParticipant:
    character: Character
    current_hp: int
    effects: List[dict] = field(default_factory=list)

    id: str = field(init=False)

    def __post_init__(self) -> None:
        self.id = str(self.character.id)

    @classmethod
    def from_character(cls, character: Character) -> "BattleParticipant":
        return cls(character=character, current_hp=character.hp)


@dataclass
class BattleState:
    attacker: BattleParticipant
    defender: BattleParticipant
    current_turn_player_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    turn_number: int = 1
    battle_log: List[str] = field(default_factory=list)
    winner_id: str | None = None
    last_action: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    end_reason: str | None = None
