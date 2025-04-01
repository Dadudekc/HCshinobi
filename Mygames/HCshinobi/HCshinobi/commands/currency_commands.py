"""Currency commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
import logging

from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.utils.embed_utils import get_rarity_color

class CurrencyCommands(commands.Cog):
    def __init__(self, bot, currency_system: CurrencySystem, clan_system: ClanSystem):
        """Initialize currency commands.
        
        Args:
            bot: The bot instance
            currency_system: The currency system instance
            clan_system: The clan system instance
        """
        self.bot = bot
        self.currency_system = currency_system
        self.clan_system = clan_system
        self.logger = logging.getLogger(__name__)

    @commands.command(name="balance", description="Check your Ryō balance")
    async def balance(self, ctx):
        """Check your Ryō balance."""
        player_id = str(ctx.author.id)
        
        # Get player's clan
        player_clan = self.clan_system.get_player_clan(player_id)
        
        # Get balance
        balance = self.currency_system.get_balance(player_id)
        
        # Create embed
        embed = discord.Embed(
            title="💰 Ryō Balance",
            description=f"Your current balance: **{balance:,}** Ryō",
            color=discord.Color.gold()
        )
        
        # Add clan bonus if applicable
        if player_clan:
            clan_bonus = self.currency_system.get_clan_bonus(player_clan)
            if clan_bonus > 0:
                embed.add_field(
                    name="Clan Bonus",
                    value=f"+{clan_bonus}% Ryō from {player_clan} clan",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.command(name="daily", description="Claim your daily Ryō reward")
    async def daily(self, ctx):
        """Claim your daily Ryō reward."""
        player_id = str(ctx.author.id)
        
        # Get player's clan
        player_clan = self.clan_system.get_player_clan(player_id)
        
        # Claim daily reward
        amount = await self.currency_system.claim_daily_reward(player_id)
        
        # Create embed
        embed = discord.Embed(
            title="🎁 Daily Reward",
            description=f"You claimed **{amount:,}** Ryō!",
            color=discord.Color.green()
        )
        
        # Add clan bonus if applicable
        if player_clan:
            clan_bonus = self.currency_system.get_clan_bonus(player_clan)
            if clan_bonus > 0:
                bonus_amount = int(amount * (clan_bonus / 100))
                embed.add_field(
                    name="Clan Bonus",
                    value=f"+{bonus_amount:,} Ryō from {player_clan} clan",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.command(name="transfer", description="Transfer Ryō to another user")
    async def transfer(self, ctx, recipient: discord.Member, amount: int):
        """Transfer Ryō to another user.
        
        Args:
            ctx: The command context
            recipient: The user to transfer to
            amount: The amount to transfer
        """
        if amount <= 0:
            await ctx.send("Amount must be greater than 0!")
            return
            
        sender_id = str(ctx.author.id)
        recipient_id = str(recipient.id)
        
        # Transfer currency
        success = await self.currency_system.transfer_currency(sender_id, recipient_id, amount)
        
        if success:
            embed = discord.Embed(
                title="💸 Transfer Complete",
                description=f"Successfully transferred **{amount:,}** Ryō to {recipient.mention}!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Transfer Failed",
                description="You don't have enough Ryō!",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Set up the currency commands cog."""
    await bot.add_cog(CurrencyCommands(bot, bot.currency_system, bot.clan_system)) 