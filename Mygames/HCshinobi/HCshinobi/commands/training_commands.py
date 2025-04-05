"""Training commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, Dict, List
import logging
import asyncio
from datetime import datetime, timedelta

from HCshinobi.core.training_system import TrainingSystem, TrainingIntensity
from HCshinobi.core.character_system import CharacterSystem

# Available attributes for training
TRAINING_ATTRIBUTES = {
    "ninjutsu": "Ninjutsu - Your ability to use chakra for jutsu",
    "taijutsu": "Taijutsu - Your hand-to-hand combat ability",
    "genjutsu": "Genjutsu - Your ability to create illusions",
    "intelligence": "Intelligence - Your strategic thinking and knowledge",
    "strength": "Strength - Your physical power",
    "speed": "Speed - Your agility and quickness",
    "stamina": "Stamina - Your endurance and energy",
    "chakra_control": "Chakra Control - Your ability to control chakra",
    "perception": "Perception - Your awareness and senses",
    "willpower": "Willpower - Your mental fortitude"
}

class TrainingView(ui.View):
    def __init__(self, cog: 'TrainingCommands', character, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.character = character
        self.selected_attribute = None
        self.selected_intensity = None
        self.selected_duration = None
        
        # Create the initial embed
        self.initial_embed = discord.Embed(
            title="🎯 Training Setup",
            description="Select your training options below:",
            color=discord.Color.blue()
        )
        
        # Add current stat values to help the user decide what to train
        self.initial_embed.add_field(
            name="Your Stats",
            value="\n".join([
                f"**{attr.title()}**: {getattr(character, attr, 0)}"
                for attr in TRAINING_ATTRIBUTES.keys()
            ]),
            inline=False
        )
        
        self.initial_embed.add_field(
            name="Instructions",
            value="1. Select an attribute to train\n2. Choose training intensity\n3. Set training duration\n4. Click 'Start Training'",
            inline=False
        )
        
        # Create intensity options
        intensity_options = [
            discord.SelectOption(
                label=intensity.title(),
                description=f"{intensity.title()} training - {self.get_intensity_description(intensity)}",
                value=intensity
            ) for intensity in [TrainingIntensity.LIGHT, TrainingIntensity.MODERATE, 
                              TrainingIntensity.INTENSE, TrainingIntensity.EXTREME]
        ]
        
        # Set up the intensity select
        self.select_intensity = ui.Select(
            placeholder="Select training intensity",
            min_values=1,
            max_values=1,
            options=intensity_options
        )
        self.select_intensity.callback = self.select_intensity_callback
        self.add_item(self.select_intensity)
        
        # Set up the attribute select
        self.select_attribute = ui.Select(
            placeholder="Select an attribute to train",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=attr.title(),
                    description=desc,
                    value=attr
                ) for attr, desc in TRAINING_ATTRIBUTES.items()
            ]
        )
        self.select_attribute.callback = self.select_attribute_callback
        self.add_item(self.select_attribute)
        
        # Set up the duration select
        self.select_duration = ui.Select(
            placeholder="Select training duration",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=f"{i} hours",
                    description=f"Train for {i} hours",
                    value=str(i)
                ) for i in range(1, 25)
            ]
        )
        self.select_duration.callback = self.select_duration_callback
        self.add_item(self.select_duration)
        
    async def select_attribute_callback(self, interaction: discord.Interaction):
        self.selected_attribute = self.select_attribute.values[0]
        await self.update_training_embed(interaction)
        
    async def select_intensity_callback(self, interaction: discord.Interaction):
        self.selected_intensity = self.select_intensity.values[0]
        await self.update_training_embed(interaction)
        
    async def select_duration_callback(self, interaction: discord.Interaction):
        self.selected_duration = int(self.select_duration.values[0])
        await self.update_training_embed(interaction)
        
    @ui.button(label="Start Training", style=discord.ButtonStyle.success, disabled=True)
    async def start_training_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Callback when the 'Start Training' button is pressed."""
        try:
            # Ensure all selections are made
            if not all([self.selected_attribute, self.selected_intensity, self.selected_duration]):
                await interaction.response.send_message("❌ Please select an attribute, intensity, and duration.", ephemeral=True)
                return
            
            # Defer to allow time for system interaction
            await interaction.response.defer(ephemeral=True)
            
            # Call the refactored TrainingSystem method
            success, message = await self.cog.training_system.start_training(
                player_id=str(interaction.user.id),
                attribute=self.selected_attribute,
                duration_hours=self.selected_duration,
                intensity=self.selected_intensity
            )
            
            # Edit the original ephemeral message with the result
            await interaction.followup.send(message, ephemeral=True)
            
            if success:
                self.stop() # Stop the view on success
                # Optionally edit the original interaction message if it wasn't ephemeral initially
                # try:
                #     original_message = await interaction.original_response()
                #     await original_message.edit(content="Training started! Check `/training_status`.", view=None)
                # except discord.NotFound:
                #     pass # Original message might have been deleted

        except Exception as e:
            self.cog.logger.error(f"Error in start_training_callback: {e}", exc_info=True)
            # Try to send an error message
            try:
                await interaction.followup.send("❌ An unexpected error occurred while trying to start training.", ephemeral=True)
            except Exception:
                pass # Ignore if followup fails
        
    def get_intensity_description(self, intensity: str) -> str:
        descriptions = {
            TrainingIntensity.LIGHT: "Safe but slow progress",
            TrainingIntensity.MODERATE: "Balanced training",
            TrainingIntensity.INTENSE: "Fast progress but higher risk",
            TrainingIntensity.EXTREME: "Maximum gains but very risky"
        }
        return descriptions.get(intensity, "Unknown intensity")
        
    async def update_training_embed(self, interaction: discord.Interaction):
        """Update the training embed with current selections."""
        embed = discord.Embed(
            title="🎯 Training Setup",
            description="Select your training options below:",
            color=discord.Color.blue()
        )
        
        # Add current selections
        if self.selected_attribute:
            embed.add_field(
                name="Selected Attribute",
                value=f"**{self.selected_attribute.title()}**\n{TRAINING_ATTRIBUTES[self.selected_attribute]}",
                inline=False
            )
            
        if self.selected_intensity:
            embed.add_field(
                name="Selected Intensity",
                value=f"**{self.selected_intensity.title()}**\n{self.get_intensity_description(self.selected_intensity)}",
                inline=False
            )
            
        if self.selected_duration:
            embed.add_field(
                name="Selected Duration",
                value=f"**{self.selected_duration} hours**",
                inline=False
            )
            
        # Update start button state - Find the button by its label
        start_button = discord.utils.get(self.children, label="Start Training")
        if start_button:
            start_button.disabled = not all([self.selected_attribute, self.selected_intensity, self.selected_duration])
        
        await interaction.response.edit_message(embed=embed, view=self)

