"""
UnifiedDiscordService - Centralized Discord integration service.
Combines message dispatch, template rendering, and channel management.
"""

import discord
from discord.ext import commands
import asyncio
import logging
import threading
import json
import os
from typing import Union, Dict, Any, Optional, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("discord_service")
logger.setLevel(logging.INFO)

class UnifiedDiscordService:
    """
    Centralized Discord integration service that handles:
    - Bot lifecycle management
    - Message/file dispatch
    - Template rendering
    - Channel mapping
    - Status monitoring
    - Event notifications
    - Dreamscape episode management
    - Prompt response handling
    """

    CONFIG_FILE = "config/discord_service.json"
    DEFAULT_TEMPLATE_DIR = "templates/discord"

    def __init__(self, 
                 bot_token: str = None, 
                 default_channel_id: Union[int, str] = None,
                 template_dir: str = None) -> None:
        """
        Initialize UnifiedDiscordService.
        
        Args:
            bot_token: Discord Bot Token (optional, loaded from config if not provided)
            default_channel_id: Default Channel ID (optional, loaded from config if not provided)
            template_dir: Directory containing Discord message templates
        """
        # Core state
        self.is_running: bool = False
        self.start_time: Optional[datetime] = None
        self._lock = threading.Lock()
        
        # Configuration
        self.config: Dict[str, Any] = {
            "bot_token": bot_token or "",
            "default_channel_id": int(default_channel_id) if default_channel_id else 0,
            "channel_mappings": {},
            "allowed_roles": [],
            "auto_responses": {},
            "prompt_channel_map": {},  # Map prompt types to specific channels
            "status_data": {
                "cycle_active": False,
                "current_prompt": None,
                "completed_prompts": [],
                "progress_message": "Idle"
            }
        }
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        
        # Load existing config if available
        self.load_config()
        
        # Initialize template engine
        template_dir = template_dir or self.DEFAULT_TEMPLATE_DIR
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Message queue for async dispatch
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Set up Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # Register event handlers and commands
        self._register_events()
        self._register_commands()
        
        # External logging callback
        self.log_callback = None
        
        logger.info("UnifiedDiscordService initialized")

    def _register_events(self) -> None:
        """Register Discord bot event handlers."""
        
        @self.bot.event
        async def on_ready():
            self._log(f"✅ Discord Bot connected as {self.bot.user}")
            self.is_running = True
            self.start_time = datetime.utcnow()

        @self.bot.event
        async def on_message(message):
            if message.author == self.bot.user:
                return
                
            # Handle auto-responses if configured
            channel_id = str(message.channel.id)
            if channel_id in self.config["auto_responses"]:
                await message.channel.send(self.config["auto_responses"][channel_id])
            
            # Process commands
            await self.bot.process_commands(message)

    def _register_commands(self) -> None:
        """Register Discord bot commands."""
        
        @self.bot.command(name="status")
        async def status_command(ctx):
            """Get current bot status."""
            status = self.get_status()
            embed = discord.Embed(title="Bot Status", color=discord.Color.blue())
            
            # Add status fields
            embed.add_field(name="Status", value="🟢 Online" if status["is_running"] else "🔴 Offline")
            if status["uptime"]:
                hours = int(status["uptime"] / 3600)
                minutes = int((status["uptime"] % 3600) / 60)
                embed.add_field(name="Uptime", value=f"{hours}h {minutes}m")
            embed.add_field(name="Servers", value=str(status["connected_servers"]))
            
            await ctx.send(embed=embed)

        @self.bot.command(name="channels")
        async def channels_command(ctx):
            """List available channels."""
            if not ctx.guild:
                await ctx.send("This command can only be used in a server.")
                return
                
            channels = [c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)]
            embed = discord.Embed(title="Text Channels", color=discord.Color.blue())
            
            for channel in channels:
                embed.add_field(name=channel.name, value=f"ID: {channel.id}", inline=False)
                
            await ctx.send(embed=embed)

    def load_config(self) -> None:
        """Load configuration from file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                self._log("✅ Loaded configuration from file")
            except Exception as e:
                self._log(f"❌ Failed to load config: {e}", level=logging.ERROR)

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            self._log("💾 Saved configuration to file")
        except Exception as e:
            self._log(f"❌ Failed to save config: {e}", level=logging.ERROR)

    def run(self) -> None:
        """Start the Discord bot in a separate thread."""
        if self.is_running:
            self._log("⚠️ Bot is already running", level=logging.WARNING)
            return
            
        if not self.config["bot_token"]:
            self._log("❌ Bot token not configured", level=logging.ERROR)
            return
            
        def run_bot():
            try:
                asyncio.run(self._start_bot())
            except Exception as e:
                self._log(f"❌ Bot error: {e}", level=logging.ERROR)
                self.is_running = False
                
        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()
        self._log("🚀 Bot started in background thread")

    async def _start_bot(self) -> None:
        """Internal coroutine to start the bot and message dispatcher."""
        try:
            # Start message dispatcher
            self.bot.loop.create_task(self._process_message_queue())
            # Start bot
            await self.bot.start(self.config["bot_token"])
        except Exception as e:
            self._log(f"❌ Failed to start bot: {e}", level=logging.ERROR)
            raise

    def stop(self) -> None:
        """Stop the Discord bot."""
        if not self.is_running:
            self._log("⚠️ Bot is not running", level=logging.WARNING)
            return
            
        try:
            # Stop the bot
            if self.bot.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.bot.close(), self.bot.loop)
                future.result(timeout=10)
            
            self.is_running = False
            self.start_time = None
            self._log("✅ Bot stopped successfully")
        except Exception as e:
            self._log(f"❌ Failed to stop bot: {e}", level=logging.ERROR)

    async def _process_message_queue(self) -> None:
        """Process messages from the queue and send them to Discord."""
        while True:
            try:
                msg_data = await self.message_queue.get()
                channel_id = msg_data.get("channel_id", self.config["default_channel_id"])
                content = msg_data.get("content", "")
                file_path = msg_data.get("file_path")
                embed = msg_data.get("embed")
                
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    self._log(f"❌ Channel {channel_id} not found", level=logging.ERROR)
                    continue
                    
                kwargs = {"content": content}
                if file_path:
                    if os.path.exists(file_path):
                        kwargs["file"] = discord.File(file_path)
                    else:
                        self._log(f"❌ File not found: {file_path}", level=logging.ERROR)
                        continue
                if embed:
                    kwargs["embed"] = embed
                    
                await channel.send(**kwargs)
                self._log(f"📤 Sent message to channel {channel_id}")
                    
            except Exception as e:
                self._log(f"❌ Error processing message: {e}", level=logging.ERROR)

    def send_message(self, 
                    content: str, 
                    channel_id: int = None,
                    embed: discord.Embed = None) -> None:
        """
        Queue a message to be sent to Discord.
        
        Args:
            content: The message content to send
            channel_id: Optional channel ID (uses default if not specified)
            embed: Optional Discord embed to send
        """
        if not self.is_running:
            self._log("⚠️ Bot is not running", level=logging.WARNING)
            return
            
        msg_data = {
            "channel_id": channel_id or self.config["default_channel_id"],
            "content": content,
            "embed": embed
        }
        
        asyncio.run_coroutine_threadsafe(
            self.message_queue.put(msg_data), 
            self.bot.loop
        )

    def send_file(self, 
                  file_path: str, 
                  content: str = "", 
                  channel_id: int = None) -> None:
        """
        Queue a file to be sent to Discord.
        
        Args:
            file_path: Path to the file to send
            content: Optional message content to send with the file
            channel_id: Optional channel ID (uses default if not specified)
        """
        if not self.is_running:
            self._log("⚠️ Bot is not running", level=logging.WARNING)
            return
            
        if not os.path.exists(file_path):
            self._log(f"❌ File not found: {file_path}", level=logging.ERROR)
            return
            
        msg_data = {
            "channel_id": channel_id or self.config["default_channel_id"],
            "content": content,
            "file_path": file_path
        }
        
        asyncio.run_coroutine_threadsafe(
            self.message_queue.put(msg_data), 
            self.bot.loop
        )

    def send_template(self, 
                     template_name: str, 
                     context: dict, 
                     channel_id: int = None) -> None:
        """
        Render and send a templated message.
        
        Args:
            template_name: Name of the template file (without extension)
            context: Dictionary of context variables for the template
            channel_id: Optional channel ID (uses default if not specified)
        """
        try:
            template = self.template_env.get_template(f"{template_name}.j2")
            content = template.render(**context)
            self.send_message(content, channel_id)
            self._log(f"✅ Sent templated message using '{template_name}'")
        except Exception as e:
            self._log(f"❌ Template error: {e}", level=logging.ERROR)

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status information."""
        status = {
            "is_running": self.is_running,
            "uptime": None,
            "connected_servers": 0,
            "active_channels": []
        }
        
        if self.is_running and self.start_time:
            status["uptime"] = (datetime.utcnow() - self.start_time).total_seconds()
            if self.bot.is_ready():
                status["connected_servers"] = len(self.bot.guilds)
                status["active_channels"] = [
                    {"id": c.id, "name": c.name} 
                    for g in self.bot.guilds 
                    for c in g.channels
                    if isinstance(c, discord.TextChannel)
                ]
                
        return status

    def set_log_callback(self, callback) -> None:
        """Set external logging callback."""
        self.log_callback = callback

    def _log(self, message: str, level: int = logging.INFO) -> None:
        """Internal logging with optional callback."""
        logger.log(level, message)
        if self.log_callback:
            self.log_callback(message)

    # ----------------------------------------
    # Prompt Channel Management
    # ----------------------------------------
    
    def map_prompt_to_channel(self, prompt_type: str, channel_id: Union[int, str]) -> None:
        """Map a specific prompt type to a channel ID."""
        self.config["prompt_channel_map"][prompt_type] = int(channel_id)
        self.save_config()
        self._log(f"🔗 Mapped prompt '{prompt_type}' to channel {channel_id}")

    def unmap_prompt_channel(self, prompt_type: str) -> None:
        """Remove mapping for a given prompt type."""
        if prompt_type in self.config["prompt_channel_map"]:
            del self.config["prompt_channel_map"][prompt_type]
            self.save_config()
            self._log(f"❌ Unmapped channel for prompt '{prompt_type}'")

    def get_channel_for_prompt(self, prompt_type: str) -> int:
        """Get channel ID for the given prompt type."""
        return self.config["prompt_channel_map"].get(prompt_type, self.config["default_channel_id"])

    # ----------------------------------------
    # Enhanced Message Sending
    # ----------------------------------------
    
    def send_dreamscape_episode(self, 
                              prompt_type: str, 
                              episode_file_path: str, 
                              post_full_text: bool = False) -> None:
        """
        Send a Dreamscape episode either as text or file.
        
        Args:
            prompt_type: The prompt type for channel mapping
            episode_file_path: Path to the episode file
            post_full_text: Whether to post full text if within limits
        """
        if not os.path.exists(episode_file_path):
            self._log(f"❌ Episode file not found: {episode_file_path}", level=logging.ERROR)
            return

        try:
            with open(episode_file_path, "r", encoding="utf-8") as f:
                episode_text = f.read()

            episode_title = os.path.basename(episode_file_path).replace("_", " ").replace(".txt", "")
            channel_id = self.get_channel_for_prompt(prompt_type)

            if post_full_text and len(episode_text) <= 1800:
                content = (
                    f"📜 **New Dreamscape Episode Released!**\n\n"
                    f"**{episode_title}**\n\n{episode_text}"
                )
                self.send_message(content, channel_id)
                self._log(f"✅ Sent Dreamscape episode text for '{prompt_type}'")
            else:
                description = f"📜 **New Dreamscape Episode Released!**\n\n**{episode_title}**"
                self.send_file(episode_file_path, description, channel_id)
                self._log(f"✅ Sent Dreamscape episode file for '{prompt_type}'")
        except Exception as e:
            self._log(f"❌ Failed to send Dreamscape episode: {e}", level=logging.ERROR)

    def send_prompt_response(self, 
                           prompt_type: str, 
                           response_text: str = None, 
                           response_file: str = None) -> None:
        """
        Send a prompt response to Discord.
        
        Args:
            prompt_type: The prompt type for channel mapping
            response_text: Optional response text
            response_file: Optional response file path
        """
        if not self.is_running:
            self._log("⚠️ Bot not running. Cannot send prompt response.", level=logging.WARNING)
            return

        channel_id = self.get_channel_for_prompt(prompt_type)

        if response_file and os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) <= 2000:
                self.send_message(content, channel_id)
            else:
                self.send_file(response_file, "📜 Prompt response", channel_id)
        elif response_text:
            if len(response_text) <= 2000:
                self.send_message(response_text, channel_id)
            else:
                # Create temporary file for long responses
                temp_file = "temp_prompt_response.txt"
                try:
                    with open(temp_file, "w", encoding="utf-8") as f:
                        f.write(response_text)
                    self.send_file(temp_file, "📜 Prompt response", channel_id)
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
        else:
            self._log("⚠️ No response provided to send.", level=logging.WARNING)

    # ----------------------------------------
    # Status Management
    # ----------------------------------------
    
    def update_status(self, key: str, value: Any) -> None:
        """Update internal status information."""
        if key not in self.config["status_data"]:
            self._log(f"⚠️ Unknown status key: {key}", level=logging.WARNING)
            return
        self.config["status_data"][key] = value
        self._log(f"🔧 Updated status_data[{key}] = {value}")
        self.save_config()

    def get_prompt_status(self) -> Dict[str, Any]:
        """Get current prompt cycle status."""
        return self.config["status_data"] 