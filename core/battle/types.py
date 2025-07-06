"""Data structures for battles."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict

BattleLogCallback = Callable[["BattleState", str], None]


@dataclass
class StatusEffect:
    name: str
    duration: int
    potency: float
    effect_type: str
    description: str
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "duration": self.duration,
            "potency": self.potency,
            "effect_type": self.effect_type,
            "description": self.description,
            "applied_at": self.applied_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "StatusEffect":
        obj = cls(
            name=data["name"],
            duration=data["duration"],
            potency=data.get("potency", 0),
            effect_type=data.get("effect_type", ""),
            description=data.get("description", ""),
        )
        if "applied_at" in data:
            obj.applied_at = datetime.fromisoformat(data["applied_at"])
        return obj
