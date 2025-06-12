"""
Quest commands for the Shinobi bot.
"""
import discord
from discord.ext import commands
import logging
from typing import Optional

from ..core.quest_system import QuestSystem

logger = logging.getLogger(__name__)

class QuestCommands(commands.Cog):
    """Commands for managing quests."""

    def __init__(self, bot, quest_system: QuestSystem):
        """
        Initialize quest commands.

        Args:
            bot: Discord bot instance
            quest_system: Quest system instance
        """
        self.bot = bot
        self.quest_system = quest_system

    @commands.command(name="quests")
    async def list_quests(self, ctx):
        """List available quests."""
        # Get character
        character = await self.quest_system.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send("You need to create a character first!")
            return

        # Get available quests
        quests = self.quest_system.get_available_quests(character)
        if not quests:
            await ctx.send("No quests available at the moment.")
            return

        embed = discord.Embed(
            title="📜 Available Quests",
            color=discord.Color.blue()
        )

        for quest in quests:
            embed.add_field(
                name=f"{quest['name']} (ID: {quest['id']})",
                value=(
                    f"Level: {quest['level_req']}\n"
                    f"Reward: {quest['reward']:,} ryo\n"
                    f"Description: {quest['description']}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="accept_quest")
    async def accept_quest(self, ctx, quest_id: str):
        """
        Accept a quest.

        Args:
            quest_id: ID of the quest to accept
        """
        # Get character
        character = await self.quest_system.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send("You need to create a character first!")
            return

        # Try to accept quest
        success, message = await self.quest_system.accept_quest(character, quest_id)
        if not success:
            await ctx.send(message)
            return

        embed = discord.Embed(
            title="📜 Quest Accepted",
            description=message,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="active_quests")
    async def view_active_quests(self, ctx):
        """View your active quests."""
        # Get character
        character = await self.quest_system.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send("You need to create a character first!")
            return

        # Get active quests
        quests = await self.quest_system.get_active_quests(character)
        if not quests:
            await ctx.send("You have no active quests.")
            return

        embed = discord.Embed(
            title="📜 Active Quests",
            color=discord.Color.blue()
        )

        for quest in quests:
            embed.add_field(
                name=f"{quest['name']} (ID: {quest['id']})",
                value=(
                    f"Progress: {quest['progress']}/{quest['target']}\n"
                    f"Reward: {quest['reward']:,} ryo\n"
                    f"Description: {quest['description']}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="complete_quest")
    async def complete_quest(self, ctx, quest_id: str):
        """
        Complete a quest.

        Args:
            quest_id: ID of the quest to complete
        """
        # Get character
        character = await self.quest_system.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send("You need to create a character first!")
            return

        # Try to complete quest
        success, message, reward = await self.quest_system.complete_quest(character, quest_id)
        if not success:
            await ctx.send(message)
            return

        embed = discord.Embed(
            title="🎉 Quest Completed",
            description=(
                f"{message}\n"
                f"Reward: {reward:,} ryo"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="abandon_quest")
    async def abandon_quest(self, ctx, quest_id: str):
        """
        Abandon a quest.

        Args:
            quest_id: ID of the quest to abandon
        """
        # Get character
        character = await self.quest_system.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send("You need to create a character first!")
            return

        # Try to abandon quest
        success, message = await self.quest_system.abandon_quest(character, quest_id)
        if not success:
            await ctx.send(message)
            return

        embed = discord.Embed(
            title="❌ Quest Abandoned",
            description=message,
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command(name="quest_history")
    async def view_history(self, ctx, page: int = 1):
        """
        View your quest history.

        Args:
            page: Page number to view (default: 1)
        """
        # Get character
        character = await self.quest_system.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send("You need to create a character first!")
            return

        # Get quest history
        history = await self.quest_system.get_quest_history(character)
        if not history:
            await ctx.send("No quest history found.")
            return

        # Paginate history
        per_page = 5
        total_pages = (len(history) + per_page - 1) // per_page
        
        if page < 1 or page > total_pages:
            await ctx.send(f"Invalid page number! Please choose between 1 and {total_pages}")
            return

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_entries = history[start_idx:end_idx]

        embed = discord.Embed(
            title="📚 Quest History",
            description=f"Page {page}/{total_pages}",
            color=discord.Color.blue()
        )

        for entry in page_entries:
            embed.add_field(
                name=f"{entry['name']} (ID: {entry['id']})",
                value=(
                    f"Status: {entry['status']}\n"
                    f"Completed: {entry['completed_at']}\n"
                    f"Reward: {entry['reward']:,} ryo"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    """Set up the quest commands cog."""
    await bot.add_cog(QuestCommands(bot, bot.quest_system)) 