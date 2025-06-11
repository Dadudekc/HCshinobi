"""
Room commands for HCShinobi.
Handles room-related commands like join, leave, view rooms, etc.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class RoomCommands(commands.Cog):
    """Room-related commands for HCShinobi."""
    def __init__(self, bot, room_system):
        self.bot = bot
        self.room_system = room_system

    @app_commands.command(name="roominfo", description="View your room info")
    async def roominfo(self, interaction: discord.Interaction):
        await interaction.response.send_message("Room info goes here. (stub)")

async def setup(bot):
    await bot.add_cog(RoomCommands(bot, None)) 