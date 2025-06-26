"""Basic training command stubs."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..services import ServiceContainer
from ...core.training_system import TrainingIntensity

# Attributes players can train. Minimal set for tests.
TRAINING_ATTRIBUTES = {
    "taijutsu": "Taijutsu",
    "ninjutsu": "Ninjutsu",
    "genjutsu": "Genjutsu",
}


class TrainingView(discord.ui.View):
    def __init__(self, character, *, timeout: float | None = 180) -> None:
        super().__init__(timeout=timeout)
        self.character = character

        self.attribute_select = discord.ui.Select(
            placeholder="Select Attribute",
            custom_id="training_attribute_select",
            options=[discord.SelectOption(label=v, value=k) for k, v in TRAINING_ATTRIBUTES.items()],
        )
        self.attribute_select.callback = self.select_attribute_callback
        self.add_item(self.attribute_select)

        self.intensity_select = discord.ui.Select(
            placeholder="Select Intensity",
            custom_id="training_intensity_select",
            options=[
                discord.SelectOption(label="Light", value=str(TrainingIntensity.LIGHT.value)),
                discord.SelectOption(label="Moderate", value=str(TrainingIntensity.MODERATE.value)),
                discord.SelectOption(label="Intense", value=str(TrainingIntensity.INTENSE.value)),
            ],
        )
        self.intensity_select.callback = self.select_intensity_callback
        self.add_item(self.intensity_select)

        self.duration_select = discord.ui.Select(
            placeholder="Duration (hours)",
            custom_id="training_duration_select",
            options=[discord.SelectOption(label=str(h), value=str(h)) for h in [1, 2, 4, 8]],
        )
        self.duration_select.callback = self.select_duration_callback
        self.add_item(self.duration_select)

        self.start_button = discord.ui.Button(label="Start Training", style=discord.ButtonStyle.primary)
        self.start_button.callback = self.start_training_callback
        self.add_item(self.start_button)

        self.selected_attribute: str | None = None
        self.selected_intensity: TrainingIntensity | None = None
        self.selected_duration: int | None = None

    async def select_attribute_callback(self, interaction: discord.Interaction):
        self.selected_attribute = self.attribute_select.values[0]
        await interaction.response.defer(ephemeral=True)

    async def select_intensity_callback(self, interaction: discord.Interaction):
        value = int(self.intensity_select.values[0])
        self.selected_intensity = TrainingIntensity(value)
        await interaction.response.defer(ephemeral=True)

    async def select_duration_callback(self, interaction: discord.Interaction):
        self.selected_duration = int(self.duration_select.values[0])
        await interaction.response.defer(ephemeral=True)

    async def start_training_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not all([self.selected_attribute, self.selected_intensity, self.selected_duration]):
            await interaction.response.send_message("Please select attribute, intensity and duration first.", ephemeral=True)
            return
        training_system = interaction.client.services.training_system
        await training_system.start_training(
            interaction.user.id,
            self.selected_attribute,
            self.selected_duration,
            self.selected_intensity,
        )
        await interaction.response.send_message("Training started!", ephemeral=True)


class TrainingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        if isinstance(bot, commands.Bot):
            self.services: ServiceContainer = bot.services
        else:
            self.services = ServiceContainer()

    @app_commands.command(name="train", description="Begin a training session")
    async def train(self, interaction: discord.Interaction):
        char = await self.services.character_system.get_character(interaction.user.id)
        if not char:
            await interaction.followup.send("You must create a character first using `/create`.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        view = TrainingView(char)
        embed = discord.Embed(title="\U0001F3AF Training Setup")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="training_status", description="Check your training status")
    async def training_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = self.services.training_system.get_training_status_embed(interaction.user.id)
        if embed is None:
            await interaction.followup.send("You are not currently training and have no active cooldown.", ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="cancel_training", description="Cancel your current training session")
    async def cancel_training(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.services.training_system.complete_training(interaction.user.id, force_complete=True)
        await interaction.followup.send("Training cancelled.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrainingCommands(bot))
