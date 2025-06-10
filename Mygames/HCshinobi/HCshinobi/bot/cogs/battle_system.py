#!/usr/bin/env python

"""
Battle system implementation for the HCShinobi bot.
Includes battle state management, turn logic, and integration with CharacterManager.
"""

import discord # Use standard import
from discord import app_commands, ui
from discord.ext import commands
from discord.ui import View, Button, button, Select # Import UI components
from typing import Optional, TYPE_CHECKING, List, Any, Dict, Tuple
import logging
import asyncio # For sleep in animations
from datetime import datetime

# Core service imports (No longer wrapped in try...except)
from ...core.battle_manager import BattleManager, BattleState, BattleManagerError, BattleNotFoundError
from ...core.battle_system import BattleSystem
from ...core.character_system import CharacterSystem
from ...utils.embed_utils import get_rarity_color
from ...core.constants import RarityTier
from ...core.character import Character # Add Character import
# Removed dummy class definitions as bot ensures managers exist before loading cogs
# Import ServiceContainer for type hinting
from HCshinobi.bot.services import ServiceContainer
# Import Item definition if needed for type hints or checks (adjust path as needed)
# from ...data_models.item import Item # Remove unused import

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..bot import HCShinobiBot

# Store pending duels in memory: {challenged_user_id: (challenger_user_id, discord.Interaction)}
pending_duels: Dict[int, Tuple[int, discord.Interaction]] = {}

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

# --- Duel Invite View --- #

