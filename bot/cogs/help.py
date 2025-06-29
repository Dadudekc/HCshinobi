from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

class HelpCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.support_url: str | None = None

    @app_commands.command(name="help", description="Show help information")
    async def help(self, interaction: discord.Interaction, command_or_category: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Help command placeholder", ephemeral=True)
