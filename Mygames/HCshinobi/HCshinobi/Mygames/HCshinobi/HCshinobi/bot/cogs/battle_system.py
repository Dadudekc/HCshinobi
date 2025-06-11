#!/usr/bin/env python

"""
Battle system implementation for the HCShinobi bot.
Includes battle state management, turn logic, and integration with CharacterManager.
"""

import discord # Use standard import
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, button # Import UI components
from typing import Optional, TYPE_CHECKING, List, Any, Dict
import logging
import asyncio # For sleep in animations

# Core service imports (No longer wrapped in try...except)
from ...core.battle_manager import BattleManager, BattleState, BattleManagerError
# Removed dummy class definitions as bot ensures managers exist before loading cogs

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..bot import HCShinobiBot

# --- Helper: Create Battle Embed --- #

def create_battle_embed(battle_state: BattleState) -> discord.Embed:
    """Creates a Discord embed representing the current battle state."""
    if not battle_state or not battle_state.player1 or not battle_state.player2:
        return discord.Embed(title="Battle Not Found", description="Could not display battle state.", color=discord.Color.greyple())
        
    # Determine turn and color
    current_turn_player = battle_state.get_current_turn_player()
    turn_desc = f"It's **{current_turn_player.name if current_turn_player else 'Unknown'}**'s turn!" if not battle_state.is_game_over() else "Battle Ended!"
    embed_color = discord.Color.blue() # Default color, maybe change based on turn?

    # Create embed
    embed = discord.Embed(
        title=f"⚔️ Battle: {battle_state.player1.name} vs {battle_state.player2.name} ⚔️",
        description=turn_desc,
        color=embed_color
    )

    # Add player fields
    for player in [battle_state.player1, battle_state.player2]:
        # Basic safety check
        if not player or not hasattr(player, 'current_hp') or not hasattr(player, 'max_hp') or player.max_hp <= 0:
             hp_bar = "[Error]" 
             hp_text = "?/?" 
        else:
             hp_percentage = max(0, min(1, player.current_hp / player.max_hp))
             hp_blocks = int(hp_percentage * 10)
             hp_bar = "█" * hp_blocks + "░" * (10 - hp_blocks)
             hp_text = f"{player.current_hp}/{player.max_hp}"

        status_effects = ", ".join(player.status_effects) if hasattr(player, 'status_effects') and player.status_effects else "None"
        player_id_tag = f" (Player: {player.player_id[:6]}...)" if getattr(player, 'is_player', False) else " (AI)"
        embed.add_field(
            name=f"{getattr(player, 'name', 'Unknown')}{player_id_tag}",
            value=f"HP: `{hp_text}` [{hp_bar}]\nStatus: {status_effects}",
            inline=True
        )
        
    # Add log messages
    log_text = "\n".join(battle_state.recent_logs[-5:]) # Show last 5 log messages
    if log_text:
         embed.add_field(name="Recent Actions", value=f"```\n{log_text}\n```", inline=False)
         
    embed.set_footer(text=f"Battle ID: {battle_state.battle_id} | Turn: {battle_state.turn_count}")
    return embed

# --- Battle View --- #

