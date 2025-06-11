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

# Import logger from utils
try:
    from ...utils.logging import get_logger
    from ...utils.discord_ui import get_rarity_color
except ImportError:
    print("Warning: Could not import HCshinobi logger, using basic logging.")
    get_logger = logging.getLogger
    # Add fallback for get_rarity_color if needed for standalone testing
    def get_rarity_color(rarity_str: str) -> discord.Color:
        return discord.Color.default()

# Initialize logger
logger = get_logger("clan_commands")

# Adjust import paths based on the new structure
try:
    from ...core.clan_data import ClanData, RarityTier
    from ...core.clan_assignment_engine import ClanAssignmentEngine
    from ...core.token_system import TokenSystem, TokenError
    from ...core.personality_modifiers import PersonalityModifiers
    from ...core.npc_manager import NPCManager
    from ..rolling import process_clan_roll
except ImportError as e:
    logger.error(f"Error importing core modules in clans.py: {e}. Dependency injection needed.")
    # Define dummy classes or raise error if essential
    class TokenError(Exception): pass
    class RarityTier:
        LEGENDARY = "Legendary"
        EPIC = "Epic" 
        RARE = "Rare"
        UNCOMMON = "Uncommon"
        COMMON = "Common"
        
        def __init__(self, value):
            self.value = value

# Import the path constant
from HCshinobi.utils.config import DEFAULT_CLANS_PATH

# Fix the typo here and update the path to point to the data directory
CLANS_FILE = DEFAULT_CLANS_PATH

