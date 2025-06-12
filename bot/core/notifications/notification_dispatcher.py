import os
import logging
import discord
from typing import Optional, List, Dict
from discord import Webhook

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    """Handles sending notifications via webhook with fallback support."""
    
    def __init__(
        self,
        webhook: Optional[Webhook] = None,
        fallback_channel=None,
        clan_channels: Optional[Dict[str, discord.TextChannel]] = None
    ):
        """Initialize the notification dispatcher.
        
        Args:
            webhook: Discord webhook for sending notifications
            fallback_channel: Channel to use if webhook fails
            clan_channels: Dictionary of clan-specific announcement channels
        """
        self.webhook = webhook
        self.fallback_channel = fallback_channel
        self.clan_channels = clan_channels or {}

    async def dispatch(
        self,
        embed: discord.Embed,
        ping_everyone: bool = False,
        target_clans: Optional[List[str]] = None
    ) -> None:
        """Dispatch a notification using webhook or fallback channel.
        
        Args:
            embed: Discord embed to send
            ping_everyone: Whether to ping @everyone
            target_clans: List of clan names to target for clan-specific announcements
        """
        content = "@everyone" if ping_everyone else None

        # Try webhook first
        if self.webhook:
            try:
                await self.webhook.send(content=content, embed=embed)
                logger.info("Notification sent via webhook successfully")
            except Exception as e:
                logger.warning(f"Webhook failed, fallback triggered: {e}")

        # Send to fallback channel if webhook failed or not configured
        if self.fallback_channel:
            try:
                await self.fallback_channel.send(content=content or "", embed=embed)
                logger.info("Notification sent via fallback channel successfully")
            except Exception as e:
                logger.error(f"Failed to send notification via fallback: {e}")

        # Send to clan-specific channels if requested
        if target_clans and self.clan_channels:
            for clan in target_clans:
                if clan in self.clan_channels:
                    try:
                        channel = self.clan_channels[clan]
                        clan_content = f"<@&{channel.guild.me.top_role.id}>" if ping_everyone else None
                        await channel.send(content=clan_content or "", embed=embed)
                        logger.info(f"Notification sent to clan channel: {clan}")
                    except Exception as e:
                        logger.error(f"Failed to send notification to clan channel {clan}: {e}")

    def add_clan_channel(self, clan_name: str, channel: discord.TextChannel) -> None:
        """Add a clan-specific announcement channel.
        
        Args:
            clan_name: Name of the clan
            channel: Discord text channel for clan announcements
        """
        self.clan_channels[clan_name] = channel
        logger.info(f"Added clan channel for {clan_name}: {channel.name}")

    def remove_clan_channel(self, clan_name: str) -> None:
        """Remove a clan-specific announcement channel.
        
        Args:
            clan_name: Name of the clan to remove
        """
        if clan_name in self.clan_channels:
            del self.clan_channels[clan_name]
            logger.info(f"Removed clan channel for {clan_name}") 