class DuelInviteView(ui.View):
    """Presents Accept/Decline buttons to the challenged user."""
    def __init__(
        self,
        cog: 'BattleSystemCommands',
        challenger: discord.Member,
        opponent: discord.Member,
        timeout: float = 120
    ):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.challenger = challenger
        self.opponent = opponent
        self.accepted: Optional[bool] = None
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the targeted opponent can click the Accept/Decline buttons."""
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "This duel invitation is not for you.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        """If time expires, mark as declined and update the message."""
        self.accepted = False
        if self.message:
            try:
                await self.message.edit(
                    content=(
                        f"⌛ {self.challenger.mention}'s duel invitation to "
                        f"{self.opponent.mention} **timed out**."
                    ),
                    view=None
                )
            except discord.NotFound:
                pass
        self.stop()

    @ui.button(label="Accept Duel", style=discord.ButtonStyle.success, custom_id="duel_accept")
    async def accept_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handles acceptance of the duel invite."""
        self.accepted = True
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        
        await interaction.response.edit_message(
            content=(
                f"✅ {self.opponent.mention} **accepted** the duel challenge from "
                f"{self.challenger.mention}! Starting battle..."
            ),
            view=self
        )
        self.stop()

    @ui.button(label="Decline Duel", style=discord.ButtonStyle.danger, custom_id="duel_decline")
    async def decline_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handles declining of the duel invite."""
        self.accepted = False
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        
        await interaction.response.edit_message(
            content=(
                f"❌ {self.opponent.mention} **declined** the duel challenge from "
                f"{self.challenger.mention}."
            ),
            view=self
        )
        self.stop()

# --- Opponent Select View --- #

class OpponentSelectView(ui.View):
    """View to select an opponent for battle, currently focused on NPCs."""
    def __init__(self, cog: 'BattleSystemCommands', original_interaction: discord.Interaction):
        super().__init__(timeout=120)
        self.cog = cog
        self.original_interaction = original_interaction
        self.message: Optional[discord.Message] = None

        # TODO: Dynamically fetch challengeable NPCs
        # For now, hardcode Solomon if available
        # In the future, query character_system for NPCs with 'is_challengeable' flag
        # or from a predefined list.
        # self.add_item(Button(label="Battle Solomon", style=discord.ButtonStyle.danger, custom_id="select_npc_Solomon")) # REMOVED THIS LINE
        # Add more buttons or a Select menu for other NPCs/Players later

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original user to interact."""
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("This battle selection is not for you.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="Battle selection timed out.", view=None)
            except discord.NotFound:
                pass
        self.stop()

    @button(label="Battle Solomon", style=discord.ButtonStyle.danger, custom_id="select_npc_Solomon")
    async def battle_solomon_button(self, interaction: discord.Interaction, button: Button):
        """Callback for the 'Battle Solomon' button."""
        npc_id_to_battle = "Solomon" # Hardcoded for this button
        
        # Disable buttons on selection
        for item in self.children:
            if isinstance(item, ui.Button):
                item.disabled = True
        await interaction.response.edit_message(content=f"Attempting to start battle against {npc_id_to_battle}...", view=self)
        
        try:
            # Fetch characters
            logger.debug(f"Attempting to fetch challenger character: {interaction.user.id}")
            challenger_char = await self.cog.services.character_system.get_character(str(interaction.user.id))
            logger.debug(f"Challenger fetch result: {challenger_char is not None}")
            
            logger.debug(f"Attempting to fetch opponent character: {npc_id_to_battle}")
            opponent_char = await self.cog.services.character_system.get_character(npc_id_to_battle)
            logger.debug(f"Opponent fetch result: {opponent_char is not None}")

            if not challenger_char:
                # Use followup as the original message was edited
                await interaction.followup.send(f"You don't have a character! Use `/create_character`.", ephemeral=True)
                self.stop()
                return
            if not opponent_char:
                await interaction.followup.send(f"Could not find the opponent: {npc_id_to_battle}", ephemeral=True)
                self.stop()
                return

            # Check if challenger is already in battle
            challenger_battle_id, _, _ = self.cog._get_current_battle_for_user(str(interaction.user.id))
            if challenger_battle_id:
                await interaction.followup.send("You are already in a battle!", ephemeral=True)
                self.stop()
                return
                
            # Start the battle using the existing logic function
            # Pass the button interaction, which _start_battle_logic will edit
            success, message = await self.cog._start_battle_logic(interaction, challenger_char, opponent_char)
            
            if not success:
                # _start_battle_logic might fail after editing the message initially
                # Send a followup error
                await interaction.followup.send(f"Failed to start battle: {message}", ephemeral=True)
                # We might want to re-enable the view here, but for now, just stop

        except Exception as e:
            logger.exception(f"Error starting battle via OpponentSelectView for {interaction.user.id} vs {npc_id_to_battle}")
            try:
                # Try to send a followup if possible
                await interaction.followup.send("An unexpected error occurred while starting the battle.", ephemeral=True)
            except discord.HTTPException:
                pass # Ignore if followup fails
                
        # Stop the view regardless of success/failure after attempt
        self.stop()


# --- Battle View --- #

# Forward declare BattleView for type hints in Select menus
class BattleView(View):
    pass

# --- Jutsu Select --- #

class JutsuSelect(Select):
    """A dropdown that shows all jutsu the current player knows."""
    def __init__(self, battle_view: BattleView):
        self.battle_view = battle_view
        # Get current player character directly from battle_state
        player = self.battle_view.battle_state.get_current_turn_player()

        # Access master data via battle_system -> services
        master_jutsu_data = self.battle_view.battle_system.services.jutsu_manager.get_all_jutsu()
        options = []

        if player and player.known_jutsu:
            for jutsu_name in player.known_jutsu:
                jutsu_info = master_jutsu_data.get(jutsu_name)
                if jutsu_info:
                    jutsu_type = jutsu_info.type
                    jutsu_cost = jutsu_info.cost
                    cost_parts = []
                    if jutsu_cost.chakra > 0:
                        cost_parts.append(f"{jutsu_cost.chakra} Chakra")
                    if jutsu_cost.stamina > 0:
                        cost_parts.append(f"{jutsu_cost.stamina} Stamina")
                    cost_str = ", ".join(cost_parts) if cost_parts else "No Cost"
                    description = f"{jutsu_type.capitalize()} - Cost: {cost_str}"
                else:
                    description = "(Data not found)"
                options.append(
                    discord.SelectOption(
                        label=jutsu_name,
                        description=description
                    )
                )
        else:
            options.append(discord.SelectOption(
                label="No Jutsu Known",
                description="You haven't learned any jutsu yet.",
                value="_none_"
            ))

        if not options:
            options.append(discord.SelectOption(
                label="No Jutsu Found",
                description="You have no usable jutsu.",
                value="_none_"
            ))

        super().__init__(
            placeholder="Choose a Jutsu...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="jutsu_select",
            row=1 # Place jutsu select on the second row
        )

    async def callback(self, interaction: discord.Interaction):
        """Called when the player selects a jutsu from the dropdown."""
        # Use the battle_view's check
        if not await self.battle_view.interaction_check(interaction):
            return

        selected_jutsu_id = self.values[0] # Renamed for clarity
        if selected_jutsu_id in ("_none_", "_error_"):
            await interaction.response.send_message(
                f"Invalid selection: {selected_jutsu_id}",
                ephemeral=True
            )
            # Re-enable the select or handle appropriately if needed
            return

        # --- Get Jutsu Data and Target Type --- 
        jutsu_manager = self.battle_view.battle_system.services.jutsu_manager
        jutsu_data = jutsu_manager.get_jutsu(selected_jutsu_id) # Use get_jutsu
        if not jutsu_data:
            # Attempt to access name attribute safely if available
            jutsu_name_display = getattr(jutsu_data, 'name', selected_jutsu_id) if jutsu_data else selected_jutsu_id
            await interaction.response.send_message(f"Error: Could not find data for jutsu {jutsu_name_display}.", ephemeral=True)
            return
            
        target_type = jutsu_data.get("target_type", "opponent") # Default to opponent
        user_id = str(interaction.user.id)
        opponent_id = self.battle_view.battle_state.get_opponent_player_id(user_id)

        # --- Handle Targeting --- 
        target_id = None
        if target_type == "self" or target_type == "utility": # Treat utility as self-target for now
            target_id = user_id
        elif target_type == "opponent":
            # If requires opponent target, prompt user
            if opponent_id:
                view = TargetSelectView(
                    battle_view=self.battle_view, 
                    # Pass jutsu_id instead of item_id
                    item_id=selected_jutsu_id, # Re-use TargetSelectView for simplicity, though name is misleading
                    user_id=user_id, 
                    opponent_id=opponent_id
                )
                # Update prompt message
                await interaction.response.send_message(f"Use {jutsu_data.name} on:", view=view, ephemeral=True)
                return # Wait for button press in TargetSelectView
            else:
                 await interaction.response.send_message("Error: Could not determine opponent for targeting.", ephemeral=True)
                 return
        # Add cases for "ally" or "area" later if needed
        else: # Default case (should ideally not be reached with defined types)
            target_id = opponent_id # Default to opponent if type is unknown/other
            
        # --- Prepare and Handle Action (only if no further targeting needed) ---
        action_dict = {
            'type': 'jutsu',
            'jutsu_id': selected_jutsu_id, # Pass ID
            'target_id': target_id
        }
        # Defer response before handling action
        if not interaction.response.is_done():
             await interaction.response.defer() 
             
        await self.battle_view.handle_action(interaction, action_dict)


# --- Item Select --- #

class ItemSelect(Select):
    """A dropdown that shows usable items from the player's inventory."""
    def __init__(self, battle_view: BattleView):
        self.battle_view = battle_view
        player = self.battle_view.battle_state.get_current_turn_player()

        # Access services via battle_system
        item_manager = self.battle_view.battle_system.services.item_manager
        # character_system = self.battle_view.battle_system.services.character_system # Not needed directly here
        options = []

        if player and hasattr(player, 'inventory'):
            player_inventory = player.inventory

            for item_id, count in player_inventory.items():
                if count <= 0:
                    continue
                item_data = item_manager.get_item_definition(item_id)
                # Check if the item is usable in battle using .get()
                if item_data and item_data.get("is_usable_in_battle", False):
                    description = item_data.get("description", "No description available")
                    options.append(
                        discord.SelectOption(
                            label=f"{item_data.get('name', item_id)} (x{count})", # Use get for name too
                            value=item_id, # Store item_id as the value
                            description=description[:100] # Max description length
                        )
                    )

        if not options:
            options.append(discord.SelectOption(
                label="No Usable Items",
                description="You have no items usable in battle.",
                value="_none_"
            ))

        super().__init__(
            placeholder="Use an Item...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="item_select",
            row=2 # Place item select on the third row
        )

    async def callback(self, interaction: discord.Interaction):
        """Called when the player selects an item from the dropdown."""
        if not await self.battle_view.interaction_check(interaction):
            return

        selected_item_id = self.values[0]
        if selected_item_id == "_none_":
            await interaction.response.send_message("No item selected.", ephemeral=True)
            return

        # --- Get Item Data and Target Type --- 
        item_manager = self.battle_view.battle_system.services.item_manager
        item_data = item_manager.get_item_definition(selected_item_id)
        if not item_data:
            await interaction.response.send_message(f"Error: Could not find data for item {selected_item_id}.", ephemeral=True)
            return
            
        target_type = item_data.get("target_type", "none")
        user_id = str(interaction.user.id)
        opponent_id = self.battle_view.battle_state.get_opponent_player_id(user_id)

        # --- Handle Targeting --- 
        target_id = None
        if target_type == "self":
            target_id = user_id
        elif target_type == "opponent":
            # If requires opponent target, prompt user
            if opponent_id:
                view = TargetSelectView(
                    battle_view=self.battle_view, 
                    item_id=selected_item_id, 
                    user_id=user_id, 
                    opponent_id=opponent_id
                )
                await interaction.response.send_message("Select a target:", view=view, ephemeral=True)
                return # Wait for button press in TargetSelectView
            else:
                 # Should not happen in a 1v1 scenario, but handle defensively
                 await interaction.response.send_message("Error: Could not determine opponent for targeting.", ephemeral=True)
                 return
        elif target_type == "ally":
            # TODO: Implement ally targeting if/when team battles are supported
            await interaction.response.send_message("Ally targeting is not yet implemented.", ephemeral=True)
            return
        # For "none" or unhandled types, target_id remains None

        # --- Prepare and Handle Action (only if no further targeting needed) ---
        action_dict = {
            'type': 'item',
            'item_id': selected_item_id,
            'target_id': target_id
        }
        # Defer response before handling action
        # Need to defer here since we might have sent the target prompt
        if not interaction.response.is_done():
             await interaction.response.defer() # Defer only if no message sent yet
             
        await self.battle_view.handle_action(interaction, action_dict)


# --- Target Selection View --- (New View for Item Targeting)

class TargetSelectView(View):
    def __init__(self, battle_view: BattleView, item_id: str, user_id: str, opponent_id: str):
        # item_id here is actually the action identifier (item_id or jutsu_id)
        super().__init__(timeout=60) # Short timeout for target selection
        self.battle_view = battle_view
        self.action_id = item_id # Use a more generic name
        self.user_id = user_id
        self.opponent_id = opponent_id
        self.message: Optional[discord.Message] = None
        # Determine if the action is an item or jutsu based on context? Or pass type?
        # For now, assume resolve can handle it based on dict content.

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only the user who selected the item can choose the target
        return interaction.user.id == int(self.user_id)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="Target selection timed out.", view=None)
            except discord.NotFound:
                pass
        self.stop()

    async def _handle_target_selection(self, interaction: discord.Interaction, target_player_id: str):
        # Determine action type based on ID? Hacky.
        # Better: Pass type to view or fetch data again here.
        # Simple check: If it exists in item_manager, assume item, else jutsu.
        is_item = self.battle_view.battle_system.services.item_manager.get_item_definition(self.action_id) is not None
        action_type = 'item' if is_item else 'jutsu'
        
        action_dict = {
            'type': action_type,
            'target_id': target_player_id
        }
        if is_item:
            action_dict['item_id'] = self.action_id
        else:
             action_dict['jutsu_id'] = self.action_id # Use correct key for jutsu

        # Respond to the button click first
        action_name = self.battle_view.battle_system.services.item_manager.get_item_definition(self.action_id).get('name') if is_item else self.battle_view.battle_system.services.jutsu_manager.get_jutsu(self.action_id).name
        await interaction.response.edit_message(content=f"Target selected. Using {action_name}...", view=None)
        # Then proceed with the main battle action handling
        await self.battle_view.handle_action(interaction, action_dict)
        self.stop()

    @button(label="Target Opponent", style=discord.ButtonStyle.danger, custom_id="target_opponent")
    async def target_opponent_button(self, interaction: discord.Interaction, button: Button):
        await self._handle_target_selection(interaction, self.opponent_id)

    @button(label="Target Self", style=discord.ButtonStyle.primary, custom_id="target_self")
    async def target_self_button(self, interaction: discord.Interaction, button: Button):
        # Allow targeting self even if default is opponent, might be useful?
        await self._handle_target_selection(interaction, self.user_id)


