"""Simplified mission commands."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class MissionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mission_board", description="Show missions")
    async def mission_board(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        missions = await self.bot.services.mission_system.get_available_missions(str(interaction.user.id))
        embed = discord.Embed(title="🗒️ Mission Board")
        for m in missions:
            embed.add_field(name=m.get("title", "Mission"), value=m.get("description", ""), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mission_accept", description="Accept a mission")
    async def mission_accept(self, interaction: discord.Interaction, mission_number: int) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        missions = await self.bot.services.mission_system.get_available_missions(str(interaction.user.id))
        if mission_number <= 0 or mission_number > len(missions):
            await interaction.followup.send("Mission not found", ephemeral=True)
            return
        mission_id = missions[mission_number - 1]["mission_id"]
        success, msg = await self.bot.services.mission_system.assign_mission(str(interaction.user.id), mission_id)
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="mission_complete", description="Complete your mission")
    async def mission_complete(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        success, msg, rewards = await self.bot.services.mission_system.complete_mission(str(interaction.user.id))
        if not success:
            await interaction.followup.send(msg, ephemeral=True)
            return
        embed = discord.Embed(title="Mission Complete", description=msg)
        embed.add_field(name="Rewards", value=str(rewards))
        await interaction.followup.send(embed=embed, ephemeral=True)
