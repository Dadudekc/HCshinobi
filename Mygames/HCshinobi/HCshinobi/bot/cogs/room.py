"""Room commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import TYPE_CHECKING, Optional, Dict, List, Any
from datetime import datetime

from HCshinobi.core.room_system import RoomSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.utils.embed_utils import create_error_embed

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

logger = logging.getLogger(__name__)

class RoomCommands(commands.Cog):
    def __init__(self, bot: "HCBot"):
        """Initialize room commands."""
        self.bot = bot
        # Get systems from bot services
        self.room_system = bot.services.room_system
        self.character_system = bot.services.character_system
        
        if not all([self.room_system, self.character_system]):
            logging.error("RoomCommands initialized without one or more required systems")
            
        self.logger = logging.getLogger(__name__)

    @app_commands.command(name="move", description="Move to a different room")
    async def move(self, interaction: discord.Interaction, direction: str):
        """Move to a different room."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for move: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            
            # Check if player has a character
            character = await self.character_system.get_character(player_id)
            if not character:
                await interaction.followup.send("❌ You need a character to move around!", ephemeral=True)
                return
                
            # Attempt to move the character
            success, message = await self.room_system.move_character(player_id, direction)
            
            if success:
                # Create success embed
                embed = discord.Embed(
                    title="🚶 Movement Successful",
                    description=message,
                    color=discord.Color.green()
                )
                
                # Add room description if available
                current_room = await self.room_system.get_current_room(player_id)
                if current_room:
                    embed.add_field(
                        name="Current Room",
                        value=current_room.description,
                        inline=False
                    )
                    
                    # Add available exits
                    exits = current_room.get_available_exits()
                    if exits:
                        embed.add_field(
                            name="Available Exits",
                            value=", ".join(exits),
                            inline=False
                        )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Create error embed
                embed = discord.Embed(
                    title="❌ Movement Failed",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /move command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while trying to move.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending move error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="look", description="Look around your current room")
    async def look(self, interaction: discord.Interaction):
        """Look around your current room."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for look: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            
            # Check if player has a character
            character = await self.character_system.get_character(player_id)
            if not character:
                await interaction.followup.send("❌ You need a character to look around!", ephemeral=True)
                return
                
            # Get current room information
            current_room = await self.room_system.get_current_room(player_id)
            if not current_room:
                await interaction.followup.send("❌ You are not in any room!", ephemeral=True)
                return
                
            # Create room description embed
            embed = discord.Embed(
                title=f"👀 {current_room.name}",
                description=current_room.description,
                color=discord.Color.blue()
            )
            
            # Add room details
            if current_room.details:
                embed.add_field(
                    name="Details",
                    value=current_room.details,
                    inline=False
                )
                
            # Add available exits
            exits = current_room.get_available_exits()
            if exits:
                embed.add_field(
                    name="Available Exits",
                    value=", ".join(exits),
                    inline=False
                )
                
            # Add room contents
            contents = await self.room_system.get_room_contents(current_room.id)
            if contents:
                embed.add_field(
                    name="Room Contents",
                    value="\n".join([f"• {item}" for item in contents]),
                    inline=False
                )
                
            # Add other characters in the room
            characters = await self.room_system.get_characters_in_room(current_room.id)
            if characters:
                embed.add_field(
                    name="Other Characters",
                    value="\n".join([f"• {char}" for char in characters if char != character.name]),
                    inline=False
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /look command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while looking around.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending look error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="enter", description="Enter a specific room")
    async def enter(self, interaction: discord.Interaction, room_id: str):
        """Enter a specific room."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for enter: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            
            # Check if player has a character
            character = await self.character_system.get_character(player_id)
            if not character:
                await interaction.followup.send("❌ You need a character to enter rooms!", ephemeral=True)
                return
                
            # Attempt to enter the room
            success, message = await self.room_system.enter_room(player_id, room_id)
            
            if success:
                # Create success embed
                embed = discord.Embed(
                    title="🚪 Room Entered",
                    description=message,
                    color=discord.Color.green()
                )
                
                # Add room description if available
                current_room = await self.room_system.get_current_room(player_id)
                if current_room:
                    embed.add_field(
                        name="Current Room",
                        value=current_room.description,
                        inline=False
                    )
                    
                    # Add available exits
                    exits = current_room.get_available_exits()
                    if exits:
                        embed.add_field(
                            name="Available Exits",
                            value=", ".join(exits),
                            inline=False
                        )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Create error embed
                embed = discord.Embed(
                    title="❌ Room Entry Failed",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /enter command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while trying to enter the room.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending enter error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="exit", description="Exit the current room")
    async def exit(self, interaction: discord.Interaction):
        """Exit the current room."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for exit: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            
            # Check if player has a character
            character = await self.character_system.get_character(player_id)
            if not character:
                await interaction.followup.send("❌ You need a character to exit rooms!", ephemeral=True)
                return
                
            # Attempt to exit the room
            success, message = await self.room_system.exit_room(player_id)
            
            if success:
                # Create success embed
                embed = discord.Embed(
                    title="🚪 Room Exited",
                    description=message,
                    color=discord.Color.green()
                )
                
                # Add new room description if available
                current_room = await self.room_system.get_current_room(player_id)
                if current_room:
                    embed.add_field(
                        name="Current Room",
                        value=current_room.description,
                        inline=False
                    )
                    
                    # Add available exits
                    exits = current_room.get_available_exits()
                    if exits:
                        embed.add_field(
                            name="Available Exits",
                            value=", ".join(exits),
                            inline=False
                        )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Create error embed
                embed = discord.Embed(
                    title="❌ Room Exit Failed",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /exit command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while trying to exit the room.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending exit error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="npcs", description="List NPCs in a specific room")
    @app_commands.describe(room_id="The ID of the room (e.g., training_grounds)")
    async def npcs(self, interaction: discord.Interaction, room_id: str):
        """List NPCs in a specific room."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for npcs: {e}", exc_info=True)
            return

        try:
            # Check if room exists
            room = await self.room_system.get_room(room_id)
            if not room:
                await interaction.followup.send("❌ Room not found!", ephemeral=True)
                return
                
            # Get NPCs in the room
            npcs = await self.room_system.get_npcs_in_room(room_id)
            
            if npcs:
                # Create NPC list embed
                embed = discord.Embed(
                    title=f"👥 NPCs in {room.name}",
                    description="\n".join([f"• {npc}" for npc in npcs]),
                    color=discord.Color.blue()
                )
                
                # Add room description
                embed.add_field(
                    name="Room Description",
                    value=room.description,
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("No NPCs found in this room.", ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /npcs command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while listing NPCs.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending npcs error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="room_info", description="Get detailed information about a room")
    @app_commands.describe(room_id="The ID of the room to get information about")
    async def room_info(self, interaction: discord.Interaction, room_id: str):
        """Get detailed information about a room."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for room_info: {e}", exc_info=True)
            return

        try:
            # Get room information
            room = await self.room_system.get_room(room_id)
            if not room:
                await interaction.followup.send(f"❌ Room '{room_id}' not found!", ephemeral=True)
                return
                
            # Create room info embed
            embed = discord.Embed(
                title=f"🏠 {room.name}",
                description=room.description,
                color=discord.Color.blue()
            )
            
            # Add room details
            if room.details:
                embed.add_field(
                    name="Details",
                    value=room.details,
                    inline=False
                )
                
            # Add available exits
            exits = room.get_available_exits()
            if exits:
                embed.add_field(
                    name="Available Exits",
                    value=", ".join(exits),
                    inline=False
                )
                
            # Add room contents
            contents = await self.room_system.get_room_contents(room.id)
            if contents:
                embed.add_field(
                    name="Room Contents",
                    value="\n".join([f"• {item}" for item in contents]),
                    inline=False
                )
                
            # Add characters in the room
            characters = await self.room_system.get_characters_in_room(room.id)
            if characters:
                embed.add_field(
                    name="Characters Present",
                    value="\n".join([f"• {char}" for char in characters]),
                    inline=False
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /room_info command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while getting room information.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending room_info error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="room_enter", description="Enter a specific room by ID")
    @app_commands.describe(room_id="The ID of the room to enter")
    async def room_enter(self, interaction: discord.Interaction, room_id: str):
        """Enter a specific room by ID."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for room_enter: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            
            # Check if player has a character
            character = await self.character_system.get_character(player_id)
            if not character:
                await interaction.followup.send("❌ You need a character to enter rooms!", ephemeral=True)
                return
                
            # Attempt to enter the room
            success, message = await self.room_system.enter_room(player_id, room_id)
            
            if success:
                # Create success embed
                embed = discord.Embed(
                    title="🚪 Room Entered",
                    description=message,
                    color=discord.Color.green()
                )
                
                # Add room description if available
                room = await self.room_system.get_room(room_id)
                if room:
                    embed.add_field(
                        name="Room Description",
                        value=room.description,
                        inline=False
                    )
                    
                    # Add available exits
                    exits = room.get_available_exits()
                    if exits:
                        embed.add_field(
                            name="Available Exits",
                            value=", ".join(exits),
                            inline=False
                        )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Create error embed
                embed = discord.Embed(
                    title="❌ Room Entry Failed",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /room_enter command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while trying to enter the room.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending room_enter error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="room_leave", description="Leave the current room")
    async def room_leave(self, interaction: discord.Interaction):
        """Leave the current room."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for room_leave: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            
            # Check if player has a character
            character = await self.character_system.get_character(player_id)
            if not character:
                await interaction.followup.send("❌ You need a character to leave rooms!", ephemeral=True)
                return
                
            # Attempt to leave the room
            success, message = await self.room_system.leave_room(player_id)
            
            if success:
                # Create success embed
                embed = discord.Embed(
                    title="🚶 Room Left",
                    description=message,
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Create error embed
                embed = discord.Embed(
                    title="❌ Room Leave Failed",
                    description=message,
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /room_leave command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while trying to leave the room.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending room_leave error followup: {http_err_fatal}", exc_info=True)

async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    # Get required services
    room_system = getattr(bot.services, 'room_system', None)
    character_system = getattr(bot.services, 'character_system', None)
    
    if not all([room_system, character_system]):
        logger.error("Cannot load RoomCommands cog: Missing RoomSystem or CharacterSystem in bot.services")
        return # Do not load cog if dependencies are missing
        
    cog = RoomCommands(bot) # Pass the bot instance
    await bot.add_cog(cog)
    logger.info("RoomCommands Cog loaded and added to bot.")
    
    # Assuming commands are in a group named 'room'
    # If they are standalone commands, this block is not needed
    try:
        room_group = bot.tree.get_command("room")
        if room_group:
            # Check if commands are already added before adding again
            # (or handle potential errors if add_command is called multiple times)
            # This example assumes they need explicit adding here after cog is loaded
            # Note: Often, commands are discovered automatically when the cog is added.
            # This manual registration might be unnecessary or specific to this setup.
            # If commands are already registered via @app_commands.command, this block might be removed.
            room_group.add_command(cog.move)
            room_group.add_command(cog.look)
            # room_group.add_command(cog.whereami) # <-- whereami is commented/removed
            room_group.add_command(cog.enter)
            room_group.add_command(cog.exit)
            room_group.add_command(cog.npcs)
            room_group.add_command(cog.room_info)
            room_group.add_command(cog.room_enter)
            room_group.add_command(cog.room_leave)
            logger.info("Added RoomCommands subcommands to 'room' group.")
        else:
            logger.warning("Could not find 'room' command group to add subcommands.")
    except Exception as e:
        logger.error(f"Error adding RoomCommands subcommands to group: {e}", exc_info=True) 