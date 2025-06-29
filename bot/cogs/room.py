from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

class RoomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="look")
    async def look(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(title="Room"), ephemeral=True)

    @app_commands.command(name="move")
    async def move(self, interaction: discord.Interaction, direction: str) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(title="Moved"), ephemeral=True)

    @app_commands.command(name="enter")
    async def enter(self, interaction: discord.Interaction, room_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(title="Entered"), ephemeral=True)

    @app_commands.command(name="room_info")
    async def room_info(self, interaction: discord.Interaction, room_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(title="Room Info"), ephemeral=True)

    @app_commands.command(name="room_enter")
    async def room_enter(self, interaction: discord.Interaction, room_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(title="Entered Room"), ephemeral=True)

    @app_commands.command(name="room_leave")
    async def room_leave(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=discord.Embed(title="Left Room"), ephemeral=True)
