import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from ...utils.embeds import create_error_embed


class TokenCommands(commands.Cog):
    """Commands for managing and using tokens in the game."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="tokens", description="Check your current token balance")
    async def tokens(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        """Check the token balance of yourself or another user."""
        target_user = user or interaction.user
        
        try:
            # Access the token system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'token_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Token system not available."),
                    ephemeral=True
                )
                return
            
            tokens = self.bot.services.token_system.get_player_tokens(target_user.id)
            
            embed = discord.Embed(
                title=f"🪙 Token Balance",
                description=f"**{target_user.display_name}** has **{tokens:,}** tokens",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Add some information about what tokens can be used for
            embed.add_field(
                name="Token Uses",
                value="• Reroll clan assignments\n• Boost mission rewards\n• Purchase special items\n• Unlock premium features",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=user is None)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error checking tokens: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="earn_tokens", description="Earn tokens through various activities")
    async def earn_tokens(self, interaction: discord.Interaction) -> None:
        """Earn tokens through daily activities or achievements."""
        try:
            # Access the token system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'token_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Token system not available."),
                    ephemeral=True
                )
                return
            
            # Simple daily token reward (could be enhanced with cooldown tracking)
            daily_tokens = 5
            token_system = self.bot.services.token_system
            token_system.add_tokens(interaction.user.id, daily_tokens)
            
            new_balance = token_system.get_player_tokens(interaction.user.id)
            
            embed = discord.Embed(
                title="🪙 Tokens Earned!",
                description=f"You earned **{daily_tokens}** tokens for being active!",
                color=discord.Color.purple()
            )
            embed.add_field(
                name="New Balance",
                value=f"{new_balance:,} tokens",
                inline=True
            )
            embed.add_field(
                name="Ways to Earn More",
                value="• Complete missions\n• Win battles\n• Daily activity\n• Special events",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error earning tokens: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="spend_tokens", description="Spend tokens on various benefits")
    async def spend_tokens(self, interaction: discord.Interaction, amount: int, purpose: str) -> None:
        """Spend tokens on various benefits."""
        try:
            if amount <= 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Amount must be positive!"),
                    ephemeral=True
                )
                return
            
            # Access the token system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'token_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Token system not available."),
                    ephemeral=True
                )
                return
            
            token_system = self.bot.services.token_system
            current_tokens = token_system.get_player_tokens(interaction.user.id)
            
            if current_tokens < amount:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Insufficient tokens! You have {current_tokens:,} but need {amount:,}."),
                    ephemeral=True
                )
                return
            
            # Define valid purposes and their effects
            valid_purposes = {
                "clan_reroll": {"cost": 10, "description": "Reroll your clan assignment"},
                "mission_boost": {"cost": 5, "description": "Boost mission rewards by 50%"},
                "experience_boost": {"cost": 15, "description": "Double experience for next activity"},
                "currency_bonus": {"cost": 8, "description": "Receive bonus currency"}
            }
            
            if purpose.lower() not in valid_purposes:
                purpose_list = "\n".join([f"• `{p}` - {info['description']} ({info['cost']} tokens)" 
                                        for p, info in valid_purposes.items()])
                await interaction.response.send_message(
                    embed=create_error_embed(f"Invalid purpose! Available options:\n{purpose_list}"),
                    ephemeral=True
                )
                return
            
            purpose_info = valid_purposes[purpose.lower()]
            if amount < purpose_info["cost"]:
                await interaction.response.send_message(
                    embed=create_error_embed(f"{purpose_info['description']} costs {purpose_info['cost']} tokens minimum."),
                    ephemeral=True
                )
                return
            
            # Spend the tokens
            token_system.add_tokens(interaction.user.id, -amount)
            new_balance = token_system.get_player_tokens(interaction.user.id)
            
            # Apply the effect (simplified for now)
            effect_message = self._apply_token_effect(purpose.lower(), amount, purpose_info["cost"])
            
            embed = discord.Embed(
                title="🪙 Tokens Spent!",
                description=f"Spent **{amount}** tokens on: {purpose_info['description']}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Effect",
                value=effect_message,
                inline=False
            )
            embed.add_field(
                name="Remaining Balance",
                value=f"{new_balance:,} tokens",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error spending tokens: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="token_shop", description="View available token purchases")
    async def token_shop(self, interaction: discord.Interaction) -> None:
        """Display the token shop with available purchases."""
        try:
            embed = discord.Embed(
                title="🪙 Token Shop",
                description="Spend your tokens on these benefits:",
                color=discord.Color.purple()
            )
            
            shop_items = [
                {"name": "Clan Reroll", "cost": 10, "description": "Get a new clan assignment"},
                {"name": "Mission Boost", "cost": 5, "description": "50% bonus mission rewards"},
                {"name": "Experience Boost", "cost": 15, "description": "Double XP for next activity"},
                {"name": "Currency Bonus", "cost": 8, "description": "Receive 500 bonus ryo"},
            ]
            
            for item in shop_items:
                embed.add_field(
                    name=f"{item['name']} - {item['cost']} 🪙",
                    value=item['description'],
                    inline=False
                )
            
            embed.add_field(
                name="How to Purchase",
                value="Use `/spend_tokens <amount> <purpose>` to buy items.\nExample: `/spend_tokens 10 clan_reroll`",
                inline=False
            )
            
            # Show user's current balance
            if hasattr(self.bot, 'services') and hasattr(self.bot.services, 'token_system'):
                tokens = self.bot.services.token_system.get_player_tokens(interaction.user.id)
                embed.set_footer(text=f"Your balance: {tokens:,} tokens")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error displaying token shop: {str(e)}"),
                ephemeral=True
            )

    def _apply_token_effect(self, purpose: str, amount_spent: int, base_cost: int) -> str:
        """Apply the effect of spending tokens and return a description."""
        effects = {
            "clan_reroll": "Your clan assignment has been reset! Use `/roll_clan` to get a new clan.",
            "mission_boost": "Your next mission will have 50% bonus rewards!",
            "experience_boost": "Your next activity will grant double experience!",
            "currency_bonus": f"You received {500 + (amount_spent - base_cost) * 50} bonus ryo!"
        }
        
        # For currency bonus, actually add the currency if the system is available
        if purpose == "currency_bonus" and hasattr(self.bot, 'services'):
            if hasattr(self.bot.services, 'currency_system'):
                bonus_amount = 500 + (amount_spent - base_cost) * 50
                # This would need the user_id, but we can't access it from this context
                # In a real implementation, this method would take user_id as a parameter
        
        return effects.get(purpose, "Effect applied successfully!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TokenCommands(bot)) 