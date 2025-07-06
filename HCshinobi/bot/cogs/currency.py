import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from ...utils.embeds import create_error_embed


class CurrencyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="balance", description="Check your current balance")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        """Check the balance of yourself or another user."""
        target_user = user or interaction.user
        
        try:
            # Access the currency system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'currency_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Currency system not available."),
                    ephemeral=True
                )
                return
            
            balance = self.bot.services.currency_system.get_player_balance(target_user.id)
            
            embed = discord.Embed(
                title=f"💰 Balance",
                description=f"**{target_user.display_name}** has **{balance:,}** ryo",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed, ephemeral=user is None)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error checking balance: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="transfer", description="Transfer currency to another user")
    async def transfer(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int
    ) -> None:
        """Transfer currency to another user."""
        try:
            if amount <= 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Amount must be positive!"),
                    ephemeral=True
                )
                return
            
            if user.id == interaction.user.id:
                await interaction.response.send_message(
                    embed=create_error_embed("You can't transfer currency to yourself!"),
                    ephemeral=True
                )
                return
            
            # Access the currency system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'currency_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Currency system not available."),
                    ephemeral=True
                )
                return
            
            currency_system = self.bot.services.currency_system
            sender_balance = currency_system.get_player_balance(interaction.user.id)
            
            if sender_balance < amount:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Insufficient funds! You have {sender_balance:,} ryo but need {amount:,} ryo."),
                    ephemeral=True
                )
                return
            
            # Perform the transfer
            currency_system.add_balance_and_save(interaction.user.id, -amount)
            currency_system.add_balance_and_save(user.id, amount)
            
            embed = discord.Embed(
                title="💸 Transfer Successful",
                description=f"Transferred **{amount:,}** ryo to {user.mention}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Your new balance",
                value=f"{sender_balance - amount:,} ryo",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error transferring currency: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="daily", description="Claim your daily currency reward")
    async def daily(self, interaction: discord.Interaction) -> None:
        """Claim daily currency reward."""
        try:
            # Access the currency system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'currency_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Currency system not available."),
                    ephemeral=True
                )
                return
            
            # For now, give a fixed daily amount (could be enhanced with cooldown tracking)
            daily_amount = 100
            currency_system = self.bot.services.currency_system
            currency_system.add_balance_and_save(interaction.user.id, daily_amount)
            
            new_balance = currency_system.get_player_balance(interaction.user.id)
            
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                description=f"You received **{daily_amount:,}** ryo!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="New Balance",
                value=f"{new_balance:,} ryo",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error claiming daily reward: {str(e)}"),
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CurrencyCommands(bot))
