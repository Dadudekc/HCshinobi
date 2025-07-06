from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Callable

BattleLogCallback = Callable[["BattleState", str], None]

@dataclass
class StatusEffect:
    name: str
    duration: int
    potency: float
    effect_type: str
    description: str = ""
    applied_at: datetime = datetime.now(timezone.utc)

    def to_dict(self):
        d = asdict(self)
        d["applied_at"] = self.applied_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        if isinstance(data.get("applied_at"), str):
            data["applied_at"] = datetime.fromisoformat(data["applied_at"])
        return cls(**data)
