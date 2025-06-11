"""Devlog commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from typing import TYPE_CHECKING, Optional, List, Dict, Any
import os # Import os
import aiofiles # Import aiofiles
from ...core.constants import DATA_DIR, LOG_DIR # Assuming DEV_LOG_FILE might be in LOG_DIR or DATA_DIR

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

# Define the path to the devlog file
DEVLOG_FILE_PATH = os.path.join(DATA_DIR, "devlog.md") # Place devlog in main data dir

logger = logging.getLogger(__name__)

class DevlogCommands(commands.Cog):
    def __init__(self, bot: "HCBot"):
        """Initialize devlog commands."""
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @app_commands.command(name="devlog", description="View the latest development updates")
    async def devlog(self, interaction: discord.Interaction):
        """View the latest development updates."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for devlog: {e}", exc_info=True)
            return

        try:
            # Try to read the devlog file asynchronously
            try:
                async with aiofiles.open(DEVLOG_FILE_PATH, mode='r', encoding='utf-8') as f:
                    devlog_content = await f.read()
                if not devlog_content.strip():
                    devlog_content = "*The devlog is currently empty.*"
            except FileNotFoundError:
                self.logger.warning(f"Devlog file not found at {DEVLOG_FILE_PATH}. Creating it.")
                # Create the file if it doesn't exist
                try:
                    async with aiofiles.open(DEVLOG_FILE_PATH, mode='w', encoding='utf-8') as f:
                        await f.write("# HCShinobi Development Log\n\n*No entries yet.*")
                    devlog_content = "*The devlog is currently empty.*"
                except Exception as create_err:
                    self.logger.error(f"Failed to create devlog file: {create_err}", exc_info=True)
                    devlog_content = "*Error accessing the devlog file.*"
            except Exception as read_err:
                 self.logger.error(f"Error reading devlog file: {read_err}", exc_info=True)
                 devlog_content = "*Error accessing the devlog file.*"

            # Create the devlog embed
            embed = discord.Embed(
                title="📝 Development Log",
                description=devlog_content[:4000], # Limit description length
                color=discord.Color.blue()
            )

            # Add footer with last update time (file modification time)
            try:
                mtime = os.path.getmtime(DEVLOG_FILE_PATH)
                last_updated = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                embed.set_footer(text=f"Last updated: {last_updated} UTC")
            except Exception:
                embed.set_footer(text="Last updated: Unknown")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error in /devlog command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while fetching the devlog.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending devlog error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="bug_report", description="Report a bug or issue")
    async def bug_report(self, interaction: discord.Interaction, description: str):
        """Report a bug or issue to the development team."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for bug_report: {e}", exc_info=True)
            return

        try:
            # Create the bug report embed
            embed = discord.Embed(
                title="🐛 Bug Report",
                description=f"**Reported by:** {interaction.user.mention}\n**Description:** {description}",
                color=discord.Color.red()
            )
            
            # Add timestamp
            embed.timestamp = datetime.now()
            
            # Send to bug reports channel if configured
            # Use the configured ID from bot.config
            bug_channel_id = self.bot.config.bug_report_channel_id 
            bug_channel = self.bot.get_channel(bug_channel_id) if bug_channel_id else None
            
            if bug_channel:
                await bug_channel.send(embed=embed)
                await interaction.followup.send("✅ Your bug report has been submitted. Thank you for helping improve the bot!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Bug reporting is currently unavailable. Please try again later.", ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /bug_report command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while submitting your bug report.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending bug_report error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="suggest", description="Submit a feature suggestion")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        """Submit a feature suggestion to the development team."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for suggest: {e}", exc_info=True)
            return

        try:
            # Create the suggestion embed
            embed = discord.Embed(
                title="💡 Feature Suggestion",
                description=f"**Suggested by:** {interaction.user.mention}\n**Suggestion:** {suggestion}",
                color=discord.Color.green()
            )
            
            # Add timestamp
            embed.timestamp = datetime.now()
            
            # Send to suggestions channel if configured
            # Use the configured ID from bot.config
            suggest_channel_id = self.bot.config.suggestion_channel_id 
            suggest_channel = self.bot.get_channel(suggest_channel_id) if suggest_channel_id else None
            
            if suggest_channel:
                await suggest_channel.send(embed=embed)
                await interaction.followup.send("✅ Your suggestion has been submitted. Thank you for your input!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Suggestion submission is currently unavailable. Please try again later.", ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /suggest command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while submitting your suggestion.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending suggest error followup: {http_err_fatal}", exc_info=True)

async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(DevlogCommands(bot)) 