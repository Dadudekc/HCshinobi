"""Simplified training system used by the tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Tuple


class TrainingIntensity:
    LIGHT = "Light"
    MODERATE = "Moderate"
    INTENSE = "Intense"

    @staticmethod
    def get_multipliers(intensity: str) -> Tuple[float, float]:
        if intensity == TrainingIntensity.MODERATE:
            return 1.5, 1.5
        if intensity == TrainingIntensity.INTENSE:
            return 2.0, 2.0
        return 1.0, 1.0


@dataclass
class TrainingSession:
    user_id: str
    attribute: str
    duration_hours: int
    intensity: str
    start_time: datetime


class TrainingSystem:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir) / "training"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: Dict[str, TrainingSession] = {}
        self.cooldowns: Dict[str, datetime] = {}

    def _get_training_cost(self, attribute: str) -> int:
        return 10

    async def start_training(
        self,
        user_id: int | str,
        attribute: str,
        duration_hours: int,
        intensity: str,
    ) -> Tuple[bool, str]:
        user_id = str(user_id)
        if user_id in self.active_sessions:
            return False, "Already training"
        self.active_sessions[user_id] = TrainingSession(
            user_id,
            attribute,
            duration_hours,
            intensity,
            datetime.now(timezone.utc),
        )
        return True, "✅ Training session started!"

    def get_training_status(self, user_id: int | str) -> TrainingSession | None:
        return self.active_sessions.get(str(user_id))

    def get_training_status_embed(self, user_id: int | str):
        session = self.get_training_status(user_id)
        if not session:
            return None
        remaining = session.start_time + timedelta(hours=session.duration_hours) - datetime.now(
            timezone.utc
        )
        hours_left = max(int(remaining.total_seconds() // 3600), 0)
        import discord

        embed = discord.Embed(title="🏋️ Training Status", color=discord.Color.blue())
        embed.description = f"⏳ Training in progress... {hours_left} hours remaining"
        embed.add_field(name="Attribute", value=session.attribute, inline=True)
        embed.add_field(name="Intensity", value=session.intensity, inline=True)
        embed.add_field(name="Progress", value="`██████████░░░░░░░░░░` 50%", inline=False)
        return embed

    async def cancel_training(self, user_id: int | str) -> Tuple[bool, str]:
        uid = str(user_id)
        if uid not in self.active_sessions:
            return False, "No active training"
        self.active_sessions.pop(uid)
        return True, "Training cancelled"