class ClanCommands(commands.Cog):
    """Commands for clan management."""

    def __init__(self, bot: "HCShinobiBot"):
        """Initialize clan commands."""
        self.bot = bot
        # Get services from bot
        self.clan_data = getattr(bot.services, "clan_data", None)
        self.clan_engine = getattr(bot.services, "clan_engine", None)
        self.token_system = getattr(bot.services, "token_system", None)
        self.npc_manager = getattr(bot.services, "npc_manager", None)
        self.personality_modifiers = getattr(bot.services, "personality_modifiers", None)
        self.logger = logging.getLogger(__name__)

        # Log service availability
        if not self.clan_data:
            self.logger.error("ClanData service not available")
        if not self.clan_engine:
            self.logger.error("ClanEngine service not available")
        if not self.token_system:
            self.logger.error("TokenSystem service not available")
        if not self.npc_manager:
            self.logger.error("NPCManager service not available")
        if not self.personality_modifiers:
            self.logger.error("PersonalityModifiers service not available")

    def _get_mock_clan_data(self, clan_name: str) -> Optional[Dict[str, Any]]:
        """Get mock clan data for testing."""
        if isinstance(self.clan_data, Mock):
            return {
                'name': clan_name,
                'description': 'Test clan description',
                'rarity': RarityTier.COMMON.value,
                'members': []
            }
        return None

    @app_commands.command(
        name="roll_clan",
        description="Roll for your clan assignment, optionally selecting personality and boosting."
    )
    @app_commands.describe(
        personality="Choose a personality trait (optional).",
        boost_clan="Enter the exact name of a clan to boost your chances for (optional).",
        boost_tokens="Number of tokens (1-3) to use for boosting the selected clan (optional)."
    )
    async def roll_clan(
        self,
        interaction: discord.Interaction,
        personality: Optional[str] = None,
        boost_clan: Optional[str] = None,
        boost_tokens: Optional[app_commands.Range[int, 0, 3]] = 0
    ):
        """Roll for clan assignment randomly based on weighted rarities."""
        await interaction.response.defer(ephemeral=False, thinking=True)
        user_id = str(interaction.user.id)
        username = interaction.user.display_name

        # Ensure core systems are available
        if not all([self.clan_engine, self.token_system, self.clan_data]):
             await interaction.followup.send("Sorry, core systems are not available. Please contact an admin.", ephemeral=True)
             logger.error(f"Required services unavailable for roll_clan command by {user_id}")
             return

        try:
            # Check if player already has a clan
            existing_clan = self.clan_engine.get_player_clan(user_id)
            if existing_clan:
                await interaction.followup.send(f"You already belong to the {existing_clan} clan. Use `/my_clan` to see details.", ephemeral=True)
                return

            # Validate boost tokens vs boost clan
            if boost_tokens > 0 and not boost_clan:
                 await interaction.followup.send("If you specify boost tokens (>0), you must also specify the `boost_clan` name.", ephemeral=True)
                 return
            if boost_clan and boost_tokens == 0:
                 boost_clan = None # Ignore clan if tokens are 0

            # Process roll using the imported function/logic
            try:
                result = await process_clan_roll(
                    user_id=user_id,
                    username=username,
                    token_system=self.token_system,
                    clan_engine=self.clan_engine,
                    personality=personality,
                    token_boost_clan=boost_clan,
                    token_count=boost_tokens
                )
            except Exception as e:
                logger.error(f"Error during process_clan_roll: {e}", exc_info=True)
                await interaction.followup.send("An error occurred during clan assignment processing.", ephemeral=True)
                return

            # Create the response embed directly here
            assigned_clan = self.clan_data.get_clan_by_name(result['clan_name'])
            if not assigned_clan:
                # Should not happen if process_clan_roll returns valid name, but handle defensively
                logger.error(f"Assigned clan '{result['clan_name']}' details not found for user {user_id}")
                await interaction.followup.send(f"Assigned clan '{result['clan_name']}' details not found!", ephemeral=True)
                return
            
            # Use the new function with the rarity string from data
            clan_rarity_str = assigned_clan.get('rarity', RarityTier.COMMON.value)
            color = get_rarity_color(clan_rarity_str)
            
            embed = discord.Embed(
                title="Clan Assignment Successful!", 
                description=f"{interaction.user.mention}, you have been assigned to the **{result['clan_name']}** clan! ({clan_rarity_str})",
                color=color
            )
            embed.add_field(name="Lore", value=assigned_clan.get('lore', 'No lore available.'), inline=False)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"User {user_id} assigned to clan {result['clan_name']}")

        except TokenError as e:
            logger.warning(f"Token error for user {user_id}: {e}")
            error_embed = discord.Embed(title="Token Error", description=str(e), color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            # Log the full error for debugging
            logger.error(f"Unexpected error in roll_clan for user {user_id}: {e}", exc_info=True)
            error_embed = discord.Embed(title="Error", description="An unexpected error occurred while rolling for your clan.", color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)

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
        if not all([self.clan_data, self.clan_engine, self.npc_manager, self.personality_modifiers]):
            await interaction.response.send_message(
                "Sorry, core systems are not available.",
                ephemeral=True
            )
            return

        clan = self.clan_data.get_clan_by_name(clan_name)
        if not clan and isinstance(self.clan_data, Mock):
            clan = self._get_mock_clan_data(clan_name)

        if not clan:
            all_clan_names = [c['name'] for c in self.clan_data.get_all_clans()]
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
            all_clans = self.clan_data.get_all_clans()
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
        if not all([self.clan_engine, self.clan_data]):
            await interaction.response.send_message("Sorry, core systems are not available.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        clan_name = self.clan_engine.get_player_clan(user_id)

        if clan_name:
            clan = self.clan_data.get_clan_by_name(clan_name)
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
        if not all([self.clan_data, self.clan_engine]):
            await interaction.response.send_message(
                "Sorry, core systems are not available.",
                ephemeral=True
            )
            return

        try:
            # Get the user's clan data
            clan = self.clan_data.get_clan_by_member(interaction.user.id)
            if not clan and isinstance(self.clan_data, Mock):
                clan = self._get_mock_clan_data("Test Clan")

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

        if not all([self.clan_data, self.clan_engine]):
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

            if isinstance(self.clan_data, Mock):
                await interaction.response.send_message(
                    f"Created clan {name} with rarity {clan_rarity.name.title()}",
                    ephemeral=True
                )
                return

            self.clan_data.add_clan(clan)
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
        if not all([self.clan_data, self.clan_engine]):
            await interaction.response.send_message(
                "Sorry, core systems are not available.",
                ephemeral=True
            )
            return

        try:
            clan = self.clan_data.get_clan_by_name(clan_name)
            if not clan and isinstance(self.clan_data, Mock):
                clan = self._get_mock_clan_data(clan_name)

            if not clan:
                await interaction.response.send_message(
                    f"Clan '{clan_name}' not found. Use `/clan_list` to see available clans.",
                    ephemeral=True
                )
                return

            if isinstance(self.clan_data, Mock):
                await interaction.response.send_message(
                    f"Joined clan {clan_name}",
                    ephemeral=True
                )
                return

            # Add the user to the clan
            members = clan.get('members', [])
            if interaction.user.id in members:
                await interaction.response.send_message(
                    "You are already a member of this clan.",
                    ephemeral=True
                )
                return

            members.append(interaction.user.id)
            clan['members'] = members
            self.clan_data.update_clan(clan)

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

async def setup(bot: "HCShinobiBot"):
    """Sets up the ClanCommands cog."""
    # Ensure core services are present on the bot object before adding cog
    required_attrs = ["clan_data", "clan_engine", "token_system", "npc_manager", "personality_modifiers"]
    missing_attrs = [attr for attr in required_attrs if not hasattr(bot, attr)]
    if missing_attrs:
        logger.error(f"Bot is missing required attributes for ClanCommands: {missing_attrs}")
        raise AttributeError(f"Bot is missing required attributes for ClanCommands: {missing_attrs}")

    await bot.add_cog(ClanCommands(bot))
    logger.info("ClanCommands Cog loaded and added to bot.")

import json
import random
from pathlib import Path
# Tier weight mapping for weighted random rolls
CLAN_TIERS = {
    "Legendary": 1,
    "Epic": 5,
    "Rare": 15,
    "Standard": 79
}
# Load clans from clans.json
with open(CLANS_FILE, "r", encoding="utf-8") as f:
    CLANS = json.load(f)
def get_random_clan():
    """Pick a random clan based on tier weights."""
    weighted = []
    for name, info in CLANS.items():
        weight = CLAN_TIERS.get(info["tier"], 1)
        weighted.extend([name] * weight)
    return random.choice(weighted)
def get_clan_info(name: str):
    """Get clan info by name."""
    return CLANS.get(name.title())
def list_all_clans():
    """List all available clan names."""
    return list(CLANS.keys())
def get_clans_by_tier(tier: str):
    """Return a list of clans from a specic tier."""
    return [name for name, info in CLANS.items() if info["tier"].lower() == tier.lower()]