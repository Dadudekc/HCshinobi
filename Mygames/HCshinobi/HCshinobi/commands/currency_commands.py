"""Currency commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import app_commands # Import app_commands
import logging
from typing import Optional, Dict # Added Dict
import random # Added random
from datetime import datetime, timedelta # Added datetime

# Corrected imports
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.character_system import CharacterSystem 
from HCshinobi.core.clan_data import ClanData 
from HCshinobi.utils.embed_utils import get_rarity_color # Use this for color
from HCshinobi.core.constants import RarityTier # Import RarityTier for default

# Cooldown setting
DAILY_COOLDOWN = timedelta(minutes=30) 
MIN_DAILY_REWARD = 100
MAX_DAILY_REWARD = 500

class CurrencyCommands(commands.Cog):
    # Corrected __init__ signature
    def __init__(self, bot):
        """Initialize currency commands."""
        self.bot = bot
        # --- Get systems from other Cogs --- #
        currency_cog = bot.get_cog('Currency') # Use the Cog name specified in currency_system.py
        if not currency_cog:
            raise RuntimeError("CurrencyCog not loaded, cannot initialize CurrencyCommands")
        self.currency_system: CurrencySystem = currency_cog.get_system()
        
        # Assuming CharacterSystem and ClanData are still passed via bot.services or similar
        # If they are also Cogs, get them similarly.
        self.character_system = getattr(bot.services, 'character_system', None)
        self.clan_data = getattr(bot.services, 'clan_data', None)
        if not self.character_system or not self.clan_data:
             # Log error or raise exception, depending on desired handling
             # For now, log and proceed, commands might fail later
             logging.error("CurrencyCommands initialized without CharacterSystem or ClanData.")
        # --- End Get systems --- #

        self.logger = logging.getLogger(__name__)
        self.daily_claimed: Dict[str, datetime] = {} # Dictionary to track last claim time

    @app_commands.command(name="balance", description="Check your Ryō balance")
    async def balance(self, interaction: discord.Interaction):
        """Check your Ryō balance."""
        # Defer early
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for balance: {e}", exc_info=True)
            return # Cannot followup if defer failed

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
            
            # Removed clan bonus section for now as it wasn't implemented in CurrencySystem/ClanData
            
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
        # Defer first. Claim message should be public, errors ephemeral.
        try:
            # Initially defer ephemerally, can make followup public later.
            await interaction.response.defer(ephemeral=True) 
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for daily: {e}", exc_info=True)
            return # Cannot followup if defer failed

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
                color=rarity_color # Use rarity color
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
            # Try to send an error message if interaction wasn't used already
            try:
                await interaction.followup.send("❌ An error occurred while claiming your daily reward.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                 self.logger.error(f"HTTP error sending daily error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="transfer", description="Transfer Ryō to another user")
    @app_commands.describe(recipient="The user to transfer Ryō to", amount="The amount of Ryō to transfer")
    async def transfer(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        """Transfer Ryō to another user."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for transfer: {e}", exc_info=True)
            return # Cannot followup if defer failed

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
                 self.logger.error(f"HTTP error sending transfer fatal error followup: {http_err_fatal}", exc_info=True)

async def setup(bot):
    """Set up the currency commands cog."""
    # Ensure dependencies are loaded BEFORE adding this cog
    # Specifically, the CurrencyCog must be loaded
    # Assuming CharacterSystem and ClanData are loaded via bot.services setup elsewhere
    
    # Removed dependency injection from here, handled in __init__
    # currency_system = bot.services.currency_system
    # character_system = bot.services.character_system 
    # clan_data = bot.services.clan_data 
    # if not currency_system or not character_system or not clan_data:
    #     logger.error("Failed to setup CurrencyCommands: Missing one or more required services.")
    #     return
    await bot.add_cog(CurrencyCommands(bot)) 