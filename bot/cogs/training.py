"""Simplified training commands."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from HCshinobi.core.training_system import TrainingIntensity


class TrainingView(discord.ui.View):
    def __init__(self, character) -> None:
        super().__init__()
        self.character = character
        self.attribute = None
        self.intensity = None
        self.duration = None


class TrainingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="train", description="Begin training")
    async def train(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        char = await self.bot.services.character_system.get_character(interaction.user.id)
        if not char:
            await interaction.followup.send("You must create a character first using `/create`.", ephemeral=True)
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
            await interaction.followup.send("You are not currently training and have no active cooldown.", ephemeral=True)

    @app_commands.command(name="cancel_training", description="Cancel active training")
    async def cancel_training(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        success, msg = await self.bot.services.training_system.cancel_training(interaction.user.id)
        await interaction.followup.send(msg, ephemeral=True)
