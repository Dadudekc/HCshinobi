"""Clan commands extension."""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.character_system import CharacterSystem

logger = logging.getLogger(__name__)

class ClanCommands(commands.Cog):
    """Commands for clan management."""
    
    def __init__(self, bot, clan_system: ClanSystem, character_system: CharacterSystem):
        """Initialize clan commands.
        
        Args:
            bot: Discord bot instance
            clan_system: Clan system instance
            character_system: Character system instance
        """
        self.bot = bot
        self.clan_system = clan_system
        self.character_system = character_system
        
    def _get_rarity_color(self, rarity: str) -> discord.Color:
        """Get color based on rarity.
        
        Args:
            rarity: Rarity level
            
        Returns:
            Discord color for the rarity
        """
        colors = {
            'common': discord.Color.light_grey(),
            'uncommon': discord.Color.green(),
            'rare': discord.Color.blue(),
            'epic': discord.Color.purple(),
            'legendary': discord.Color.gold()
        }
        return colors.get(rarity.lower(), discord.Color.default())
        
    @app_commands.command(name='clan')
    async def clan(self, interaction: discord.Interaction):
        """Clan management commands."""
        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message("You need to create a character first!")
                return
                
            if not character.clan:
                await interaction.response.send_message("You are not in a clan. Use /clan create or /clan join to join one!")
                return
                
            clan = await self.clan_system.get_clan(character.clan)
            if not clan:
                await interaction.response.send_message("Your clan could not be found.")
                return
                
            embed = discord.Embed(
                title=f"Clan: {clan.name}",
                description=clan.description or "No description",
                color=self._get_rarity_color(clan.rarity)
            )
            embed.add_field(name="Leader", value=f"<@{clan.leader_id}>", inline=True)
            embed.add_field(name="Members", value=str(len(clan.members)), inline=True)
            embed.add_field(name="Level", value=str(clan.level), inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error retrieving clan information: {e}")
            await interaction.response.send_message("An error occurred while retrieving clan information.")
            
    @app_commands.command(name='clan_create')
    async def create_clan(self, interaction: discord.Interaction, name: str, description: str = None):
        """Create a new clan.
        
        Args:
            interaction: Discord interaction
            name: Name of the clan
            description: Optional clan description
        """
        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message("You need to create a character first!")
                return
                
            if character.clan:
                await interaction.response.send_message("You are already in a clan!")
                return
                
            clan = await self.clan_system.create_clan(name, str(interaction.user.id), description)
            if not clan:
                await interaction.response.send_message("Failed to create clan. The name may be taken.")
                return
            
            # Update the character's clan
            update_success = await self.character_system.update_character(
                str(interaction.user.id),
                {"clan": clan.name}
            )
            if not update_success:
                # Log error, maybe inform user? Clan was created but assignment failed.
                logger.error(f"Clan '{clan.name}' created, but failed to assign to character {interaction.user.id}")
                await interaction.response.send_message(
                    f"Clan '{clan.name}' created, but there was an issue assigning it to your character.", 
                    ephemeral=True
                )
                return
                
            embed = discord.Embed(
                title="Clan Created",
                description=f"Successfully created clan: {clan.name}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error creating clan: {e}")
            await interaction.response.send_message("An error occurred while creating the clan.")
            
    @app_commands.command(name='clan_join')
    async def join_clan(self, interaction: discord.Interaction, name: str):
        """Join an existing clan.
        
        Args:
            interaction: Discord interaction
            name: Name of the clan to join
        """
        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message("You need to create a character first!")
                return
                
            if character.clan:
                await interaction.response.send_message("You are already in a clan!")
                return
                
            clan = await self.clan_system.get_clan(name)
            if not clan:
                await interaction.response.send_message(f"Clan '{name}' not found.")
                return
                
            success = await self.clan_system.add_member(clan.name, str(interaction.user.id))
            if not success:
                await interaction.response.send_message("Failed to join clan.")
                return
                
            embed = discord.Embed(
                title="Clan Joined",
                description=f"Successfully joined clan: {clan.name}",
                color=self._get_rarity_color(clan.rarity)
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error joining clan: {e}")
            await interaction.response.send_message("An error occurred while joining the clan.")
            
    @app_commands.command(name='clan_leave')
    async def leave_clan(self, interaction: discord.Interaction):
        """Leave current clan."""
        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message("You need to create a character first!")
                return
                
            if not character.clan:
                await interaction.response.send_message("You are not in a clan!")
                return
                
            success = await self.clan_system.remove_member(character.clan, str(interaction.user.id))
            if not success:
                await interaction.response.send_message("Failed to leave clan.")
                return
                
            await interaction.response.send_message("Successfully left your clan.")
            
        except Exception as e:
            logger.error(f"Error leaving clan: {e}")
            await interaction.response.send_message("An error occurred while leaving the clan.")
            
    @app_commands.command(name='clan_list')
    async def clan_list(self, interaction: discord.Interaction):
        """List all clans."""
        try:
            clans = await self.clan_system.get_all_clans()
            if not clans:
                await interaction.response.send_message("No clans found.")
                return
                
            embed = discord.Embed(
                title="Available Clans",
                color=discord.Color.blue()
            )
            
            for clan in clans:
                embed.add_field(
                    name=f"{clan.name} ({clan.rarity})",
                    value=f"Members: {len(clan.members)}\nLevel: {clan.level}",
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing clans: {e}")
            await interaction.response.send_message("An error occurred while retrieving clan list.") 