"""Quest commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional
import logging

from HCshinobi.core.quest_system import QuestSystem
from HCshinobi.core.clan_data import ClanData
from HCshinobi.utils.embed_utils import get_rarity_color

class QuestCommands(commands.Cog):
    def __init__(self, bot, quest_system: QuestSystem, clan_data: ClanData):
        """Initialize quest commands.
        
        Args:
            bot: The bot instance
            quest_system: The quest system instance
            clan_data: The clan data
        """
        self.bot = bot
        self.quest_system = quest_system
        self.clan_data = clan_data
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
        name="quest",
        aliases=["quests", "mission"],
        description="Get a new quest or view your current quests",
        help="Get a new quest with 'quest new' or view current quests with 'quest view'"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def quest(self, ctx, action: str = "view"):
        """Get a new quest or view current quests.
        
        Args:
            ctx: The command context
            action: Action to perform (new or view)
        """
        try:
            player_id = str(ctx.author.id)
            
            # Get player's clan
            # For this Cog implementation, we need to adapt the clan fetching logic
            player_clan = None
            character = self.bot.character_system.get_character(player_id)
            if character and hasattr(character, 'clan'):
                player_clan = character.clan
                
            if not player_clan:
                await ctx.send("❌ You haven't been assigned to a clan yet! Use !assign_clan first.")
                return
            
            # Get clan info
            clan_info = self.clan_data.get(player_clan)
            if not clan_info:
                await ctx.send(f"❌ Clan {player_clan} not found in clan data!")
                return
            
            if action == "new":
                # Generate new quest
                quest = self.quest_system.generate_quest(player_id, player_clan)
                self.quest_system.add_quest_to_player(player_id, quest)
                
                # Create quest embed
                embed = discord.Embed(
                    title="🎯 New Quest Available!",
                    description=quest["description"],
                    color=get_rarity_color(clan_info.get('rarity', 'common'))
                )
                
                # Add quest details
                embed.add_field(
                    name="Difficulty",
                    value=f"{quest['difficulty'].title()}",
                    inline=True
                )
                embed.add_field(
                    name="Reward",
                    value=f"💰 {quest['reward']:,} Ryo",
                    inline=True
                )
                embed.add_field(
                    name="Time Limit",
                    value=f"⏰ 24 hours",
                    inline=True
                )
                
                await ctx.send(embed=embed)
                
            elif action == "view":
                # Get player's quests
                quests = self.quest_system.get_player_quests(player_id)
                
                if not quests:
                    await ctx.send("❌ You don't have any quests! Use !quest new to get a new quest.")
                    return
                
                # Create quests embed
                embed = discord.Embed(
                    title=f"📜 {ctx.author.display_name}'s Quests",
                    description=f"Total Quests: {len(quests)}",
                    color=get_rarity_color(clan_info.get('rarity', 'common'))
                )
                
                # Add each quest
                for quest in quests:
                    status_emoji = {
                        "active": "⚡",
                        "completed": "✅",
                        "expired": "⏰"
                    }.get(quest["status"], "❓")
                    
                    quest_text = f"{status_emoji} **{quest['description']}**\n"
                    quest_text += f"Difficulty: {quest['difficulty'].title()}\n"
                    quest_text += f"Reward: {quest['reward']:,} Ryo\n"
                    
                    if quest["status"] == "active":
                        expires_at = datetime.strptime(quest["expires_at"], "%Y-%m-%d %H:%M:%S")
                        time_left = expires_at - datetime.now()
                        hours_left = int(time_left.total_seconds() / 3600)
                        quest_text += f"Time Left: {hours_left} hours\n"
                    
                    embed.add_field(
                        name=f"Quest {quest['id']}",
                        value=quest_text,
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
            else:
                await ctx.send("❌ Invalid action! Use 'new' to get a new quest or 'view' to view your current quests.")
        except Exception as e:
            self.logger.error(f"Error in quest command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="complete_quest",
        aliases=["finish_quest", "finish_task"],
        description="Complete a quest and claim your reward",
        help="Complete a quest by providing the quest ID, e.g., 'complete_quest q123'"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def complete_quest(self, ctx, quest_id: str):
        """Complete a quest and claim the reward.
        
        Args:
            ctx: The command context
            quest_id: The ID of the quest to complete
        """
        try:
            player_id = str(ctx.author.id)
            
            # Get player's clan
            player_clan = None
            character = self.bot.character_system.get_character(player_id)
            if character and hasattr(character, 'clan'):
                player_clan = character.clan
                
            if not player_clan:
                await ctx.send("❌ You haven't been assigned to a clan yet! Use !assign_clan first.")
                return
            
            # Get clan info
            clan_info = self.clan_data.get(player_clan)
            if not clan_info:
                await ctx.send(f"❌ Clan {player_clan} not found in clan data!")
                return
            
            # Complete the quest
            success, message, reward = self.quest_system.complete_quest(player_id, quest_id)
            
            # Create response embed
            embed = discord.Embed(
                title="🎯 Quest Completion",
                description=message,
                color=get_rarity_color(clan_info.get('rarity', 'common'))
            )
            
            if success:
                # Update player's balance
                current_balance = self.bot.currency_system.get_player_balance(player_id)
                self.bot.currency_system.set_player_balance(player_id, current_balance + reward)
                
                embed.add_field(
                    name="Reward",
                    value=f"💰 {reward:,} Ryo",
                    inline=True
                )
            
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in complete_quest command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

async def setup(bot):
    """Set up the quest commands cog."""
    await bot.add_cog(QuestCommands(bot, bot.quest_system, bot.clan_data)) 