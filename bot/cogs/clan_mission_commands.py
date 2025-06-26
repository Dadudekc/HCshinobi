"""Simplified clan mission commands."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class ClanMissionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="clan_mission_board", description="Clan missions")
    async def mission_board(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Clan missions not implemented", ephemeral=True)

    @app_commands.command(name="clan_mission_accept", description="Accept clan mission")
    async def accept_mission(self, interaction: discord.Interaction, mission_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Mission accepted", ephemeral=True)

    @app_commands.command(name="clan_mission_complete", description="Complete clan mission")
    async def complete_mission(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Mission complete", ephemeral=True)
