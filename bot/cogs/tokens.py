"""
Discord Cog for Token-related commands.
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, TYPE_CHECKING, Any
import logging

# Adjust import paths
try:
    from ...core.token_system import TokenSystem, TokenError
    # from ...utils.logging import log_command, log_error # If needed for specific logging
except ImportError as e:
    logging.error(f"Error importing core modules in tokens.py: {e}. Dependency injection needed.")
    class TokenError(Exception): pass
    # Define dummies if needed

# Feature unlock constants (consider moving to core/constants.py)
FEATURE_COSTS = {
    "weapon_crafting": 15,
    "elemental_affinity": 20,
    "style_switching": 10,
    "summon_contract": 25,
    "jutsu_creation": 30,
}

FEATURE_CHOICES = [
    app_commands.Choice(name=name.replace("_", " ").title(), value=name)
    for name in FEATURE_COSTS.keys()
]

# Assuming logger is set up elsewhere
logger = logging.getLogger(__name__)

# Type hint for bot
if TYPE_CHECKING:
    # Assume bot object structure includes services
    from ..bot import HCBot 
    class BotWithServices(HCBot):
         services: Any # Replace Any with actual ServiceContainer type if available

class TokenCommands(commands.Cog):
    """Commands for token management and usage."""

    # --- MODIFIED: Use bot.services for injection --- #
    def __init__(self, bot: 'BotWithServices'):
        self.bot = bot
        # Access TokenSystem via bot.services
        self.token_system: Optional[TokenSystem] = None
        if hasattr(bot, 'services') and hasattr(bot.services, 'token_system'):
            self.token_system = bot.services.token_system
        
        if not self.token_system:
            logger.error("TokenSystem service not found via bot.services in TokenCommands __init__.")
            # Decide how to handle: raise error, disable cog, or operate without?
            # For now, commands will check self.token_system availability.
        else:
             logger.info("TokenCommands Cog initialized with injected TokenSystem.")
    # --- END MODIFIED --- #

    @app_commands.command(
        name="tokens",
        description="Check your token balance"
    )
    async def tokens(self, interaction: discord.Interaction):
        """Displays the user's current token balance and unlocked features."""
        if not self.token_system:
             await interaction.response.send_message("Sorry, the token system is not available.", ephemeral=True)
             return

        user_id = str(interaction.user.id)
        balance = await self.token_system.get_player_tokens(user_id)
        unlocks = self.token_system.get_player_unlocks(user_id)

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Balance",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Tokens", value=str(balance), inline=False)

        if unlocks:
            unlock_text = "\n".join([f"- {feat.replace('_', ' ').title()}" for feat in unlocks])
            embed.add_field(name="🔓 Unlocked Features", value=unlock_text, inline=False)
        else:
            embed.add_field(name="🔓 Unlocked Features", value="None yet!", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Admin command - Consider restricting access further if needed
    @app_commands.command(
        name="add_tokens",
        description="[Admin] Add tokens to a user"
    )
    @app_commands.describe(
        user="The user to add tokens to",
        amount="The number of tokens to add (can be negative to remove)"
    )
    @app_commands.checks.has_permissions(administrator=True) # Restrict to admins
    async def add_tokens(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        amount: int
    ):
        """Admin command to grant or remove tokens for a user."""
        if not self.token_system:
             await interaction.response.send_message("Sorry, the token system is not available.", ephemeral=True)
             return

        admin_user = interaction.user
        target_user_id = str(user.id)

        try:
            new_balance = await self.token_system.add_tokens(target_user_id, amount, f"Admin: {admin_user.name}")
            action = "added" if amount >= 0 else "removed"
            abs_amount = abs(amount)

            embed = discord.Embed(
                title="Tokens Updated",
                description=f"Successfully {action} {abs_amount} tokens {'to' if amount >= 0 else 'from'} {user.mention}.",
                color=discord.Color.green() if amount >= 0 else discord.Color.orange()
            )
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Amount Changed", value=f"{amount:+} ({action})", inline=True)
            embed.add_field(name="New Balance", value=str(new_balance), inline=True)
            embed.set_footer(text=f"Action performed by {admin_user.display_name}")

            await interaction.response.send_message(embed=embed)

            # Optionally DM the user
            try:
                dm_embed = discord.Embed(
                    title="Your Token Balance Was Updated",
                    description=f"An administrator ({admin_user.mention}) {action} {abs_amount} tokens {'to' if amount >= 0 else 'from'} your account.",
                    color=embed.color
                )
                dm_embed.add_field(name="New Balance", value=str(new_balance))
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                # Cannot DM the user
                pass
            except Exception as dm_e:
                 # Log DM error
                 logger.error(f"Failed to DM user {user.id} about token change: {dm_e}")

        except Exception as e:
            # Log error
            logger.error(f"Error in add_tokens: {e}")
            await interaction.response.send_message(f"An error occurred while adding tokens: {e}", ephemeral=True)

    @add_tokens.error
    async def add_tokens_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in add_tokens command check: {error}")
            await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)

    @app_commands.command(
        name="unlock_feature",
        description="Unlock a special game feature using tokens"
    )
    @app_commands.describe(feature="The feature to unlock")
    @app_commands.choices(feature=FEATURE_CHOICES)
    async def unlock_feature(
        self,
        interaction: discord.Interaction,
        feature: str
    ):
        """Allows players to spend tokens to unlock persistent features."""
        if not self.token_system:
             await interaction.response.send_message("Sorry, the token system is not available.", ephemeral=True)
             return

        user_id = str(interaction.user.id)
        # Cost is now fetched directly inside token_system.unlock_feature
        # cost = FEATURE_COSTS_LOCAL.get(feature)

        # if cost is None: # Should not happen if choices are generated correctly
        #     await interaction.response.send_message(f"Invalid feature selected: {feature}", ephemeral=True)
        #     return

        # Check if already unlocked
        if self.token_system.has_unlock(user_id, feature):
            await interaction.response.send_message(f"You have already unlocked '{feature.replace('_',' ').title()}'.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            # Attempt to unlock using the feature name directly
            # The core system now handles finding the cost via TOKEN_COSTS
            remaining_balance = self.token_system.unlock_feature(user_id, feature)

            feature_name = feature.replace("_", " ").title()
            # Get cost again for display (or modify unlock_feature to return it)
            cost = TOKEN_COSTS.get(f"unlock_feature_{feature}")
            embed = discord.Embed(
                title="Feature Unlocked!",
                description=f"You have successfully unlocked **{feature_name}** for {cost or '?'} tokens!",
                color=discord.Color.green()
            )
            embed.add_field(name="Feature", value=feature_name)
            embed.add_field(name="Cost", value=f"{cost or '?'} Tokens")
            embed.add_field(name="Remaining Tokens", value=str(remaining_balance))
            await interaction.followup.send(embed=embed)

        except (TokenError, ValueError) as e: # Catch ValueError from core system too
            error_embed = discord.Embed(
                title="Unlock Failed",
                description=str(e),
                color=discord.Color.red()
            )
            cost = TOKEN_COSTS.get(f"unlock_feature_{feature}")
            if cost:
                 error_embed.add_field(name="Feature", value=feature.replace("_", " ").title())
                 error_embed.add_field(name="Required Tokens", value=str(cost))
            await interaction.followup.send(embed=error_embed)
        except Exception as e:
            logger.exception(f"Error in unlock_feature command for {user_id}: {e}")
            await interaction.followup.send(f"An unexpected error occurred: {e}")


async def setup(bot: 'BotWithServices'):
    """Sets up the TokenCommands cog."""
    # --- MODIFIED: Check bot.services.token_system --- #
    if not hasattr(bot, 'services') or not hasattr(bot.services, 'token_system') or bot.services.token_system is None:
        logger.error("Bot is missing required attribute 'services.token_system' for TokenCommands.")
        return # Prevent loading if dependency missing
    # --- END MODIFIED --- #

    await bot.add_cog(TokenCommands(bot))
    logger.info("TokenCommands Cog loaded and added to bot.") 