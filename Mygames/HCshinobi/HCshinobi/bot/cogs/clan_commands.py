import discord
from discord import app_commands
from discord.ext import commands
import logging
from HCshinobi.utils.embed_utils import get_rarity_color
from HCshinobi.core.constants import RarityTier # Import necessary constants/types
from HCshinobi.core.character import Character
from typing import Optional, TYPE_CHECKING

# Assume systems/models are correctly typed/imported
# from HCshinobi.core.clan_system import ClanSystem
# from HCshinobi.core.character_system import CharacterSystem
# from HCshinobi.models.character import Character 
# from HCshinobi.bot.bot import HCShinobiBot

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

logger = logging.getLogger(__name__)

class ClanCommands(commands.Cog):
    """Cog for handling clan-related commands."""

    def __init__(self, bot: "HCBot", clan_system, character_system):
        self.bot = bot
        self.clan_system = clan_system
        self.character_system = character_system
        logger.info("ClanCommands Cog initialized.")

    async def _check_character(self, interaction: discord.Interaction) -> 'Character | None':
        """Helper to check if user has a character."""
        character = await self.character_system.get_character(str(interaction.user.id))
        if not character:
            await interaction.response.send_message("You need to create a character first using `/create`.", ephemeral=True)
            return None
        return character

    @app_commands.command(name="clan", description="View your clan information or another clan's info.")
    @app_commands.describe(name="(Optional) The name of the clan to view.")
    async def view_clan(self, interaction: discord.Interaction, name: str = None):
        """Displays information about the user's clan or a specified clan."""
        target_clan_name = name
        
        if not target_clan_name:
            # If no name provided, view own clan
            character = await self._check_character(interaction)
            if not character:
                return # Error sent by helper
            
            if not character.clan:
                await interaction.response.send_message("You are not currently in a clan.", ephemeral=True)
                return
            target_clan_name = character.clan

        # Fetch clan info and display using the helper method
        await self._display_clan_info(interaction, target_clan_name)

    async def _display_clan_info(self, interaction: discord.Interaction, clan_name: str):
        """Helper method to fetch and display clan information."""
        # Ensure services are available
        if not self.clan_system:
            await interaction.response.send_message("Clan system is unavailable.", ephemeral=True)
            return
            
        clan_info = await self.clan_system.get_clan_info(clan_name)

        if not clan_info:
            await interaction.response.send_message(f"❌ Clan '{clan_name}' not found.", ephemeral=True)
            return

        # Build embed
        # Use get_rarity_color if available, otherwise default
        try:
            color = get_rarity_color(clan_info.get('rarity', RarityTier.COMMON.value))
        except NameError:
            color = discord.Color.blue()
            
        embed = discord.Embed(
            title=f"⚜️ Clan: {clan_info.get('name', 'Unknown Clan')}",
            description=clan_info.get('description', 'No description available.'),
            color=color
        )
        embed.add_field(name="👥 Members", value=str(len(clan_info.get('members', []))), inline=True)
        embed.add_field(name="✨ Rarity", value=clan_info.get('rarity', 'Unknown'), inline=True)
        embed.add_field(name="🎌 Village", value=clan_info.get('village', 'Unknown'), inline=True)
        embed.add_field(name="🛡️ Power", value=f"{clan_info.get('power', 0):,}", inline=True)
        # Add more fields like leader, level, perks etc. if available in clan_info

        # Check response state before sending
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed)
        else:
            # If already responded (e.g., from defer), use followup
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="clan_info", description="View information about a specific clan.")
    @app_commands.describe(name="The name of the clan to view.")
    async def clan_info(self, interaction: discord.Interaction, name: str):
        """Displays detailed information about a specific clan."""
        # Call the helper method directly
        await self._display_clan_info(interaction, name)

    @app_commands.command(name="clan_list", description="List all available clans.")
    async def list_clans(self, interaction: discord.Interaction):
        """Lists all clans with basic information."""
        clans = await self.clan_system.list_clans()

        if not clans:
            await interaction.response.send_message("There are no clans formed yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📜 Clan List",
            description="List of known clans in the village.",
            color=discord.Color.gold()
        )

        for clan in clans[:25]: # Limit to 25 fields
            embed.add_field(
                name=clan.get('name', 'Unknown Clan'),
                value=f"Members: {clan.get('member_count', '?')}\nRarity: {clan.get('rarity', '?')}",
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="my_clan", description="Check your current clan assignment")
    async def my_clan(self, interaction: discord.Interaction):
        """Check your current clan assignment."""
        character = await self._check_character(interaction)
        if not character:
            return

        if not character.clan:
            await interaction.response.send_message("You are not currently in a clan.", ephemeral=True)
            return

        await self._display_clan_info(interaction, character.clan)

    @app_commands.command(name="create_clan", description="Create a new clan")
    async def create_clan(self, interaction: discord.Interaction):
        """Create a new clan."""
        # Implementation of create_clan command
        await interaction.response.send_message("This command is not implemented yet.")

    @app_commands.command(name="join_clan", description="Join a clan")
    async def join_clan(self, interaction: discord.Interaction):
        """Join a clan."""
        # Implementation of join_clan command
        await interaction.response.send_message("This command is not implemented yet.")

    @app_commands.command(name="leave_clan", description="Leave your current clan")
    async def leave_clan(self, interaction: discord.Interaction):
        """Leave your current clan."""
        character = await self._check_character(interaction)
        if not character:
            return

        if not self.clan_system:
            await interaction.response.send_message("Clan system is unavailable.", ephemeral=True)
            return

        # Try to leave clan
        success, message = await self.clan_system.leave_clan(character)
        
        if not success:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        embed = discord.Embed(
            title="👋 Clan Left",
            description=message,
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='clan_leaderboard', description="View the clan rankings by power")
    async def clan_leaderboard(self, interaction: discord.Interaction):
        """View the clan rankings."""
        if not self.clan_system:
            await interaction.response.send_message("Clan system is unavailable.", ephemeral=True)
            return
            
        try:
            # Assuming get_clan_rankings exists and returns sorted list of clan dicts
            rankings = await self.clan_system.get_clan_rankings()
            if not rankings:
                await interaction.response.send_message("No clan ranking data available.", ephemeral=True)
                return

            embed = discord.Embed(
                title="🏆 Clan Leaderboard (Top 10 by Power)",
                color=discord.Color.gold()
            )

            for i, clan in enumerate(rankings[:10], 1):
                value = (
                    f"Power: {clan.get('power', 0):,}\n"
                    f"Members: {len(clan.get('members', []))}\n"
                    f"Village: {clan.get('village', 'Unknown')}"
                )
                embed.add_field(
                    name=f"#{i}. {clan.get('name', 'Unknown Clan')}",
                    value=value,
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            self.logger.error(f"Error displaying clan leaderboard: {e}", exc_info=True)
            await interaction.response.send_message("An error occurred while retrieving clan rankings.", ephemeral=True)

    @app_commands.command(name='clan_members', description="View members of a specified clan or your own")
    @app_commands.describe(clan_name="(Optional) Name of the clan to view members for.")
    async def clan_members(self, interaction: discord.Interaction, clan_name: Optional[str] = None):
        """View members of a clan."""
        target_clan_name = clan_name
        
        if not target_clan_name:
            character = await self._check_character(interaction)
            if not character:
                 return # Error sent by helper
            if not character.clan:
                await interaction.response.send_message("You are not in a clan.", ephemeral=True)
                return
            target_clan_name = character.clan
            
        if not self.clan_system or not self.character_system:
            await interaction.response.send_message("Clan or Character system is unavailable.", ephemeral=True)
            return

        try:
            clan_info = await self.clan_system.get_clan_info(target_clan_name)
            if not clan_info:
                await interaction.response.send_message(f"❌ Clan '{target_clan_name}' not found.", ephemeral=True)
                return

            member_ids = clan_info.get('members', [])
            if not member_ids:
                await interaction.response.send_message(f"Clan '{target_clan_name}' has no members listed.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"👥 Members of {target_clan_name}",
                color=discord.Color.blue()
            )
            
            member_details = []
            for member_id in member_ids:
                # Fetch character name (could be slow for large clans)
                member_char = await self.character_system.get_character(str(member_id))
                name = member_char.name if member_char else f"ID: {member_id}"
                # Fetch Discord user name (even slower)
                # discord_user = await self.bot.fetch_user(int(member_id))
                # display_name = discord_user.display_name if discord_user else "Unknown User"
                member_details.append(f"- {name}")
            
            # Paginate if too many members
            # For now, just join, but Discord has embed field limits
            members_str = "\n".join(member_details)
            if len(members_str) > 1020:
                members_str = members_str[:1020] + "... (list truncated)"
                
            embed.description = members_str
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            self.logger.error(f"Error displaying clan members for '{target_clan_name}': {e}", exc_info=True)
            await interaction.response.send_message("An error occurred while retrieving clan members.", ephemeral=True)

async def setup(bot: "HCBot"):
    if not hasattr(bot, 'services'):
        logger.error("Service container not found on bot object.")
        return
        
    clan_system = getattr(bot.services, 'clan_system', None)
    character_system = getattr(bot.services, 'character_system', None)

    if not clan_system or not character_system:
        logger.error("Required systems (ClanSystem, CharacterSystem) not found in services for ClanCommands.")
        return
        
    await bot.add_cog(ClanCommands(bot, clan_system, character_system))
    logger.info("ClanCommands Cog loaded successfully.") 