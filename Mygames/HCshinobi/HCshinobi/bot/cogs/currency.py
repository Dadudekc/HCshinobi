"""Currency commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, Dict, List, TYPE_CHECKING
import random
from datetime import datetime, timedelta

from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_data import ClanData
from HCshinobi.utils.embed_utils import get_rarity_color, create_error_embed
from HCshinobi.core.constants import RarityTier

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

# Cooldown settings
DAILY_COOLDOWN = timedelta(minutes=30)
MIN_DAILY_REWARD = 100
MAX_DAILY_REWARD = 500

class CurrencyCommands(commands.Cog):
    def __init__(self, bot: "HCBot"):
        """Initialize currency commands."""
        self.bot = bot
        # Access services safely
        self.currency_system: Optional[CurrencySystem] = getattr(bot.services, 'currency_system', None)
        self.character_system: Optional[CharacterSystem] = getattr(bot.services, 'character_system', None)
        self.clan_data = bot.services.clan_data
        
        if not all([self.currency_system, self.character_system, self.clan_data]):
            logging.error("CurrencyCommands initialized without one or more required systems")
            
        self.logger = logging.getLogger(__name__)
        self.daily_claimed: Dict[str, datetime] = {}

    @app_commands.command(name="balance", description="Check your Ryō balance")
    async def balance(self, interaction: discord.Interaction):
        """Check your Ryō balance."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for balance: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            
            # Get character to potentially display name or other info later
            character = await self.character_system.get_character(player_id)
            if not character:
                # Optionally handle case where user exists but has no character yet
                # For now, just show balance which defaults to 0 if no record
                pass 
            
            # Get balance (synchronous)
            balance = self.currency_system.get_player_balance(player_id)
            
            # Create embed
            embed = discord.Embed(
                title="💰 Ryō Balance",
                description=f"Your current balance: **{balance:,}** Ryō",
                color=discord.Color.gold()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as http_err:
            self.logger.error(f"HTTP error sending balance embed followup: {http_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Error in /balance command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while checking your balance.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending balance error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="daily", description="Claim your daily Ryō reward (every 30 minutes)")
    async def daily(self, interaction: discord.Interaction):
        """Claim your daily Ryō reward."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for daily: {e}", exc_info=True)
            return

        try:
            player_id = str(interaction.user.id)
            current_time = datetime.utcnow()
            
            # Check character existence
            character = await self.character_system.get_character(player_id)
            if not character:
                try:
                    await interaction.followup.send("❌ You need a character to claim daily rewards.", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    self.logger.error(f"HTTP error sending daily no-char followup: {http_err}", exc_info=True)
                return
                
            # Check cooldown
            last_claimed_time = self.daily_claimed.get(player_id)
            if last_claimed_time and (current_time < last_claimed_time + DAILY_COOLDOWN):
                time_remaining = (last_claimed_time + DAILY_COOLDOWN) - current_time
                minutes, seconds = divmod(int(time_remaining.total_seconds()), 60)
                try:
                    await interaction.followup.send(
                        f"⏰ You have already claimed your reward. Please wait {minutes}m {seconds}s.", 
                        ephemeral=True
                    )
                except discord.errors.HTTPException as http_err:
                    self.logger.error(f"HTTP error sending daily cooldown followup: {http_err}", exc_info=True)
                return

            # Calculate reward and update balance
            amount = random.randint(MIN_DAILY_REWARD, MAX_DAILY_REWARD)
            
            # Use add_balance_and_save if available to ensure persistence
            if hasattr(self.currency_system, 'add_balance_and_save'):
                new_balance = self.currency_system.add_balance_and_save(player_id, amount)
            else:
                # Fallback to old method
                new_balance = self.currency_system.add_to_balance(player_id, amount)
                # Try to save manually if method available
                if hasattr(self.currency_system, 'save_currency_data'):
                    self.currency_system.save_currency_data()
            
            # Update last claimed time
            self.daily_claimed[player_id] = current_time
            
            # Get clan rarity for color
            rarity_color = discord.Color.gold() # Default color
            if character.clan:
                clan_info = self.clan_data.get_clan(character.clan)
                if clan_info:
                    rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                    rarity_color = get_rarity_color(rarity_str)

            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                description=f"You claimed **{amount:,}** Ryō!\nYour new balance is **{new_balance:,}** Ryō.",
                color=rarity_color
            )
            
            try:
                # Send the reward message publicly
                await interaction.followup.send(embed=embed, ephemeral=False)
            except discord.errors.HTTPException as http_err:
                self.logger.error(f"HTTP error sending daily success followup: {http_err}", exc_info=True)
                # Attempt to notify user ephemerally if public message failed
                try:
                    await interaction.followup.send("❌ Failed to display the daily reward message, but the reward was added.", ephemeral=True)
                except discord.errors.HTTPException:
                    pass # Ignore if even this fails
            
        except Exception as e:
            self.logger.error(f"Error in /daily command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while claiming your daily reward.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending daily error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="transfer", description="Transfer Ryō to another user")
    @app_commands.describe(recipient="The user to transfer Ryō to", amount="The amount of Ryō to transfer")
    async def transfer(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        """Transfer Ryō to another user."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for transfer: {e}", exc_info=True)
            return

        try:
            if amount <= 0:
                try:
                    await interaction.followup.send("❌ Amount must be greater than 0!", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    self.logger.error(f"HTTP error sending transfer amount error followup: {http_err}", exc_info=True)
                return
            
            if interaction.user.id == recipient.id:
                try:
                    await interaction.followup.send("❌ You cannot transfer Ryō to yourself!", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    self.logger.error(f"HTTP error sending transfer self error followup: {http_err}", exc_info=True)
                return
                
            sender_id = str(interaction.user.id)
            recipient_id = str(recipient.id)
            
            # Check sufficient funds first
            sender_balance = self.currency_system.get_player_balance(sender_id)
            if sender_balance < amount:
                embed = discord.Embed(
                    title="❌ Transfer Failed",
                    description=f"You don't have enough Ryō! You only have {sender_balance:,} Ryō.",
                    color=discord.Color.red()
                )
                try:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    self.logger.error(f"HTTP error sending transfer insufficient funds followup: {http_err}", exc_info=True)
                return
            
            # Use atomic operations with add_balance_and_save if available
            success = True
            if hasattr(self.currency_system, 'add_balance_and_save'):
                try:
                    # Deduct from sender first
                    self.currency_system.add_balance_and_save(sender_id, -amount)
                    # Then add to recipient
                    self.currency_system.add_balance_and_save(recipient_id, amount)
                except Exception as e:
                    self.logger.error(f"Error during transfer with add_balance_and_save: {e}", exc_info=True)
                    success = False
            else:
                # Fall back to transfer_funds which doesn't save automatically
                success = self.currency_system.transfer_funds(sender_id, recipient_id, amount)
                # Try to save manually if possible
                if success and hasattr(self.currency_system, 'save_currency_data'):
                    self.currency_system.save_currency_data()
            
            if success:
                embed = discord.Embed(
                    title="💸 Transfer Complete",
                    description=f"Successfully transferred **{amount:,}** Ryō to {recipient.mention}!",
                    color=discord.Color.green()
                )
            else:
                # Check actual balance to give a better error message
                sender_balance = self.currency_system.get_player_balance(sender_id)
                embed = discord.Embed(
                    title="❌ Transfer Failed",
                    description=f"An error occurred during the transfer. Your balance is {sender_balance:,} Ryō.",
                    color=discord.Color.red()
                )
            
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.errors.HTTPException as http_err:
                self.logger.error(f"HTTP error sending transfer result followup: {http_err}", exc_info=True)
            
        except Exception as e:
            self.logger.error(f"Error in /transfer command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred during the transfer.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending transfer error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="give", description="[Admin] Give Ryō to a user")
    @app_commands.describe(user="The user to give Ryō to", amount="The amount of Ryō to give")
    @app_commands.checks.has_permissions(administrator=True)
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """[Admin] Give Ryō to a user."""
        if not self.currency_system:
            await interaction.response.send_message("❌ Currency system is unavailable.", ephemeral=True)
            return
            
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return

        try:
            new_balance = self.currency_system.add_balance_and_save(str(user.id), amount)
            if new_balance is None: # Check if operation failed
                raise RuntimeError("add_balance_and_save returned None")
                
            embed = discord.Embed(
                title="💸 Ryō Given",
                description=f"Gave **{amount:,}** Ryō to {user.mention}. Their new balance is **{new_balance:,}** Ryō.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in /give command: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while giving Ryō.", ephemeral=True)

    @app_commands.command(name="take", description="[Admin] Take Ryō from a user")
    @app_commands.describe(user="The user to take Ryō from", amount="The amount of Ryō to take")
    @app_commands.checks.has_permissions(administrator=True)
    async def take(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """[Admin] Take Ryō from a user."""
        if not self.currency_system:
            await interaction.response.send_message("❌ Currency system is unavailable.", ephemeral=True)
            return
            
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return

        try:
            current_balance = self.currency_system.get_player_balance(str(user.id))
            if current_balance < amount:
                await interaction.response.send_message(f"❌ {user.mention} only has {current_balance:,} Ryō!", ephemeral=True)
                return

            new_balance = self.currency_system.add_balance_and_save(str(user.id), -amount)
            if new_balance is None: # Check if operation failed
                 raise RuntimeError("add_balance_and_save returned None for negative amount")
                 
            embed = discord.Embed(
                title="💸 Ryō Taken",
                description=f"Took **{amount:,}** Ryō from {user.mention}. Their new balance is **{new_balance:,}** Ryō.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in /take command: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while taking Ryō.", ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the Ryō leaderboard")
    @app_commands.describe(page="The page number to view (default: 1)")
    async def leaderboard(self, interaction: discord.Interaction, page: int = 1):
        """Show the currency leaderboard."""
        if not self.currency_system:
            await interaction.response.send_message("❌ Currency system is unavailable.", ephemeral=True)
            return
            
        per_page = 10
        try:
            # Assuming get_leaderboard is synchronous and returns list of (user_id, amount) tuples
            leaderboard_data = self.currency_system.get_leaderboard()
            
            # Calculate total pages
            total_entries = len(leaderboard_data)
            total_pages = (total_entries + per_page - 1) // per_page or 1 # Ensure at least 1 page
            
            # Validate page number
            if page < 1 or page > total_pages:
                await interaction.response.send_message(f"❌ Invalid page number! Please choose between 1 and {total_pages}", ephemeral=True)
                return
            
            # Get entries for current page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_entries = leaderboard_data[start_idx:end_idx]
            
            # Create embed
            embed = discord.Embed(
                title="💰 Richest Shinobi",
                description=f"Page {page}/{total_pages}",
                color=discord.Color.gold()
            )
            
            # Add entries
            entry_lines = []
            for i, (user_id, amount) in enumerate(page_entries, start=start_idx + 1):
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    name = user.display_name
                except Exception: # Catch broad exception for user fetching issues
                    name = f"User ID: {user_id}"
                
                entry_lines.append(f"#{i}. {name} - **{amount:,}** Ryō")
            
            if not entry_lines:
                embed.description = "The leaderboard is empty."
            else:
                 embed.description += "\n\n" + "\n".join(entry_lines)
                 
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in /leaderboard command: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while fetching the leaderboard.", ephemeral=True)

    # Add error handlers for admin commands
    @give.error
    @take.error
    async def admin_currency_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        else:
            self.logger.error(f"Error in admin currency command: {error}", exc_info=True)
            await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)

async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(CurrencyCommands(bot)) 