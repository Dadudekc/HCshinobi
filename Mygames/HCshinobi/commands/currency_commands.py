"""
Currency commands for HCShinobi.
Handles currency-related commands like balance, transfer, etc.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from HCshinobi.core.character import Character
from HCshinobi.utils.embeds import create_error_embed

class CurrencyCommands(commands.Cog):
    """Currency-related commands for HCShinobi."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="balance", description="Check your current balance")
    async def balance(self, interaction: discord.Interaction):
        """Check the user's current balance."""
        try:
            character = Character.load(interaction.user.id)
            if not character:
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have a character yet!"),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="Balance",
                description=f"Your current balance: {character.currency:,} ryo",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
            
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
    ):
        """Transfer currency to another user."""
        try:
            if amount <= 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Amount must be positive!"),
                    ephemeral=True
                )
                return
            
            sender = Character.load(interaction.user.id)
            if not sender:
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have a character yet!"),
                    ephemeral=True
                )
                return
            
            if sender.currency < amount:
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have enough currency!"),
                    ephemeral=True
                )
                return
            
            recipient = Character.load(user.id)
            if not recipient:
                await interaction.response.send_message(
                    embed=create_error_embed("Recipient doesn't have a character yet!"),
                    ephemeral=True
                )
                return
            
            # Perform transfer
            sender.currency -= amount
            recipient.currency += amount
            
            # Save changes
            sender.save()
            recipient.save()
            
            embed = discord.Embed(
                title="Transfer Successful",
                description=f"Transferred {amount:,} ryo to {user.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error transferring currency: {str(e)}"),
                ephemeral=True
            )

async def setup(bot):
    """Set up the currency commands cog."""
    await bot.add_cog(CurrencyCommands(bot)) 