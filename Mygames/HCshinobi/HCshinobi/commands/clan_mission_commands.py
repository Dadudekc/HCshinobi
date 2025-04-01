"""Commands for clan missions."""
import discord
from discord.ext import commands
import logging
from datetime import datetime
import asyncio

from HCshinobi.core.clan_missions import ClanMissions
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.utils.embed_utils import get_rarity_color

class ClanMissionCommands(commands.Cog):
    def __init__(self, bot, clan_missions: ClanMissions, clan_system: ClanSystem):
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
            
            embed.add_field(
                name="Mission",
                value=mission.get("description", "No description available."),
                inline=False
            )
            
            embed.add_field(
                name="Base Reward",
                value=f"{mission.get('reward', 0):,} Ryō",
                inline=True
            )
            
            if clan_bonus > 0:
                embed.add_field(
                    name="Clan Bonus",
                    value=f"+{bonus_amount:,} Ryō ({clan_bonus}%)",
                    inline=True
                )
            
            embed.add_field(
                name="Total Reward",
                value=f"**{reward:,}** Ryō",
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
            
            # Check if missions can be refreshed
            next_refresh = self.clan_missions.get_next_refresh_time(player_id)
            if next_refresh and next_refresh > datetime.now():
                time_left = next_refresh - datetime.now()
                hours = int(time_left.total_seconds() / 3600)
                minutes = int((time_left.total_seconds() % 3600) / 60)
                await interaction.response.send_message(
                    f"❌ You must wait {hours}h {minutes}m before refreshing missions!",
                    ephemeral=True
                )
                return
            
            # Check if player has enough currency
            refresh_cost = 500
            current_balance = self.bot.currency_system.get_player_balance(player_id)
            
            if current_balance < refresh_cost:
                await interaction.response.send_message(
                    f"❌ You need at least {refresh_cost} Ryō to refresh missions! You have {current_balance} Ryō.",
                    ephemeral=True
                )
                return
            
            # Deduct cost
            self.bot.currency_system.set_player_balance(player_id, current_balance - refresh_cost)
            
            # Assign new missions
            new_missions = self.clan_missions.refresh_missions(player_id, player_clan)
            
            # Get clan info
            clan_info = self.clan_system.CLANS.get(player_clan, {})
            clan_rarity = clan_info.get("rarity", "common")
            
            # Create embed
            embed = discord.Embed(
                title="🔄 Missions Refreshed",
                description=f"You've spent {refresh_cost} Ryō to get new missions.",
                color=get_rarity_color(clan_rarity)
            )
            
            # Add mission information
            for i, mission in enumerate(new_missions):
                embed.add_field(
                    name=f"{i+1}. {mission['name']}",
                    value=f"{mission['description']}\n"
                          f"Reward: **{mission['reward']:,}** Ryō\n"
                          f"Duration: {mission['duration'].title()}",
                    inline=False
                )
            
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

    async def cog_command_error(self, ctx, error):
        """Handle errors for all commands in this cog."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have permission to do that!")
        else:
            self.logger.error(f"Error in {ctx.command.name}: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="clan_mission_list",
        aliases=["clan_tasks", "mission_list"],
        description="View your clan missions",
        help="Shows all the clan missions you can complete for rewards."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clan_mission_list(self, ctx):
        """View your clan missions.
        
        Args:
            ctx: The command context
        """
        try:
            player_id = str(ctx.author.id)
            
            # Get player's clan
            character = self.bot.character_system.get_character(player_id)
            if not character:
                await ctx.send("❌ You need to create a character first! Use !create to get started.")
                return
                
            player_clan = character.clan if hasattr(character, 'clan') else None
            if not player_clan:
                await ctx.send("❌ You haven't been assigned to a clan yet! Use !join_clan first.")
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
                          f"Use `!finish_clan_mission {i+1}` to complete",
                    inline=False
                )
            
            # Add next refresh time
            next_refresh = self.clan_missions.get_next_refresh_time(player_id)
            if next_refresh:
                time_left = next_refresh - datetime.now()
                hours = int(time_left.total_seconds() / 3600)
                minutes = int((time_left.total_seconds() % 3600) / 60)
                embed.set_footer(text=f"New missions in {hours}h {minutes}m")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in clan_mission_list command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="finish_clan_mission",
        aliases=["complete_clan_mission", "complete_cm"],
        description="Complete a clan mission",
        help="Complete a clan mission by providing its number, e.g., !finish_clan_mission 1"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def finish_clan_mission(self, ctx, mission_index: int):
        """Complete a clan mission.
        
        Args:
            ctx: The command context
            mission_index: The index of the mission to complete (1-based)
        """
        try:
            player_id = str(ctx.author.id)
            
            # Adjust to 0-based index
            mission_index = mission_index - 1
            
            # Get player's clan
            character = self.bot.character_system.get_character(player_id)
            if not character:
                await ctx.send("❌ You need to create a character first! Use !create to get started.")
                return
                
            player_clan = character.clan if hasattr(character, 'clan') else None
            if not player_clan:
                await ctx.send("❌ You haven't been assigned to a clan yet! Use !join_clan first.")
                return
            
            # Get clan info
            clan_info = self.clan_system.CLANS.get(player_clan, {})
            clan_rarity = clan_info.get("rarity", "common")
            
            # Complete the mission
            result = self.clan_missions.complete_mission(player_id, mission_index)
            
            if not result or not result.get("success", False):
                error_msg = result.get("message", "Invalid mission index or mission already completed!") if result else "Invalid mission index or mission already completed!"
                await ctx.send(f"❌ {error_msg}")
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
            
            embed.add_field(
                name="Mission",
                value=mission.get("description", "No description available."),
                inline=False
            )
            
            embed.add_field(
                name="Base Reward",
                value=f"{mission.get('reward', 0):,} Ryō",
                inline=True
            )
            
            if clan_bonus > 0:
                embed.add_field(
                    name="Clan Bonus",
                    value=f"+{bonus_amount:,} Ryō ({clan_bonus}%)",
                    inline=True
                )
            
            embed.add_field(
                name="Total Reward",
                value=f"**{reward:,}** Ryō",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in finish_clan_mission command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="refresh_clan_missions",
        aliases=["new_clan_missions", "renew_clan_missions"],
        description="Get new clan missions",
        help="Get a new set of clan missions (costs 500 Ryō)."
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)  # Once per hour
    async def refresh_clan_missions(self, ctx):
        """Get new clan missions.
        
        Args:
            ctx: The command context
        """
        try:
            player_id = str(ctx.author.id)
            
            # Get player's clan
            character = self.bot.character_system.get_character(player_id)
            if not character:
                await ctx.send("❌ You need to create a character first! Use !create to get started.")
                return
                
            player_clan = character.clan if hasattr(character, 'clan') else None
            if not player_clan:
                await ctx.send("❌ You haven't been assigned to a clan yet! Use !join_clan first.")
                return
            
            # Check if missions can be refreshed
            next_refresh = self.clan_missions.get_next_refresh_time(player_id)
            if next_refresh and next_refresh > datetime.now():
                time_left = next_refresh - datetime.now()
                hours = int(time_left.total_seconds() / 3600)
                minutes = int((time_left.total_seconds() % 3600) / 60)
                await ctx.send(f"❌ You must wait {hours}h {minutes}m before refreshing missions!")
                return
            
            # Check if player has enough currency
            refresh_cost = 500
            current_balance = self.bot.currency_system.get_player_balance(player_id)
            
            if current_balance < refresh_cost:
                await ctx.send(f"❌ You need at least {refresh_cost} Ryō to refresh missions! You have {current_balance} Ryō.")
                return
            
            # Deduct cost
            self.bot.currency_system.set_player_balance(player_id, current_balance - refresh_cost)
            
            # Assign new missions
            new_missions = self.clan_missions.refresh_missions(player_id, player_clan)
            
            # Get clan info
            clan_info = self.clan_system.CLANS.get(player_clan, {})
            clan_rarity = clan_info.get("rarity", "common")
            
            # Create embed
            embed = discord.Embed(
                title="🔄 Missions Refreshed",
                description=f"You've spent {refresh_cost} Ryō to get new missions.",
                color=get_rarity_color(clan_rarity)
            )
            
            # Add mission information
            for i, mission in enumerate(new_missions):
                embed.add_field(
                    name=f"{i+1}. {mission['name']}",
                    value=f"{mission['description']}\n"
                          f"Reward: **{mission['reward']:,}** Ryō\n"
                          f"Duration: {mission['duration'].title()}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in refresh_clan_missions command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

async def setup(bot):
    """Set up the clan mission commands cog."""
    await bot.add_cog(ClanMissionCommands(bot, bot.clan_missions, bot.clan_system)) 