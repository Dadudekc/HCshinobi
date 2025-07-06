import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from ...utils.embeds import create_error_embed
from ...core.training_system import TrainingIntensity


class TrainingCommands(commands.Cog):
    """Commands for character training and progression."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="train", description="Start a training session")
    @app_commands.describe(
        attribute="The attribute to train (strength, speed, chakra, intelligence)",
        duration="Training duration in hours (1-8)",
        intensity="Training intensity (Light, Moderate, Intense)"
    )
    async def train(
        self,
        interaction: discord.Interaction,
        attribute: str,
        duration: int,
        intensity: str = "Moderate"
    ) -> None:
        """Start a training session for a specific attribute."""
        try:
            # Validate inputs
            valid_attributes = ["strength", "speed", "chakra", "intelligence"]
            if attribute.lower() not in valid_attributes:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Invalid attribute! Choose from: {', '.join(valid_attributes)}"),
                    ephemeral=True
                )
                return
            
            if duration < 1 or duration > 8:
                await interaction.response.send_message(
                    embed=create_error_embed("Training duration must be between 1 and 8 hours!"),
                    ephemeral=True
                )
                return
            
            valid_intensities = [TrainingIntensity.LIGHT, TrainingIntensity.MODERATE, TrainingIntensity.INTENSE]
            if intensity not in valid_intensities:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Invalid intensity! Choose from: {', '.join(valid_intensities)}"),
                    ephemeral=True
                )
                return
            
            # Access the training system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'training_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Training system not available."),
                    ephemeral=True
                )
                return
            
            training_system = self.bot.services.training_system
            success, message = await training_system.start_training(
                interaction.user.id, 
                attribute.lower(), 
                duration, 
                intensity
            )
            
            if success:
                # Calculate cost and gains
                cost_multiplier = TrainingIntensity.get_multipliers(intensity)[0]
                base_cost = training_system._get_training_cost(attribute.lower())
                total_cost = int(base_cost * duration * cost_multiplier)
                
                expected_gain = duration * cost_multiplier
                
                embed = discord.Embed(
                    title="🏋️ Training Started!",
                    description=f"You begin training your **{attribute.capitalize()}**",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Training Details",
                    value=f"**Attribute:** {attribute.capitalize()}\n**Duration:** {duration} hours\n**Intensity:** {intensity}",
                    inline=True
                )
                embed.add_field(
                    name="Cost & Gains",
                    value=f"**Cost:** {total_cost} ryo\n**Expected Gain:** {expected_gain:.1f} points",
                    inline=True
                )
                embed.add_field(
                    name="Status",
                    value="Use `/training_status` to check progress\nUse `/complete_training` when finished",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(message),
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error starting training: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="training_status", description="Check your current training status")
    async def training_status(self, interaction: discord.Interaction) -> None:
        """Check the status of your current training session."""
        try:
            # Access the training system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'training_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Training system not available."),
                    ephemeral=True
                )
                return
            
            training_system = self.bot.services.training_system
            embed = training_system.get_training_status_embed(interaction.user.id)
            
            if embed:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have any active training sessions."),
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error checking training status: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="complete_training", description="Complete your current training session")
    async def complete_training(self, interaction: discord.Interaction, force: bool = False) -> None:
        """Complete your current training session."""
        try:
            # Access the training system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'training_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Training system not available."),
                    ephemeral=True
                )
                return
            
            training_system = self.bot.services.training_system
            success, message, gain = await training_system.complete_training(interaction.user.id, force)
            
            if success:
                embed = discord.Embed(
                    title="🏆 Training Completed!",
                    description=message,
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Attribute Points Gained",
                    value=f"**{gain:.1f}** points",
                    inline=True
                )
                embed.add_field(
                    name="Cooldown",
                    value="1 hour before next training",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(message),
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error completing training: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="cancel_training", description="Cancel your current training session")
    async def cancel_training(self, interaction: discord.Interaction) -> None:
        """Cancel your current training session."""
        try:
            # Access the training system through the bot's services
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'training_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Training system not available."),
                    ephemeral=True
                )
                return
            
            training_system = self.bot.services.training_system
            success, message = await training_system.cancel_training(interaction.user.id)
            
            if success:
                embed = discord.Embed(
                    title="❌ Training Cancelled",
                    description=message,
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Note",
                    value="No progress was saved and costs are not refunded.",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(message),
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error cancelling training: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="training_info", description="Get information about the training system")
    async def training_info(self, interaction: discord.Interaction) -> None:
        """Display information about the training system."""
        try:
            embed = discord.Embed(
                title="🏋️ Training System Guide",
                description="Train your character's attributes to become stronger!",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Available Attributes",
                value="• **Strength** - Physical power\n• **Speed** - Agility and reflexes\n• **Chakra** - Energy and jutsu power\n• **Intelligence** - Strategy and learning",
                inline=False
            )
            
            embed.add_field(
                name="Training Intensities",
                value="• **Light** - 1x cost, 1x gain\n• **Moderate** - 1.5x cost, 1.5x gain\n• **Intense** - 2x cost, 2x gain",
                inline=False
            )
            
            embed.add_field(
                name="Training Rules",
                value="• Duration: 1-8 hours\n• Base cost: 10 ryo per hour\n• Cooldown: 1 hour after completion\n• Only one training session at a time",
                inline=False
            )
            
            embed.add_field(
                name="Commands",
                value="• `/train` - Start training\n• `/training_status` - Check progress\n• `/complete_training` - Finish session\n• `/cancel_training` - Cancel session",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error displaying training info: {str(e)}"),
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrainingCommands(bot)) 