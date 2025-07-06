"""Simplified clan commands."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from HCshinobi.core.clan_data import ClanData
from enum import Enum

class RarityTier(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    LEGENDARY = "Legendary"
    EPIC = "Epic"

def get_rarity_color(rarity: str) -> discord.Color:
    mapping = {
        RarityTier.COMMON.value: discord.Color.light_grey(),
        RarityTier.UNCOMMON.value: discord.Color.green(),
        RarityTier.RARE.value: discord.Color.purple(),
        RarityTier.LEGENDARY.value: discord.Color.gold(),
        RarityTier.EPIC.value: discord.Color.red(),
    }
    return mapping.get(rarity, discord.Color.default())


class ClanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="clan_list", description="List clans")
    async def clan_list(self, interaction: discord.Interaction) -> None:
        clans = await self.bot.services.clan_data.get_all_clans()
        embed = discord.Embed(title="Available Clans")
        if not clans:
            embed.description = "No clans have been loaded"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        by_rarity: dict[str, list[str]] = {}
        for clan in clans:
            by_rarity.setdefault(clan.get("rarity", RarityTier.COMMON.value), []).append(clan["name"])
        for rarity, names in sorted(by_rarity.items(), key=lambda i: i[0]):
            names.sort()
            embed.add_field(name=f"🏅 {rarity}", value="- " + "\n- ".join(names), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="my_clan", description="My clan")
    async def my_clan(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        clan_name = self.bot.services.clan_assignment_engine.get_player_clan(user_id)
        if not clan_name:
            await interaction.response.send_message("You have not been assigned a clan yet. Use `/roll_clan` to get started!", ephemeral=True)
            return
        details = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        color = get_rarity_color(details.get("rarity", ""))
        embed = discord.Embed(title="Your Clan Assignment", description=f"You belong to the **{clan_name}** clan.", color=color)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clan_info", description="Get clan info")
    async def clan_info(self, interaction: discord.Interaction, clan_name: str) -> None:
        details = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        if not details:
            all_clans = await self.bot.services.clan_data.get_all_clans()
            suggestions = [c["name"] for c in all_clans if clan_name.lower() in c["name"].lower()]
            suggestion_text = "\n".join(suggestions)
            await interaction.response.send_message(
                f"Clan '{clan_name}' not found. Did you mean one of these?\n{suggestion_text}",
                ephemeral=True,
            )
            return
        color = get_rarity_color(details.get("rarity", ""))
        embed = discord.Embed(title=f"{details['name']} Clan", description=details.get("description", ""), color=color)
        embed.add_field(name="Rarity", value=details.get("rarity", ""))
        embed.add_field(name="Members", value=str(len(details.get("members", []))))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="create_clan", description="Create a clan")
    async def create_clan(self, interaction: discord.Interaction, name: str, description: str, rarity: str) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to create clans.", ephemeral=True)
            return
        clan = {"name": name, "description": description, "rarity": rarity, "members": []}
        await self.bot.services.clan_data.add_clan(clan)
        await interaction.response.send_message(f"Successfully created clan {name}", ephemeral=True)

    @app_commands.command(name="join_clan", description="Join a clan")
    async def join_clan(self, interaction: discord.Interaction, clan_name: str) -> None:
        details = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        if not details:
            await interaction.response.send_message(f"Clan '{clan_name}' not found. Use `/clan_list` to see available clans.", ephemeral=True)
            return
        user_id = interaction.user.id
        if user_id in details.get("members", []):
            await interaction.response.send_message("You are already a member of this clan.", ephemeral=True)
            return
        details.setdefault("members", []).append(user_id)
        await self.bot.services.clan_data.update_clan(details)
        await interaction.response.send_message(f"Successfully joined clan {clan_name}", ephemeral=True)

    @app_commands.command(name="clan", description="View your current clan")
    async def clan(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        details = await self.bot.services.clan_data.get_clan_by_member(str(user_id))
        if not details:
            await interaction.response.send_message("You are not currently in a clan. Use `/clan_list` to see available clans.", ephemeral=True)
            return
        color = get_rarity_color(details.get("rarity", ""))
        embed = discord.Embed(title=f"{details['name']} Clan", description=details.get("description", ""), color=color)
        embed.add_field(name="Rarity", value=details.get("rarity", ""))
        embed.add_field(name="Members", value=str(len(details.get("members", []))))
        await interaction.response.send_message(embed=embed)
