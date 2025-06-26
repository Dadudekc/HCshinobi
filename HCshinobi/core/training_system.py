from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class TrainingSession:
    user_id: str
    attribute: str
    intensity: str

class TrainingSystem:
    """Very small placeholder training system."""

    def __init__(self) -> None:
        self.active_sessions: Dict[str, TrainingSession] = {}
        self.cooldowns: Dict[str, int] = {}

    def get_training_status(self, user_id: str) -> Optional[TrainingSession]:
        return self.active_sessions.get(user_id)

    def get_training_status_embed(self, user_id: str):
        return None
