"""Commands for clan management and missions."""
import discord
from discord.ext import commands
import logging
from datetime import datetime
import random
import asyncio
from typing import Optional

from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.clan_missions import ClanMissions
from HCshinobi.utils.embed_utils import get_rarity_color
from ..core.character import Character
from ..utils.embeds import create_clan_embed

class ClanCommands(commands.Cog):
    def __init__(self, bot, clan_system: ClanSystem, clan_missions: ClanMissions):
        """Initialize clan commands.
        
        Args:
            bot: The bot instance
            clan_system: The clan system instance
            clan_missions: The clan missions system instance
        """
        self.bot = bot
        self.clan_system = clan_system
        self.clan_missions = clan_missions
        self.logger = logging.getLogger(__name__)

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
        name="join_clan",
        aliases=["get_clan"],
        description="Get assigned to a random clan",
        help="Assigns you to a random clan with unique bonuses and abilities."
    )
    @commands.cooldown(1, 86400, commands.BucketType.user)  # Once per day
    async def join_clan(self, ctx):
        """Assign a player to a random clan.
        
        Args:
            ctx: The command context
        """
        try:
            character = await self.bot.services.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.send("❌ You need to create a character first! Use !create to get started.")
                return
                
            if character.clan:
                await ctx.send(f"❌ You are already a member of the {character.clan} clan!")
                return
                
            clans = await self.bot.services.clan_system.get_all_clans()
            if not clans:
                await ctx.send("❌ No clans are available for assignment!")
                return
                
            # Choose random clan
            clan = discord.utils.get(clans, name=discord.utils.random.choice([c.name for c in clans]))
            
            # Add member to clan
            success = await self.bot.services.clan_system.add_member(clan.name, character)
            if not success:
                await ctx.send("❌ Failed to join clan. Please try again later.")
                return
                
            embed = create_clan_embed(clan)
            embed.title = "🏰 Clan Assignment"
            embed.description = f"You have been assigned to the {clan.name} clan!"
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in join_clan command: {e}")
            await ctx.send("❌ An error occurred while joining clan.")

    @commands.command(
        name="clan_info",
        aliases=["myclan"],
        description="View information about your clan",
        help="Shows details about your clan's bonuses and abilities."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clan_info(self, ctx):
        """View information about your clan.
        
        Args:
            ctx: The command context
        """
        try:
            character = await self.bot.services.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.send("❌ You need to create a character first! Use !create to get started.")
                return
                
            if not character.clan:
                await ctx.send("❌ You haven't been assigned to a clan yet! Use !join_clan first.")
                return
                
            clan = await self.bot.services.clan_system.get_clan(character.clan)
            if not clan:
                await ctx.send(f"❌ Error: Your clan '{character.clan}' was not found.")
                return
                
            embed = create_clan_embed(clan)
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in clan_info command: {e}")
            await ctx.send("❌ An error occurred while getting clan information.")

    @commands.command(
        name="clan_missions",
        aliases=["missions", "tasks"],
        description="View your clan missions",
        help="Shows available clan missions you can complete for rewards."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clan_missions(self, ctx):
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
                          f"Use `!complete_mission {i+1}` to complete",
                    inline=False
                )
            
            # Add next refresh time
            next_refresh = self.clan_missions.get_next_refresh_time(player_id)
            if next_refresh:
                embed.set_footer(text=f"Missions refresh: {next_refresh}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in clan_missions command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="complete_mission",
        aliases=["finish_mission", "do_mission"],
        description="Complete a clan mission",
        help="Complete a clan mission by specifying its number, e.g., !complete_mission 1"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def complete_mission(self, ctx, mission_index: int):
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
            
            # Complete mission
            result = self.clan_missions.complete_mission(player_id, mission_index)
            
            if not result["success"]:
                await ctx.send(f"❌ {result['message']}")
                return
            
            # Apply reward
            mission = result["mission"]
            reward = mission["reward"]
            
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
                description=f"You have completed the mission: **{mission['name']}**",
                color=get_rarity_color(clan_rarity)
            )
            
            embed.add_field(
                name="Base Reward",
                value=f"{mission['reward']:,} Ryō",
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
            self.logger.error(f"Error in complete_mission command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="refresh_missions",
        aliases=["new_missions", "reset_missions"],
        description="Get new clan missions",
        help="Get a new set of clan missions (costs 500 Ryō)."
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)  # Once per hour
    async def refresh_missions(self, ctx):
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
            
            # Check if player has enough currency
            refresh_cost = 500
            current_balance = self.bot.currency_system.get_player_balance(player_id)
            
            if current_balance < refresh_cost:
                await ctx.send(f"❌ You need at least {refresh_cost} Ryō to refresh missions! You have {current_balance} Ryō.")
                return
            
            # Deduct cost
            self.bot.currency_system.set_player_balance(player_id, current_balance - refresh_cost)
            
            # Refresh missions
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
            
            # Add next refresh time
            next_refresh = self.clan_missions.get_next_refresh_time(player_id)
            if next_refresh:
                embed.set_footer(text=f"Next automatic refresh: {next_refresh}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in refresh_missions command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="leave_clan",
        description="Leave your current clan",
        help="Leave your current clan. You can join a new one after 24 hours."
    )
    @commands.cooldown(1, 86400, commands.BucketType.user)  # Once per day
    async def leave_clan(self, ctx):
        """Leave current clan.
        
        Args:
            ctx: Command context
        """
        try:
            character = await self.bot.services.character_system.get_character(ctx.author.id)
            if not character or not character.clan:
                await ctx.send("❌ You are not in a clan!")
                return
                
            clan_name = character.clan
            success = await self.bot.services.clan_system.remove_member(clan_name, character)
            if not success:
                await ctx.send("❌ Failed to leave clan. Please try again later.")
                return
                
            embed = discord.Embed(
                title="🏰 Clan Left",
                description=f"You have left the {clan_name} clan.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in leave_clan command: {e}")
            await ctx.send("❌ An error occurred while leaving clan.")

async def setup(bot):
    """Set up the clan commands cog."""
    await bot.add_cog(ClanCommands(bot, bot.clan_system, bot.clan_missions)) 