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
    """Interactive view for configuring and starting training sessions."""

    def __init__(self, character, training_system) -> None:
        super().__init__()
        self.character = character
        self.training_system = training_system
        self.attribute: str | None = None
        self.intensity: TrainingIntensity = TrainingIntensity.LIGHT
        self.duration_hours: int = 1

    @discord.ui.select(
        placeholder="Attribute",
        options=[
            discord.SelectOption(label=v, value=k) for k, v in TRAINING_ATTRIBUTES.items()
        ],
    )
    async def select_attribute(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.attribute = select.values[0]
        await interaction.response.defer(thinking=False)

    @discord.ui.select(
        placeholder="Intensity",
        options=[
            discord.SelectOption(label=i.value, value=i.name) for i in TrainingIntensity
        ],
    )
    async def select_intensity(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.intensity = TrainingIntensity[select.values[0]]
        await interaction.response.defer(thinking=False)

    @discord.ui.select(
        placeholder="Duration (hours)",
        options=[
            discord.SelectOption(label=str(h), value=str(h)) for h in (1, 2, 4)
        ],
    )
    async def select_duration(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.duration_hours = int(select.values[0])
        await interaction.response.defer(thinking=False)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.attribute:
            await interaction.response.send_message(
                "Please select an attribute first.", ephemeral=True
            )
            return
        await self.training_system.start_training(
            interaction.user.id, self.attribute, self.duration_hours, self.intensity.value
        )
        await interaction.response.send_message(
            f"Training {self.attribute} for {self.duration_hours}h started!", ephemeral=True
        )


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
        view = TrainingView(char, self.bot.services.training_system)
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

