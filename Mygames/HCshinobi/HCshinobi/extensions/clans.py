"""Clan commands extension."""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from ..core.clan import Clan
from ..core.character import Character
from ..utils.embeds import create_clan_embed

class ClanCommands(commands.Cog):
    """Clan related commands."""
    
    def __init__(self, bot):
        self.bot = bot
        
    def _get_rarity_color(self, rarity: str) -> int:
        """Get color for clan rarity.
        
        Args:
            rarity: Clan rarity level
            
        Returns:
            Discord color code
        """
        colors = {
            'common': 0x808080,  # Gray
            'uncommon': 0x00FF00,  # Green
            'rare': 0x0000FF,  # Blue
            'epic': 0x800080,  # Purple
            'legendary': 0xFFD700,  # Gold
            'mythic': 0xFF0000,  # Red
        }
        return colors.get(rarity.lower(), 0xFFFFFF)  # Default white
        
    @app_commands.command()
    async def clan_info(self, interaction: discord.Interaction, clan_name: str):
        """Get information about a clan.
        
        Args:
            interaction: Discord interaction
            clan_name: Name of the clan
        """
        clan = await self.bot.services.clan_system.get_clan(clan_name)
        if not clan:
            await interaction.response.send_message(f"Clan '{clan_name}' not found.", ephemeral=True)
            return
            
        embed = create_clan_embed(clan, self._get_rarity_color(clan.rarity))
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command()
    async def join_clan(self, interaction: discord.Interaction, clan_name: str):
        """Join a clan.
        
        Args:
            interaction: Discord interaction
            clan_name: Name of the clan to join
        """
        character = await self.bot.services.character_system.get_character(interaction.user.id)
        if not character:
            await interaction.response.send_message("You need to create a character first!", ephemeral=True)
            return
            
        if character.clan:
            await interaction.response.send_message("You are already in a clan!", ephemeral=True)
            return
            
        clan = await self.bot.services.clan_system.get_clan(clan_name)
        if not clan:
            await interaction.response.send_message(f"Clan '{clan_name}' not found.", ephemeral=True)
            return
            
        success = await self.bot.services.clan_system.add_member(clan_name, character)
        if success:
            embed = discord.Embed(
                title="Clan Joined",
                description=f"You have successfully joined {clan_name}!",
                color=self._get_rarity_color(clan.rarity)
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Failed to join clan.", ephemeral=True)
            
    @app_commands.command()
    async def leave_clan(self, interaction: discord.Interaction):
        """Leave current clan."""
        character = await self.bot.services.character_system.get_character(interaction.user.id)
        if not character or not character.clan:
            await interaction.response.send_message("You are not in a clan!", ephemeral=True)
            return
            
        clan_name = character.clan
        success = await self.bot.services.clan_system.remove_member(clan_name, character)
        if success:
            embed = discord.Embed(
                title="Clan Left",
                description=f"You have left {clan_name}.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Failed to leave clan.", ephemeral=True)
            
async def setup(bot):
    """Set up clan commands."""
    await bot.add_cog(ClanCommands(bot)) 