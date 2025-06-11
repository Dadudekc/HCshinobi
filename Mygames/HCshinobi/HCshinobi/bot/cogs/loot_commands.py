"""
Loot commands cog for HCShinobi.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from HCshinobi.core.loot_system import LootSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.utils.embed_utils import create_error_embed

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

logger = logging.getLogger(__name__)

class LootCommands(commands.Cog):
    """Commands related to loot."""
    
    def __init__(self, bot: "HCBot"):
        self.bot = bot
        self.loot_system = bot.services.loot_system
        self.character_system = bot.services.character_system

    @app_commands.command(name="loot", description="View your current loot")
    async def loot(self, interaction: discord.Interaction):
        """View your current loot."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        user_id = str(interaction.user.id)
        
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.followup.send("You don't have a character yet!", ephemeral=True)
            return
            
        # Get character's loot
        loot = await self.loot_system.get_character_loot(user_id)
        if not loot:
            await interaction.followup.send("You don't have any loot yet!", ephemeral=True)
            return
            
        # Create embed with loot information
        embed = discord.Embed(title=f"{character.name}'s Loot", color=discord.Color.gold())
        for item in loot:
            embed.add_field(
                name=item["name"],
                value=f"Value: {item['value']} coins\nQuantity: {item['quantity']}",
                inline=True
            )
            
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="loot_history", description="View your loot history")
    async def loot_history(self, interaction: discord.Interaction):
        """View your loot history."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        user_id = str(interaction.user.id)
        
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.followup.send("You don't have a character yet!", ephemeral=True)
            return
            
        # Get character's loot history
        history = await self.loot_system.get_character_loot_history(user_id)
        if not history:
            await interaction.followup.send("You don't have any loot history yet!", ephemeral=True)
            return
            
        # Create embed with loot history
        embed = discord.Embed(title=f"{character.name}'s Loot History", color=discord.Color.gold())
        for entry in history:
            embed.add_field(
                name=entry["timestamp"],
                value=f"Item: {entry['item_name']}\nValue: {entry['value']} coins\nQuantity: {entry['quantity']}",
                inline=False
            )
            
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="loot_sell", description="Sell an item from your loot")
    @app_commands.describe(item_id="The ID of the item to sell")
    async def loot_sell(self, interaction: discord.Interaction, item_id: str):
        """Sell an item from your loot."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        user_id = str(interaction.user.id)
        
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.followup.send("You don't have a character yet!", ephemeral=True)
            return
            
        # Try to sell the item
        try:
            result = await self.loot_system.sell_item(user_id, item_id)
            if result["success"]:
                await interaction.followup.send(
                    f"Successfully sold {result['item_name']} for {result['value']} coins!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Failed to sell item: {result['error']}",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error selling item: {str(e)}")
            await interaction.followup.send(
                "An error occurred while trying to sell the item.",
                ephemeral=True
            ) 