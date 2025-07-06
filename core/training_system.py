"""Minimal training system used in tests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Tuple, Optional

from .currency_system import CurrencySystem
from .character_system import CharacterSystem


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
    COOLDOWN_HOURS = 1

    def __init__(
        self,
        data_dir: str = "data",
        currency_system: Optional[CurrencySystem] = None,
        character_system: Optional[CharacterSystem] = None,
    ) -> None:
        self.data_dir = Path(data_dir) / "training"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: Dict[str, TrainingSession] = {}
        self.cooldowns: Dict[str, datetime] = {}
        self.currency_system = currency_system
        self.character_system = character_system

    def _get_training_cost(self, attribute: str) -> int:
        return 10

    async def start_training(self, user_id: int | str, attribute: str, duration_hours: int, intensity: str) -> Tuple[bool, str]:
        user_id = str(user_id)
        if user_id in self.active_sessions:
            return False, "Already training"
        cd_until = self.cooldowns.get(user_id)
        if cd_until and datetime.now(timezone.utc) < cd_until:
            remaining = cd_until - datetime.now(timezone.utc)
            hrs = int(remaining.total_seconds() // 3600) + 1
            return False, f"On cooldown for {hrs}h"
        cost = int(self._get_training_cost(attribute) * duration_hours * TrainingIntensity.get_multipliers(intensity)[0])
        if self.currency_system:
            balance = self.currency_system.get_player_balance(user_id)
            if balance < cost:
                return False, f"Insufficient Ryō! Cost: {cost}"
            self.currency_system.set_player_balance(user_id, balance - cost)
        session = TrainingSession(user_id, attribute, duration_hours, intensity, datetime.now(timezone.utc))
        self.active_sessions[user_id] = session
        return True, "✅ Training session started!"

    def get_training_status(self, user_id: int | str) -> TrainingSession | None:
        return self.active_sessions.get(str(user_id))

    def get_training_status_embed(self, user_id: int | str):
        session = self.get_training_status(user_id)
        if not session:
            return None
        remaining = session.start_time + timedelta(hours=session.duration_hours) - datetime.now(timezone.utc)
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

    async def complete_training(self, user_id: int | str, force_complete: bool = False) -> Tuple[bool, str, float]:
        uid = str(user_id)
        session = self.active_sessions.get(uid)
        if not session:
            return False, "No active training", 0.0
        elapsed = datetime.now(timezone.utc) - session.start_time
        if not force_complete and elapsed < timedelta(hours=session.duration_hours):
            return False, "Training still in progress", 0.0
        self.active_sessions.pop(uid)
        stat_mult, _ = TrainingIntensity.get_multipliers(session.intensity)
        gain = session.duration_hours * stat_mult
        if self.character_system:
            char = await self.character_system.get_character(uid)
            if char:
                current = getattr(char, session.attribute, 0)
                setattr(char, session.attribute, current + gain)
                await self.character_system.save_character(char)
        self.cooldowns[uid] = datetime.now(timezone.utc) + timedelta(hours=self.COOLDOWN_HOURS)
        return True, f"Training completed! Points Gained: **{gain:.2f}**", gain