class BattleView(View):
    """A view with buttons for battle actions."""
    def __init__(self, battle_cog: 'BattleSystemCommands', battle_id: str):
        super().__init__(timeout=300) # 5-minute timeout
        self.battle_cog = battle_cog
        self.battle_id = battle_id
        self.last_interaction: Optional[discord.Interaction] = None
        self.battle_message: Optional[discord.Message] = None

        # Add battle action buttons
        self.add_item(AttackButton(battle_id, battle_cog))
        self.add_item(DefendButton(battle_id, battle_cog))
        self.add_item(SkillButton(battle_id, battle_cog))
        self.add_item(FleeButton(battle_id, battle_cog))

    async def update_view(self, interaction: Optional[discord.Interaction] = None, battle_state: Optional[BattleState] = None):
        """Updates the view's message with the current battle state."""
        # Use the last interaction if a new one isn't provided (e.g., for timeout)
        current_interaction = interaction or self.last_interaction
        if not current_interaction:
            logger.warning(f"BattleView {self.battle_id}: Cannot update view without an interaction.")
            return
            
        # Fetch the latest state if not provided
        if not battle_state:
             battle_state = self.battle_cog.battle_manager.get_battle_state(self.battle_id)
             if not battle_state:
                  # Battle likely ended or was removed, try to disable view
                  logger.warning(f"BattleView {self.battle_id}: Battle state not found during update.")
                  await self.disable_and_edit(current_interaction, "Battle has ended or could not be found.")
                  return
                  
        embed = create_battle_embed(battle_state)
        self.current_player_id = battle_state.current_player_id
        
        # Determine button state based on turn and game over
        is_players_turn = False
        if current_interaction.user: # Need user context for turn check
            is_players_turn = str(current_interaction.user.id) == self.current_player_id
        disable_buttons = not is_players_turn or battle_state.is_game_over()
        
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = disable_buttons
                
        try:
            # Try editing the original response of the interaction that triggered the update
            if not current_interaction.response.is_done():
                await current_interaction.response.edit_message(embed=embed, view=self)
            elif self.battle_message: # If response done, edit the stored message
                await self.battle_message.edit(embed=embed, view=self)
            else: # Fallback: Try getting original response if message not stored
                msg = await current_interaction.original_response()
                self.battle_message = msg # Store for next time
                await msg.edit(embed=embed, view=self)
                
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            logger.error(f"BattleView {self.battle_id}: Failed to edit message ({e}). Disabling view.")
            # If editing fails, try to disable buttons on the stored message if possible
            await self.disable_and_edit(current_interaction, f"Error updating battle: {e}", embed=embed) # Pass embed for context
            self.stop()
        except Exception as e:
             logger.exception(f"BattleView {self.battle_id}: Unexpected error during update_view: {e}")
             # Attempt to notify user of error
             try:
                  if not current_interaction.response.is_done():
                       await current_interaction.response.send_message("An error occurred updating the battle view.", ephemeral=True)
                  else:
                       await current_interaction.followup.send("An error occurred updating the battle view.", ephemeral=True)
             except Exception:
                  pass # Ignore errors sending error message
                  
    async def disable_and_edit(self, interaction: discord.Interaction, content: str, embed: Optional[discord.Embed] = None):
        """Disables all buttons and edits the message, trying multiple methods."""
        for item in self.children:
            if isinstance(item, Button):
                item.disabled = True
        try:
             if not interaction.response.is_done():
                  await interaction.response.edit_message(content=content, embed=embed, view=self)
             elif self.battle_message:
                  await self.battle_message.edit(content=content, embed=embed, view=self)
             else: # Last resort: try original response
                  msg = await interaction.original_response()
                  await msg.edit(content=content, embed=embed, view=self)
        except Exception as e:
             logger.error(f"BattleView {self.battle_id}: Failed final attempt to disable buttons and edit message: {e}")
             # Maybe try a followup message? 
             # await interaction.followup.send(content, ephemeral=True)

    async def handle_action(self, interaction: discord.Interaction, action_name: str):
        """Generic handler for battle actions triggered by buttons."""
        self.last_interaction = interaction # Store for potential use in timeout or errors
        player_id = str(interaction.user.id)
        logger.info(f"Battle action '{action_name}' triggered by {interaction.user.name} ({player_id}) for battle {self.battle_id}")
        
        # Fetch current state to check turn
        current_state = self.battle_cog.battle_manager.get_battle_state(self.battle_id)
        if not current_state:
             await interaction.response.send_message("This battle no longer exists.", ephemeral=True)
             self.stop()
             return
             
        if player_id != current_state.current_player_id:
             await interaction.response.send_message("It's not your turn!", ephemeral=True)
             return
             
        # Defer is tricky with views, handle response within update_view
        # await interaction.response.defer()

        try:
            # Perform the action using the battle manager
            updated_state = await self.battle_cog.battle_manager.perform_action(self.battle_id, player_id, action_name)
            
            # Update the view with the new state
            await self.update_view(interaction, updated_state)
            
            # Check for game over
            if updated_state.is_game_over():
                 winner = updated_state.get_winner()
                 loser = updated_state.get_loser()
                 result_text = f"🎉 Battle Over! {winner.name} Wins! 🎉" if winner else "Battle Over! It's a Draw!"
                 await self.disable_and_edit(interaction, result_text)
                 self.stop() # Stop the view listener
                 
        except BattleManagerError as e:
            logger.warning(f"Battle action error for {player_id} in {self.battle_id}: {e}")
            # Try sending ephemeral error message
            try:
                 if not interaction.response.is_done():
                      await interaction.response.send_message(f"Action failed: {e}", ephemeral=True)
                 else:
                      await interaction.followup.send(f"Action failed: {e}", ephemeral=True)
            except Exception as send_e:
                 logger.error(f"BattleView {self.battle_id}: Failed to send error followup: {send_e}")
        except Exception as e:
            logger.exception(f"BattleView {self.battle_id}: Unexpected error during handle_action '{action_name}' for {player_id}: {e}")
            # Try sending generic error message
            try:
                 if not interaction.response.is_done():
                     await interaction.response.send_message("An unexpected error occurred processing your action.", ephemeral=True)
                 else:
                     await interaction.followup.send("An unexpected error occurred processing your action.", ephemeral=True)
            except Exception as send_e:
                 logger.error(f"BattleView {self.battle_id}: Failed to send generic error followup: {send_e}")

    @button(label="Attack", style=discord.ButtonStyle.primary, custom_id="battle_attack")
    async def attack_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_action(interaction, "attack")

    @button(label="Pass", style=discord.ButtonStyle.secondary, custom_id="battle_pass")
    async def pass_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_action(interaction, "pass_turn") # Ensure manager uses this action key
        
    async def on_timeout(self):
        """Called when the view times out."""
        logger.info(f"Battle view for {self.battle_id} timed out.")
        if self.last_interaction:
             await self.disable_and_edit(self.last_interaction, "Battle timed out due to inactivity.")
        # Optionally, tell the battle manager the battle ended due to timeout
        if self.battle_cog and self.battle_cog.battle_manager:
             self.battle_cog.battle_manager.end_battle(self.battle_id, reason="Timeout")

