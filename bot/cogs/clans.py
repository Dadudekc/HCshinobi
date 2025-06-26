"""Simplified clan commands."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from HCshinobi.core.clan_data import ClanData


class ClanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="clan_list", description="List clans")
    async def clan_list(self, interaction: discord.Interaction) -> None:
        clans = await self.bot.services.clan_system.list_clans()
        embed = discord.Embed(title="Available Clans")
        for clan in clans:
            embed.add_field(name=clan["name"], value=clan.get("rarity", ""), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="my_clan", description="My clan")
    async def my_clan(self, interaction: discord.Interaction) -> None:
        clan = None
        embed = discord.Embed(title="Your Clan Assignment")
        if clan:
            embed.description = f"You belong to the **{clan}** clan."
        else:
            await interaction.response.send_message("You have not been assigned a clan yet. Use `/roll_clan` to get started!", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed, ephemeral=True)
