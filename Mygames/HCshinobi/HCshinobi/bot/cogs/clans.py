"""
Discord Cog for Clan-related commands.
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import os
import random
import logging
import asyncio
from collections import defaultdict
from unittest.mock import Mock
from enum import Enum

# Import logger from utils
from HCshinobi.utils.logging import get_logger
from HCshinobi.utils.discord_ui import get_rarity_color

# Initialize logger
logger = get_logger("clan_commands")

# Adjust import paths based on the new structure
try:
    from HCshinobi.core.clan_data import ClanData, RarityTier
    from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
    from HCshinobi.core.token_system import TokenSystem, TokenError
    from HCshinobi.core.personality_modifiers import PersonalityModifiers
    from HCshinobi.core.npc_manager import NPCManager
    from HCshinobi.bot.rolling import process_clan_roll
except ImportError as e:
    logger.error(f"Error importing core modules needed by ClanCommands: {e}. Cog will not load.")
    # Re-raise the error to prevent the cog from loading with missing dependencies
    raise e

# Import the path constant
from HCshinobi.utils.config import DEFAULT_CLANS_PATH

# Fix the typo here and update the path to point to the data directory
CLANS_FILE = DEFAULT_CLANS_PATH

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

class ClanCommands(commands.Cog):
    """Commands for clan management."""

    def __init__(self, bot: "HCBot"):
        """Initialize clan commands."""
        self.bot = bot
        # Get services from bot
        self.clan_data = getattr(bot.services, "clan_data", None)
        self.clan_assignment_engine = getattr(bot.services, "clan_assignment_engine", None)
        self.token_system = getattr(bot.services, "token_system", None)
        self.npc_manager = getattr(bot.services, "npc_manager", None)
        self.personality_modifiers = getattr(bot.services, "personality_modifiers", None)
        self.logger = logging.getLogger(__name__)

        # Log service availability
        if not self.clan_data:
            self.logger.error("ClanData service not available")
        if not self.clan_assignment_engine:
            self.logger.error("ClanAssignmentEngine service not available")
        if not self.token_system:
            self.logger.error("TokenSystem service not available")
        if not self.npc_manager:
            self.logger.error("NPCManager service not available")
        if not self.personality_modifiers:
            self.logger.error("PersonalityModifiers service not available")

    @app_commands.command(
        name="clan_info",
        description="View information about a clan"
    )
    @app_commands.describe(clan_name="The name of the clan to view")
    async def clan_info(
        self,
        interaction: discord.Interaction,
        clan_name: str
    ):
        """Display information about a specific clan."""
        if not all([self.clan_data, self.clan_assignment_engine, self.npc_manager, self.personality_modifiers]):
            await interaction.response.send_message(
                "Sorry, core systems are not available.",
                ephemeral=True
            )
            return

        clan = await self.clan_data.get_clan_by_name(clan_name)
        if not clan:
            all_clan_data = await self.clan_data.get_all_clans()
            all_clan_names = [c['name'] for c in all_clan_data]
            # Basic suggestion logic (can be improved with fuzzy matching)
            similar_clans = [c for c in all_clan_names if clan_name.lower() in c.lower()]
            if similar_clans:
                suggestions = "\n".join(similar_clans[:5]) # Limit suggestions
                await interaction.response.send_message(
                    f"Clan '{clan_name}' not found. Did you mean one of these?\n{suggestions}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Clan '{clan_name}' not found. Use `/clan_list` to see available clans.",
                    ephemeral=True
                )
            return

        # Use the new function with the rarity string from data
        clan_rarity_str = clan.get('rarity', RarityTier.COMMON.value)
        color = get_rarity_color(clan_rarity_str)
        
        embed = discord.Embed(
            title=f"{clan['name']} Clan",
            description=clan['description'],
            color=color
        )
        embed.add_field(name="Rarity", value=clan_rarity_str, inline=True)
        embed.add_field(name="Members", value=str(len(clan.get('members', []))), inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="clan_list",
        description="List all clans and their rarity"
    )
    async def clan_list(
        self,
        interaction: discord.Interaction
    ):
        """List all clans grouped by rarity tier."""
        if not self.clan_data:
            await interaction.response.send_message(
                "Sorry, clan data system is not available.",
                ephemeral=True
            )
            self.logger.warning("clan_list command used but clan_data service is missing.")
            return

        embed = discord.Embed(
            title="Available Clans",
            description="List of all clans by rarity.",
            color=discord.Color.blurple()
        )

        try:
            all_clans = await self.clan_data.get_all_clans()
            if not all_clans:
                embed.description = "No clans have been loaded into the system."
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            clans_by_rarity = defaultdict(list)
            for clan in all_clans:
                rarity = clan.get('rarity', RarityTier.COMMON.value)
                clans_by_rarity[rarity].append(clan.get('name', 'Unnamed Clan'))

            rarity_order = [
                RarityTier.LEGENDARY.value,
                RarityTier.EPIC.value,
                RarityTier.RARE.value,
                RarityTier.UNCOMMON.value,
                RarityTier.COMMON.value
            ]
            
            found_any_clans = False
            for rarity_value in rarity_order:
                if rarity_value in clans_by_rarity:
                    clan_names = clans_by_rarity[rarity_value]
                    clan_names.sort()
                    clan_list_str = "\n".join([f"- {name}" for name in clan_names])
                    
                    embed.add_field(
                        name=f"🏅 {rarity_value}",
                        value=clan_list_str,
                        inline=False
                    )
                    found_any_clans = True
            
            if not found_any_clans:
                embed.description = "No clans found, although the clan data system is loaded. Check clan data file."

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in clan_list command: {e}", exc_info=True)
            await interaction.response.send_message(
                "An error occurred while fetching clan data. Please try again later.",
                ephemeral=True
            )

    @app_commands.command(
        name="my_clan",
        description="Check your current clan assignment"
    )
    async def my_clan(self, interaction: discord.Interaction):
        """Display the user's current clan assignment."""
        if not all([self.clan_assignment_engine, self.clan_data]):
            await interaction.response.send_message("Sorry, core systems are not available.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        clan_name = self.clan_assignment_engine.get_player_clan(user_id)

        if clan_name:
            clan = await self.clan_data.get_clan_by_name(clan_name)
            if clan:
                rarity = RarityTier(clan['rarity'])
                embed = discord.Embed(
                    title="Your Clan Assignment",
                    description=f"You belong to the **{clan_name}** clan.",
                    color=get_rarity_color(rarity.value)
                )
                embed.add_field(name="Rarity", value=rarity.value, inline=True)
                # Optionally add more info like join date if tracked
            else: # Should not happen if engine returns a valid clan name
                 logger.error(f"Invalid clan name '{clan_name}' returned for user {user_id}")
                 embed = discord.Embed(title="Error", description=f"Could not find data for your assigned clan '{clan_name}'.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("You have not been assigned a clan yet. Use `/roll_clan` to get started!", ephemeral=True)
            logger.debug(f"User {user_id} has no clan assignment")

    @app_commands.command(
        name="clan",
        description="View clan information"
    )
    async def clan(self, interaction: discord.Interaction):
        """Display information about your clan."""
        if not all([self.clan_data, self.clan_assignment_engine]):
            await interaction.response.send_message(
                "Sorry, core systems are not available.",
                ephemeral=True
            )
            return

        try:
            # Get the user's clan data
            clan = await self.clan_data.get_clan_by_member(interaction.user.id)
            if not clan:
                await interaction.response.send_message(
                    "You are not currently in a clan. Use `/clan_list` to see available clans.",
                    ephemeral=True
                )
                return

            # Create an embed with clan information
            clan_rarity = RarityTier(clan['rarity'])
            embed = discord.Embed(
                title=f"{clan['name']} Clan",
                description=clan['description'],
                color=get_rarity_color(clan_rarity.value)
            )
            embed.add_field(name="Rarity", value=clan_rarity.name.title(), inline=True)
            embed.add_field(name="Members", value=str(len(clan.get('members', []))), inline=True)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error retrieving clan information: {e}")
            await interaction.response.send_message(
                f"An error occurred while retrieving clan information: {e}",
                ephemeral=True
            )

    @app_commands.command(
        name="create_clan",
        description="Create a new clan"
    )
    @app_commands.describe(
        name="The name of the clan",
        description="A description of the clan",
        rarity="The rarity tier of the clan"
    )
    @app_commands.choices(rarity=[
        app_commands.Choice(name=tier.name.title(), value=tier.value) for tier in RarityTier
    ])
    async def create_clan(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str,
        rarity: str
    ):
        """Create a new clan."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to create clans.",
                ephemeral=True
            )
            return

        if not all([self.clan_data, self.clan_assignment_engine]):
            await interaction.response.send_message(
                "Sorry, core systems are not available.",
                ephemeral=True
            )
            return

        try:
            clan_rarity = RarityTier(rarity)
            clan = {
                'name': name,
                'description': description,
                'rarity': clan_rarity.value,
                'members': []
            }

            # DEBUG: print(f"DEBUG: Attempting to add clan: {clan}") # Removed debug print
            await self.clan_data.add_clan(clan)
            await interaction.response.send_message(
                f"Successfully created clan {name} with rarity {clan_rarity.name.title()}",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Error creating clan: {e}")
            await interaction.response.send_message(
                f"An error occurred while creating the clan: {e}",
                ephemeral=True
            )

    @app_commands.command(
        name="join_clan",
        description="Join a clan"
    )
    @app_commands.describe(clan_name="The name of the clan to join")
    async def join_clan(
        self,
        interaction: discord.Interaction,
        clan_name: str
    ):
        """Join a clan."""
        if not all([self.clan_data, self.clan_assignment_engine]):
            await interaction.response.send_message(
                "Sorry, core systems are not available.",
                ephemeral=True
            )
            return

        try:
            clan = await self.clan_data.get_clan_by_name(clan_name)
            if not clan:
                await interaction.response.send_message(
                    f"Clan '{clan_name}' not found. Use `/clan_list` to see available clans.",
                    ephemeral=True
                )
                return

            # Add the user to the clan
            members = clan.get('members', [])
            user_id_str = str(interaction.user.id)
            if user_id_str in members:
                await interaction.response.send_message(
                    "You are already a member of this clan.",
                    ephemeral=True
                )
                return

            members.append(user_id_str)
            clan['members'] = members
            print(f"DEBUG [join_clan]: About to update clan: {clan}")
            await self.clan_data.update_clan(clan)

            await interaction.response.send_message(
                f"Successfully joined clan {clan_name}",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"Error joining clan: {e}")
            await interaction.response.send_message(
                f"An error occurred while joining the clan: {e}",
                ephemeral=True
            )

async def setup(bot: "HCBot"):
    """Sets up the ClanCommands cog."""
    # Ensure core services are present on the bot.services container before adding cog
    required_attrs = ["clan_data", "clan_assignment_engine", "token_system", "npc_manager", "personality_modifiers"]
    missing_attrs = [attr for attr in required_attrs if not hasattr(bot.services, attr)] # Check bot.services
    if missing_attrs:
        logger.error(f"Bot.services is missing required attributes for ClanCommands: {missing_attrs}")
        # Raise an error to prevent loading the cog if dependencies are missing
        raise AttributeError(f"Bot.services is missing required attributes for ClanCommands: {missing_attrs}")

    # Initialize and add the cog if all services are present
    await bot.add_cog(ClanCommands(bot))
    logger.info("ClanCommands Cog loaded and added to bot.")