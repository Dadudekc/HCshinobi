"""
Training commands for HCShinobi.
Handles training-related commands like train, view progress, etc.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class TrainingCommands(commands.Cog):
    """Training-related commands for HCShinobi."""
    def __init__(self, bot, training_system, character_system):
        self.bot = bot
        self.training_system = training_system
        self.character_system = character_system

    @app_commands.command(name="train", description="Train your character")
    async def train(self, interaction: discord.Interaction):
        await interaction.response.send_message("Training started! (stub)")

async def setup(bot):
    await bot.add_cog(TrainingCommands(bot, None, None)) 