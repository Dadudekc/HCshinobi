"""Commands for the loot drop system."""
import discord
from discord.ext import commands
import logging

from HCshinobi.core.loot_system import LootSystem
from HCshinobi.utils.embed_utils import get_rarity_color

class LootCommands(commands.Cog):
    def __init__(self, bot, loot_system: LootSystem):
        """Initialize loot commands.
        
        Args:
            bot: The bot instance
            loot_system: The loot system instance
        """
        self.bot = bot
        self.loot_system = loot_system
        self.logger = logging.getLogger(__name__)

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
        else:
            self.logger.error(f"Error in {ctx.command.name}: {error}", exc_info=True)
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
            success, loot_data, message = self.loot_system.generate_loot_drop(player_id)
            
            if not success:
                await ctx.send(message or "❌ Failed to generate loot drop!")
                return
                
            # Create loot drop embed
            embed = discord.Embed(
                title="💰 Random Ryō Drop!",
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
            
        except Exception as e:
            self.logger.error(f"Error in loot command: {e}", exc_info=True)
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
            next_drop = self.loot_system.get_next_drop_time(player_id)
            
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
            self.logger.error(f"Error in next_loot command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

async def setup(bot):
    """Set up the loot commands cog."""
    await bot.add_cog(LootCommands(bot, bot.loot_system)) 