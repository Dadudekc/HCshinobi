from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import Mission, MissionDifficulty, MissionStatus
from .generator import MissionGenerator

class MissionInterface(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.active_missions: Dict[str, List[Mission]] = {}
        self.player_missions: Dict[int, Mission] = {}
        self._village_cooldowns: Dict[str, datetime] = {}

    async def _generate_mission(self, village: str, difficulty: str) -> Mission:
        async with MissionGenerator() as gen:
            missions = await gen.generate_mission_batch(village, [MissionDifficulty(difficulty)], 1)
            return missions[0]

    @app_commands.command(name="mission")
    async def mission_command(self, interaction: discord.Interaction, difficulty: str, village: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        now = datetime.now(timezone.utc)
        last = self._village_cooldowns.get(village)
        if last and (now - last).total_seconds() < 2:
            await interaction.followup.send("Please wait before requesting another mission.", ephemeral=True)
            return
        mission = await self._generate_mission(village, difficulty)
        self.active_missions.setdefault(village, []).append(mission)
        self.player_missions[interaction.user.id] = mission
        self._village_cooldowns[village] = now
        await interaction.followup.send(f"Mission '{mission.title}' created", ephemeral=True)

    @app_commands.command(name="missions")
    async def missions_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        mission = self.player_missions.get(interaction.user.id)
        if mission and mission.check_expired():
            await interaction.followup.send("Your mission has expired.", ephemeral=True)
            return
        if not mission:
            await interaction.followup.send("No active mission.", ephemeral=True)
            return
        embed = discord.Embed(title="Active Mission", description=mission.title)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="complete_mission")
    async def complete_mission_command(self, interaction: discord.Interaction, mission_id: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        mission = self.player_missions.get(interaction.user.id)
        if not mission or mission.id != mission_id:
            await interaction.followup.send("Mission not found", ephemeral=True)
            return
        if mission.check_expired():
            await interaction.followup.send("Mission expired", ephemeral=True)
            return
        if mission.status == MissionStatus.COMPLETED:
            await interaction.followup.send("Mission already completed", ephemeral=True)
            return
        mission.complete()
        await interaction.followup.send("Mission completed", ephemeral=True)
