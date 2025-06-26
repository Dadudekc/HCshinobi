"""Lightweight training system placeholders."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict


class TrainingIntensity(Enum):
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3


@dataclass
class TrainingSession:
    user_id: int
    intensity: TrainingIntensity


class TrainingSystem:
    def __init__(self) -> None:
        self.active_sessions: Dict[int, TrainingSession] = {}
        self.cooldowns: Dict[int, int] = {}

    async def start_training(self, user_id: int, intensity: TrainingIntensity) -> None:
        self.active_sessions[user_id] = TrainingSession(user_id, intensity)

    async def finish_training(self, user_id: int) -> None:
        self.active_sessions.pop(user_id, None)
        self.cooldowns[user_id] = 0
