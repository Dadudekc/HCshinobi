import discord
from discord import app_commands
from discord.ext import commands
import logging
from HCshinobi.utils.embed_utils import get_rarity_color
from HCshinobi.core.constants import RarityTier # Import necessary constants/types
from HCshinobi.core.character import Character
from HCshinobi.core.clan_missions import ClanMissions
from HCshinobi.core.clan_system import ClanSystem
from typing import Optional, TYPE_CHECKING
from datetime import datetime

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

class ClanMissionCommands(commands.Cog):
    def __init__(self, bot: "HCBot", clan_missions: ClanMissions, clan_system: ClanSystem):
        """Initialize clan mission commands.
        
        Args:
            bot: The bot instance
            clan_missions: The clan missions system instance
            clan_system: The clan system instance
        """
        self.bot = bot
        self.clan_missions = clan_missions
        self.clan_system = clan_system
        self.logger = logging.getLogger(__name__)
        
        # Register slash commands
        self.register_app_commands()

    def register_app_commands(self):
        """Register application commands for slash command support."""
        # Remove all existing commands with these names to avoid conflicts
        to_remove = []
        for cmd in self.bot.tree.get_commands():
            if cmd.name in ["clan_missions", "complete_mission", "refresh_missions"]:
                to_remove.append(cmd)
        
        for cmd in to_remove:
            self.bot.tree.remove_command(cmd.name)
            
        # Clan missions slash command
        @self.bot.tree.command(name="clan_missions", description="View your clan missions")
        async def clan_missions_cmd(interaction: discord.Interaction):
            await self.clan_missions_slash(interaction)
        
        # Complete mission slash command
        @self.bot.tree.command(name="complete_mission", description="Complete a clan mission")
        async def complete_mission_cmd(interaction: discord.Interaction, mission_number: int):
            await self.complete_mission_slash(interaction, mission_number)
        
        # Refresh missions slash command
        @self.bot.tree.command(name="refresh_missions", description="Get new clan missions (costs 500 Ryō)")
        async def refresh_missions_cmd(interaction: discord.Interaction):
            await self.refresh_missions_slash(interaction)
            
        self.logger.info("Clan mission slash commands registered")

    async def clan_missions_slash(self, interaction: discord.Interaction):
        """View your clan missions with a slash command.
        
        Args:
            interaction: The interaction object
        """
        try:
            player_id = str(interaction.user.id)
            
            # Get player's clan
            character = self.bot.character_system.get_character(player_id)
            if not character:
                await interaction.response.send_message(
                    "❌ You need to create a character first! Use `/create` to get started.",
                    ephemeral=True
                )
                return
                
            player_clan = character.clan if hasattr(character, 'clan') else None
            if not player_clan:
                await interaction.response.send_message(
                    "❌ You haven't been assigned to a clan yet! Use `/assign_clan` first.",
                    ephemeral=True
                )
                return
            
            # Get clan info
            clan_info = self.clan_system.CLANS.get(player_clan, {})
            clan_rarity = clan_info.get("rarity", "common")
            
            # Get active missions
            missions = self.clan_missions.get_player_missions(player_id)
            
            # Create embed
            embed = discord.Embed(
                title=f"🎯 {player_clan} Clan Missions",
                description=f"Complete missions to earn rewards and honor your clan!",
                color=get_rarity_color(clan_rarity)
            )
            
            if not missions:
                # Assign new missions if none exist
                missions = self.clan_missions.assign_missions(player_id, player_clan)
                embed.description += "\n\nNew missions have been assigned!"
            
            # Add mission information
            for i, mission in enumerate(missions):
                status = "✅" if mission["completed"] else "⏳"
                embed.add_field(
                    name=f"{status} {mission['name']}",
                    value=f"{mission['description']}\n"
                          f"Reward: **{mission['reward']:,}** Ryō\n"
                          f"Duration: {mission['duration'].title()}\n"
                          f"Use `/complete_mission {i+1}` to complete",
                    inline=False
                )
            
            # Add next refresh time
            next_refresh = self.clan_missions.get_next_refresh_time(player_id)
            if next_refresh:
                time_left = next_refresh - datetime.now()
                hours = int(time_left.total_seconds() / 3600)
                minutes = int((time_left.total_seconds() % 3600) / 60)
                embed.set_footer(text=f"New missions in {hours}h {minutes}m")
            
            await interaction.response.send_message(embed=embed)
            
        except discord.errors.NotFound:
            self.logger.warning(f"Interaction not found for clan_missions_slash command")
        except discord.errors.InteractionResponded:
            self.logger.warning(f"Interaction already responded for clan_missions_slash command")
        except Exception as e:
            self.logger.error(f"Error in clan_missions_slash command: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "❌ An unexpected error occurred. Please try again later.",
                    ephemeral=True
                )
            except:
                pass

    async def complete_mission_slash(self, interaction: discord.Interaction, mission_number: int):
        """Complete a clan mission with a slash command.
        
        Args:
            interaction: The interaction object
            mission_number: The number of the mission to complete (1-based)
        """
        try:
            player_id = str(interaction.user.id)
            
            # Adjust to 0-based index
            mission_index = mission_number - 1
            
            # Get player's clan
            character = self.bot.character_system.get_character(player_id)
            if not character:
                await interaction.response.send_message(
                    "❌ You need to create a character first! Use `/create` to get started.",
                    ephemeral=True
                )
                return
                
            player_clan = character.clan if hasattr(character, 'clan') else None
            if not player_clan:
                await interaction.response.send_message(
                    "❌ You haven't been assigned to a clan yet! Use `/assign_clan` first.",
                    ephemeral=True
                )
                return
            
            # Get clan info
            clan_info = self.clan_system.CLANS.get(player_clan, {})
            clan_rarity = clan_info.get("rarity", "common")
            
            # Complete the mission
            result = self.clan_missions.complete_mission(player_id, mission_index)
            
            if not result or not result.get("success", False):
                error_msg = result.get("message", "Invalid mission index or mission already completed!") if result else "Invalid mission index or mission already completed!"
                await interaction.response.send_message(
                    f"❌ {error_msg}",
                    ephemeral=True
                )
                return
            
            # Calculate reward
            mission = result.get("mission", {})
            reward = mission.get("reward", 0)
            
            # Apply clan bonus
            clan_bonus = clan_info.get("currency_bonus", 0)
            if clan_bonus > 0:
                bonus_amount = int(reward * (clan_bonus / 100))
                reward += bonus_amount
            
            # Update player balance
            current_balance = self.bot.currency_system.get_player_balance(player_id)
            self.bot.currency_system.set_player_balance(player_id, current_balance + reward)
            
            # Create embed
            embed = discord.Embed(
                title="✅ Mission Complete",
                description=f"You have completed the mission: **{mission.get('name', 'Unknown')}**",
                color=get_rarity_color(clan_rarity)
            )
            
            # Add reward information
            embed.add_field(
                name="💰 Reward",
                value=f"**{reward:,}** Ryō",
                inline=True
            )
            
            if clan_bonus > 0:
                embed.add_field(
                    name="✨ Clan Bonus",
                    value=f"+{clan_bonus}% ({bonus_amount:,} Ryō)",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except discord.errors.NotFound:
            self.logger.warning(f"Interaction not found for complete_mission_slash command")
        except discord.errors.InteractionResponded:
            self.logger.warning(f"Interaction already responded for complete_mission_slash command")
        except Exception as e:
            self.logger.error(f"Error in complete_mission_slash command: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "❌ An unexpected error occurred. Please try again later.",
                    ephemeral=True
                )
            except:
                pass

    async def refresh_missions_slash(self, interaction: discord.Interaction):
        """Refresh clan missions with a slash command.
        
        Args:
            interaction: The interaction object
        """
        try:
            player_id = str(interaction.user.id)
            
            # Get player's clan
            character = self.bot.character_system.get_character(player_id)
            if not character:
                await interaction.response.send_message(
                    "❌ You need to create a character first! Use `/create` to get started.",
                    ephemeral=True
                )
                return
                
            player_clan = character.clan if hasattr(character, 'clan') else None
            if not player_clan:
                await interaction.response.send_message(
                    "❌ You haven't been assigned to a clan yet! Use `/assign_clan` first.",
                    ephemeral=True
                )
                return
            
            # Get clan info
            clan_info = self.clan_system.CLANS.get(player_clan, {})
            clan_rarity = clan_info.get("rarity", "common")
            
            # Check if player can refresh
            can_refresh, message = self.clan_missions.can_refresh_missions(player_id)
            if not can_refresh:
                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True
                )
                return
            
            # Check if player has enough currency
            refresh_cost = 500
            current_balance = self.bot.currency_system.get_player_balance(player_id)
            if current_balance < refresh_cost:
                await interaction.response.send_message(
                    f"❌ You need {refresh_cost:,} Ryō to refresh missions. Your balance: {current_balance:,} Ryō",
                    ephemeral=True
                )
                return
            
            # Deduct cost and refresh missions
            self.bot.currency_system.set_player_balance(player_id, current_balance - refresh_cost)
            new_missions = self.clan_missions.assign_missions(player_id, player_clan)
            
            # Create embed
            embed = discord.Embed(
                title="🔄 Missions Refreshed",
                description="Your clan missions have been refreshed!",
                color=get_rarity_color(clan_rarity)
            )
            
            # Add mission information
            for i, mission in enumerate(new_missions):
                embed.add_field(
                    name=f"🎯 {mission['name']}",
                    value=f"{mission['description']}\n"
                          f"Reward: **{mission['reward']:,}** Ryō\n"
                          f"Duration: {mission['duration'].title()}\n"
                          f"Use `/complete_mission {i+1}` to complete",
                    inline=False
                )
            
            # Add cost information
            embed.set_footer(text=f"Cost: {refresh_cost:,} Ryō")
            
            await interaction.response.send_message(embed=embed)
            
        except discord.errors.NotFound:
            self.logger.warning(f"Interaction not found for refresh_missions_slash command")
        except discord.errors.InteractionResponded:
            self.logger.warning(f"Interaction already responded for refresh_missions_slash command")
        except Exception as e:
            self.logger.error(f"Error in refresh_missions_slash command: {e}", exc_info=True)
            try:
                await interaction.response.send_message(
                    "❌ An unexpected error occurred. Please try again later.",
                    ephemeral=True
                )
            except:
                pass

async def setup(bot: "HCBot"):
    """Set up the clan commands cog."""
    await bot.add_cog(ClanCommands(bot, bot.clan_system, bot.character_system))
    await bot.add_cog(ClanMissionCommands(bot, bot.clan_missions, bot.clan_system))
    logger.info("ClanCommands Cog loaded successfully.") 