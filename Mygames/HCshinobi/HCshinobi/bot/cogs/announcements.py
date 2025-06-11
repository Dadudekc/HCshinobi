#!/usr/bin/env python
"""
Discord Cog for handling announcements and system updates.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, TYPE_CHECKING, List, Dict, Any
import os
import sys
import time
from difflib import SequenceMatcher
from ..core.notifications.notification_dispatcher import NotificationDispatcher
from ..core.notifications.templates import (
    battle_alert,
    server_announcement,
    lore_drop,
    system_update,
    training_mission,
    system_alert
)
from ...core.views import ConfirmView
from HCshinobi.utils.config import load_config
from HCshinobi.utils.embeds import create_error_embed, create_success_embed
from HCshinobi.utils.theme import Theme

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

logger = logging.getLogger(__name__)

class AnnouncementCommands(commands.Cog):
    """Commands for managing announcements."""

    def __init__(self, bot: "HCBot"):
        """Initialize announcement commands."""
        self.bot = bot
        self.announcements_enabled = False
        self.logger = logging.getLogger(__name__)
        self.announcement_channel_id = self.bot.config.announcement_channel_id
        self.no_announcement = False
        self.recent_announcements = {}
        self.announcement_cooldown = 300  # 5 minutes cooldown
        
        # Initialize notification dispatcher
        self.dispatcher = NotificationDispatcher(
            webhook=self.bot.services.webhook,
            fallback_channel=self.bot.get_channel(self.announcement_channel_id)
        )
        
        # Check for maintenance mode
        maintenance_mode = False
        if os.getenv("MAINTENANCE_MODE", "").lower() == "true":
            maintenance_mode = True
        elif "--maintenance" in sys.argv or "-m" in sys.argv:
            maintenance_mode = True
            
        self.maintenance_mode = maintenance_mode
        logger.info("AnnouncementCommands Cog initialized.")
        logger.info(f"Announcement channel ID set to: {self.announcement_channel_id}")
        # Set initial announcement state based on maintenance mode
        self.announcements_enabled = not self.maintenance_mode 
        if self.maintenance_mode:
            logger.info("Maintenance mode is active - announcements will be disabled")
            # self.no_announcement = True # Remove this redundant flag

    def _is_duplicate_announcement(self, message: str) -> bool:
        """Check if an announcement is a duplicate of a recent one."""
        current_time = time.time()
        
        # Clean up old announcements
        self.recent_announcements = {
            msg: timestamp for msg, timestamp in self.recent_announcements.items()
            if current_time - timestamp < self.announcement_cooldown
        }
        
        # Check for duplicates
        for recent_msg, timestamp in self.recent_announcements.items():
            # Use fuzzy matching to detect similar messages
            similarity = self._calculate_similarity(message, recent_msg)
            if similarity > 0.8:  # 80% similarity threshold
                return True
        
        # Add new announcement to tracking
        self.recent_announcements[message] = current_time
        return False

    def _calculate_similarity(self, msg1: str, msg2: str) -> float:
        """Calculate similarity between two messages using Levenshtein distance."""
        return SequenceMatcher(None, msg1.lower(), msg2.lower()).ratio()

    @app_commands.command(
        name="toggle_announcements",
        description="Toggle announcements on/off"
    )
    async def toggle_announcements(self, interaction: discord.Interaction):
        """Toggle announcements on/off."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to toggle announcements.",
                ephemeral=True
            )
            return

        self.announcements_enabled = not self.announcements_enabled
        status = "enabled" if self.announcements_enabled else "disabled"
        await interaction.response.send_message(
            f"Announcements are now {status}.",
            ephemeral=True
        )

    @app_commands.command(
        name="maintenance_status",
        description="[Admin] Check the current maintenance mode status."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def maintenance_status(self, interaction: discord.Interaction) -> None:
        """Check the current maintenance mode status."""
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="Maintenance Mode Status",
            color=discord.Color.orange() if self.maintenance_mode else discord.Color.green()
        )
        embed.add_field(
            name="Maintenance Mode",
            value="✅ Active" if self.maintenance_mode else "❌ Inactive",
            inline=False
        )
        embed.add_field(
            name="Announcements",
            value="✅ Enabled" if self.announcements_enabled else "❌ Disabled",
            inline=False
        )
        if self.maintenance_mode:
            embed.add_field(
                name="Note",
                value="Announcements cannot be enabled while in maintenance mode.",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"Maintenance status checked by {interaction.user.name} (ID: {interaction.user.id})")

    @app_commands.command(
        name="update",
        description="[Admin] Announce an impending system update."
    )
    @app_commands.describe(
        version="The version number of the update",
        release_date="When the update will be released",
        changes="Key changes in this update",
        downtime="Expected downtime (if any)",
        additional_info="Any additional information"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def update(
        self,
        interaction: discord.Interaction,
        version: str,
        release_date: str,
        changes: str,
        downtime: Optional[str] = None,
        additional_info: Optional[str] = None
    ) -> None:
        """Announce an impending system update."""
        logger.info(f"update command triggered by {interaction.user.name} (ID: {interaction.user.id})")
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send(None)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_enabled:
            await interaction.followup.send(None)
            return

        try:
            # Validate release date format
            from datetime import datetime
            try:
                datetime.strptime(release_date, "%Y-%m-%d")
            except ValueError:
                await interaction.followup.send(f"Invalid date format: {release_date}")
                return

            # Create announcement message
            message = f"System Update v{version} - Release Date: {release_date}\nChanges: {changes}"
            if downtime:
                message += f"\nDowntime: {downtime}"
            if additional_info:
                message += f"\nAdditional Info: {additional_info}"

            # Check for duplicate announcements
            if self._is_duplicate_announcement(message):
                await interaction.followup.send(None)
                return

            # Create system update embed
            embed = system_update(
                title=f"System Update v{version}",
                description=message,
                release_date=release_date
            )
            
            # Send announcement
            await self.dispatcher.send_announcement(embed)
            await interaction.followup.send(None)
            
        except Exception as e:
            logger.error(f"Error sending update announcement: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="battle_announce",
        description="[Admin] Announce an upcoming battle."
    )
    @app_commands.describe(
        fighter_a="First fighter's name",
        fighter_b="Second fighter's name",
        arena="Battle location",
        time="Time of battle"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def battle_announce(
        self,
        interaction: discord.Interaction,
        fighter_a: str,
        fighter_b: str,
        arena: str,
        time: str
    ) -> None:
        """Announce an upcoming battle."""
        logger.info(f"battle_announce command triggered by {interaction.user.name} (ID: {interaction.user.id})")
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send(None)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_enabled:
            await interaction.followup.send(None)
            return

        try:
            # Create battle announcement embed
            embed = battle_alert(
                fighter_a=fighter_a,
                fighter_b=fighter_b,
                arena=arena,
                time=time
            )
            
            # Send announcement
            await self.dispatcher.send_announcement(embed)
            logger.info(f"Battle announcement sent: {fighter_a} vs {fighter_b}")
            await interaction.followup.send(None)
            
        except Exception as e:
            logger.error(f"Error sending battle announcement: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="lore_drop",
        description="[Admin] Share a piece of lore with the community."
    )
    @app_commands.describe(
        title="Title of the lore piece",
        snippet="The lore content",
        chapter="Optional chapter name",
        image_url="Optional image URL"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def lore_drop(
        self,
        interaction: discord.Interaction,
        title: str,
        snippet: str,
        chapter: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> None:
        """Share a piece of lore with the community."""
        logger.info(f"lore_drop command triggered by {interaction.user.name} (ID: {interaction.user.id})")
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send(None)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_enabled:
            await interaction.followup.send(None)
            return

        try:
            # Create lore drop embed
            embed = lore_drop(
                title=title,
                snippet=snippet,
                chapter=chapter,
                image_url=image_url
            )
            
            # Send announcement
            await self.dispatcher.send_announcement(embed)
            logger.info(f"Lore drop sent: {title}")
            await interaction.followup.send(None)
            
        except Exception as e:
            logger.error(f"Error sending lore drop: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="check_permissions",
        description="[Admin] Check the bot's permissions in the current server."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def check_permissions(self, interaction: discord.Interaction) -> None:
        """Check the bot's permissions in the current server."""
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ This command can only be used in a server.", ephemeral=True)
            return
            
        bot_member = guild.me
        # List of required permission attribute names (strings)
        required_permission_names = [
            "send_messages",
            "embed_links",
            "manage_webhooks",
            "manage_messages"
        ]

        missing_permissions = []
        # Iterate through the names and check the attributes
        for perm_name in required_permission_names:
            if not getattr(bot_member.guild_permissions, perm_name, False): # Use getattr with name
                missing_permissions.append(f"`{perm_name}`")

        embed = discord.Embed(
            title="Bot Permissions Check",
            color=discord.Color.green() if not missing_permissions else discord.Color.red()
        )
        
        embed.add_field(
            name="Server",
            value=guild.name,
            inline=False
        )
        
        embed.add_field(
            name="Bot Name",
            value=bot_member.display_name,
            inline=False
        )
        
        if missing_permissions:
            embed.add_field(
                name="Missing Permissions",
                value="\n".join(f"❌ {perm}" for perm in missing_permissions),
                inline=False
            )
            embed.add_field(
                name="How to Fix",
                value="Please grant the missing permissions in Server Settings > Roles > Bot Role",
                inline=False
            )
        else:
            embed.add_field(
                name="Permissions",
                value="✅ All required permissions are present",
                inline=False
            )
            
        embed.add_field(
            name="Command Tree",
            value="\n".join(f"• {cmd.name}" for cmd in self.bot.tree.get_commands()),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"Permission check requested by {interaction.user.name} (ID: {interaction.user.id})")

    @app_commands.command(
        name="check_bot_role",
        description="[Admin] Check the bot's role and permissions in the current server."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def check_bot_role(self, interaction: discord.Interaction) -> None:
        """Check the bot's role and permissions in the current server."""
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ This command can only be used in a server.", ephemeral=True)
            return
            
        bot_member = guild.me
        roles = [role.name for role in bot_member.roles]
        
        embed = discord.Embed(
            title="Bot Role Check",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Server",
            value=guild.name,
            inline=False
        )
        
        embed.add_field(
            name="Bot Name",
            value=bot_member.display_name,
            inline=False
        )
        
        embed.add_field(
            name="Bot Roles",
            value="\n".join(f"• {role}" for role in roles) if roles else "No roles assigned",
            inline=False
        )
        
        embed.add_field(
            name="Administrator Permission",
            value="✅ Yes" if bot_member.guild_permissions.administrator else "❌ No",
            inline=False
        )
        
        embed.add_field(
            name="Manage Messages Permission",
            value="✅ Yes" if bot_member.guild_permissions.manage_messages else "❌ No",
            inline=False
        )
        
        embed.add_field(
            name="Send Messages Permission",
            value="✅ Yes" if bot_member.guild_permissions.send_messages else "❌ No",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"Bot role check requested by {interaction.user.name} (ID: {interaction.user.id})")

    @app_commands.command(
        name="announce",
        description="[Admin] Send a general server announcement."
    )
    @app_commands.describe(
        title="The title of the announcement.",
        message="The main content of the announcement (supports Markdown)."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def announce(
        self, 
        interaction: discord.Interaction, 
        title: str, 
        message: str
    ) -> None:
        """Send a general server announcement."""
        logger.info(f"announce command triggered by {interaction.user.name} (ID: {interaction.user.id})")
        await interaction.response.defer(ephemeral=True)
        
        if not message:
            await interaction.followup.send("Announcement message cannot be empty")
            return
            
        if self.maintenance_mode:
            await interaction.followup.send(None)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_enabled:
            await interaction.followup.send(None)
            return

        # Check for duplicate announcements
        if self._is_duplicate_announcement(message):
            await interaction.followup.send(None)
            return

        try:
            # Create announcement embed
            embed = server_announcement(
                title=title,
                description=message
            )
            
            # Send announcement
            await self.dispatcher.send_announcement(embed)
            await interaction.followup.send(None)
            
        except Exception as e:
            logger.error(f"Error sending announcement: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="send_system_alert",
        description="[Admin] Manually trigger a system announcement to webhook or fallback channel."
    )
    @app_commands.describe(
        title="The title of the alert",
        message="The body of the announcement",
        ping_everyone="Should this ping everyone in the channel?",
        icon_url="Optional image or icon URL"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def send_system_alert(
        self,
        interaction: discord.Interaction,
        title: str,
        message: str,
        ping_everyone: bool = False,
        icon_url: Optional[str] = None
    ) -> None:
        """Send a system alert."""
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send(None)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_enabled:
            await interaction.followup.send(None)
            return

        try:
            # Create system alert embed
            embed = system_alert(
                title=title,
                description=message,
                icon_url=icon_url
            )
            
            # Send alert
            await self.dispatcher.send_notification(
                embed=embed,
                ping_everyone=ping_everyone
            )
            
            await interaction.followup.send(None)
            logger.info(f"System alert sent: {title}")
            
        except Exception as e:
            logger.error(f"Failed to send notification via fallback: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="broadcast_lore",
        description="[Admin] Broadcast a lore entry to the server."
    )
    @app_commands.describe(
        trigger="The event trigger type for the lore",
        target_clans="Optional clans to target (comma-separated)",
        ping_everyone="Whether to ping everyone"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def broadcast_lore(
        self,
        interaction: discord.Interaction,
        trigger: str,
        target_clans: Optional[str] = None,
        ping_everyone: bool = False
    ) -> None:
        """Broadcast a lore entry."""
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send(None)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_enabled:
            await interaction.followup.send(None)
            return

        try:
            # Trigger lore event
            success = await self.bot.event_engine.trigger_event(
                event_type="lore",
                trigger=trigger,
                target_clans=target_clans.split(",") if target_clans else None,
                ping_everyone=ping_everyone
            )
            
            if not success:
                await interaction.followup.send(None)
                return
                
            await interaction.followup.send(None)
            logger.info(f"Lore broadcast triggered: {trigger}")
            
        except Exception as e:
            logger.error(f"Error broadcasting lore: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="alert_clan",
        description="[Admin] Send an alert to a specific clan."
    )
    @app_commands.describe(
        clan_name="Name of the clan to alert",
        title="Alert title",
        message="Alert message (supports markdown)",
        ping_everyone="Whether to ping everyone"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def alert_clan(
        self,
        interaction: discord.Interaction,
        clan_name: str,
        title: str,
        message: str,
        ping_everyone: bool = False
    ) -> None:
        """Send an alert to a specific clan."""
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send(None)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_enabled:
            await interaction.followup.send(None)
            return

        try:
            # Create clan alert embed
            embed = system_alert(
                title=title,
                description=message
            )
            
            # Send alert to clan
            await self.dispatcher.send_notification(
                embed=embed,
                ping_everyone=ping_everyone,
                target_clan=clan_name
            )
            
            await interaction.followup.send(None)
            logger.info(f"Clan alert sent to {clan_name}: {title}")
            
        except Exception as e:
            logger.error(f"Failed to send notification via fallback: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="view_lore",
        description="[Admin] View available lore entries and their triggers."
    )
    @app_commands.describe(
        tags="Optional tags to filter lore entries (comma-separated)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def view_lore(
        self,
        interaction: discord.Interaction,
        tags: Optional[str] = None
    ) -> None:
        """View available lore entries."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get lore entries
            lore_entries = await self.bot.event_engine.get_lore_entries(tags=tags.split(",") if tags else None)
            
            if not lore_entries:
                await interaction.followup.send(None)
                return
                
            # Create lore view embed
            embed = discord.Embed(
                title="Available Lore Entries",
                color=discord.Color.blue()
            )
            
            for entry in lore_entries:
                embed.add_field(
                    name=entry.title,
                    value=f"Trigger: {entry.trigger}\nTags: {', '.join(entry.tags)}",
                    inline=False
                )
            
            await interaction.followup.send(None)
            
        except Exception as e:
            logger.error(f"Error viewing lore: {str(e)}")
            await interaction.followup.send(None)

    @app_commands.command(
        name="send_update",
        description="Send an update announcement"
    )
    @app_commands.describe(
        title="The update title",
        description="The update description",
        channel="The channel to send the update to (optional)"
    )
    async def update_cmd(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        channel: Optional[discord.TextChannel] = None
    ):
        """Send an update announcement.
        
        Args:
            interaction: The Discord interaction
            title: The update title
            description: The update description
            channel: The channel to send to (optional)
        """
        try:
            # Get the target channel
            if channel is None:
                # Use the default updates channel
                channel_id = self.bot.config.updates_channel_id
                if channel_id:
                    channel = interaction.guild.get_channel(channel_id)
                
                if channel is None:
                    # Fall back to the current channel
                    channel = interaction.channel
            
            # Create the update embed
            embed = discord.Embed(
                title=f"🔄 {title}",
                description=description,
                color=discord.Color.green()
            )
            embed.set_footer(
                text=f"Update by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            
            # Send confirmation view
            confirm_view = ConfirmView(interaction.user)
            await interaction.response.send_message(
                "Are you sure you want to send this update?",
                embed=embed,
                view=confirm_view,
                ephemeral=True
            )
            
            # Wait for confirmation
            await confirm_view.wait()
            
            if confirm_view.value:
                # Send the update
                await channel.send(embed=embed)
                
                # Send success message
                success_embed = create_success_embed(
                    "Update sent successfully!",
                    f"The update has been sent to {channel.mention}"
                )
                await interaction.edit_original_response(
                    content=None,
                    embed=success_embed,
                    view=None
                )
            else:
                # Send cancellation message
                await interaction.edit_original_response(
                    content="Update cancelled.",
                    embed=None,
                    view=None
                )
                
        except Exception as e:
            logger.error(f"Error sending update: {e}", exc_info=True)
            raise # Re-raise the error

    @update_cmd.error
    async def update_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Error handler for the update command.
        
        Args:
            interaction: The Discord interaction
            error: The error that occurred
        """
        error_embed = create_error_embed(
            "Error",
            "An error occurred while processing your update. Please try again."
        )
        
        if isinstance(error, app_commands.MissingPermissions):
            error_embed.description = "You don't have permission to send updates."
        
        try:
            await interaction.response.send_message(
                embed=error_embed,
                ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.edit_original_response(
                embed=error_embed
            )

# Define the 'update' command group separately
@app_commands.guild_only() # Or remove if intended to be global
class SystemUpdateCommands(commands.GroupCog, group_name="system_update"):
    """Commands related to system update announcements."""
    
    def __init__(self, bot: commands.Bot, announcements_cog: AnnouncementCommands):
        self.bot = bot
        self.announcements_cog = announcements_cog
        self.logger = logging.getLogger(__name__)

    @app_commands.command(
        name="now", # Renamed from 'update' to 'now' to avoid conflict with group name
        description="[Admin] Announce an impending system update."
    )
    @app_commands.describe(
        version="The version number of the update",
        release_date="When the update will be released",
        changes="Key changes in this update",
        downtime="Expected downtime (if any)",
        additional_info="Any additional information"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def update(
        self,
        interaction: discord.Interaction,
        version: str,
        release_date: str,
        changes: str,
        downtime: Optional[str] = None,
        additional_info: Optional[str] = None
    ) -> None:
        """Announce an impending system update."""
        logger.info(f"update command triggered by {interaction.user.name} (ID: {interaction.user.id})")
        await interaction.response.defer(ephemeral=True)
        
        if self.announcements_cog.maintenance_mode:
            await interaction.followup.send("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)
            return
            
        # Use the unified announcements_enabled flag
        if not self.announcements_cog.announcements_enabled:
            await interaction.followup.send("❌ Announcements are currently disabled via /toggle_announcements.", ephemeral=True)
            return

        # Create announcement message
        message = f"System Update v{version} - Release Date: {release_date}\nChanges: {changes}"
        if downtime:
            message += f"\nDowntime: {downtime}"
        if additional_info:
            message += f"\nAdditional Info: {additional_info}"

        # Check for duplicate announcements
        if self.announcements_cog._is_duplicate_announcement(message):
            await interaction.followup.send(
                "This update announcement is too similar to a recent one. Please wait a few minutes before posting a similar announcement.",
                ephemeral=True
            )
            return

        try:
            # Create system update embed
            embed = system_update(
                title=f"System Update v{version}",
                version=version,
                changes=changes,
                downtime=downtime
            )
            
            # Send notification
            await self.announcements_cog.dispatcher.dispatch(embed, ping_everyone=True)
            
            logger.info("Update announcement sent successfully")
            await interaction.followup.send("✅ Update announcement sent successfully!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error sending update announcement: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to send the announcement. Check the logs for details.", ephemeral=True)

async def setup(bot: "HCBot"):
    """Adds the AnnouncementCommands cog to the bot."""
    try:
        await bot.add_cog(AnnouncementCommands(bot))
        logger.info("AnnouncementCommands Cog loaded and added to bot successfully.")
    except Exception as e:
        logger.error(f"Failed to load AnnouncementCommands Cog: {e}", exc_info=True)
        raise 