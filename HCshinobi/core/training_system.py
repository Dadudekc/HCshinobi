from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import discord

class TrainingIntensity(Enum):
    LIGHT = 1
    MODERATE = 2
    INTENSE = 3

    @staticmethod
    def get_multipliers(intensity: 'TrainingIntensity'):
        mapping = {
            TrainingIntensity.LIGHT: (1.0, 1.0),
            TrainingIntensity.MODERATE: (1.5, 1.5),
            TrainingIntensity.INTENSE: (2.0, 2.0),
        }
        return mapping[intensity]

@dataclass
class TrainingSession:
    user_id: str
    attribute: str
    duration_hours: int
    intensity: TrainingIntensity
    start_time: float

class TrainingSystem:
    def __init__(self) -> None:
        self.active_sessions: Dict[str, TrainingSession] = {}
        self.cooldowns: Dict[str, float] = {}

    async def start_training(self, user_id: int | str, attribute: str, duration_hours: int, intensity: TrainingIntensity):
        if str(user_id) in self.active_sessions:
            return False, "Already training"
        self.active_sessions[str(user_id)] = TrainingSession(str(user_id), attribute, duration_hours, intensity, 0.0)
        return True, "Training started"

    async def complete_training(self, user_id: int | str, force_complete: bool = False):
        self.active_sessions.pop(str(user_id), None)
        return True, "Training completed"

    def get_training_status_embed(self, user_id: int | str) -> Optional[discord.Embed]:
        if str(user_id) not in self.active_sessions:
            return None
        session = self.active_sessions[str(user_id)]
        embed = discord.Embed(title="\U0001F3CB Training Status")
        embed.add_field(name="Attribute", value=session.attribute.title())
        return embed
