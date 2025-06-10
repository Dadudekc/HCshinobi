"""
Mission system for dynamic quests and tasks.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class MissionDifficulty(Enum):
    """Mission difficulty levels."""
    D_RANK = "D"
    C_RANK = "C"
    B_RANK = "B"
    A_RANK = "A"
    S_RANK = "S"

class MissionStatus(Enum):
    """Mission status states."""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

@dataclass
class Mission:
    """Represents a dynamic mission in the game."""
    id: str
    title: str
    description: str
    difficulty: MissionDifficulty
    village: str
    reward: Dict[str, int]
    duration: timedelta
    status: MissionStatus = field(default=MissionStatus.AVAILABLE)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requirements: Dict[str, Any] = field(default_factory=dict)
    progress: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert mission to dictionary for storage."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty.value,
            "village": self.village,
            "reward": self.reward,
            "duration": self.duration.total_seconds(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "requirements": self.requirements,
            "progress": self.progress,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mission':
        """Create mission from dictionary data."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            difficulty=MissionDifficulty(data["difficulty"]),
            village=data["village"],
            reward=data["reward"],
            duration=timedelta(seconds=data["duration"]),
            status=MissionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None,
            requirements=data["requirements"],
            progress=data["progress"],
            metadata=data["metadata"]
        )

    def start(self) -> None:
        """Start the mission."""
        if self.status != MissionStatus.AVAILABLE:
            raise ValueError("Mission cannot be started in its current state")
        self.status = MissionStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def complete(self) -> None:
        """Complete the mission."""
        if self.status != MissionStatus.IN_PROGRESS:
            raise ValueError("Mission cannot be completed in its current state")
        self.status = MissionStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def fail(self) -> None:
        """Fail the mission."""
        if self.status != MissionStatus.IN_PROGRESS:
            raise ValueError("Mission cannot be failed in its current state")
        self.status = MissionStatus.FAILED
        self.completed_at = datetime.utcnow()

    def check_expired(self) -> bool:
        """Check if mission has expired."""
        if self.status != MissionStatus.IN_PROGRESS:
            return False
        if not self.started_at:
            return False
        
        # Calculate time elapsed since mission start
        elapsed = datetime.utcnow() - self.started_at
        
        # Check if elapsed time exceeds duration
        if elapsed >= self.duration:
            self.status = MissionStatus.EXPIRED
            self.completed_at = datetime.utcnow()
            return True
            
        return False

    def update_progress(self, key: str, value: Any) -> None:
        """Update mission progress."""
        if self.status != MissionStatus.IN_PROGRESS:
            raise ValueError("Cannot update progress of non-active mission")
        self.progress[key] = value 