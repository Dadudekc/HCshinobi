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

    @app_commands.command(name="roll_clan", description="Roll for a clan assignment (or reroll)")
    async def roll_clan(self, interaction: discord.Interaction, use_tokens: bool = False) -> None:
        """Roll for a clan assignment, optionally using tokens for reroll."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            
            # Check if services are available
            if not hasattr(self.bot, 'services'):
                await interaction.followup.send(
                    "Clan system not available. Please try again later.",
                    ephemeral=True
                )
                return
            
            clan_assignment_engine = self.bot.services.clan_assignment_engine
            
            # Check if user already has a clan assignment
            existing_clan = clan_assignment_engine.get_player_clan(user_id)
            
            if existing_clan and not use_tokens:
                await interaction.followup.send(
                    f"You are already assigned to the **{existing_clan}** clan!\n"
                    f"Use `/roll_clan use_tokens:True` to reroll using tokens, or `/my_clan` to view your current clan.",
                    ephemeral=True
                )
                return
            
            # If rerolling with tokens, check token balance
            if use_tokens and existing_clan:
                if hasattr(self.bot.services, 'token_system'):
                    token_system = self.bot.services.token_system
                    tokens = await token_system.get_player_tokens(user_id)
                    reroll_cost = 5  # Cost to reroll clan
                    
                    if tokens < reroll_cost:
                        await interaction.followup.send(
                            f"You need **{reroll_cost}** tokens to reroll your clan, but you only have **{tokens}** tokens.\n"
                            f"Use `/earn_tokens` to get more tokens.",
                            ephemeral=True
                        )
                        return
                    
                    # Deduct tokens
                    await token_system.spend_tokens(user_id, reroll_cost, "clan_reroll")
                else:
                    await interaction.followup.send(
                        "Token system not available for rerolls.",
                        ephemeral=True
                    )
                    return
            
            # Assign/reassign clan
            clan_result = await clan_assignment_engine.assign_clan(user_id)
            assigned_clan = clan_result.get("assigned_clan", "Civilian")
            clan_rarity = clan_result.get("clan_rarity", "Common")
            
            # Get clan color based on rarity
            color = get_rarity_color(clan_rarity)
            
            # Create response embed
            if existing_clan and use_tokens:
                title = "🎲 Clan Reroll Complete!"
                description = f"Your clan has been rerolled from **{existing_clan}** to **{assigned_clan}**!"
                footer_text = f"Reroll cost: 5 tokens | New clan rarity: {clan_rarity}"
            else:
                title = "🎲 Clan Assignment Complete!"
                description = f"You have been assigned to the **{assigned_clan}** clan!"
                footer_text = f"Clan rarity: {clan_rarity}"
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            
            embed.add_field(name="Your Clan", value=assigned_clan, inline=True)
            embed.add_field(name="Rarity", value=clan_rarity, inline=True)
            
            # Add clan benefits/description if available
            embed.add_field(
                name="🎯 Next Steps",
                value="• Use `/my_clan` to view detailed clan info\n"
                      "• Use `/create` to create your character (if not done)\n"
                      "• Use `/clan_mission_board` for clan-specific missions",
                inline=False
            )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=footer_text)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"Error during clan assignment: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClanCommands(bot))


__all__ = [
    "ClanCommands",
    "RarityTier",
    "get_rarity_color",
]