class TrainingCommands(commands.Cog):
    def __init__(self, bot, training_system: TrainingSystem, character_system: CharacterSystem):
        """Initialize training commands."""
        self.bot = bot
        self.training_system = training_system
        self.character_system = character_system
        self.logger = logging.getLogger(__name__)

    @app_commands.command(name="train", description="Start a new training session")
    async def train(self, interaction: discord.Interaction):
        """Start a new training session for your character."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for train: {e}", exc_info=True)
            return

        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                try:
                    await interaction.followup.send("❌ You need a character to train!", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    self.logger.error(f"HTTP error sending train no-char followup: {http_err}", exc_info=True)
                return

            # Check if already training using the active_sessions dictionary
            if str(interaction.user.id) in self.training_system.active_sessions:
                 try:
                     # Maybe show status instead?
                     status_embed = self.training_system.get_training_status_embed(str(interaction.user.id))
                     if status_embed:
                         await interaction.followup.send("⏳ You are already training! Use `/training_status` to check progress.", embed=status_embed, ephemeral=True)
                     else:
                          await interaction.followup.send("⏳ You are already training! Use `/training_status` to check progress.", ephemeral=True)
                 except discord.errors.HTTPException as http_err:
                      self.logger.error(f"HTTP error sending train already-training followup: {http_err}", exc_info=True)
                 return

            view = TrainingView(self, character)
            # Use followup to send the initial message
            try:
                await interaction.followup.send(embed=view.initial_embed, view=view, ephemeral=True)
            except discord.errors.HTTPException as http_err:
                 self.logger.error(f"HTTP error sending train view followup: {http_err}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error in train command: {e}", exc_info=True)
            # Try to send error if possible
            try:
                await interaction.followup.send(
                    "❌ An error occurred while starting training.",
                    ephemeral=True
                )
            except discord.errors.HTTPException as http_err_fatal:
                 self.logger.error(f"HTTP error sending train fatal error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="training_status", description="Check your current training status")
    async def training_status(self, interaction: discord.Interaction):
        """Check the status of your current training session."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for training_status: {e}", exc_info=True)
            return

        try:
            user_id = str(interaction.user.id)
            
            # Check character exists (though training system might implicitly handle this)
            character = await self.character_system.get_character(user_id)
            if not character:
                 try:
                     await interaction.followup.send("❌ You need a character to check training status.", ephemeral=True)
                 except discord.errors.HTTPException as http_err:
                      self.logger.error(f"HTTP error sending training_status no-char followup: {http_err}", exc_info=True)
                 return
                 
            embed = self.training_system.get_training_status_embed(user_id)
            if embed:
                try:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                except discord.errors.HTTPException as http_err:
                     self.logger.error(f"HTTP error sending training_status embed followup: {http_err}", exc_info=True)
            else:
                try:
                    await interaction.followup.send("You are not currently training.", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                     self.logger.error(f"HTTP error sending training_status not-training followup: {http_err}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error in training_status command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ An error occurred while processing your command. Please try again later.",
                    ephemeral=True
                )
            except discord.errors.HTTPException as http_err_fatal:
                 self.logger.error(f"HTTP error sending training_status fatal error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="complete", description="Complete your current training session and claim results.")
    async def complete(self, interaction: discord.Interaction):
        """Complete your current training session and claim results."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True) # Defer ephemerally initially
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for complete training: {e}", exc_info=True)
            return

        try:
            user_id = str(interaction.user.id)
            # Add await
            success, message = await self.training_system.complete_training(user_id)
            
            if not success:
                try:
                    # Send error message ephemerally
                    await interaction.followup.send(f"❌ {message}", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                     self.logger.error(f"HTTP error sending complete training fail followup: {http_err}", exc_info=True)
                return
                
            # Create completion embed
            embed = discord.Embed(
                title="🎉 Training Complete!",
                description=message,
                color=discord.Color.green()
            )
            
            try:
                # Send success message publicly
                await interaction.followup.send(embed=embed, ephemeral=False) 
            except discord.errors.HTTPException as http_err:
                 self.logger.error(f"HTTP error sending complete training success followup: {http_err}", exc_info=True)
                 # Try to notify user ephemerally if public failed
                 try:
                      await interaction.followup.send("✅ Training completed, but failed to display the results message publicly.", ephemeral=True)
                 except discord.errors.HTTPException:
                      pass 
            
        except Exception as e:
            self.logger.error(f"Error in complete command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ An error occurred while processing your command. Please try again later.",
                    ephemeral=True
                )
            except discord.errors.HTTPException as http_err_fatal:
                 self.logger.error(f"HTTP error sending complete training fatal error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="cancel_training", description="Cancel your current training session without receiving benefits.")
    async def cancel_training(self, interaction: discord.Interaction):
        """Cancel your current training session without receiving benefits."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for cancel training: {e}", exc_info=True)
            return

        try:
            user_id = str(interaction.user.id)
            # Add await
            success, message = await self.training_system.cancel_training(user_id)
            
            if not success:
                try:
                    await interaction.followup.send(f"❌ {message}", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                     self.logger.error(f"HTTP error sending cancel training fail followup: {http_err}", exc_info=True)
                return
                
            # Create cancellation embed
            embed = discord.Embed(
                title="❌ Training Cancelled",
                description=message,
                color=discord.Color.red()
            )
            
            try:
                # Send cancellation message ephemerally
                await interaction.followup.send(embed=embed, ephemeral=True) 
            except discord.errors.HTTPException as http_err:
                 self.logger.error(f"HTTP error sending cancel training success followup: {http_err}", exc_info=True)
            
        except Exception as e:
            self.logger.error(f"Error in cancel_training command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "❌ An error occurred while processing your command. Please try again later.",
                    ephemeral=True
                )
            except discord.errors.HTTPException as http_err_fatal:
                 self.logger.error(f"HTTP error sending cancel training fatal error followup: {http_err_fatal}", exc_info=True)

async def setup(bot):
    """Set up the training commands cog."""
    try:
        training_system = bot.services.training_system
        character_system = bot.services.character_system
        training_commands = TrainingCommands(bot, training_system, character_system)
        await bot.add_cog(training_commands)
        return training_commands
    except Exception as e:
        logging.error(f"Error setting up TrainingCommands: {e}", exc_info=True)
        raise 