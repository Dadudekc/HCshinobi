from discord.ext import commands
from discord import Intents
from discord.app_commands import AppCommandError
from .config import BotConfig
from .services import ServiceContainer
import logging

class HCBot(commands.Bot):
    def __init__(self, config: BotConfig, silent_start: bool = False):
        # Create intents with all permissions needed for the bot
        intents = Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(command_prefix=config.command_prefix, intents=intents)
        self.config = config
        self.silent_start = silent_start
        self.services = ServiceContainer(config)

    async def setup_hook(self) -> None:
        await self.services.initialize(self)
        register_commands_command(self)

    # Removed custom interaction handlers to let discord.py handle them normally

    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle errors in event methods."""
        logging.error(f"❌ Error in event {event_method}: {args} {kwargs}")
        await super().on_error(event_method, *args, **kwargs)

    async def on_app_command_error(self, interaction, error: AppCommandError):
        """Global error handler for all slash commands."""
        import traceback
        from discord.errors import NotFound, HTTPException
        
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # Log detailed error information
        logging.error(f"❌ SLASH COMMAND ERROR:")
        logging.error(f"   Command: {interaction.command.name if interaction.command else 'Unknown'}")
        logging.error(f"   User: {interaction.user.name}#{interaction.user.discriminator} ({interaction.user.id})")
        logging.error(f"   Guild: {interaction.guild.name if interaction.guild else 'DM'} ({interaction.guild.id if interaction.guild else 'DM'})")
        logging.error(f"   Error: {error}")
        logging.error(f"   Traceback:\n{tb}")
        
        # Handle specific interaction errors
        if isinstance(error, NotFound) and "Unknown interaction" in str(error):
            logging.warning(f"⚠️ Interaction expired for user {interaction.user.id} in command {interaction.command.name}")
            # Try to send a DM as fallback
            try:
                await interaction.user.send("⚠️ **Command Response Delayed**\nThe command took too long to respond. Please try again.")
            except:
                logging.error(f"Failed to send DM fallback to user {interaction.user.id}")
            return
        
        if isinstance(error, HTTPException) and "Interaction has already been acknowledged" in str(error):
            logging.warning(f"⚠️ Interaction already acknowledged for user {interaction.user.id} in command {interaction.command.name}")
            return
        
        # Send user-friendly error message for other errors
        error_msg = (
            f"❌ **An error occurred while running `/{interaction.command.name if interaction.command else 'unknown'}`:**\n"
            f"```{str(error)}```\n"
            f"**Error ID:** `{id(error)}`\n"
            f"Please contact an admin if this persists."
        )
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)
        except Exception as e:
            logging.error(f"❌ Failed to send error message to user: {e}")
            # Try to send a simple error message
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            except:
                pass


def register_commands_command(bot: commands.Bot):
    @bot.command(name="commands")
    async def _list_commands(ctx: commands.Context):
        names = sorted(f"!{c.name}" for c in bot.commands)
        await ctx.send("Available commands: " + " ".join(names))

    return _list_commands