# --- Battle View (Main Class Definition) --- #

class BattleView(View):
    """Main interactive View for an active battle."""
    def __init__(
        self,
        battle_state: BattleState,
        battle_system: BattleSystem,
        # character_system: CharacterSystem, # Can get from battle_system.services
        battle_manager: BattleManager,
        original_interaction: discord.Interaction # Store the interaction that started the battle
    ):
        super().__init__(timeout=300)  # 5 minute default timeout
        self.battle_state = battle_state
        self.battle_system = battle_system
        # self.character_system = character_system
        self.battle_manager = battle_manager
        self.original_interaction = original_interaction # Use this for followups
        self.message: Optional[discord.Message] = None # To store the battle message

        # Add UI components
        # Row 0: Basic actions
        self.attack_button = Button(label="Basic Attack", style=discord.ButtonStyle.primary, custom_id="battle_attack", row=0)
        self.attack_button.callback = self.attack_button_callback
        self.add_item(self.attack_button)

        self.defend_button = Button(label="Defend", style=discord.ButtonStyle.secondary, custom_id="battle_defend", row=0)
        self.defend_button.callback = self.defend_button_callback
        self.add_item(self.defend_button)

        # Row 1: Jutsu Select
        self.add_item(JutsuSelect(self))

        # Row 2: Item Select
        self.add_item(ItemSelect(self))

        # Row 3: Flee Button
        self.flee_button = Button(label="Flee", style=discord.ButtonStyle.danger, custom_id="battle_flee", row=3)
        self.flee_button.callback = self.flee_button_callback
        self.add_item(self.flee_button)

        self.update_components()

    def create_embed(self) -> discord.Embed:
        """Creates an embed reflecting the current state of the battle."""
        # Use the standalone helper function
        return create_battle_embed(self.battle_state)

    def update_components(self):
        """Updates button and select states based on current turn and battle state."""
        # Check if the battle is still active
        is_active = self.battle_state.is_active()
        if not is_active:
            # Disable everything if the battle is over
            for item in self.children:
                item.disabled = True
            return

        # Get the ID of the player whose turn it is
        current_player_id = self.battle_state.get_current_turn_player_id()

        # Enable/disable components based on whose turn it is
        # We need to know which user ID corresponds to which component interaction.
        # This requires storing the original interaction user IDs or fetching them.
        # For simplicity, let's assume the 'original_interaction' user is always player 1?
        # This is likely incorrect. A better approach is needed.

        # Problem: How does the View know which discord user ID corresponds to player1 vs player2?
        # The BattleState knows player_id, but the View's interaction comes from a discord.Interaction.user.id.
        # We need to map interaction.user.id to player_id.

        # Let's assume, for now, the interaction check handles this implicitly.
        # Disable all components by default
        # for item in self.children:
        #     item.disabled = True

        # We need to re-enable components only for the current player.
        # The interaction_check will prevent wrong player interaction, but visually disabling
        # for the *other* player is better UX.
        # How to do this cleanly? Maybe pass the current interaction user_id to update_components?
        # Or maybe the view is only interacted with by one user at a time?
        # If the view is shared, disabling/enabling per user is complex.

        # Let's rely on interaction_check for now and keep components visually enabled.
        # Refine later if UX feels wrong.
        for item in self.children:
             item.disabled = not is_active

        # Update Select options dynamically if needed (e.g., inventory changes)
        # This requires removing and re-adding the select menus, which can be complex.
        # Let's skip dynamic updates for now.

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the current player in the battle can interact."""
        # Get the Character object for the interacting user
        acting_player_char = self.battle_state.get_player_by_id(str(interaction.user.id))
        if not acting_player_char:
            # This should not happen if the user is part of the battle
            # Check if the user is player1 or player2 based on their ID
            if str(interaction.user.id) == self.battle_state.player1.player_id or str(interaction.user.id) == self.battle_state.player2.player_id:
                # It's one of the players, but maybe not their turn?
                pass # Proceed to turn check
            else:
                await interaction.response.send_message("You are not part of this battle!", ephemeral=True)
                return False

        # Check if it's the interacting user's turn
        current_turn_player = self.battle_state.get_current_turn_player()
        if not current_turn_player or str(interaction.user.id) != current_turn_player.player_id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return False

        # Check if the battle is still active
        if not self.battle_state.is_active():
             await interaction.response.send_message("The battle has already ended!", ephemeral=True)
             return False

        return True

    async def update_view(self, interaction: discord.Interaction, result: Dict[str, Any]):
        """Updates the message embed and view components after an action."""
        # Update the components (e.g., disable buttons if needed, update selects)
        self.update_components()

        # Create the updated embed
        embed = self.create_embed()

        # Edit the original message
        try:
            # Use the interaction associated with the action (button/select click)
            if not interaction.response.is_done():
                 await interaction.response.edit_message(embed=embed, view=self)
            else:
                 # If response was deferred/sent, use followup or original message edit
                 if self.message:
                      await self.message.edit(embed=embed, view=self)
                 else: # Fallback to original interaction if message not stored
                      await self.original_interaction.edit_original_response(embed=embed, view=self)
        except discord.NotFound:
            logger.warning(f"Failed to edit battle message for battle {self.battle_state.battle_id} - message not found.")
        except discord.HTTPException as e:
             logger.error(f"HTTP Error updating battle view: {e}")
             # Potentially send a followup if edit fails
             try:
                await interaction.followup.send("Error updating battle display.", ephemeral=True)
             except Exception:
                 pass # Ignore errors sending the error message

    async def handle_action(self, interaction: discord.Interaction, action_dict: Dict[str, Any]):
        """Handles battle actions triggered by buttons or selections."""
        # Interaction check should happen *before* calling handle_action (in button/select callbacks)
        # But double-check here just in case.
        if not await self.interaction_check(interaction):
             # If interaction_check sent a response, we might not need another one.
             # However, if interaction.response.defer() was called, we need to send something.
             if interaction.response.is_done():
                  try:
                       await interaction.followup.send("Action cancelled or invalid.", ephemeral=True)
                  except discord.HTTPException:
                       pass # Ignore if followup fails
             return

        try:
            # Perform the action using the core battle system
            # Pass the whole action_dict now
            result = await self.battle_system.process_action(
                self.battle_state.battle_id,
                str(interaction.user.id), # Pass the acting player's Discord ID
                action_dict
            )

            # Update the view with the results
            await self.update_view(interaction, result)

            # Check for game over
            if not self.battle_state.is_active():
                winner = self.battle_state.winner
                loser = self.battle_state.loser
                result_text = f"🎉 Battle Over! {winner.name} defeats {loser.name}! 🎉" if winner and loser else "Battle Over! It's a Draw!"

                # Disable components and edit the message one last time
                await self.disable_and_edit(interaction, result_text)
                self.stop() # Stop the view

        except BattleManagerError as e:
            logger.warning(f"Battle logic error: {e}")
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"Battle Error: {str(e)}", ephemeral=True)
            else:
                 await interaction.followup.send(f"Battle Error: {str(e)}", ephemeral=True)
        except Exception as e:
            logger.exception(f"Unexpected error handling battle action for {self.battle_state.battle_id}")
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            else:
                 await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)

    # --- Button Callbacks --- #
    # We need separate callback methods for each button now that Selects are involved.

    async def attack_button_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction):
            return
        await interaction.response.defer() # Defer before processing
        await self.handle_action(interaction, {'type': 'attack'})

    async def defend_button_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction):
            return
        await interaction.response.defer()
        await self.handle_action(interaction, {'type': 'defend'})

    async def flee_button_callback(self, interaction: discord.Interaction):
        if not await self.interaction_check(interaction):
            return
        await interaction.response.defer()
        await self.handle_action(interaction, {'type': 'flee'})

    async def on_timeout(self):
        """Called when the view times out."""
        logger.info(f"Battle view for {self.battle_state.battle_id} timed out.")
        # Check if battle still exists and is active before ending it
        try:
            current_state = self.battle_manager.get_battle_state(self.battle_state.battle_id)
            if current_state and current_state.is_active():
                 # Optionally, force end the battle on timeout?
                 # await self.battle_manager.end_battle(self.battle_state.battle_id, outcome="timeout")
                 timeout_message = "Battle timed out due to inactivity."
            else:
                 timeout_message = "Battle already ended."
        except BattleManagerError:
             timeout_message = "Battle session expired."
        except Exception as e:
             logger.error(f"Error checking battle state on timeout: {e}")
             timeout_message = "Error during timeout cleanup."

        if self.message:
            try:
                # Disable components and show timeout message
                await self.disable_and_edit(None, timeout_message)
            except Exception as e:
                 logger.error(f"Error disabling view on timeout: {e}")
        self.stop()

    async def disable_and_edit(self, interaction: Optional[discord.Interaction], content: str):
        """Disables all components and edits the message with final content."""
        for item in self.children:
            item.disabled = True

        # Get the current embed, update its description or add a field
        embed = self.create_embed()
        # Clear existing fields if needed, or just update description
        embed.description = content # Overwrite description with final status
        # Optionally clear fields related to turn-based actions
        # embed.clear_fields() # Or remove specific fields

        try:
            if interaction and not interaction.response.is_done():
                await interaction.response.edit_message(content=None, embed=embed, view=self)
            elif self.message:
                await self.message.edit(content=None, embed=embed, view=self)
            elif self.original_interaction: # Fallback to original if message not set
                 await self.original_interaction.edit_original_response(content=None, embed=embed, view=self)
        except discord.NotFound:
            logger.warning(f"Failed to edit battle message for battle {self.battle_state.battle_id} during disable - message not found.")
        except discord.HTTPException as e:
            logger.error(f"HTTP Error disabling/editing battle view: {e}")

# --- Battle System Commands --- #

class BattleSystemCommands(commands.Cog):
    """Commands for managing battles and duels."""
    def __init__(
        self,
        bot: 'HCShinobiBot',
        services: ServiceContainer
    ):
        self.bot = bot
        self.services = services
        # Store active battle message IDs: {battle_id: (channel_id, message_id)}
        self.active_battle_messages: Dict[str, Tuple[int, int]] = {}

    @app_commands.command(name="duel", description="Challenge another player to a duel")
    @app_commands.describe(opponent="The player you want to challenge")
    async def duel(self, interaction: discord.Interaction, opponent: discord.Member):
        """Challenge another player to a duel."""
        # Use False for is_duel as the underlying system may not differentiate yet
        await self._battle_command_impl(interaction, opponent, is_duel=False)

    @app_commands.command(name="battle", description="Challenge another player or NPC to a battle, or browse opponents.")
    @app_commands.describe(
        opponent="The player you want to battle against (starts PvP challenge)",
        npc_id="The ID of the NPC you want to battle (starts PvNPC battle directly)"
    )
    async def battle(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None, npc_id: Optional[str] = None):
        """Challenge a specific opponent or browse available opponents."""
        if opponent or npc_id:
            # If opponent or NPC ID is specified, use the existing direct challenge logic
            await self._battle_command_impl(interaction, opponent=opponent, npc_id=npc_id, is_duel=False)
        else:
            # No specific opponent given, show the selection view
            view = OpponentSelectView(self, interaction)
            await interaction.response.send_message("Choose an opponent to battle:", view=view, ephemeral=True)
            view.message = await interaction.original_response()
            # Timeout is handled by the view itself

    async def _battle_command_impl(
        self,
        interaction: discord.Interaction,
        opponent: Optional[discord.Member] = None,
        npc_id: Optional[str] = None,
        is_duel: bool = False
    ):
        """Shared implementation for duel and battle commands, handles players and NPCs."""
        # --- Basic Checks ---
        if not opponent and not npc_id:
            await interaction.response.send_message("You must specify an opponent player or an NPC ID to battle.", ephemeral=True)
            return
        
        if opponent and npc_id:
            await interaction.response.send_message("Please specify either an opponent player OR an NPC ID, not both.", ephemeral=True)
            return
            
        if opponent and opponent.id == interaction.user.id:
            await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)
            return

        if opponent and opponent.bot:
             await interaction.response.send_message("You can't battle bots directly this way!", ephemeral=True)
             return
             
        if npc_id and is_duel:
            await interaction.response.send_message("You cannot duel NPCs.", ephemeral=True)
            return

        # --- Get Challenger Character ---
        challenger_char = await self.services.character_system.get_character(str(interaction.user.id))
        if not challenger_char:
            await interaction.response.send_message(f"You don't have a character! Use `/create_character`.", ephemeral=True)
            return
            
        # --- Check if Challenger is Already in Battle ---
        challenger_battle_id, _, _ = self._get_current_battle_for_user(str(interaction.user.id))
        if challenger_battle_id:
            await interaction.response.send_message("You are already in a battle!", ephemeral=True)
            return

        # --- Determine and Get Opponent Character ---
        opponent_char: Optional[Character] = None
        opponent_display_name: str = "Unknown Opponent"
        is_opponent_npc = False
        
        if opponent:
            opponent_char = await self.services.character_system.get_character(str(opponent.id))
            if not opponent_char:
                await interaction.response.send_message(f"{opponent.mention} doesn't have a character!", ephemeral=True)
                return
            opponent_display_name = opponent.mention
            
            # Check if opponent is already in battle
            opponent_battle_id, _, _ = self._get_current_battle_for_user(str(opponent.id))
            if opponent_battle_id:
                await interaction.response.send_message(f"{opponent.mention} is already in a battle!", ephemeral=True)
                return
                
            # Check if opponent has a pending duel (only relevant if opponent is a player)
            if opponent.id in pending_duels:
                await interaction.response.send_message(f"{opponent.mention} already has a pending duel invitation!", ephemeral=True)
                return
                
        elif npc_id:
            opponent_char = await self.services.character_system.get_character(npc_id)
            if not opponent_char:
                await interaction.response.send_message(f"Could not find an NPC with ID: `{npc_id}`", ephemeral=True)
                return
            # Check if this NPC is even allowed to battle?
            # Add any specific NPC checks here if needed (e.g., is_battlable flag)
            opponent_display_name = opponent_char.name # Use NPC name
            is_opponent_npc = True
            
            # Check if NPC is somehow already marked as 'in battle' (might need specific logic)
            # This might require a dedicated check in CharacterSystem or BattleManager for NPCs
            # For now, assume NPCs can be fought unless explicitly marked otherwise.
            pass 

        # --- Proceed with Battle/Duel Start --- 
        if not opponent_char:
             # This should ideally not be reachable due to earlier checks
             logger.error(f"_battle_command_impl: Failed to resolve opponent character for user {interaction.user.id} vs {opponent.id if opponent else npc_id}")
             await interaction.response.send_message("Failed to identify the opponent character.", ephemeral=True)
             return

        # --- Handle Player vs Player Invite Logic --- 
        if opponent and not is_opponent_npc:
            # Create and send the duel invitation
            view = DuelInviteView(self, interaction.user, opponent)
            await interaction.response.send_message(
                f"{opponent.mention}, {interaction.user.mention} has challenged you to a {'duel' if is_duel else 'battle'}!",
                view=view
            )
            view.message = await interaction.original_response()
            pending_duels[opponent.id] = (interaction.user.id, interaction)
            timed_out = await view.wait()
            
            # Clean up pending duel state
            if opponent.id in pending_duels and pending_duels[opponent.id][1] == interaction:
                del pending_duels[opponent.id]
            else:
                logger.info(f"Pending duel for {opponent.id} was overwritten or removed before timeout/response.")

            if timed_out and view.accepted is None:
                 logger.info(f"Battle invite from {interaction.user.id} to {opponent.id} timed out.")
                 # on_timeout handles the message edit
                 return
                 
            if not view.accepted:
                 # Decline message handled by view button
                 return
            
            # --- Opponent Accepted --- 
            # Proceed to start the battle logic
            try:
                # Pass Character objects directly
                success, message = await self._start_battle_logic(interaction, challenger_char, opponent_char)
                if not success:
                    try:
                        await interaction.edit_original_response(content=f"Failed to start battle: {message}", view=None)
                    except discord.HTTPException:
                        await interaction.followup.send(f"Failed to start battle: {message}", ephemeral=True)
            except discord.NotFound:
                 logger.warning("Original interaction for battle start not found after acceptance.")
                 await interaction.user.send("Error starting your battle: the original challenge message could not be found.")
            except Exception as e:
                 logger.exception("Error during battle start after acceptance.")
                 # Check if response is done before editing
                 if not interaction.response.is_done():
                    # Initial response was the invite, need to edit
                    await interaction.edit_original_response(content=f"An error occurred starting the battle: {e}", view=None)
                 else:
                    # If edit already happened (e.g. accept message), use followup?
                    # This state might be tricky, try editing first, fallback to followup
                    try:
                        await interaction.edit_original_response(content=f"An error occurred starting the battle: {e}", view=None)
                    except discord.HTTPException:
                        await interaction.followup.send(f"An error occurred starting the battle: {e}", ephemeral=True)
                        
        # --- Handle Player vs NPC Start Logic --- 
        elif is_opponent_npc:
            await interaction.response.defer(thinking=True) # Acknowledge command
            try:
                # Pass Character objects directly
                success, message = await self._start_battle_logic(interaction, challenger_char, opponent_char)
                if not success:
                    await interaction.followup.send(f"Failed to start battle vs {opponent_display_name}: {message}")
                # On success, _start_battle_logic edits the response with the battle view
            except Exception as e:
                 logger.exception(f"Error during PvE battle start ({challenger_char.id} vs {opponent_char.id}).")
                 await interaction.followup.send(f"An unexpected error occurred starting the battle vs {opponent_display_name}.")
        
        # else: # Should not be reached if logic is correct
        #     logger.error("Reached unexpected state in _battle_command_impl")
        #     await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

    async def _start_battle_logic(
        self,
        interaction: discord.Interaction, # Keep interaction for editing response
        challenger_char: Character, 
        opponent_char: Character
    ) -> Tuple[bool, str]:
        """Logic for starting a battle between two characters (player or NPC)."""
        # Characters are now passed directly
        try:
            # Basic checks are done in the caller (_battle_command_impl)
            # No need to re-check if characters exist here
            
            # Create the battle using services
            battle_id = await self.services.battle_system.create_battle(
                challenger_char,
                opponent_char,
                is_duel=False # Differentiate later if needed
            )

            # Get the initial battle state
            # Retrieve state from BattleSystem or Persistence layer now
            battle_state = self.services.battle_system.persistence.active_battles.get(battle_id)
            # Alternatively, if BattleManager still holds state:
            # battle_state = self.services.battle_manager.get_battle_state(battle_id)
            if not battle_state:
                 # This should not happen immediately after creation
                 raise BattleManagerError(f"Failed to retrieve battle state for newly created battle {battle_id}")

            # Create the battle view
            view = BattleView(
                battle_state,
                self.services.battle_system, # Pass BattleSystem service
                self.services.battle_manager, # Pass BattleManager service
                interaction # Pass the original interaction for followups
            )

            # Send the initial battle embed and view
            embed = view.create_embed()
            
            # Edit the original response (which was either the invite or the thinking message)
            # Check if interaction response is already done before editing
            if interaction.response.is_done():
                # If deferred (PvNPC) or invite accepted (PvP), edit the original message
                await interaction.edit_original_response(content=None, embed=embed, view=view)
            else:
                # This case shouldn't happen if defer() or send_message() was called before
                logger.warning("_start_battle_logic called with interaction response not done. Sending new message.")
                await interaction.response.send_message(content=None, embed=embed, view=view)
                
            message = await interaction.original_response() # Store the message for future edits
            view.message = message
            
            # Store the message reference for admin clearing
            self.active_battle_messages[battle_id] = (interaction.channel_id, message.id)
            logger.info(f"Stored active battle message for {battle_id}: Ch={interaction.channel_id}, Msg={message.id}")

            return True, ""

        except BattleManagerError as e:
            logger.error(f"BattleManagerError starting battle: {e}")
            return False, str(e)
        except Exception as e:
            challenger_id_str = getattr(challenger_char, 'id', 'Unknown')
            opponent_id_str = getattr(opponent_char, 'id', 'Unknown')
            logger.exception(f"Unexpected error starting battle between {challenger_id_str} and {opponent_id_str}")
            return False, f"An unexpected server error occurred while starting the battle."

    def _get_current_battle_for_user(self, user_id: str) -> Tuple[Optional[str], Optional[str], Optional[BattleState]]:
        """Gets the current battle for a user."""
        # Access battle manager via services
        active_battles = self.services.battle_manager.active_battles
        for battle_id, battle_state in active_battles.items():
            # Ensure players exist before accessing id
            if battle_state.player1 and str(battle_state.player1.player_id) == user_id:
                 return battle_id, battle_state.player1.player_id, battle_state
            if battle_state.player2 and str(battle_state.player2.player_id) == user_id:
                 return battle_id, battle_state.player2.player_id, battle_state
        return None, None, None

    @app_commands.command(name="battle_surrender", description="Surrender your current battle.")
    async def battle_surrender(self, interaction: discord.Interaction):
        """Surrender the current battle."""
        battle_id, player_char_id, battle_state = self._get_current_battle_for_user(str(interaction.user.id))
        if not battle_id or not battle_state:
            await interaction.response.send_message("You're not in a battle!", ephemeral=True)
            return

        if not battle_state.is_active():
             await interaction.response.send_message("This battle has already ended.", ephemeral=True)
             return

        try:
            # End the battle with surrender, identifying the loser
            await self.services.battle_manager.end_battle(battle_id, "surrender", loser_id=player_char_id)
            await interaction.response.send_message("You have surrendered the battle.")

            # Optionally, update the original battle message if possible
            # Find the original interaction or message associated with the battle view
            # This is tricky without a direct link stored.

        except BattleManagerError as e:
            logger.error(f"Error processing surrender for battle {battle_id}: {e}")
            await interaction.response.send_message(
                f"An error occurred while trying to surrender: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Unexpected error during surrender for battle {battle_id}")
            await interaction.response.send_message(
                 f"An unexpected server error occurred while surrendering.",
                 ephemeral=True
            )

    @app_commands.command(name="battle_history", description="View your battle history")
    async def battle_history(self, interaction: discord.Interaction):
        """View the user's battle history."""
        try:
            # Access battle manager via services
            history = await self.services.battle_manager.get_battle_history(str(interaction.user.id))
            if not history:
                await interaction.response.send_message("You have no battle history yet.", ephemeral=True)
                return

            # Create an embed with the battle history
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Battle History",
                description="Your recent battles:",
                color=discord.Color.blue()
            )

            for battle in history[:10]:  # Show last 10 battles
                opponent_id_str = battle.player2_id if battle.player1_id == str(interaction.user.id) else battle.player1_id
                opponent_char = await self.services.character_system.get_character(opponent_id_str)
                opponent_name = opponent_char.name if opponent_char else f"Character {opponent_id_str[:6]}..."
                opponent_user = self.bot.get_user(int(opponent_id_str)) # Try to get discord user
                opponent_display = f"{opponent_name} ({opponent_user.display_name if opponent_user else 'Unknown User'})"

                result = "Victory" if battle.winner_id == str(interaction.user.id) else "Defeat" if battle.winner_id else "Draw"
                outcome_reason = f" ({battle.outcome})" if battle.outcome else ""

                # Format end time
                end_time_str = battle.end_time.strftime('%Y-%m-%d %H:%M') if battle.end_time else "Ongoing?"

                embed.add_field(
                    name=f"vs {opponent_display}",
                    value=f"Result: **{result}**{outcome_reason}\nTurns: {battle.turn_count}\nDate: {end_time_str}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.exception(f"Error retrieving battle history for {interaction.user.id}")
            await interaction.response.send_message(
                f"An error occurred while retrieving your battle history.",
                ephemeral=True
            )

    @app_commands.command(name="admin_clear_battle", description="[Admin] Force clear a player's active battle.")
    @app_commands.describe(user="The user whose battle to clear")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_clear_battle(self, interaction: discord.Interaction, user: discord.User):
        """Admin command to force clear a player's active battle."""
        battle_id, _, battle_state = self._get_current_battle_for_user(str(user.id))
        if not battle_id:
            await interaction.response.send_message(f"{user.mention} is not in a battle.", ephemeral=True)
            return

        message_info = self.active_battle_messages.get(battle_id)

        try:
            # Access battle manager via services
            await self.services.battle_manager.end_battle(battle_id, "admin_clear")
            admin_response = f"Successfully cleared {user.mention}'s battle ({battle_id})."
            await interaction.response.send_message(admin_response)
            
            # Attempt to disable the original battle view message
            if message_info:
                channel_id, message_id = message_info
                try:
                    channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
                    if channel:
                         message = await channel.fetch_message(message_id)
                         if message:
                              # Create a simple embed indicating forced end
                              end_embed = discord.Embed(title="Battle Ended", description=f"This battle was forcibly ended by an administrator.", color=discord.Color.red())
                              await message.edit(content=None, embed=end_embed, view=None) # Remove view entirely
                              logger.info(f"Disabled battle view message {message_id} in channel {channel_id} for cleared battle {battle_id}.")
                         else:
                              logger.warning(f"Could not fetch message {message_id} for cleared battle {battle_id}.")
                    else:
                         logger.warning(f"Could not find channel {channel_id} for cleared battle {battle_id}.")
                    # Remove from active messages after attempting disable
                    del self.active_battle_messages[battle_id]
                except discord.NotFound:
                    logger.warning(f"Message {message_id} or channel {channel_id} not found when trying to disable view for battle {battle_id}.")
                    if battle_id in self.active_battle_messages: del self.active_battle_messages[battle_id]
                except discord.Forbidden:
                     logger.error(f"Bot lacks permissions to fetch/edit message {message_id} in channel {channel_id} for battle {battle_id}.")
                     if battle_id in self.active_battle_messages: del self.active_battle_messages[battle_id]
                except Exception as e:
                     logger.exception(f"Error disabling battle view for {battle_id}: {e}")
                     if battle_id in self.active_battle_messages: del self.active_battle_messages[battle_id]
            else:
                logger.warning(f"No active message found for cleared battle {battle_id}.")

        except BattleManagerError as e:
            logger.error(f"Error admin clearing battle {battle_id}: {e}")
            # Check if response already sent before sending again
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"An error occurred while clearing the battle: {str(e)}", ephemeral=True)
            else:
                 await interaction.followup.send(f"An error occurred while clearing the battle: {str(e)}", ephemeral=True)
        except Exception as e:
             logger.exception(f"Unexpected error admin clearing battle {battle_id}")
             if not interaction.response.is_done():
                 await interaction.response.send_message(f"An unexpected server error occurred while clearing the battle.", ephemeral=True)
             else:
                  await interaction.followup.send(f"An unexpected server error occurred while clearing the battle.", ephemeral=True)

    @app_commands.command(name="battle_status", description="Check the status of a specific battle by ID.")
    @app_commands.describe(battle_id="The ID of the battle to check.")
    async def battle_status(self, interaction: discord.Interaction, battle_id: str):
        """Checks and displays the status of a specific battle."""
        await interaction.response.defer(ephemeral=True) # Defer for potentially slow lookup

        try:
            battle_state = self.services.battle_manager.get_battle_state(battle_id)
            if not battle_state:
                 # Should be caught by BattleNotFoundError, but check just in case
                await interaction.followup.send(f"Battle with ID `{battle_id}` not found or is inactive.", ephemeral=True)
                return

            # Reuse the existing embed creation helper
            embed = create_battle_embed(battle_state)
            await interaction.followup.send(embed=embed, ephemeral=False) # Show status publicly

        except BattleNotFoundError:
            await interaction.followup.send(f"Battle with ID `{battle_id}` not found or is inactive.", ephemeral=True)
        except Exception as e:
            logger.exception(f"Error fetching battle status for ID {battle_id}", exc_info=e)
            await interaction.followup.send("An error occurred while trying to fetch the battle status.", ephemeral=True)

async def setup(bot: 'HCShinobiBot'):
    """Sets up the Battle System Cog."""
    # Ensure core systems are available via services
    if not hasattr(bot, 'services') or not bot.services.battle_manager or not bot.services.character_system or not bot.services.battle_system:
        logger.error("Cannot load BattleSystemCommands cog: Bot is missing required services (battle_manager, character_system, battle_system).")
        return

    try:
        # Pass the whole services container
        await bot.add_cog(BattleSystemCommands(bot, bot.services))
        logger.info("BattleSystemCommands Cog loaded successfully.")
    except Exception as e:
        logger.exception(f"Failed to load BattleSystemCommands cog: {e}")
        # Re-raise the exception to prevent the bot from potentially starting in a broken state
        raise e 