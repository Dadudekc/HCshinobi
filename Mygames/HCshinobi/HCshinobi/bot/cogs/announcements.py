#!/usr/bin/env python
"""
Discord Cog for handling announcements and system updates.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from ..bot import HCBot
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
from ...utils.config import load_config
from ...utils.embeds import create_error_embed, create_success_embed

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
        if self.maintenance_mode:
            logger.info("Maintenance mode is active - announcements will be disabled")
            self.no_announcement = True

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
            value="❌ Disabled" if self.no_announcement else "✅ Enabled",
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
            await interaction.followup.send("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)
            return
            
        if self.no_announcement:
            await interaction.followup.send("❌ Announcements are currently disabled.", ephemeral=True)
            return

        # Create announcement message
        message = f"System Update v{version} - Release Date: {release_date}\nChanges: {changes}"
        if downtime:
            message += f"\nDowntime: {downtime}"
        if additional_info:
            message += f"\nAdditional Info: {additional_info}"

        # Check for duplicate announcements
        if self._is_duplicate_announcement(message):
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
            await self.dispatcher.dispatch(embed, ping_everyone=True)
            
            logger.info("Update announcement sent successfully")
            await interaction.followup.send("✅ Update announcement sent successfully!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error sending update announcement: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to send the announcement. Check the logs for details.", ephemeral=True)

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
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)
            return
            
        if self.no_announcement:
            await interaction.followup.send("❌ Announcements are currently disabled.", ephemeral=True)
            return

        try:
            # Create battle alert embed
            embed = battle_alert(
                title="Battle Incoming",
                fighter_a=fighter_a,
                fighter_b=fighter_b,
                arena=arena,
                time_str=time
            )
            
            # Send notification
            await self.dispatcher.dispatch(embed, ping_everyone=True)
            
            logger.info(f"Battle announcement sent: {fighter_a} vs {fighter_b}")
            await interaction.followup.send("✅ Battle announcement sent successfully!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error sending battle announcement: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to send the announcement. Check the logs for details.", ephemeral=True)

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
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)
            return
            
        if self.no_announcement:
            await interaction.followup.send("❌ Announcements are currently disabled.", ephemeral=True)
            return

        try:
            # Create lore drop embed
            embed = lore_drop(
                title=title,
                snippet=snippet,
                chapter=chapter,
                image_url=image_url
            )
            
            # Send notification
            await self.dispatcher.dispatch(embed)
            
            logger.info(f"Lore drop sent: {title}")
            await interaction.followup.send("✅ Lore drop sent successfully!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error sending lore drop: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to send the lore drop. Check the logs for details.", ephemeral=True)

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
        required_permissions = [
            discord.Permissions.send_messages,
            discord.Permissions.embed_links,
            discord.Permissions.use_slash_commands,
            discord.Permissions.manage_webhooks,
            discord.Permissions.manage_messages
        ]
        
        missing_permissions = []
        for perm in required_permissions:
            if not getattr(bot_member.guild_permissions, perm.name):
                missing_permissions.append(perm.name)
        
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
        description="Send an announcement message"
    )
    @app_commands.describe(
        message="The announcement message to send",
        embed="Whether to send the message as an embed",
        ping_everyone="Whether to ping @everyone"
    )
    async def announce_message(
        self,
        interaction: discord.Interaction,
        message: str,
        embed: bool = False,
        ping_everyone: bool = False
    ):
        """Send an announcement message."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True
            )
            return

        if not self.announcements_enabled:
            await interaction.response.send_message(
                "Announcements are currently disabled. Use `/toggle_announcements` to enable them.",
                ephemeral=True
            )
            return

        # Check for duplicate announcements
        if self._is_duplicate_announcement(message):
            await interaction.response.send_message(
                "This announcement is too similar to a recent one. Please wait a few minutes before posting a similar announcement.",
                ephemeral=True
            )
            return

        try:
            content = f"@everyone {message}" if ping_everyone else message
            if embed:
                embed = discord.Embed(
                    title="Announcement",
                    description=message,
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(content=content if ping_everyone else None, embed=embed)
            else:
                await interaction.response.send_message(content=content)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to send announcements in this channel.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in announce_message: {e}", exc_info=True)
            raise  # Re-raise the error for global handling or test assertions

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
        """Send a system alert with optional markdown formatting."""
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)
            return
            
        if self.no_announcement:
            await interaction.followup.send("❌ Announcements are currently disabled.", ephemeral=True)
            return

        try:
            # Create system alert embed
            embed = system_alert(
                title=title,
                message=message,
                icon_url=icon_url
            )
            
            # Send notification
            await self.dispatcher.dispatch(embed, ping_everyone=ping_everyone)
            
            logger.info(f"System alert sent: {title}")
            await interaction.followup.send("✅ Alert dispatched successfully!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error sending system alert: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to send the alert. Check the logs for details.", ephemeral=True)

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
        """Broadcast a lore entry based on an event trigger."""
        await interaction.response.defer(ephemeral=True)
        
        if self.maintenance_mode:
            await interaction.followup.send("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)
            return
            
        if self.no_announcement:
            await interaction.followup.send("❌ Announcements are currently disabled.", ephemeral=True)
            return

        try:
            # Parse target clans if provided
            clan_list = [clan.strip() for clan in target_clans.split(",")] if target_clans else None
            
            # Trigger the event
            success = await self.bot.event_engine.trigger_event(
                event_type=trigger,
                target_clans=clan_list,
                ping_everyone=ping_everyone
            )
            
            if success:
                logger.info(f"Lore broadcast triggered: {trigger}")
                await interaction.followup.send("✅ Lore broadcast sent successfully!", ephemeral=True)
            else:
                await interaction.followup.send("❌ No lore entry found for this trigger.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error broadcasting lore: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to broadcast lore. Check the logs for details.", ephemeral=True)

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
            await interaction.followup.send("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)
            return
            
        if self.no_announcement:
            await interaction.followup.send("❌ Announcements are currently disabled.", ephemeral=True)
            return

        try:
            # Create system alert embed
            embed = system_alert(
                title=f"Clan Alert: {title}",
                message=message
            )
            
            # Send notification to specific clan
            await self.dispatcher.dispatch(
                embed=embed,
                ping_everyone=ping_everyone,
                target_clans=[clan_name]
            )
            
            logger.info(f"Clan alert sent to {clan_name}: {title}")
            await interaction.followup.send("✅ Clan alert sent successfully!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error sending clan alert: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to send clan alert. Check the logs for details.", ephemeral=True)

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
        """View available lore entries and their triggers."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get available triggers
            triggers = self.bot.event_engine.get_available_triggers()
            
            # Create embed for triggers
            trigger_embed = discord.Embed(
                title="Available Event Triggers",
                color=Theme.LORE
            )
            trigger_embed.description = "Use these triggers with `/broadcast_lore`"
            trigger_embed.add_field(
                name="Triggers",
                value="\n".join(f"• {trigger}" for trigger in triggers),
                inline=False
            )
            
            # If tags provided, get matching lore entries
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",")]
                matching_entries = self.bot.event_engine.get_lore_by_tags(tag_list)
                
                if matching_entries:
                    lore_embed = discord.Embed(
                        title=f"Lore Entries Matching Tags: {', '.join(tag_list)}",
                        color=Theme.LORE
                    )
                    
                    for entry in matching_entries:
                        lore_embed.add_field(
                            name=f"{entry['title']} ({entry['trigger']})",
                            value=f"Chapter: {entry['chapter']}\n{entry['snippet']}",
                            inline=False
                        )
                    
                    # Send both embeds
                    await interaction.followup.send(embeds=[trigger_embed, lore_embed], ephemeral=True)
                else:
                    await interaction.followup.send(
                        f"No lore entries found matching tags: {', '.join(tag_list)}",
                        ephemeral=True
                    )
            else:
                # Send just the triggers embed
                await interaction.followup.send(embed=trigger_embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error viewing lore: {e}", exc_info=True)
            await interaction.followup.send("❌ Failed to retrieve lore information. Check the logs for details.", ephemeral=True)

    @app_commands.command(
        name="update",
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

async def setup(bot: HCBot):
    """Adds the AnnouncementCommands cog to the bot."""
    try:
        await bot.add_cog(AnnouncementCommands(bot))
        logger.info("AnnouncementCommands Cog loaded and added to bot successfully.")
    except Exception as e:
        logger.error(f"Failed to load AnnouncementCommands Cog: {e}", exc_info=True)
        raise 