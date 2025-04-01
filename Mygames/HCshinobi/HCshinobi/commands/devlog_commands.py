"""DevLog commands for the HCshinobi Discord bot.

This module contains commands to post development logs and updates to a designated channel.
"""
import discord
from discord.ext import commands, tasks
from discord import ui
import logging
import datetime
import asyncio
import json
import os
import subprocess
import re
from typing import List, Dict, Optional, Union, Any

logger = logging.getLogger(__name__)

# Constants
DEVLOG_CHANNEL_ID = 1356487107778056214  # The channel ID specified by the user
LOG_FILE = "data/devlog.json"

# Categories for development logs
DEV_CATEGORIES = {
    "in_progress": {"emoji": "🔨", "name": "Work in Progress", "color": discord.Color.blue()},
    "completed": {"emoji": "✅", "name": "Completed", "color": discord.Color.green()},
    "bug": {"emoji": "🐛", "name": "Bug Found", "color": discord.Color.red()},
    "fix": {"emoji": "🔧", "name": "Bug Fixed", "color": discord.Color.gold()},
    "feature": {"emoji": "✨", "name": "New Feature", "color": discord.Color.purple()},
    "announcement": {"emoji": "📢", "name": "Announcement", "color": discord.Color.orange()}
}

# Ollama prompts for Naruto-themed content
OLLAMA_PROMPTS = {
    "bug": "Create a short Naruto-themed bug report about '{issue}'. Style it as if a ninja is reporting a mission failure to the Hokage. Keep it under 300 words.",
    "fix": "Create a short Naruto-themed bug fix announcement about '{issue}'. Style it as if a ninja is reporting a successful mission to the Hokage. Keep it under 300 words.",
    "feature": "Create a short Naruto-themed feature announcement about '{feature}'. Style it as if a ninja is introducing a new jutsu technique to the village. Keep it under 300 words.",
    "announcement": "Create a short Naruto-themed announcement about '{topic}'. Style it as if the Hokage is addressing the entire village. Keep it under 300 words."
}

