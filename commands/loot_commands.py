"""Commands for the loot drop system."""
import discord
from discord.ext import commands
import logging
import traceback
from datetime import datetime

from HCshinobi.core.loot_system import LootSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.utils.embed_utils import get_rarity_color
from HCshinobi.database.loot_history import LootHistoryDB

logger = logging.getLogger(__name__)

class LootCommands(commands.Cog):
    def __init__(self, bot: 'HCShinobiBot', loot_system: LootSystem, character_system: CharacterSystem, data_dir: str):
        """Initialize loot commands.
        
        Args:
            bot: The bot instance
            loot_system: The loot system instance
            character_system: The character system instance
            data_dir: The base data directory path
        """
        super().__init__()
        self.bot = bot
        self.loot_system = loot_system
        self.character_system = character_system
        self.data_dir = data_dir
        try:
            self.loot_db = LootHistoryDB(data_dir=data_dir)
            logger.info("LootHistoryDB initialized successfully within LootCommands.")
        except Exception as e:
            logger.error(f"Failed to initialize LootHistoryDB in LootCommands: {e}", exc_info=True)
            self.loot_db = None
        logger.info("LootCommands Cog initialized.")

    async def cog_command_error(self, ctx, error):
        """Handle errors for all commands in this cog."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have permission to do that!")
        elif isinstance(error, commands.UserInputError):
            await ctx.send(f"❌ Invalid input. Use `!help {ctx.command.name}` for details.")
        else:
            logger.error(f"Error in {ctx.command.name}: {error}", exc_info=True)
            traceback.print_exception(type(error), error, error.__traceback__)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="loot",
        aliases=["get_loot", "find_ryo"],
        description="Try to get a random Ryō drop",
        help="Try your luck to find some Ryō lying around"
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)  # Once per hour
    async def loot(self, ctx):
        """Try to get a random Ryō drop.
        
        Args:
            ctx: The command context
        """
        try:
            player_id = str(ctx.author.id)
            
            # Try to generate loot drop
            success, loot_data, message = await self.loot_system.generate_loot_drop(player_id)
            
            if not success:
                await ctx.send(message or "❌ Failed to generate loot drop!")
                return
                
            # 🎨 Add rarity-based emoji
            rarity_icons = {
                "Common": "🪙",
                "Uncommon": "💼",
                "Rare": "💎",
                "Epic": "🌟",
                "Legendary": "👑"
            }
            icon = rarity_icons.get(loot_data["rarity"], "🪙")
            
            # Create loot drop embed
            embed = discord.Embed(
                title=f"{icon} {loot_data['rarity']} Ryō Drop!",
                description=f"{ctx.author.mention} found some Ryō!",
                color=loot_data["color"]
            )
            
            # Add loot details
            embed.add_field(
                name="Amount",
                value=f"**{loot_data['amount']:,}** Ryō",
                inline=True
            )
            
            embed.add_field(
                name="Rarity",
                value=f"**{loot_data['rarity']}**",
                inline=True
            )
            
            embed.add_field(
                name="Rank Bonus",
                value=f"Base: {loot_data['base_reward']:,} × {loot_data['multiplier']}x",
                inline=False
            )
            
            # Add next drop time
            next_drop = self.loot_system.get_next_drop_time(player_id)
            if next_drop:
                embed.add_field(
                    name="Next Drop",
                    value=f"Available in {next_drop}",
                    inline=False
                )
            
            # Add footer with rank
            embed.set_footer(text=f"Rank: {loot_data['rank']}")
            
            await ctx.send(embed=embed)
            
            # 🔄 Log to devlog system (if available)
            if hasattr(self.bot, "devlog"):
                try:
                    self.bot.devlog.log_event(
                        "loot",
                        f"{ctx.author} gained {loot_data['amount']:,} Ryō ({loot_data['rarity']})"
                    )
                except Exception as e:
                    logger.warning(f"Devlog logging failed for loot event: {e}")
            
            # 🔄 Persist loot drop to storage
            if self.loot_db:
                try:
                    self.loot_db.log_loot(player_id, loot_data['amount'], loot_data['rarity'])
                except Exception as db_err:
                    logger.error(f"Failed to log loot history: {db_err}", exc_info=True)
            else:
                logger.warning("LootHistoryDB not available, skipping loot history logging.")
            
        except Exception as e:
            logger.error(f"Error in loot command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            
    @commands.command(
        name="next_loot",
        aliases=["loot_cooldown", "loot_timer"],
        description="Check when your next loot drop will be available",
        help="See when you can use the !loot command again"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def next_loot(self, ctx):
        """Check when your next loot drop will be available.
        
        Args:
            ctx: The command context
        """
        try:
            player_id = str(ctx.author.id)
            
            # Get next drop time
            next_drop = await self.loot_system.get_next_drop_time(player_id)
            
            if not next_drop:
                await ctx.send("✅ You're ready for your next loot drop! Use `!loot` to try your luck!")
                return
                
            # Create embed
            embed = discord.Embed(
                title="⏰ Next Loot Drop",
                description=f"Your next loot drop will be available in **{next_drop}**",
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in next_loot command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    # --- NEW: Loot History Command --- #
    @commands.command(
        name="loothistory",
        aliases=["lh"],
        description="View your recent loot drops",
        help="Shows your last 10 loot drops recorded."
    )
    @commands.cooldown(1, 10, commands.BucketType.user) # Limit spam
    async def loothistory(self, ctx, user: discord.Member = None):
        """Displays the user's recent loot history.

        Args:
            ctx: The command context.
            user: The user whose history to view (optional, defaults to command author).
        """
        target_user = user or ctx.author
        player_id = str(target_user.id)

        if not self.loot_db:
            logger.warning(f"Loot history command used but DB not available.")
            await ctx.send("❌ Loot history tracking is currently unavailable.")
            return

        try:
            history = self.loot_db.get_loot_history(player_id)

            if not history:
                await ctx.send(f"📜 {target_user.mention} has no recorded loot history yet.")
                return

            embed = discord.Embed(
                title=f"📜 Loot History for {target_user.display_name}",
                color=discord.Color.gold()
            )

            # Display last 10 entries
            history_entries = []
            for entry in history[:10]:
                try:
                    # Parse timestamp and convert to Discord timestamp
                    timestamp_dt = datetime.fromisoformat(entry['timestamp'])
                    unix_timestamp = int(timestamp_dt.timestamp())
                    timestamp_str = f"<t:{unix_timestamp}:R>" # Relative time
                except (ValueError, TypeError):
                    timestamp_str = "(invalid date)" 
                
                # Get rarity icon
                rarity_icons = {
                    "Common": "🪙", "Uncommon": "💼", "Rare": "💎",
                    "Epic": "🌟", "Legendary": "👑"
                }
                icon = rarity_icons.get(entry['rarity'], '❓')

                history_entries.append(
                    f"{icon} **{entry['loot_amount']:,}** Ryō ({entry['rarity']}) - {timestamp_str}"
                )
            
            embed.description = "\n".join(history_entries)
            embed.set_footer(text=f"Showing last {len(history_entries)} drops.")

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in loothistory command for user {player_id}: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while retrieving loot history.")
    # --- END NEW --- #

    def get_loot_system(self):
        """Returns the loot system for use by other cogs."""
        return self.loot_system

async def setup(bot: 'HCShinobiBot'):
    """Set up the loot commands cog."""
    if not hasattr(bot, 'services') or not hasattr(bot.services, 'config'):
        logger.error("Service container or config not found on bot object during LootCommands setup!")
        return
        
    data_dir = getattr(bot.services.config, 'data_dir', None)
    if not data_dir:
        logger.error("data_dir not found in bot config during LootCommands setup!")
        return
        
    await bot.add_cog(LootCommands(bot, bot.services.loot_system, bot.services.character_system, data_dir)) 
    logger.info("LootCommands Cog loaded successfully.") 