"""Basic clan commands and utilities used in tests."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, List, Dict

import discord
from discord import app_commands
from discord.ext import commands

from ...utils.embeds import create_clan_embed


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
        user_id = interaction.user.id
        clan_name = self.bot.services.clan_assignment_engine.get_player_clan(user_id)
        if not clan_name:
            await interaction.response.send_message(
                "You have not been assigned a clan yet. Use `/roll_clan` to get started!",
                ephemeral=True,
            )
            return

        clan_details = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        color = get_rarity_color(clan_details.get("rarity", ""))
        embed = discord.Embed(
            title="Your Clan Assignment",
            description=f"You belong to the **{clan_name}** clan.",
            color=color,
        )
        embed.add_field(name="Rarity", value=clan_details.get("rarity"), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clan_list", description="List clans")
    async def clan_list(self, interaction: discord.Interaction) -> None:
        clans = await self.bot.services.clan_data.get_all_clans()
        if not clans:
            embed = discord.Embed(description="No clans have been loaded")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="Available Clans")
        by_rarity = {}
        for clan in clans:
            by_rarity.setdefault(clan.get("rarity"), []).append(clan["name"])

        for tier in RarityTier:
            names = sorted(by_rarity.get(tier.value, []))
            if names:
                value = "\n".join(f"- {n}" for n in names)
                embed.add_field(name=f"🏅 {tier.value}", value=value, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clan_info", description="Get info on a clan")
    async def clan_info(self, interaction: discord.Interaction, clan_name: str) -> None:
        clan = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        if not clan:
            all_clans = await self.bot.services.clan_data.get_all_clans()
            suggestions = [c["name"] for c in all_clans if clan_name.lower() in c["name"].lower()]
            suggestion_text = "\n".join(suggestions)
            await interaction.response.send_message(
                f"Clan '{clan_name}' not found. Did you mean one of these?\n{suggestion_text}",
                ephemeral=True,
            )
            return

        color = get_rarity_color(clan.get("rarity", ""))
        embed = create_clan_embed(
            clan.get("name", clan_name),
            clan.get("description", ""),
            rarity=clan.get("rarity"),
            members=clan.get("members"),
        )
        embed.color = color
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="create_clan", description="Create a new clan")
    async def create_clan(self, interaction: discord.Interaction, name: str, description: str, rarity: str) -> None:
        if not getattr(interaction.user.guild_permissions, "administrator", False):
            await interaction.response.send_message(
                "You need administrator permissions to create clans.",
                ephemeral=True,
            )
            return

        clan = {"name": name, "description": description, "rarity": rarity, "members": []}
        await self.bot.services.clan_data.add_clan(clan)
        await interaction.response.send_message(
            f"Successfully created clan {name}",
            ephemeral=True,
        )

    @app_commands.command(name="join_clan", description="Join a clan")
    async def join_clan(self, interaction: discord.Interaction, clan_name: str) -> None:
        user_id = interaction.user.id
        clan = await self.bot.services.clan_data.get_clan_by_name(clan_name)
        if not clan:
            await interaction.response.send_message(
                f"Clan '{clan_name}' not found. Use `/clan_list` to see available clans.",
                ephemeral=True,
            )
            return

        members = clan.setdefault("members", [])
        if user_id in members:
            await interaction.response.send_message("You are already a member of this clan.", ephemeral=True)
            return

        members.append(user_id)
        await self.bot.services.clan_data.update_clan(clan)
        await interaction.response.send_message(
            f"Successfully joined clan {clan_name}",
            ephemeral=True,
        )

    @app_commands.command(name="clan", description="Show your current clan")
    async def clan(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        clan = await self.bot.services.clan_data.get_clan_by_member(user_id)
        if not clan:
            await interaction.response.send_message(
                "You are not currently in a clan. Use `/clan_list` to see available clans.",
                ephemeral=True,
            )
            return

        color = get_rarity_color(clan.get("rarity", ""))
        embed = create_clan_embed(
            clan.get("name", ""),
            clan.get("description", ""),
            rarity=clan.get("rarity"),
            members=clan.get("members"),
        )
        embed.color = color
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClanCommands(bot))


__all__ = [
    "ClanCommands",
    "RarityTier",
    "get_rarity_color",
]