class DevLogEntry:
    """Represents a development log entry."""
    
    def __init__(self, category: str, title: str, description: str, author_id: int, timestamp: Optional[datetime.datetime] = None):
        """Initialize a development log entry.
        
        Args:
            category: The category of the log entry
            title: The title of the log entry
            description: The description of the log entry
            author_id: The Discord ID of the author
            timestamp: The timestamp of the entry (defaults to now)
        """
        self.category = category
        self.title = title
        self.description = description
        self.author_id = author_id
        self.timestamp = timestamp or datetime.datetime.utcnow()
        self.message_id = None  # ID of the posted message, if any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entry to a dictionary for storage."""
        return {
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "author_id": self.author_id,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DevLogEntry':
        """Create an entry from a dictionary."""
        entry = cls(
            category=data["category"],
            title=data["title"],
            description=data["description"],
            author_id=data["author_id"],
            timestamp=datetime.datetime.fromisoformat(data["timestamp"])
        )
        entry.message_id = data.get("message_id")
        return entry
    
    def create_embed(self) -> discord.Embed:
        """Create a Discord embed for this log entry."""
        category_info = DEV_CATEGORIES.get(self.category, DEV_CATEGORIES["announcement"])
        
        embed = discord.Embed(
            title=f"{category_info['emoji']} {self.title}",
            description=self.description,
            color=category_info["color"],
            timestamp=self.timestamp
        )
        
        embed.set_footer(text=f"{category_info['name']}")
        
        return embed

class DevLogModal(ui.Modal, title="Add Development Log"):
    """Modal for creating a new development log entry."""
    
    category = ui.Select(
        placeholder="Select the log category",
        options=[
            discord.SelectOption(
                label=info["name"],
                value=category,
                emoji=info["emoji"]
            ) for category, info in DEV_CATEGORIES.items()
        ],
        min_values=1,
        max_values=1
    )
    
    title = ui.TextInput(
        label="Log Title",
        placeholder="Enter a title for this log entry",
        min_length=3,
        max_length=100,
        required=True
    )
    
    description = ui.TextInput(
        label="Log Description",
        placeholder="Enter the details for this log entry",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=2000,
        required=True
    )
    
    use_naruto_theme = ui.Select(
        placeholder="Apply Naruto theme?",
        options=[
            discord.SelectOption(
                label="Yes",
                value="yes",
                emoji="✨"
            ),
            discord.SelectOption(
                label="No",
                value="no",
                emoji="📝"
            )
        ],
        min_values=1,
        max_values=1
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission."""
        try:
            category = self.category.values[0]
            title = self.title.value
            description = self.description.value
            apply_theme = self.use_naruto_theme.values[0] == "yes"
            
            # If theme requested, try to generate it
            if apply_theme and self.cog.is_ollama_available():
                themed_description = await self.cog.generate_themed_content(category, description)
                if themed_description:
                    description = themed_description
            
            # Create new log entry
            entry = DevLogEntry(
                category=category,
                title=title,
                description=description,
                author_id=interaction.user.id
            )
            
            # Store and post the entry
            await self.cog.add_log_entry(entry)
            
            # Acknowledge the interaction
            await interaction.response.send_message(
                "✅ Development log entry created and posted to the dev log channel!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error submitting devlog entry: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ An error occurred while creating the log entry.",
                ephemeral=True
            )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle errors in the modal."""
        logger.error(f"Error in DevLogModal: {error}", exc_info=True)
        await interaction.response.send_message(
            "❌ An error occurred. Please try again later.",
            ephemeral=True
        )

class DevLogEntryMenu(ui.View):
    """Menu for interacting with the DevLog system."""
    
    def __init__(self, cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        
        # Add category select to use later
        self.category_select = ui.Select(
            placeholder="Select a category",
            options=[
                discord.SelectOption(
                    label=info["name"],
                    value=category,
                    emoji=info["emoji"]
                ) for category, info in DEV_CATEGORIES.items()
            ],
            min_values=1,
            max_values=1,
            custom_id="category_select"
        )
        self.category_select.callback = self.on_category_select
        self.add_item(self.category_select)
        
        # Initialize state variables
        self.selected_category = None
        self.message = None
        self.phase = "initial"  # Initial, topic, title, preview
    
    async def on_category_select(self, interaction: discord.Interaction):
        """Handle category selection."""
        self.selected_category = self.category_select.values[0]
        self.phase = "topic"
        
        # Ask for topic
        await interaction.response.send_message(
            f"You selected **{DEV_CATEGORIES[self.selected_category]['name']}**. "
            "Please describe the topic or issue in a few words (this will be used for AI generation):",
            ephemeral=True
        )
        
        # Set up a listener for the next message
        def check(message):
            return message.author == interaction.user and message.channel == interaction.channel
        
        try:
            topic_message = await self.cog.bot.wait_for('message', check=check, timeout=60.0)
            await self.process_topic(interaction, topic_message.content)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timed out waiting for a response. Please try again.", ephemeral=True)
            self.stop()
    
    async def process_topic(self, interaction, topic):
        """Process the topic and generate content with Ollama."""
        self.phase = "generating"
        
        await interaction.followup.send(
            "🔄 Generating Naruto-themed content... Please wait.",
            ephemeral=True
        )
        
        # Try to generate content
        themed_content = await self.cog.generate_themed_content(self.selected_category, topic)
        
        if not themed_content:
            await interaction.followup.send(
                "❌ Failed to generate themed content. Please try again or use the manual entry form.",
                ephemeral=True
            )
            self.stop()
            return
        
        # Create preliminary title based on topic
        title = f"{topic.strip().title()}"
        if len(title) > 100:
            title = title[:97] + "..."
        
        # Preview the content
        self.phase = "preview"
        preview_embed = DevLogEntry(
            category=self.selected_category,
            title=title,
            description=themed_content,
            author_id=interaction.user.id
        ).create_embed()
        
        # Create view for confirmation
        confirmation_view = ui.View(timeout=60)
        
        # Add title edit option
        title_button = ui.Button(
            label="Edit Title",
            style=discord.ButtonStyle.secondary,
            custom_id="edit_title"
        )
        
        async def title_callback(title_interaction):
            # Create a modal for title editing
            title_modal = ui.Modal(title="Edit Log Title")
            title_input = ui.TextInput(
                label="Title",
                placeholder="Enter a title for this log entry",
                default=title,
                min_length=3,
                max_length=100,
                required=True
            )
            title_modal.add_item(title_input)
            
            async def on_title_submit(modal_interaction):
                nonlocal title
                nonlocal preview_embed
                
                # Update title
                title = title_input.value
                
                # Update preview
                preview_embed.title = f"{DEV_CATEGORIES[self.selected_category]['emoji']} {title}"
                await title_interaction.edit_original_response(
                    content="Preview updated! Ready to post?",
                    embed=preview_embed,
                    view=confirmation_view
                )
            
            title_modal.on_submit = on_title_submit
            await title_interaction.response.send_modal(title_modal)
        
        title_button.callback = title_callback
        confirmation_view.add_item(title_button)
        
        # Add confirmation buttons
        confirm_button = ui.Button(
            label="Post to DevLog",
            style=discord.ButtonStyle.success,
            custom_id="confirm"
        )
        
        async def confirm_callback(confirm_interaction):
            # Create and post the entry
            entry = DevLogEntry(
                category=self.selected_category,
                title=title,
                description=themed_content,
                author_id=interaction.user.id
            )
            
            await self.cog.add_log_entry(entry)
            await confirm_interaction.response.send_message(
                "✅ Development log entry posted to the dev log channel!",
                ephemeral=True
            )
            self.stop()
        
        confirm_button.callback = confirm_callback
        confirmation_view.add_item(confirm_button)
        
        # Add cancel button
        cancel_button = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="cancel"
        )
        
        async def cancel_callback(cancel_interaction):
            await cancel_interaction.response.send_message(
                "❌ DevLog creation cancelled.",
                ephemeral=True
            )
            self.stop()
        
        cancel_button.callback = cancel_callback
        confirmation_view.add_item(cancel_button)
        
        # Show preview with confirmation options
        await interaction.followup.send(
            content="Here's a preview of your DevLog entry. Ready to post?",
            embed=preview_embed,
            view=confirmation_view,
            ephemeral=True
        )
    
    async def on_timeout(self):
        """Handle timeout."""
        if self.message:
            await self.message.edit(content="The DevLog menu has timed out. Please try again.", view=None)

class DevLogCommands(commands.Cog):
    """Commands for developer logging and updates."""
    
    def __init__(self, bot):
        """Initialize the DevLog cog.
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.log_entries: List[DevLogEntry] = []
        self.log_file = LOG_FILE
        
        # Make sure the data directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Load existing log entries
        self.load_logs()
        
        # Start the summary posting task
        self.weekly_summary.start()
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.weekly_summary.cancel()
    
    def load_logs(self):
        """Load log entries from the log file."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                
                self.log_entries = [DevLogEntry.from_dict(entry) for entry in data]
                logger.info(f"Loaded {len(self.log_entries)} development log entries")
            except Exception as e:
                logger.error(f"Error loading development logs: {e}", exc_info=True)
                self.log_entries = []
        else:
            logger.info("No existing development log file found, starting fresh")
            self.log_entries = []
    
    def save_logs(self):
        """Save log entries to the log file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump([entry.to_dict() for entry in self.log_entries], f, indent=2)
            logger.info(f"Saved {len(self.log_entries)} development log entries")
        except Exception as e:
            logger.error(f"Error saving development logs: {e}", exc_info=True)
    
    async def add_log_entry(self, entry: DevLogEntry):
        """Add a new log entry and post it to the dev log channel.
        
        Args:
            entry: The log entry to add
        """
        # Get the dev log channel
        channel = self.bot.get_channel(DEVLOG_CHANNEL_ID)
        if not channel:
            logger.error(f"Could not find devlog channel with ID {DEVLOG_CHANNEL_ID}")
            return
        
        # Post the entry to the channel
        try:
            embed = entry.create_embed()
            message = await channel.send(embed=embed)
            entry.message_id = message.id
            
            # Store the entry
            self.log_entries.append(entry)
            self.save_logs()
            
            logger.info(f"Added and posted dev log entry: {entry.title}")
        except Exception as e:
            logger.error(f"Error posting dev log entry: {e}", exc_info=True)
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama is available on the system."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2
            )
            return "mistral" in result.stdout.lower()
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            return False
    
    async def generate_themed_content(self, category: str, topic: str) -> Optional[str]:
        """Generate Naruto-themed content using Ollama.
        
        Args:
            category: The category of the log entry
            topic: The topic or issue to generate content about
            
        Returns:
            The generated content or None if generation failed
        """
        if not self.is_ollama_available():
            logger.warning("Ollama is not available for content generation")
            return None
        
        # Select appropriate prompt template
        prompt_template = OLLAMA_PROMPTS.get(
            category,
            OLLAMA_PROMPTS["announcement"]  # Default to announcement prompt
        )
        
        # Format the prompt
        if "issue" in prompt_template:
            prompt = prompt_template.format(issue=topic)
        elif "feature" in prompt_template:
            prompt = prompt_template.format(feature=topic)
        else:
            prompt = prompt_template.format(topic=topic)
        
        try:
            # Run Ollama process to generate content
            result = await asyncio.create_subprocess_exec(
                "ollama", "run", "mistral", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Ollama generation failed: {stderr.decode()}")
                return None
            
            # Clean and format the output
            content = stdout.decode().strip()
            
            # Remove leading/trailing quotes if present
            content = re.sub(r'^["\']+|["\']+$', '', content)
            
            # Check for a reasonable length
            if len(content) < 20:
                logger.warning(f"Generated content too short: {content}")
                return None
                
            return content
        except Exception as e:
            logger.error(f"Error generating content with Ollama: {e}")
            return None
    
    @tasks.loop(hours=168)  # Weekly (7 days * 24 hours)
    async def weekly_summary(self):
        """Post a weekly summary of development logs."""
        # Skip if no entries exist
        if not self.log_entries:
            return
        
        # Get the dev log channel
        channel = self.bot.get_channel(DEVLOG_CHANNEL_ID)
        if not channel:
            logger.error(f"Could not find devlog channel with ID {DEVLOG_CHANNEL_ID}")
            return
        
        # Calculate the start of the summary period (7 days ago)
        now = datetime.datetime.utcnow()
        start_date = now - datetime.timedelta(days=7)
        
        # Filter entries from the last week
        recent_entries = [e for e in self.log_entries if e.timestamp >= start_date]
        
        # Skip if no recent entries
        if not recent_entries:
            return
        
        # Create the summary embed
        embed = discord.Embed(
            title="📋 Weekly Development Summary",
            description=f"Here's what happened in Shinobi Chronicles development over the past week:",
            color=discord.Color.teal(),
            timestamp=now
        )
        
        # Group entries by category
        categories = {}
        for entry in recent_entries:
            if entry.category not in categories:
                categories[entry.category] = []
            categories[entry.category].append(entry)
        
        # Add a field for each category
        for category, entries in categories.items():
            category_info = DEV_CATEGORIES.get(category, DEV_CATEGORIES["announcement"])
            
            # Create a list of entries in this category
            entry_list = "\n".join(f"• **{e.title}**" for e in entries[:5])
            
            # Add ellipsis if there are more entries
            if len(entries) > 5:
                entry_list += f"\n• *...and {len(entries) - 5} more*"
            
            embed.add_field(
                name=f"{category_info['emoji']} {category_info['name']} ({len(entries)})",
                value=entry_list,
                inline=False
            )
        
        # Add a count of total entries
        embed.set_footer(text=f"Total updates: {len(recent_entries)}")
        
        # Post the summary
        try:
            await channel.send(embed=embed)
            logger.info(f"Posted weekly development summary with {len(recent_entries)} entries")
        except Exception as e:
            logger.error(f"Error posting weekly development summary: {e}", exc_info=True)
    
    @weekly_summary.before_loop
    async def before_weekly_summary(self):
        """Wait until the bot is ready before starting the weekly summary task."""
        await self.bot.wait_until_ready()
        
        # Wait until next Sunday at midnight to post the first summary
        now = datetime.datetime.utcnow()
        days_until_sunday = (6 - now.weekday()) % 7  # 0 = Monday, 6 = Sunday
        if days_until_sunday == 0 and now.hour >= 0:  # It's already Sunday after midnight
            days_until_sunday = 7  # Wait until next Sunday
            
        target_datetime = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=days_until_sunday)
        seconds_to_wait = (target_datetime - now).total_seconds()
        
        logger.info(f"Weekly summary will start in {seconds_to_wait / 3600:.1f} hours")
        await asyncio.sleep(seconds_to_wait)
    
    @commands.command(
        name="devlog",
        aliases=["dev_log", "dev"],
        description="Post a development log entry",
        help="Post a development update to the devlog channel."
    )
    @commands.has_permissions(administrator=True)
    async def devlog_prefix(self, ctx, category: str, title: str, *, description: str):
        """Post a development log entry using a prefix command.
        
        Args:
            ctx: The command context
            category: The category of the log entry
            title: The title of the log entry
            description: The description of the log entry
        """
        # Validate the category
        if category not in DEV_CATEGORIES:
            categories_list = ", ".join(f"`{c}`" for c in DEV_CATEGORIES.keys())
            await ctx.send(f"❌ Invalid category! Available categories: {categories_list}")
            return
        
        # Create and post the entry
        entry = DevLogEntry(
            category=category,
            title=title,
            description=description,
            author_id=ctx.author.id
        )
        
        await self.add_log_entry(entry)
        await ctx.send("✅ Development log entry created and posted to the dev log channel!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Handle the on_ready event."""
        logger.info("DevLog commands cog is ready")
        
        # Register slash commands
        self.register_app_commands()
    
    def register_app_commands(self):
        """Register application commands for slash command support."""
        # Remove existing commands with this name to avoid conflicts
        to_remove = []
        for cmd in self.bot.tree.get_commands():
            if cmd.name in ["devlog"]:
                to_remove.append(cmd)
        
        for cmd in to_remove:
            self.bot.tree.remove_command(cmd.name)
        
        # Add the devlog slash command
        @self.bot.tree.command(name="devlog", description="Post a development log entry")
        @discord.app_commands.describe(
            interactive="Whether to use the interactive menu (with AI generation) or a form"
        )
        @discord.app_commands.default_permissions(administrator=True)
        async def devlog_slash(interaction: discord.Interaction, interactive: bool = True):
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                return
            
            # For interactive mode, use the menu system
            if interactive:
                # Check if ollama is available first
                if self.is_ollama_available():
                    # Start the interactive menu
                    menu = DevLogEntryMenu(self)
                    await interaction.response.send_message(
                        "Welcome to the DevLog system! Please select a category to begin:",
                        view=menu,
                        ephemeral=True
                    )
                    menu.message = await interaction.original_response()
                else:
                    # Warn that AI generation isn't available
                    await interaction.response.send_message(
                        "⚠️ Ollama with Mistral model is not available. Falling back to manual entry form.",
                        ephemeral=True
                    )
                    
                    # Create modal for manual entry
                    modal = DevLogModal(self)
                    await interaction.response.send_modal(modal)
            else:
                # Use the manual form
                try:
                    modal = DevLogModal(self)
                    await interaction.response.send_modal(modal)
                except Exception as e:
                    logger.error(f"Error sending devlog modal: {e}", exc_info=True)
                    await interaction.response.send_message(
                        "❌ An error occurred while creating the log form.",
                        ephemeral=True
                    )
        
        logger.info("DevLog slash commands registered")

    @commands.command(
        name="devlog_test",
        description="Post a test entry to the devlog channel",
        help="Post a Naruto-themed test message to the devlog channel."
    )
    @commands.has_permissions(administrator=True)
    async def devlog_test(self, ctx):
        """Post a test entry to the devlog channel.
        
        Args:
            ctx: The command context
        """
        # Post a themed entry right away
        entry = DevLogEntry(
            category="bug",
            title="Jutsu Malfunction Report",
            description=(
                "Esteemed shinobi of the village, this is an urgent report from the Debugging Division. "
                "Our jutsu scrolls are experiencing a chakra disruption.\n\n"
                "**Mission Status**: Our ninja commands are unable to flow chakra properly through the "
                "Discord channels. The forbidden error '403' has been cast upon our techniques.\n\n"
                "**Investigation**: Our elite ANBU debugging squad suspects that our bot requires additional "
                "permissions to channel its chakra. We are analyzing the chakra pathways now.\n\n"
                "**Next Steps**: The Hokage has assigned a team of jōnin developers to resolve this issue. "
                "Please stand by as we perform the necessary hand signs to restore functionality."
            ),
            author_id=ctx.author.id
        )
        
        await self.add_log_entry(entry)
        await ctx.send("✅ Test entry posted to the devlog channel!")

async def setup(bot):
    """Set up the DevLog commands cog."""
    await bot.add_cog(DevLogCommands(bot)) 