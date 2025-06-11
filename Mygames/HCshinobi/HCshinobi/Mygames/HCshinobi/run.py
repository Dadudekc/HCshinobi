"""Main entry point for the HCshinobi Discord bot."""
import os
import logging
import discord
from discord.ext import commands, tasks
import datetime
from dotenv import load_dotenv
import asyncio

from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.training_system import TrainingSystem
from HCshinobi.core.quest_system import QuestSystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.clan_missions import ClanMissions
from HCshinobi.core.loot_system import LootSystem
from HCshinobi.core.room_system import RoomSystem
from HCshinobi.commands.currency_commands import CurrencyCommands
from HCshinobi.commands.character_commands import CharacterCommands
from HCshinobi.commands.battle_commands import BattleCommands
from HCshinobi.commands.training_commands import TrainingCommands
from HCshinobi.commands.quest_commands import QuestCommands
from HCshinobi.commands.clan_commands import ClanCommands
from HCshinobi.commands.clan_mission_commands import ClanMissionCommands
from HCshinobi.commands.loot_commands import LootCommands
from HCshinobi.commands.room_commands import RoomCommands
from HCshinobi.commands.devlog_commands import DevLogCommands  # Import the new DevLog cog
from HCshinobi.commands.announcement_commands import AnnouncementCommands  # Import the announcement commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ShinobiHelpCommand(commands.HelpCommand):
    """Custom help command for the Shinobi bot."""
    
    async def send_bot_help(self, mapping):
        """Send help for all commands."""
        embed = discord.Embed(
            title="🌀 Shinobi Bot Commands",
            description="Use `!help <command>` for more info on a command.\n"
                      "Use `!help <category>` for more info on a category.",
            color=discord.Color.blue()
        )
        
        # Add a note about prefix commands
        embed.add_field(
            name="⚠️ Command System",
            value="All commands use the `!` prefix.\n"
                "Example: Use `!create` to create a character",
            inline=False
        )
        
        # Group commands by cog
        for cog, cmds in mapping.items():
            if not cmds:
                continue
                
            cog_name = getattr(cog, "qualified_name", "No Category")
            if cog_name == "No Category":
                continue
                
            # Filter out hidden commands
            filtered_cmds = [cmd for cmd in cmds if not cmd.hidden]
            if not filtered_cmds:
                continue
                
            # Format command list
            cmd_list = ", ".join(f"`{cmd.name}`" for cmd in filtered_cmds)
            embed.add_field(
                name=f"📚 {cog_name}",
                value=cmd_list,
                inline=False
            )
        
        embed.set_footer(text="Tip: Use !help <command> to see more details")
        await self.get_destination().send(embed=embed)
        
    async def send_command_help(self, command):
        """Send help for a specific command."""
        embed = discord.Embed(
            title=f"Command: !{command.name}",
            description=command.help or "No description available.",
            color=discord.Color.green()
        )
        
        # Add usage
        usage = self.get_command_signature(command)
        embed.add_field(
            name="Usage",
            value=f"`{usage}`",
            inline=False
        )
        
        # Add aliases if they exist
        if command.aliases:
            aliases = ", ".join(f"`!{alias}`" for alias in command.aliases)
            embed.add_field(
                name="Aliases",
                value=aliases,
                inline=False
            )
            
        # Add cooldown if it exists
        if command._buckets and command._buckets._cooldown:
            cooldown = command._buckets._cooldown
            embed.add_field(
                name="Cooldown",
                value=f"{cooldown.rate} use(s) every {cooldown.per:.0f} seconds",
                inline=False
            )
            
        await self.get_destination().send(embed=embed)
        
    async def send_cog_help(self, cog):
        """Send help for a specific cog."""
        embed = discord.Embed(
            title=f"{cog.qualified_name} Commands",
            description=cog.__doc__ or "No description available.",
            color=discord.Color.gold()
        )
        
        # Add commands
        for command in cog.get_commands():
            if command.hidden:
                continue
                
            embed.add_field(
                name=f"!{command.name}",
                value=command.description or "No description available.",
                inline=False
            )
            
        embed.set_footer(text="Use !help <command> for more details on a command")
        await self.get_destination().send(embed=embed)
        
    async def send_error_message(self, error):
        """Send error message when help command fails."""
        embed = discord.Embed(
            title="Error",
            description=error,
            color=discord.Color.red()
        )
        await self.get_destination().send(embed=embed)

def get_discord_token():
    """Get the Discord token from environment variables."""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("Discord token not found! Please set the DISCORD_BOT_TOKEN environment variable.")
        logger.info("You can set it by:")
        logger.info("1. Creating a .env file with DISCORD_BOT_TOKEN=your_token_here")
        logger.info("2. Setting it in your system environment variables")
        logger.info("3. Setting it directly in the command line: set DISCORD_BOT_TOKEN=your_token_here")
        raise ValueError("Discord token not found in environment variables")
    return token

