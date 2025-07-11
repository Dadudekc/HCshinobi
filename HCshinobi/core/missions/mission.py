from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any

class MissionStatus(Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

class MissionDifficulty(Enum):
    D_RANK = "D"
    C_RANK = "C"
    B_RANK = "B"
    A_RANK = "A"
    S_RANK = "S"

@dataclass
class Mission:
    id: str
    title: str
    description: str
    difficulty: MissionDifficulty
    village: str
    reward: Dict[str, Any]
    duration: timedelta
    requirements: Dict[str, Any] | None = None
    status: MissionStatus = MissionStatus.AVAILABLE
    progress: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def start(self) -> None:
        if self.status != MissionStatus.AVAILABLE:
            raise ValueError("Mission cannot be started")
        self.status = MissionStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        if self.status != MissionStatus.IN_PROGRESS:
            raise ValueError("Mission cannot be completed")
        self.status = MissionStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def fail(self) -> None:
        if self.status not in (MissionStatus.IN_PROGRESS, MissionStatus.AVAILABLE):
            raise ValueError("Mission cannot be failed")
        self.status = MissionStatus.FAILED

    def check_expired(self) -> bool:
        if not self.started_at:
            return False
        if datetime.now(timezone.utc) >= self.started_at + self.duration:
            self.status = MissionStatus.EXPIRED
            return True
        return False

    def update_progress(self, key: str, value: Any) -> None:
        if self.status != MissionStatus.IN_PROGRESS:
            raise ValueError("Mission not active")
        self.progress[key] = value

    def to_dict(self) -> Dict[str, Any]:
        def get_val(val):
            return val.value if hasattr(val, 'value') else val
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "difficulty": get_val(self.difficulty),
            "village": self.village,
            "reward": self.reward,
            "duration_seconds": int(self.duration.total_seconds()),
            "requirements": self.requirements or {},
            "status": get_val(self.status),
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mission":
        mission = cls(
            id=data["id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            difficulty=MissionDifficulty(data.get("difficulty", "D")),
            village=data.get("village", ""),
            reward=data.get("reward", {}),
            duration=timedelta(seconds=data.get("duration_seconds", 0)),
            requirements=data.get("requirements", {}),
        )
        mission.status = MissionStatus(data.get("status", MissionStatus.AVAILABLE.value))
        mission.progress = data.get("progress", {})
        if data.get("started_at"):
            mission.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            mission.completed_at = datetime.fromisoformat(data["completed_at"])
        return mission
