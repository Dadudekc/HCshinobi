"""Basic clan commands and utilities used in tests."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, List, Dict

import discord
from discord import app_commands
from discord.ext import commands


class RarityTier(Enum):
    """Simplified rarity tiers for clans."""

    LEGENDARY = "Legendary"
    EPIC = "Epic"
    RARE = "Rare"
    UNCOMMON = "Uncommon"
    COMMON = "Common"


_RARITY_COLORS = {
    RarityTier.LEGENDARY: discord.Color.red(),
    RarityTier.EPIC: discord.Color.purple(),
    RarityTier.RARE: discord.Color.blue(),
    RarityTier.UNCOMMON: discord.Color.dark_teal(),
    RarityTier.COMMON: discord.Color.light_grey(),
}


def get_rarity_color(rarity_str: str) -> discord.Color:
    """Return a :class:`discord.Color` for a given rarity string."""

    try:
        tier = RarityTier(rarity_str)
    except ValueError:
        return discord.Color.default()
    return _RARITY_COLORS.get(tier, discord.Color.default())


class ClanCommands(commands.Cog):
    """Minimal implementation of clan related commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="my_clan", description="View your clan info")
    async def my_clan(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        clan_name = self.bot.services.clan_assignment_engine.get_player_clan(user_id)
        if not clan_name:
            await interaction.followup.send(
                "You have not been assigned a clan yet. Use `/roll_clan` to get started!",
                ephemeral=True,
            )
            return

        clan_details = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        embed = discord.Embed(title="Your Clan Assignment")
        embed.description = f"You belong to the **{clan_name}** clan."
        if clan_details:
            rarity = clan_details.get("rarity")
            if rarity:
                embed.add_field(name="Rarity", value=rarity, inline=False)
                embed.color = get_rarity_color(rarity)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="clan_list", description="List clans by rarity")
    async def clan_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        clans: List[Dict[str, str]] = await self.bot.services.clan_data.get_all_clans()
        if not clans:
            embed = discord.Embed(
                title="Available Clans",
                description="No clans have been loaded",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="Available Clans")
        grouped: Dict[str, List[str]] = {}
        for clan in clans:
            rarity = clan.get("rarity", RarityTier.COMMON.value)
            grouped.setdefault(rarity, []).append(clan["name"])

        for rarity, names in grouped.items():
            names.sort()
            embed.add_field(
                name=f"🏅 {rarity}",
                value="\n".join(f"- {n}" for n in names),
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="clan_info", description="Get info about a clan")
    async def clan_info(self, interaction: discord.Interaction, clan_name: str) -> None:
        await interaction.response.defer()
        info = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        if not info:
            suggestions = await self.bot.services.clan_data.get_all_clans()
            matches = [c["name"] for c in suggestions if clan_name.lower() in c["name"].lower()]
            suggestion_text = "\n".join(matches)
            await interaction.followup.send(
                f"Clan '{clan_name}' not found. Did you mean one of these?\n{suggestion_text}",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"{info['name']} Clan",
            description=info.get("description", ""),
            color=get_rarity_color(info.get("rarity", "")),
        )
        rarity = info.get("rarity")
        if rarity:
            embed.add_field(name="Rarity", value=rarity, inline=True)
        members = info.get("members")
        if members is not None:
            embed.add_field(name="Members", value=str(len(members)), inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClanCommands(bot))


__all__ = [
    "ClanCommands",
    "RarityTier",
    "get_rarity_color",
]

