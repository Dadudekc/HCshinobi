"""
Event handlers for HCShinobi bot.
Handles bot events like ready, command errors, and notifications.
"""

import discord
from discord.ext import commands
from typing import Optional
from .config import BotConfig
from .services import ServiceContainer

class BotEvents:
    """Handles bot events and notifications."""
    
    def __init__(self, bot: commands.Bot, config: BotConfig, services: ServiceContainer):
        self.bot = bot
        self.config = config
        self.services = services
    
    async def on_ready(self) -> None:
        """Called when the bot is ready and connected to Discord."""
        print(f"Logged in as {self.bot.user.name} (ID: {self.bot.user.id})")
        print("------")
        
        # Set bot username
        try:
            await self.bot.user.edit(username="Shinobi Chronicles")
            print("Successfully set bot username to 'Shinobi Chronicles'")
        except Exception as e:
            print(f"Failed to set bot username: {e}")
        
        # Log basic info
        print(f"Discord.py Version: {discord.__version__}")
        print(f"Connected to {len(self.bot.guilds)} guild(s).")
        
        # Get the target guild
        target_guild = None
        if self.config.guild_id:
            target_guild = self.bot.get_guild(self.config.guild_id)
            print(f"Target guild: {target_guild.name if target_guild else 'Not Found'} (ID: {self.config.guild_id})")
            
            # Log guild channels for debugging
            if target_guild:
                print("\nAvailable channels in target guild:")
                for channel in target_guild.channels:
                    print(f"- {channel.name} (ID: {channel.id}, Type: {channel.type})")
        else:
            print("WARNING: No target guild ID configured")
        
        print("Bot is ready and fully operational.")
        
        # Initialize services and set initialized flag
        await self.services.initialize()
        self.bot.initialized = True
        
        # Send online notification
        await self._send_online_notification()
    
    async def on_message(self, message: discord.Message) -> None:
        """Called when a message is sent in any channel the bot can see."""
        # Ignore messages from the bot itself
        if message.author.id == self.bot.user.id:
            print(f"Ignoring bot's own message: {message.content}")
            return

        # Debug logging
        print(f"\nMessage received: {message.content}")
        print(f"Channel: {message.channel.name} (ID: {message.channel.id})")
        print(f"Author: {message.author.name} (ID: {message.author.id})")
        print(f"Command prefix: {self.bot.command_prefix}")
        print(f"Command channel ID: {self.config.command_channel_id}")

        # Check if message starts with command prefix
        if not message.content.startswith(self.bot.command_prefix):
            print(f"Message does not start with command prefix: {self.bot.command_prefix}")
            return

        print(f"Processing command: {message.content}")
        # Process commands
        await self.bot.process_commands(message)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I don't have permission to do that.")
        else:
            print(f"Error in command {ctx.command}: {error}")
            await ctx.send(f"An error occurred: {str(error)}")
    
    async def _send_online_notification(self) -> None:
        """Send a notification to the configured channel that the bot is online."""
        try:
            channel_id = getattr(self.config, 'online_channel_id', None) or self.config.command_channel_id
            channel = self.bot.get_channel(channel_id)
            
            if channel:
                await channel.send(f"🟢 **{self.bot.user.name}** is now online and ready!")
            else:
                self.logger.warning(f"Could not find channel with ID {channel_id} for online notification")
        except Exception as e:
            self.logger.error(f"Error sending online notification: {e}") 