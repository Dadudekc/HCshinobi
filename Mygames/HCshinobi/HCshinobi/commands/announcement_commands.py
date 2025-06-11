"""
Announcement commands for HCShinobi.
Handles announcement-related commands for the bot.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class AnnouncementCommands(commands.Cog):
    """Announcement commands for HCShinobi."""
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Send an announcement")
    async def announce(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(f"Announcement: {message}")

async def setup(bot):
    await bot.add_cog(AnnouncementCommands(bot)) 