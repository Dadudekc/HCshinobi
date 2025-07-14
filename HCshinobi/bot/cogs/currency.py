import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging

from ...utils.embeds import create_error_embed


class CurrencyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _safe_response(self, interaction: discord.Interaction, content=None, embed=None, ephemeral=False):
        """Safely respond to an interaction, handling expired interactions gracefully."""
        try:
            if interaction.response.is_done():
                # Interaction already responded to, use followup
                await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            else:
                # First response, use response.send_message
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
        except discord.errors.NotFound:
            # Interaction expired (error code 10062)
            logging.warning(f"Interaction expired for user {interaction.user.id} in {interaction.command.name}")
            # Try to send a DM as fallback
            try:
                if embed:
                    await interaction.user.send(embed=embed)
                elif content:
                    await interaction.user.send(content)
            except:
                logging.error(f"Failed to send DM fallback to user {interaction.user.id}")
        except Exception as e:
            logging.error(f"Error responding to interaction: {e}")

    @app_commands.command(name="balance", description="Check your current balance")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        logging.info(f"💰 /balance command called by {interaction.user.display_name} ({interaction.user.id})")
        
        try:
            target_user = user or interaction.user
            logging.info(f"   📊 Checking balance for: {target_user.display_name}")
            
            # Access the currency system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'currency_system'):
                logging.error("   ❌ Currency system not available")
                await self._safe_response(
                    interaction, 
                    embed=create_error_embed("Currency system not available."),
                    ephemeral=True
                )
                return
                
            balance = await self.bot.services.currency_system.get_player_balance(target_user.id)
            logging.info(f"   ✅ Balance retrieved: {balance:,} ryo")
            
            embed = discord.Embed(
                title=f"💰 Balance",
                description=f"**{target_user.display_name}** has **{balance:,}** ryo",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            await self._safe_response(interaction, embed=embed, ephemeral=user is None)
            logging.info(f"   ✅ Balance response sent successfully")
            
        except Exception as e:
            logging.error(f"   ❌ ERROR in /balance command:")
            logging.error(f"      User: {interaction.user.display_name} ({interaction.user.id})")
            logging.error(f"      Error: {e}")
            logging.error(f"      Traceback:", exc_info=True)
            
            await self._safe_response(
                interaction,
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
        logging.info(f"💸 /transfer command called by {interaction.user.display_name} ({interaction.user.id})")
        logging.info(f"   📤 Transferring {amount:,} ryo to {user.display_name}")
        
        try:
            if amount <= 0:
                logging.warning(f"   ⚠️ Invalid amount: {amount}")
                await self._safe_response(
                    interaction,
                    embed=create_error_embed("Amount must be positive!"),
                    ephemeral=True
                )
                return
                
            if user.id == interaction.user.id:
                logging.warning(f"   ⚠️ User trying to transfer to themselves")
                await self._safe_response(
                    interaction,
                    embed=create_error_embed("You can't transfer currency to yourself!"),
                    ephemeral=True
                )
                return
                
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'currency_system'):
                logging.error("   ❌ Currency system not available")
                await self._safe_response(
                    interaction,
                    embed=create_error_embed("Currency system not available."),
                    ephemeral=True
                )
                return
                
            currency_system = self.bot.services.currency_system
            sender_balance = await currency_system.get_player_balance(interaction.user.id)
            logging.info(f"   💰 Sender balance: {sender_balance:,} ryo")
            
            if sender_balance < amount:
                logging.warning(f"   ⚠️ Insufficient funds: {sender_balance:,} < {amount:,}")
                await self._safe_response(
                    interaction,
                    embed=create_error_embed(f"Insufficient funds! You have {sender_balance:,} ryo but need {amount:,} ryo."),
                    ephemeral=True
                )
                return
                
            # Perform the transfer
            currency_system.add_balance_and_save(interaction.user.id, -amount)
            currency_system.add_balance_and_save(user.id, amount)
            logging.info(f"   ✅ Transfer completed successfully")
            
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
            
            await self._safe_response(interaction, embed=embed)
            logging.info(f"   ✅ Transfer response sent successfully")
            
        except Exception as e:
            logging.error(f"   ❌ ERROR in /transfer command:")
            logging.error(f"      User: {interaction.user.display_name} ({interaction.user.id})")
            logging.error(f"      Error: {e}")
            logging.error(f"      Traceback:", exc_info=True)
            
            await self._safe_response(
                interaction,
                embed=create_error_embed(f"Error transferring currency: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="daily", description="Claim your daily currency reward")
    async def daily(self, interaction: discord.Interaction) -> None:
        logging.info(f"🎁 /daily command called by {interaction.user.display_name} ({interaction.user.id})")
        
        try:
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'currency_system'):
                logging.error("   ❌ Currency system not available")
                await self._safe_response(
                    interaction,
                    embed=create_error_embed("Currency system not available."),
                    ephemeral=True
                )
                return
                
            daily_amount = 100
            currency_system = self.bot.services.currency_system
            currency_system.add_balance_and_save(interaction.user.id, daily_amount)
            new_balance = await currency_system.get_player_balance(interaction.user.id)
            logging.info(f"   ✅ Daily reward claimed: +{daily_amount} ryo, new balance: {new_balance:,}")
            
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
            
            await self._safe_response(interaction, embed=embed, ephemeral=True)
            logging.info(f"   ✅ Daily reward response sent successfully")
            
        except Exception as e:
            logging.error(f"   ❌ ERROR in /daily command:")
            logging.error(f"      User: {interaction.user.display_name} ({interaction.user.id})")
            logging.error(f"      Error: {e}")
            logging.error(f"      Traceback:", exc_info=True)
            
            await self._safe_response(
                interaction,
                embed=create_error_embed(f"Error claiming daily reward: {str(e)}"),
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CurrencyCommands(bot))
