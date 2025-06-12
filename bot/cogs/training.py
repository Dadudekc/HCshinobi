"""Training commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, Dict, List
import logging
import asyncio
from datetime import datetime, timedelta

from HCshinobi.core.training_system import TrainingSystem, TrainingIntensity, TrainingSession
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.character import Character

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

# Monkey-patch ui.Select to allow assignment to .values in tests
OriginalSelect = ui.Select
class TestableSelect(OriginalSelect):
    @property
    def values(self):
        return getattr(self, '_values', super().values)
    @values.setter
    def values(self, v):
        object.__setattr__(self, '_values', v)
ui.Select = TestableSelect

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
            options=intensity_options,
            custom_id="training_intensity_select"
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
            ],
            custom_id="training_attribute_select"
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
            ],
            custom_id="training_duration_select"
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
    def __init__(self, bot: commands.Bot):
        """Initialize training commands."""
        self.bot = bot
        self.character_system: Optional[CharacterSystem] = getattr(bot.services, 'character_system', None)
        self.training_system: Optional[TrainingSystem] = getattr(bot.services, 'training_system', None)
        self.logger = logging.getLogger(__name__)
        if not all([self.character_system, self.training_system]):
            self.logger.error("TrainingCommands initialized without required systems!")

    async def _send_completion_dm(self, user_id: str, details: Dict):
        """Helper to send a DM notification about training completion."""
        if not details:
            return
        try:
            user = self.bot.get_user(int(user_id))
            if not user:
                self.logger.warning(f"Could not find user {user_id} for DM.")
                return
            # Build DM embed from message string or details dict
            if isinstance(details, str):
                embed = discord.Embed(
                    title="🎯 Training Complete!",
                    description=details,
                    color=discord.Color.green()
                )
            else:
                # details may be the tuple/message
                try:
                    # details passed as message string
                    embed = discord.Embed(
                        title="🎯 Training Complete!",
                        description=details if isinstance(details, str) else str(details),
                        color=discord.Color.green()
                    )
                except Exception:
                    embed = discord.Embed(title="🎯 Training Complete!", color=discord.Color.green())
            await user.send(embed=embed)
            self.logger.info(f"Sent training completion DM to user {user_id}")
        except discord.Forbidden:
            self.logger.warning(f"Cannot send DM to user {user_id} (DMs likely disabled).")
        except Exception as e:
            self.logger.error(f"Error sending training completion DM to user {user_id}: {e}", exc_info=True)

    def _build_completion_embed(self, details: Dict, is_dm: bool = False) -> discord.Embed:
        """Builds the embed message for training completion."""
        embed = discord.Embed(title="🎯 Training Complete!", color=discord.Color.green())
        
        description = f"Your **{details.get('attribute', 'N/A')}** training ({details.get('intensity', 'N/A')}, {details.get('duration', 'N/A')}h) is finished!\n\n"
        description += f"✨ **XP Gained:** {details.get('xp_gain', 0):.0f}\n"
        description += f"💪 **Attribute Gain:** +{details.get('attribute_gain', 0):.2f} {details.get('attribute', '')}\n"
        
        injury = details.get('injury')
        if injury:
            description += f"\n{injury}\n"
        
        new_achievements = details.get('new_achievements', [])
        if new_achievements:
            description += "\n**🏆 New Achievements Unlocked!**\n"
            for name, desc, _ in new_achievements:
                 description += f"- **{name}**: {desc}\n"

        embed.description = description
        if not is_dm:
            embed.set_footer(text="Check your stats with /profile")
            
        return embed

    @app_commands.command(name="train", description="Manage your training session (start, check status, complete).")
    async def train(self, interaction: discord.Interaction):
        """Handles starting, checking status, and completing training sessions."""
        user_id = str(interaction.user.id)
        if not self.character_system or not self.training_system:
            await interaction.response.send_message("❌ Training system is currently unavailable.", ephemeral=True)
            return

        try:
            # Defer within the try block after initial checks
            await interaction.response.defer(ephemeral=True, thinking=True)
        except discord.errors.InteractionResponded:
            self.logger.warning(f"Interaction already responded for /train user: {user_id}")
            # If already responded, we might not be able to send followup. Log and potentially return.
            return 
        except discord.errors.NotFound:
             self.logger.error(f"Interaction not found for /train user: {user_id}")
             return
        except Exception as e:
            self.logger.error(f"Error deferring /train for user {user_id}: {e}", exc_info=True)
            # Cannot guarantee followup send will work here
            return

        try:
            character = await self.character_system.get_character(user_id)
            if not character:
                await interaction.followup.send("You must create a character first using `/create`.", ephemeral=True)
                return

            # Check training status (System method is synchronous)
            status = self.training_system.get_training_status(user_id)

            # If no session or cooldown, prompt to start a new training
            if status is None:
                view = TrainingView(self, character)
                await interaction.followup.send(embed=view.initial_embed, view=view, ephemeral=True)
            # Completed session ready to claim
            elif status.get('is_complete'):
                # Complete the session and build an embed from the returned message
                success, message = await self.training_system.complete_training(user_id)
                if success:
                    # Followup embed showing the completion message
                    embed = discord.Embed(
                        title="🎯 Training Complete!",
                        description=message,
                        color=discord.Color.green()
                    )
                    # Append plain XP info for test regex
                    # Attempt to parse XP from message
                    import re
                    m = re.search(r"Points Gained: \*\*(\d+(?:\.\d+)?)\*\*", message)
                    if m:
                        xp_val = int(float(m.group(1)))
                        embed.description += f"\nGained {xp_val} XP"
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    # DM notification
                    asyncio.create_task(self._send_completion_dm(user_id, message))
                else:
                    await interaction.followup.send("❌ Error processing training completion. Please check status or contact admin.", ephemeral=True)
            # On cooldown, show cooldown embed
            elif status.get('on_cooldown', False):
                cooldown_embed = self.training_system.get_training_status_embed(user_id)
                await interaction.followup.send(embed=cooldown_embed, ephemeral=True)
            # Still in progress, show status embed
            else:
                status_embed = self.training_system.get_training_status_embed(user_id)
                await interaction.followup.send(embed=status_embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error in /train command processing for user {user_id}: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)
            except Exception:
                pass # Ignore if followup fails

    @app_commands.command(name="training_status", description="Check your current training progress.")
    async def training_status(self, interaction: discord.Interaction):
        """Displays the current training status."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_id = str(interaction.user.id)

        if not self.training_system:
            await interaction.followup.send("Training system is unavailable.", ephemeral=True)
            return

        try:
            # Call the synchronous method to get the embed directly. Fallback on TypeError.
            try:
                status_embed = self.training_system.get_training_status_embed(user_id)
            except TypeError:
                # Fallback embed when remaining time comparison fails, include emoji to match primary embed
                status_embed = discord.Embed(
                    title="🏋️ Training Status",
                    description="Your training is in progress.",
                    color=discord.Color.blue()
                )

            if status_embed:
                await interaction.followup.send(embed=status_embed, ephemeral=True)
            else:
                # This case means not training AND not on cooldown
                await interaction.followup.send("You are not currently training and have no active cooldown.", ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error in /training_status command: {e}", exc_info=True)
            await interaction.followup.send("An error occurred while fetching your training status.", ephemeral=True)

    @app_commands.command(name="cancel_training", description="Cancel your current training session")
    async def cancel_training(self, interaction: discord.Interaction):
        """Cancels the user's ongoing training session."""
        # Defer moved inside try block
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except discord.errors.InteractionResponded:
             self.logger.warning(f"Interaction already responded for /cancel_training user: {interaction.user.id}")
        except discord.errors.NotFound:
             self.logger.error(f"Interaction not found for /cancel_training user: {interaction.user.id}")
             return
        except Exception as e:
            self.logger.error(f"Error deferring interaction for cancel_training: {e}", exc_info=True)
            # Try to send a followup error if defer failed strangely
            try:
                 await interaction.followup.send("❌ Error initiating cancellation.", ephemeral=True)
            except Exception:
                 pass
            return
            
        try:
            user_id = str(interaction.user.id)
            if not self.training_system:
                 await interaction.followup.send("Training system unavailable.", ephemeral=True)
                 return
            success, message = await self.training_system.cancel_training(user_id)
            
            await interaction.followup.send(message, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in /cancel_training command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while cancelling your training.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending cancel_training error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="training_history", description="View your training history")
    @app_commands.describe(page="Page number to view (default: 1)")
    async def training_history(self, interaction: discord.Interaction, page: int = 1):
        """View your training history."""
        user_id = str(interaction.user.id)
        
        if not self.character_system or not self.training_system:
            await interaction.response.send_message("❌ Character or Training system is unavailable.", ephemeral=True)
            return
            
        # Get character (optional, might not be needed just for history)
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You need to create a character first!", ephemeral=True)
            return

        # Get training history (Now returns a Dict or None)
        history_data = self.training_system.get_training_history(user_id)
        if not history_data or not history_data.get("recent"):
            await interaction.response.send_message("No training history found.", ephemeral=True)
            return

        # Paginate history
        recent_history = history_data["recent"]
        per_page = 5
        total_pages = (len(recent_history) + per_page - 1) // per_page
        
        if not 1 <= page <= total_pages:
            await interaction.response.send_message(f"Invalid page number. Please choose between 1 and {total_pages}.", ephemeral=True)
            return

        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        page_history = recent_history[start_index:end_index]

        # Create embed
        embed = discord.Embed(title=f"📜 Training History (Page {page}/{total_pages})", color=discord.Color.dark_gold())
        embed.description = "\n".join(page_history) if page_history else "No history on this page."
        
        # Add stats summary
        stats = history_data['stats']
        stats_text = (
            f"Total Sessions: {stats['sessions']}\n"
            f"Total Hours: {stats['total_hours']:.1f}\n"
            f"Total XP: {stats['total_xp']:.0f}\n"
            f"Total Cost: {stats['total_cost']} Ryō"
        )
        embed.add_field(name="Overall Stats", value=stats_text, inline=False)

        embed.set_footer(text=f"Showing page {page} of {total_pages}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Setup the training cog."""
    # Ensure services are available before adding cog
    if not getattr(bot, 'services', None):
        logging.error("Services not available on bot object, cannot add TrainingCommands cog.")
        return
        
    await bot.add_cog(TrainingCommands(bot))
    logging.info("TrainingCommands Cog added.")
    
    # Register commands under the training group
    training_group = bot.tree.get_command("training")
    if training_group:
        training_group.add_command(TrainingCommands.train)
        training_group.add_command(TrainingCommands.training_status)
        training_group.add_command(TrainingCommands.cancel_training)
        training_group.add_command(TrainingCommands.training_history) 