class AttackButton(discord.ui.Button):
    def __init__(self, battle_id: str, battle_system: Any):
        super().__init__(
            label="⚔️ Attack",
            style=discord.ButtonStyle.primary,
            custom_id=f"attack_{battle_id}"
        )
        self.battle_id = battle_id
        self.battle_system = battle_system
        
    async def callback(self, interaction: discord.Interaction):
        try:
            result = await self.battle_system.process_action(self.battle_id, "attack")
            await self._handle_battle_result(interaction, result)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error processing attack: {e}", ephemeral=True)

class DefendButton(discord.ui.Button):
    def __init__(self, battle_id: str, battle_system: Any):
        super().__init__(
            label="🛡️ Defend",
            style=discord.ButtonStyle.secondary,
            custom_id=f"defend_{battle_id}"
        )
        self.battle_id = battle_id
        self.battle_system = battle_system
        
    async def callback(self, interaction: discord.Interaction):
        try:
            result = await self.battle_system.process_action(self.battle_id, "defend")
            await self._handle_battle_result(interaction, result)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error processing defense: {e}", ephemeral=True)

class SkillButton(discord.ui.Button):
    def __init__(self, battle_id: str, battle_system: Any):
        super().__init__(
            label="✨ Use Skill",
            style=discord.ButtonStyle.success,
            custom_id=f"skill_{battle_id}"
        )
        self.battle_id = battle_id
        self.battle_system = battle_system
        
    async def callback(self, interaction: discord.Interaction):
        try:
            # Show skill selection modal
            modal = SkillSelectionModal(self.battle_id, self.battle_system)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error selecting skill: {e}", ephemeral=True)

class FleeButton(discord.ui.Button):
    def __init__(self, battle_id: str, battle_system: Any):
        super().__init__(
            label="🏃 Flee",
            style=discord.ButtonStyle.danger,
            custom_id=f"flee_{battle_id}"
        )
        self.battle_id = battle_id
        self.battle_system = battle_system
        
    async def callback(self, interaction: discord.Interaction):
        try:
            result = await self.battle_system.process_action(self.battle_id, "flee")
            await self._handle_battle_result(interaction, result)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error processing flee: {e}", ephemeral=True)

class SkillSelectionModal(discord.ui.Modal):
    def __init__(self, battle_id: str, battle_system: Any):
        super().__init__(title="Select Skill")
        self.battle_id = battle_id
        self.battle_system = battle_system
        
        # Add skill selection dropdown
        self.skill_select = discord.ui.Select(
            placeholder="Choose a skill to use",
            options=self._get_skill_options()
        )
        self.add_item(self.skill_select)
        
    def _get_skill_options(self) -> List[discord.SelectOption]:
        """Get available skills for the current battle."""
        battle_state = self.battle_system.get_battle_state(self.battle_id)
        if not battle_state:
            return []
            
        player_skills = battle_state.get("player_skills", [])
        return [
            discord.SelectOption(
                label=skill["name"],
                value=skill["id"],
                description=f"Cost: {skill.get('chakra_cost', 0)} Chakra"
            )
            for skill in player_skills
            if skill.get("chakra_cost", 0) <= battle_state.get("player_chakra", 0)
        ]
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            skill_id = self.skill_select.values[0]
            result = await self.battle_system.process_action(self.battle_id, "skill", skill_id=skill_id)
            await self._handle_battle_result(interaction, result)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error using skill: {e}", ephemeral=True)