class ShinobiBot(commands.Bot):
    """Main bot class for HCshinobi."""
    
    def __init__(self):
        """Initialize the bot and its systems."""
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',  # Use only ! as the command prefix
            intents=intents,
            help_command=ShinobiHelpCommand()
        )
        
        # Define special channels
        self.command_channel_id = 1356639366742802603
        self.announcement_channel_id = 1356639366742802603  # Using the same channel for now, change as needed
        
        # Create data directory
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize core systems
        self.currency_system = CurrencySystem(self.data_dir)
        self.character_system = CharacterSystem(self.data_dir)
        self.battle_system = BattleSystem(
            character_system=self.character_system,
            data_dir=self.data_dir
        )
        self.training_system = TrainingSystem(self.data_dir, self.character_system, self.currency_system)
        self.quest_system = QuestSystem(self.data_dir)
        self.clan_system = ClanSystem(self.data_dir)
        self.clan_missions = ClanMissions(self.data_dir)
        self.loot_system = LootSystem(self.data_dir, self.currency_system)
        self.room_system = RoomSystem(self.data_dir, self.battle_system)
        self.clan_data = self.clan_system.CLANS  # Access clan data from clan system
    
    async def setup_hook(self):
        """Set up the bot's command handlers."""
        # Add command handlers to the bot
        await self.add_cog(CurrencyCommands(self, self.currency_system, self.clan_system))
        await self.add_cog(CharacterCommands(self, self.character_system, self.clan_data))
        await self.add_cog(BattleCommands(self, self.battle_system, self.character_system))
        await self.add_cog(TrainingCommands(self, self.training_system, self.character_system))
        await self.add_cog(QuestCommands(self, self.quest_system, self.clan_data))
        await self.add_cog(ClanCommands(self, self.clan_system, self.clan_missions))
        await self.add_cog(ClanMissionCommands(self, self.clan_missions, self.clan_system))
        await self.add_cog(LootCommands(self, self.loot_system))
        await self.add_cog(RoomCommands(self, self.room_system))
        await self.add_cog(DevLogCommands(self))  # Add the DevLog cog
        await self.add_cog(AnnouncementCommands(self))  # Add the announcement commands
        
        # Simple ping command for testing
        @self.command(name="ping")
        async def ping_prefix(ctx):
            """Respond with Pong!"""
            await ctx.send(f"Pong! Bot latency is {round(self.latency * 1000)}ms")
            
        # Skip sync_commands since we're only using prefix commands now
        logger.info(f"Registered prefix commands: {[cmd.name for cmd in self.commands]}")
        
        # Set a custom status message
        await self.change_presence(
            activity=discord.Game(name="!help"),
            status=discord.Status.online
        )
    
    async def on_ready(self):
        """Handle bot ready event."""
        logger.info(f"Logged in as {self.user.name}")
        logger.info("Bot is ready!")
        logger.info("IMPORTANT: The bot now uses prefix commands (!) only")
        
        # Print the bot's invite link for easier adding to servers
        app_info = await self.application_info()
        permissions = discord.Permissions(
            send_messages=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_messages=True,
            add_reactions=True,
            use_external_emojis=True,
            read_message_history=True,
            manage_roles=True,
            manage_channels=True
        )
        invite_link = discord.utils.oauth_url(app_info.id, permissions=permissions)
        logger.info(f"Bot invite link: {invite_link}")
        
        # Log registered commands
        logger.info(f"Registered prefix commands: {[cmd.name for cmd in self.commands]}")
        
        # Set a custom status message
        await self.change_presence(
            activity=discord.Game(name="!help"),
            status=discord.Status.online
        )
        
        # Start the battle cleanup task
        self.battle_cleanup_task.start()
    
    @tasks.loop(hours=6)
    async def battle_cleanup_task(self):
        """Background task to clean up inactive battles every 6 hours."""
        try:
            logger.info("Running scheduled inactive battle cleanup...")
            await self.battle_system.cleanup_inactive_battles()
            logger.info("Inactive battle cleanup completed")
        except Exception as e:
            logger.error(f"Error in battle cleanup task: {e}", exc_info=True)
    
    @battle_cleanup_task.before_loop
    async def before_battle_cleanup(self):
        """Wait until the bot is ready before starting the battle cleanup task."""
        await self.wait_until_ready()
    
    async def on_message(self, message):
        """Handle incoming messages."""
        # Ignore our own messages
        if message.author == self.user or message.author.bot:
            return
        
        # DEBUGGING: Process all commands regardless of channel
        # Award chat rewards for non-command messages if they're not commands
        if not message.content.startswith('!'):
            self.currency_system.award_chat_reward(str(message.author.id))
        
        # Log command attempts for debugging
        if message.content.startswith('!'):
            cmd = message.content.split()[0][1:] if len(message.content) > 1 else ""
            if cmd:  # Only log if there's an actual command
                logger.info(f"Command attempt: {message.content} by {message.author}")
        
        # Process commands - REMOVED permission checks for debugging
        await self.process_commands(message)
    
    async def process_commands(self, message):
        """Process commands, override to skip command processing for certain cases."""
        # DEBUGGING: Log all command processing attempts
        if message.content.startswith('!'):
            logger.info(f"Processing command: {message.content} in channel {message.channel.name}")
            
        # Process the command normally - removed all checks
        await super().process_commands(message)

    async def on_member_join(self, member):
        """Send welcome message to new members."""
        try:
            # Create a welcome embed
            embed = discord.Embed(
                title=f"Welcome to the server, {member.display_name}!",
                description="Begin your journey as a shinobi with these essential commands:",
                color=discord.Color.green()
            )
            
            # Add beginner commands with categorization
            embed.add_field(
                name="📚 Getting Started (Character)",
                value=(
                    "• `!create <name>` - Create your character\n"
                    "• `!profile` - View your character's profile\n"
                    "• `!assign_clan` - Join a clan\n"
                    "• `!status` - Check your character's current status"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💰 Economy & Items",
                value=(
                    "• `!daily` - Claim your daily reward\n"
                    "• `!balance` - Check your current Ryō balance\n"
                    "• `!inventory` - View your items\n"
                    "• `!loot` - Collect loot from your location"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📈 Progression",
                value=(
                    "• `!train` - Train to improve your stats\n"
                    "• `!quest` - Accept and view available quests\n"
                    "• `!levelup` - Level up when you have enough experience\n"
                    "• `!clan_missions` - Complete missions for your clan"
                ),
                inline=False
            )
            
            # Add note about command types
            embed.add_field(
                name="⚠️ Command Types",
                value="All commands use the `!` prefix.\nExample: `!create`, `!daily`, etc.",
                inline=False
            )
            
            embed.set_footer(text="Have fun and enjoy your adventure in the ninja world!")
            
            # Send welcome message as a DM
            await member.send(embed=embed)
            
            # Also send to the system channel if available
            if member.guild.system_channel:
                simple_embed = discord.Embed(
                    title=f"Welcome {member.display_name}!",
                    description=f"Welcome to the server, {member.mention}! Check your DMs for info on how to get started.",
                    color=discord.Color.blue()
                )
                await member.guild.system_channel.send(embed=simple_embed)
                
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
            
    async def send_announcement(self, title: str, description: str, color: discord.Color = discord.Color.blue()):
        """Send an announcement to the announcement channel.
        
        This is used by the AnnouncementCommands cog to send announcements.
        
        Args:
            title: The title of the announcement
            description: The description/content of the announcement
            color: The color of the embed
        
        Returns:
            The message object that was sent, or None if there was an error
        """
        try:
            # Find the announcement channel
            for guild in self.guilds:
                channel = guild.get_channel(self.announcement_channel_id)
                if channel:
                    # Create embed for the announcement
                    embed = discord.Embed(
                        title=title,
                        description=description,
                        color=color,
                        timestamp=datetime.datetime.utcnow()
                    )
                    
                    # Send the announcement
                    message = await channel.send(embed=embed)
                    logger.info(f"Announcement sent: {title}")
                    return message
                    
            logger.warning(f"Announcement channel not found in any guild: {self.announcement_channel_id}")
            return None
        except Exception as e:
            logger.error(f"Error sending announcement: {e}", exc_info=True)
            return None
            
    def calculate_progression_time(self, target_level):
        """Calculate approximate time to reach a given level."""
        # Base assumptions
        exp_per_level = 100  # Experience needed per level
        avg_daily_exp = 150  # Average experience gained per day with moderate play
        
        # Calculate total exp needed
        total_exp_needed = 0
        for level in range(1, target_level):
            total_exp_needed += level * exp_per_level
            
        # Calculate days needed
        days_needed = total_exp_needed / avg_daily_exp
        
        # Convert to days and hours
        full_days = int(days_needed)
        hours = int((days_needed - full_days) * 24)
        
        return (full_days, hours)
        
    async def on_command_error(self, ctx, error):
        """Handle errors in prefix commands."""
        if isinstance(error, commands.CommandNotFound):
            cmd = ctx.message.content.split()[0][1:] if len(ctx.message.content) > 1 else ""
            logger.warning(f"Command not found: {cmd}")
            await ctx.send(f"Command `{cmd}` not found. Use `!help` to see available commands.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {str(error)}")
        else:
            logger.error(f"Error in command {ctx.command}: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")