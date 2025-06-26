"""Training related commands and helper classes used in the test suite."""

from __future__ import annotations

from enum import Enum
from typing import Dict

import discord
from discord import app_commands
from discord.ext import commands


class TrainingIntensity(Enum):
    LIGHT = "Light"
    MODERATE = "Moderate"
    INTENSE = "Intense"

    @staticmethod
    def get_multipliers(intensity: "TrainingIntensity") -> tuple[float, float]:
        if intensity is TrainingIntensity.MODERATE:
            return 1.5, 1.5
        if intensity is TrainingIntensity.INTENSE:
            return 2.0, 2.0
        return 1.0, 1.0


TRAINING_ATTRIBUTES: Dict[str, str] = {
    "strength": "Strength",
    "speed": "Speed",
    "ninjutsu": "Ninjutsu",
    "genjutsu": "Genjutsu",
    "taijutsu": "Taijutsu",
}


class TrainingView(discord.ui.View):
    """Simple view object holding training configuration."""

    def __init__(self, character) -> None:
        super().__init__()
        self.character = character


class TrainingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="train", description="Begin training")
    async def train(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        char = await self.bot.services.character_system.get_character(interaction.user.id)
        if not char:
            await interaction.followup.send(
                "You must create a character first using `/create`.", ephemeral=True
            )
            return
        view = TrainingView(char)
        embed = discord.Embed(title="🎯 Training Setup")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="training_status", description="View training status")
    async def training_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = self.bot.services.training_system.get_training_status_embed(interaction.user.id)
        if embed:
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                "You are not currently training and have no active cooldown.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrainingCommands(bot))


__all__ = [
    "TrainingCommands",
    "TrainingView",
    "TrainingIntensity",
    "TRAINING_ATTRIBUTES",
]