async def _handle_battle_result(interaction: discord.Interaction, result: Dict[str, Any]):
    """Handle the result of a battle action."""
    if result.get("battle_ended", False):
        # Battle is over, show final result
        embed = discord.Embed(
            title="Battle Ended",
            description=result.get("message", "Battle has concluded."),
            color=discord.Color.green() if result.get("victory", False) else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    else:
        # Battle continues, update the view
        view = BattleView(result["battle_id"], interaction.client.battle_system)
        await interaction.response.edit_message(
            content=result.get("message", "Battle continues..."),
            view=view
        )

# --- Battle Cog --- #

class BattleSystemCommands(commands.Cog):
    """Commands for using the battle system."""

    def __init__(self, bot: 'HCShinobiBot'):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        # Instantiate BattleManager using the actual CharacterManager
        self.battle_manager = BattleManager(
            character_system=bot.get_character_system(),
            progression_engine=bot.get_progression_engine()
        )
        self.logger.info("BattleSystemCommands cog loaded successfully.")
        
    def get_battle_system(self):
        """Returns the battle system for use by other cogs."""
        return self.battle_manager
    
    # Player Character Autocomplete
    async def character_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for player characters owned by the user."""
        if not hasattr(self.bot, 'character_manager') or not self.bot.character_manager:
             return []
        player_id = str(interaction.user.id)
        try:
             chars = self.bot.character_manager.get_user_characters(player_id)
             char_names = [c.name for c in chars]
        except Exception as e:
             logger.error(f"Error fetching characters for autocomplete for user {player_id}: {e}")
             return []
             
        if not current:
            return [app_commands.Choice(name=name, value=name) for name in char_names[:25]]
        else:
            matches = [name for name in char_names if current.lower() in name.lower()]
            return [app_commands.Choice(name=match, value=match) for match in matches[:25]]

    @app_commands.command(name="battle_status", description="Check the status of your current battle.")
    async def battle_status(self, interaction: discord.Interaction):
        """Displays the status of the user's current battle."""
        if not self.battle_manager:
            await interaction.response.send_message("Battle system is currently unavailable.", ephemeral=True)
            return

        player_id = str(interaction.user.id)
        battle_id = self.battle_manager.get_player_battle_id(player_id) # Assume this helper exists
        if not battle_id:
             await interaction.response.send_message("You are not currently in an active battle.", ephemeral=True)
             return
             
        battle_state = self.battle_manager.get_battle_state(battle_id)
        if not battle_state:
            # Should not happen if get_player_battle_id returned an ID, but good practice
            await interaction.response.send_message("Could not retrieve the status of your battle.", ephemeral=True)
            return

        embed = create_battle_embed(battle_state)
        # Create a temporary view just to display buttons correctly (they might be disabled)
        view = BattleView(self, battle_state.battle_id)
        view.current_player_id = battle_state.current_player_id
        is_players_turn = player_id == battle_state.current_player_id
        disable_buttons = not is_players_turn or battle_state.is_game_over()
        for item in view.children:
             if isinstance(item, Button):
                  item.disabled = disable_buttons
                  
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @app_commands.command(name="end_battle", description="[Admin] Forcibly end an ongoing battle.")
    @app_commands.describe(battle_id="The ID of the battle to end (get from /battle_status or embed footer).")
    @app_commands.checks.has_permissions(administrator=True)
    async def end_battle(self, interaction: discord.Interaction, battle_id: str):
         """Admin command to end a specific battle."""
         if not self.battle_manager:
             await interaction.response.send_message("Battle system is currently unavailable.", ephemeral=True)
             return
         
         try:
             success = self.battle_manager.end_battle(battle_id, reason=f"Ended by Admin {interaction.user.name}")
             if success:
                  await interaction.response.send_message(f"Battle `{battle_id}` ended successfully.", ephemeral=True)
             else:
                  await interaction.response.send_message(f"Battle `{battle_id}` not found or already ended.", ephemeral=True)
         except Exception as e:
              logger.error(f"Error during admin end_battle for {battle_id}: {e}", exc_info=True)
              await interaction.response.send_message(f"An error occurred ending battle `{battle_id}`.", ephemeral=True)

async def setup(bot: 'HCShinobiBot'):
    """Sets up the Battle System Cog."""
    # Ensure core BattleManager is available on the bot
    if not hasattr(bot, 'battle_manager'):
        logger.error("Cannot load BattleSystemCommands cog: Bot is missing 'battle_manager' attribute.")
        # Decide whether to raise an error or just log and disable
        # raise commands.ExtensionFailed("battle_system", "Bot is missing 'battle_manager'")
        return # Or return gracefully without loading

    try:
        await bot.add_cog(BattleSystemCommands(bot)) # Use the new class name
        logger.info("BattleSystemCommands Cog loaded successfully.")
    except Exception as e:
        logger.exception(f"Failed to load BattleSystemCommands cog: {e}")
        # Rethrow or handle as needed
        raise e 