"""Commands for managing announcements and system updates."""
import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class AnnouncementCommands(commands.Cog):
    """Commands for managing announcements."""
    
    def __init__(self, bot):
        """Initialize announcement commands.
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
    async def cog_load(self):
        """Called when the cog is loaded."""
        self.logger.info("AnnouncementCommands cog loaded")
        self.register_app_commands()
        
    def register_app_commands(self):
        """Register slash commands for this cog."""
        try:
            # We don't need to manually register commands here
            # They will be automatically registered through the decorated methods
            self.logger.info("Announcement commands registered successfully")
        except Exception as e:
            self.logger.error(f"Error registering announcement commands: {e}")
            raise
            
    @commands.command(name="announce")
    @commands.has_permissions(administrator=True)
    async def announce_prefix(self, ctx, *, message: str):
        """[Admin] Send an announcement to the announcement channel."""
        try:
            # Create an embed for the announcement
            embed = discord.Embed(
                title="📢 Announcement",
                description=message,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f"Announced by {ctx.author.name}")
            
            # Send the announcement
            await self.bot.send_announcement(
                title="📢 Announcement",
                description=message,
                color=discord.Color.blue()
            )
            
            await ctx.send("✅ Announcement sent!")
        except Exception as e:
            self.logger.error(f"Error in announce command: {e}")
            await ctx.send("❌ Failed to send announcement.")

    @app_commands.command(
        name="update",
        description="[Admin] Announce a system update"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def update_slash(self, interaction: discord.Interaction, version: str, changes: str, downtime: Optional[str] = None):
        """Announce a system update."""
        await self.update(interaction, version, changes, downtime)
            
    @app_commands.command(
        name="battle_announce",
        description="[Admin] Announce an upcoming battle"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def battle_announce_slash(self, interaction: discord.Interaction, fighter_a: str, fighter_b: str, arena: str, time: str):
        """Announce an upcoming battle."""
        await self.battle_announce(interaction, fighter_a, fighter_b, arena, time)
            
    @app_commands.command(
        name="lore_drop",
        description="[Admin] Share a piece of lore"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def lore_drop_slash(self, interaction: discord.Interaction, title: str, content: str, chapter: Optional[str] = None):
        """Share a piece of lore."""
        await self.lore_drop(interaction, title, content, chapter)
            
    @app_commands.command(
        name="maintenance",
        description="[Admin] Announce maintenance mode"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def maintenance_slash(self, interaction: discord.Interaction, reason: str, duration: Optional[str] = None):
        """Announce maintenance mode."""
        await self.maintenance(interaction, reason, duration)
            
    @app_commands.command(
        name="countdown",
        description="[Admin] Start a countdown for system maintenance"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def countdown_slash(self, interaction: discord.Interaction, minutes: int, reason: str):
        """Start a countdown for system maintenance."""
        await self.countdown(interaction, minutes, reason)

    async def update(self, interaction: discord.Interaction, version: str, changes: str, downtime: Optional[str] = None):
        """Announce a system update."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title=f"🔄 System Update v{version}",
                description=f"**Changes:**\n{changes}",
                color=discord.Color.blue()
            )
            
            if downtime:
                embed.add_field(
                    name="⏰ Downtime",
                    value=downtime,
                    inline=False
                )
                
            embed.set_footer(text=f"Update announced by {interaction.user.name}")
            
            await self.bot.send_announcement(
                title=f"🔄 System Update v{version}",
                description=f"**Changes:**\n{changes}",
                color=discord.Color.blue()
            )
            
            await interaction.followup.send("✅ Update announcement sent!", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error in update command: {e}")
            await interaction.followup.send("❌ Failed to send update announcement.", ephemeral=True)

    async def battle_announce(self, interaction: discord.Interaction, fighter_a: str, fighter_b: str, arena: str, time: str):
        """Announce an upcoming battle."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title="⚔️ Battle Announcement",
                description=f"**{fighter_a}** vs **{fighter_b}**",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="📍 Location",
                value=arena,
                inline=True
            )
            
            embed.add_field(
                name="⏰ Time",
                value=time,
                inline=True
            )
            
            embed.set_footer(text=f"Announced by {interaction.user.name}")
            
            await self.bot.send_announcement(
                title="⚔️ Battle Announcement",
                description=f"**{fighter_a}** vs **{fighter_b}**\n\n**Location:** {arena}\n**Time:** {time}",
                color=discord.Color.red()
            )
            
            await interaction.followup.send("✅ Battle announcement sent!", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error in battle_announce command: {e}")
            await interaction.followup.send("❌ Failed to send battle announcement.", ephemeral=True)

    async def lore_drop(self, interaction: discord.Interaction, title: str, content: str, chapter: Optional[str] = None):
        """Share a piece of lore."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title=f"📚 {title}",
                description=content,
                color=discord.Color.purple()
            )
            
            if chapter:
                embed.add_field(
                    name="📑 Chapter",
                    value=chapter,
                    inline=False
                )
                
            embed.set_footer(text=f"Shared by {interaction.user.name}")
            
            await self.bot.send_announcement(
                title=f"📚 {title}",
                description=f"{content}\n\n**Chapter:** {chapter}" if chapter else content,
                color=discord.Color.purple()
            )
            
            await interaction.followup.send("✅ Lore drop sent!", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error in lore_drop command: {e}")
            await interaction.followup.send("❌ Failed to send lore drop.", ephemeral=True)

    async def maintenance(self, interaction: discord.Interaction, reason: str, duration: Optional[str] = None):
        """Announce maintenance mode."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title="🔧 Maintenance Mode",
                description=f"**Reason:**\n{reason}",
                color=discord.Color.orange()
            )
            
            if duration:
                embed.add_field(
                    name="⏱️ Expected Duration",
                    value=duration,
                    inline=False
                )
                
            embed.set_footer(text=f"Announced by {interaction.user.name}")
            
            await self.bot.send_announcement(
                title="🔧 Maintenance Mode",
                description=f"**Reason:**\n{reason}\n\n**Duration:** {duration}" if duration else f"**Reason:**\n{reason}",
                color=discord.Color.orange()
            )
            
            await interaction.followup.send("✅ Maintenance announcement sent!", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error in maintenance command: {e}")
            await interaction.followup.send("❌ Failed to send maintenance announcement.", ephemeral=True)

    async def countdown(self, interaction: discord.Interaction, minutes: int, reason: str):
        """Start a countdown for system maintenance."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get announcement channel using bot instance
            channel = self.bot.get_channel(self.bot.announcement_channel_id)
            if not channel:
                await interaction.followup.send("❌ Announcement channel not found! Check bot configuration.", ephemeral=True)
                return
            
            # Create initial embed
            embed = discord.Embed(
                title="⚠️ System Maintenance Countdown",
                description=f"**Reason:** {reason}\n\n**Time Remaining:** {minutes} minutes",
                color=discord.Color.red()
            )
            embed.set_footer(text="Stay tuned for updates!")
            
            # Send initial message
            message = await channel.send(embed=embed)
            
            # Start countdown
            for i in range(minutes, 0, -1):
                if i % 5 == 0 or i <= 5:  # Update every 5 minutes or last 5 minutes
                    embed.description = f"**Reason:** {reason}\n\n**Time Remaining:** {i} minutes"
                    await message.edit(embed=embed)
                    await asyncio.sleep(60)  # Wait 1 minute
                else:
                    await asyncio.sleep(60)  # Wait 1 minute
            
            # Final message
            embed.description = f"**Reason:** {reason}\n\n**Time Remaining:** 0 minutes\n\nSystem is now going down for maintenance!"
            await message.edit(embed=embed)
            
            await interaction.followup.send("✅ Countdown completed!", ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in countdown command: {e}")
            await interaction.followup.send("❌ Failed to start countdown. Please try again.", ephemeral=True)

async def setup(bot):
    """Set up the announcement commands cog."""
    await bot.add_cog(AnnouncementCommands(bot)) 