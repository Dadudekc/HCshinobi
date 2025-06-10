import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
from typing import TYPE_CHECKING, Optional, List, Dict, Any, Tuple, Set
import random
import asyncio
import inspect
from discord.ui import View

# Core system imports (adjust paths if needed)
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.utils.ollama_client import OllamaClient
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from HCshinobi.core.item_registry import ItemRegistry
from HCshinobi.core.jutsu_system import JutsuSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.utils.embed_utils import get_rarity_color
from HCshinobi.core.constants import RarityTier
from HCshinobi.core.loot_system import LootSystem
from HCshinobi.core.battle_manager import BattleManager
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.token_system import TokenSystem, TokenError
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.personality_modifiers import PersonalityModifiers
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.training_system import TrainingSystem

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCShinobiBot

logger = logging.getLogger(__name__)

# --- UI Views ---

# --- Delete Confirmation View ---
class DeleteConfirmationView(ui.View):
    def __init__(self, cog: 'CharacterCommands', user: discord.User, character: Character):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.character = character
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    @ui.button(label="Yes, Delete My Character", style=discord.ButtonStyle.danger, custom_id="delete_confirm_yes")
    async def confirm_delete(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            success = await self.cog.character_system.delete_character(str(self.user.id))
            if success:
                await interaction.followup.send("🗑️ Your character has been deleted.", ephemeral=True)
                self.cog.logger.info(f"Character {self.character.name} (User: {self.user.id}) deleted by user confirmation.")
            else:
                await interaction.followup.send("❌ Failed to delete character data.", ephemeral=True)
        except Exception as e:
            self.cog.logger.error(f"Error during confirmed character deletion for {self.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred during deletion.", ephemeral=True)
        finally:
            self.stop()
            if self.message:
                try: await self.message.edit(view=None) # Disable buttons on original message
                except discord.NotFound: pass

    @ui.button(label="No, Keep My Character", style=discord.ButtonStyle.success, custom_id="delete_confirm_no")
    async def cancel_delete(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return

        if self.message:
             try: await self.message.edit(content="✅ Character deletion cancelled.", view=None)
             except discord.NotFound:
                 await interaction.response.send_message("✅ Character deletion cancelled.", ephemeral=True) # Fallback
             except Exception as e:
                 self.cog.logger.error(f"Error editing message on delete cancel: {e}")
                 await interaction.response.send_message("✅ Character deletion cancelled.", ephemeral=True) # Fallback
        else:
             await interaction.response.send_message("✅ Character deletion cancelled.", ephemeral=True)

        self.cog.logger.info(f"Character deletion cancelled by user {self.user.id}.")
        self.stop()

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="Character deletion confirmation timed out.", view=None)
            except discord.NotFound: pass
        self.stop()

# --- Title Equip View ---
class TitleEquipView(ui.View):
    def __init__(self, cog: 'CharacterCommands', character: Character, options: List[discord.SelectOption]):
        super().__init__(timeout=180)
        self.cog = cog
        self.character = character
        self.add_item(TitleSelect(character.id, options)) # Pass character_id directly

class TitleSelect(discord.ui.Select):
    def __init__(self, character_id: str, options: List[discord.SelectOption]):
        self.character_id = character_id # Store character_id
        placeholder = "Select a title to equip" if options else "No titles available"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id="title_equip_select")

    async def callback(self, interaction: discord.Interaction):
        view: TitleEquipView = self.view
        if not view or not view.cog or not view.character:
            await interaction.response.send_message("Error: Could not find necessary data.", ephemeral=True)
            return

        selected_title_key = self.values[0]
        character = view.character
        cog = view.cog

        current_equipped = getattr(character, 'equipped_title', None)
        if current_equipped == selected_title_key:
            await interaction.response.send_message(f"➡️ Title '{selected_title_key}' is already equipped.", ephemeral=True)
            return

        character.equipped_title = selected_title_key
        # Access character_system via cog
        save_success = await cog.character_system.save_character(character)

        if save_success:
            title_data = cog.progression_engine.get_title_data(selected_title_key) if cog.progression_engine else None
            display_name = title_data.get('name', selected_title_key) if title_data else selected_title_key
            await interaction.response.send_message(f"✅ Title **{display_name}** equipped!", ephemeral=True)
            cog.logger.info(f"User {interaction.user.id} equipped title: {selected_title_key}")

            # Refresh original message
            try:
                new_embed = await cog._create_titles_embed(character)
                await interaction.edit_original_response(embed=new_embed, view=view)
            except Exception as e:
                cog.logger.error(f"Failed to refresh /titles message after equip: {e}")
        else:
            await interaction.response.send_message("❌ Failed to save equipped title.", ephemeral=True)
            character.equipped_title = current_equipped # Revert

# --- Specialization Choice View ---
class SpecializationChoiceView(ui.View):
     def __init__(self, cog: 'CharacterCommands', character: Character, specializations: List[str]):
         super().__init__(timeout=180)
         self.cog = cog
         self.character = character
         # Use buttons if few options, select if many
         if len(specializations) <= 5:
             for spec in specializations:
                 self.add_item(SpecializationButton(spec, self))
         else:
            self.add_item(SpecializationSelect(specializations))
         self.message: Optional[discord.Message] = None

     async def handle_selection(self, interaction: discord.Interaction, specialization: str):
        await interaction.response.defer(ephemeral=True)
        try:
            # Basic check: Ensure character object is still valid
            if not self.character:
                await interaction.followup.send("Error: Character data lost.", ephemeral=True)
                self.stop()
                return

            # Check prerequisites (level, etc.) - Use available character attributes
            # Example: Level check (assuming level attribute exists)
            required_level = 10 # Define required level here or fetch from config/engine
            if getattr(self.character, 'level', 0) < required_level:
                await interaction.followup.send(f"❌ You must be at least level {required_level} to specialize.", ephemeral=True)
                # Do not stop the view, allow user to maybe level up and try again?
                # Or stop() if selection should be final once shown.
                return # Prevent proceeding

            # Check if already specialized (double-check)
            if getattr(self.character, 'specialization', None):
                 await interaction.followup.send(f"❌ You have already specialized in {self.character.specialization.title()}.")
                 self.stop()
                 return

            self.character.specialization = specialization
            save_success = await self.cog.character_system.save_character(self.character)
            if not save_success:
                 await interaction.followup.send("❌ Failed to save specialization. Please try again.", ephemeral=True)
                 # Revert specialization on character object if save failed
                 self.character.specialization = None
                 return

            # Handle roles if applicable (ensure guild and member context)
            if interaction.guild and isinstance(interaction.user, discord.Member):
                await self.cog._handle_specialization_roles(interaction.guild, interaction.user, self.character)
            else:
                 self.cog.logger.warning("Could not update specialization roles: Missing guild or member context.")

            await interaction.followup.send(f"✅ You have specialized in **{specialization}**!", ephemeral=True)

            # Update original message if possible
            if self.message:
                try: await self.message.edit(content=f"Specialization chosen: {specialization}", view=None)
                except discord.NotFound: pass
            self.stop()
        except Exception as e:
            self.cog.logger.error(f"Error setting specialization via view for {interaction.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred while setting specialization.", ephemeral=True)
            self.stop()

     async def on_timeout(self):
        if self.message:
            try: await self.message.edit(content="Specialization selection timed out.", view=None)
            except discord.NotFound: pass
        self.stop()

class SpecializationSelect(ui.Select):
    def __init__(self, specializations: List[str]):
        options = [discord.SelectOption(label=spec.title(), description=f"Choose {spec.title()} specialization", value=spec) for spec in specializations]
        super().__init__(placeholder="Choose your specialization...", min_values=1, max_values=1, options=options, custom_id="spec_select")

    async def callback(self, interaction: discord.Interaction):
        view: SpecializationChoiceView = self.view
        if not view: return
        selected_spec = self.values[0]
        await view.handle_selection(interaction, selected_spec)

class SpecializationButton(ui.Button):
    def __init__(self, specialization: str, parent_view: SpecializationChoiceView):
        super().__init__(label=specialization.title(), style=discord.ButtonStyle.primary, custom_id=f"spec_button_{specialization}")
        self.specialization = specialization
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.handle_selection(interaction, self.specialization)

# --- Starter Battle UI (Copied and adapted from starter_battle.py) ---

class StarterBattleActionButton(discord.ui.Button):
    """Button specific to the starter battle view."""
    def __init__(self, action_type: str, label: str, style: discord.ButtonStyle, emoji: Optional[str] = None):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=f"starter_battle_action_{action_type}")
        self.action_type = action_type

    async def callback(self, interaction: discord.Interaction):
        # Check if view exists and is of the correct type
        view = self.view
        if not isinstance(view, StarterBattleView):
            await interaction.response.send_message("Error: Battle context lost.", ephemeral=True)
            return
        await view.handle_action(interaction, self.action_type)

class StarterBattleJutsuSelectMenu(discord.ui.Select):
    """Select menu specific to the starter battle view."""
    def __init__(self, jutsu_list: List[str]):
        # Ensure labels/values are within Discord limits
        options = [discord.SelectOption(label=jutsu_name[:100], value=jutsu_name) for jutsu_name in jutsu_list[:25]]
        super().__init__(placeholder="Select a jutsu...", min_values=1, max_values=1, options=options, custom_id="starter_battle_jutsu_select")

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, StarterBattleView):
            await interaction.response.send_message("Error: Battle context lost.", ephemeral=True)
            return
        await view.handle_jutsu_selection(interaction, self.values[0])

class StarterBattleView(discord.ui.View):
    """Interactive UI for the Academy Entrance Test battle."""
    def __init__(self, battle_handler: 'StarterBattleHandler', player: Character, opponent: Character):
        super().__init__(timeout=300) # 5 minute timeout for the battle
        self.battle_handler = battle_handler
        self.player = player
        self.opponent = opponent
        # Store current HP separately from base character HP for the duration of this specific battle
        self.player_hp = getattr(player, 'hp', 1) # Default to 1 if hp missing
        self.opponent_hp = getattr(opponent, 'hp', 1)
        self.turn_count = 1
        self.battle_log: List[str] = []
        self.message: Optional[discord.Message] = None
        self.winner_id: Optional[str] = None # Store ID of winner
        self.player_defending = False # Track if player chose to defend

        # Add action buttons
        self.add_item(StarterBattleActionButton("attack", "Attack", discord.ButtonStyle.danger, "⚔️"))
        self.add_item(StarterBattleActionButton("defend", "Defend", discord.ButtonStyle.primary, "🛡️"))

        # Add Jutsu Select Menu if player has jutsu
        player_jutsu = getattr(player, 'jutsu', [])
        if player_jutsu:
            self.add_item(StarterBattleJutsuSelectMenu(player_jutsu))

        # Add Flee Button
        self.add_item(StarterBattleActionButton("flee", "Flee", discord.ButtonStyle.secondary, "🏃"))

    def add_to_log(self, message: str):
        """Adds a message to the battle log, keeping the last few entries."""
        self.battle_log.append(message)
        if len(self.battle_log) > 10: self.battle_log.pop(0) # Keep last 10 messages

    def _create_hp_bar(self, current_hp: int, max_hp: int, blocks: int = 10) -> str:
        """Helper to create a text-based HP bar."""
        if max_hp <= 0: return "[UNKNOWN]"
        current_hp = max(0, current_hp)
        percentage = min(1, current_hp / max_hp)
        filled_blocks = int(percentage * blocks)
        empty_blocks = blocks - filled_blocks
        # Use ASCII characters for broader compatibility
        return f"[{'#' * filled_blocks}{'-' * empty_blocks}]"

    def create_battle_embed(self) -> discord.Embed:
        """Creates the Discord Embed displaying the current battle state."""
        if self.winner_id:
            color = discord.Color.green() if self.winner_id == self.player.id else discord.Color.red()
            title_suffix = "Victory!" if self.winner_id == self.player.id else "Defeat!"
            description = f"Battle Complete! {title_suffix}"
        else:
            color = discord.Color.gold()
            title_suffix = f"vs {self.opponent.name}"
            description = f"Turn {self.turn_count}"

        embed = discord.Embed(title=f"⚔️ Academy Entrance Test: {self.player.name} {title_suffix}", description=description, color=color)

        player_max_hp = getattr(self.player, 'max_hp', self.player_hp)
        opponent_max_hp = getattr(self.opponent, 'max_hp', self.opponent_hp)
        player_hp_bar = self._create_hp_bar(self.player_hp, player_max_hp)
        opponent_hp_bar = self._create_hp_bar(self.opponent_hp, opponent_max_hp)

        embed.add_field(
            name=f"{self.player.name} (You)",
            value=f"HP: {self.player_hp}/{player_max_hp} {player_hp_bar}\nChakra: {getattr(self.player, 'chakra', '?')}/{getattr(self.player, 'max_chakra', '?')}",
            inline=True
        )
        embed.add_field(
            name=f"{self.opponent.name} ({getattr(self.opponent, 'rank', 'Unknown')})",
            value=f"HP: {self.opponent_hp}/{opponent_max_hp} {opponent_hp_bar}\nChakra: {getattr(self.opponent, 'chakra', '?')}/{getattr(self.opponent, 'max_chakra', '?')}",
            inline=True
        )
        if self.battle_log:
            log_text = "\n".join(self.battle_log[-5:])
            embed.add_field(name="Recent Actions", value=f"```\n{log_text}\n```", inline=False)

        embed.set_footer(text="Choose your action below.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the player involved in this battle instance can interact."""
        is_player = str(interaction.user.id) == self.player.id
        if not is_player:
            await interaction.response.send_message("This is not your battle!", ephemeral=True)
        return is_player

    async def handle_action(self, interaction: discord.Interaction, action_type: str):
        """Handles button presses for basic actions."""
        if self.winner_id:
            await interaction.response.send_message("The battle is already over.", ephemeral=True)
            return

        action_map = {
            'attack': {'type': 'attack'},
            'defend': {'type': 'defend'},
            'flee': {'type': 'flee'}
        }
        if action_type in action_map:
            await self.process_turn(interaction, action_map[action_type])
        else:
            await interaction.response.send_message("Invalid action.", ephemeral=True)

    async def handle_jutsu_selection(self, interaction: discord.Interaction, jutsu_name: str):
        """Handles selection from the jutsu dropdown."""
        if self.winner_id:
            await interaction.response.send_message("The battle is already over.", ephemeral=True)
            return
        await self.process_turn(interaction, {'type': 'jutsu', 'jutsu_id': jutsu_name})

    async def process_turn(self, interaction: discord.Interaction, player_action: Dict[str, Any]):
        """Processes a full turn: player action, checks, opponent action, checks, update."""
        await interaction.response.defer() # Acknowledge the interaction
        self.player_defending = False # Reset defense state at start of player turn

        # --- Player Action Execution --- #
        action_log = ""
        action_type = player_action.get('type')

        if action_type == 'attack':
            # Simplified damage calculation (can be expanded)
            base_damage = getattr(self.player, 'strength', 5) // 2
            variation = random.randint(-max(1, base_damage // 5), max(1, base_damage // 5))
            damage = max(1, base_damage + variation)
            # Apply opponent defense if applicable (using opponent stats)
            opponent_defense = getattr(self.opponent, 'defense', 0)
            mitigated_damage = max(0, damage - (opponent_defense // 3))
            self.opponent_hp = max(0, self.opponent_hp - mitigated_damage)
            action_log = f"{self.player.name} attacks {self.opponent.name} for {mitigated_damage} damage!"
            self.add_to_log(action_log)

        elif action_type == 'defend':
            self.player_defending = True
            action_log = f"{self.player.name} takes a defensive stance."
            self.add_to_log(action_log)

        elif action_type == 'jutsu':
            jutsu_id = player_action['jutsu_id']
            # Example jutsu logic (needs refinement based on JutsuSystem)
            chakra_cost = 5 # Placeholder
            if getattr(self.player, 'chakra', 0) < chakra_cost:
                 action_log = f"{self.player.name} tries to use {jutsu_id}, but lacks chakra!"
            else:
                # Deduct chakra (ensure attribute exists)
                current_chakra = getattr(self.player, 'chakra', 0)
                setattr(self.player, 'chakra', max(0, current_chakra - chakra_cost))
                # Damage based on ninjutsu
                base_damage = getattr(self.player, 'ninjutsu', 5) // 2 + 2
                variation = random.randint(-max(1, base_damage // 5), max(1, base_damage // 5) + 1)
                damage = max(1, base_damage + variation)
                # Apply opponent defense/resistance if applicable
                opponent_defense = getattr(self.opponent, 'defense', 0)
                mitigated_damage = max(0, damage - (opponent_defense // 4)) # Jutsu might bypass some defense
                self.opponent_hp = max(0, self.opponent_hp - mitigated_damage)
                action_log = f"{self.player.name} uses {jutsu_id} on {self.opponent.name} for {mitigated_damage} damage!"
            self.add_to_log(action_log)

        elif action_type == 'flee':
            flee_chance = 0.5 # Simple 50% flee chance for starter battle
            if random.random() < flee_chance:
                action_log = f"{self.player.name} successfully fled the test!"
                self.add_to_log(action_log)
                await self.end_battle(None) # None indicates flee/no winner
                await self.update_battle_view(interaction) # Update view to show flee message
                return # End turn here
            else:
                action_log = f"{self.player.name} tried to flee but failed!"
                self.add_to_log(action_log)

        # --- Check for Player Victory --- #
        if self.opponent_hp <= 0:
            await self.end_battle(self.player.id)
            await self.update_battle_view(interaction)
            return

        # --- Opponent's Turn --- #
        if not self.winner_id: # Only proceed if battle isn't over
            opponent_action_log = await self.opponent_turn()
            self.add_to_log(opponent_action_log)

            # --- Check for Opponent Victory --- #
            if self.player_hp <= 0:
                await self.end_battle(self.opponent.id)

        # --- End of Turn --- #
        self.turn_count += 1
        await self.update_battle_view(interaction) # Update embed and buttons

    async def opponent_turn(self) -> str:
        """Contains the simple AI logic for the opponent's action."""
        # Basic AI: Prioritize attacking
        action_type = 'attack'
        # Could add basic logic: If low HP, maybe try to defend? If high chakra, use jutsu?

        if action_type == 'attack':
            base_damage = getattr(self.opponent, 'strength', 3) // 2
            variation = random.randint(-max(1, base_damage // 5), max(1, base_damage // 5))
            damage = max(1, base_damage + variation)
            # Apply player defense if player chose defend action
            if self.player_defending:
                player_defense = getattr(self.player, 'defense', 0)
                # Defending significantly increases effective defense
                mitigated_damage = max(0, damage - (player_defense // 2)) # Stronger mitigation when defending
                log_msg = f"{self.opponent.name} attacks, but {self.player.name} defends, taking {mitigated_damage} damage!"
            else:
                player_defense = getattr(self.player, 'defense', 0)
                mitigated_damage = max(0, damage - (player_defense // 3))
                log_msg = f"{self.opponent.name} attacks {self.player.name} for {mitigated_damage} damage!"
            self.player_hp = max(0, self.player_hp - mitigated_damage)
            return log_msg

        # Fallback message if no action taken
        return f"{self.opponent.name} considers their next move."

    async def end_battle(self, winner_id: Optional[str]):
        """Marks the battle as ended and disables UI components."""
        if self.winner_id: return # Already ended
        self.winner_id = winner_id
        # Disable all buttons and select menus in the view
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        self.stop() # Stop the view from listening to further interactions

        # Trigger post-battle logic (XP, loot) via the handler
        await self.battle_handler.handle_battle_end(self.player, self.opponent, self.winner_id)

    async def update_battle_view(self, interaction: discord.Interaction):
        """Updates the original battle message with the new embed and view state."""
        embed = self.create_battle_embed()
        try:
            # Use interaction.edit_original_response to update the message the view is attached to
            await interaction.edit_original_response(embed=embed, view=self)
            # Update the message reference in case it changed (though unlikely with edit_original_response)
            self.message = await interaction.original_response()
        except discord.NotFound:
            self.battle_handler.cog.logger.warning(f"Could not find original interaction message to update for starter battle (Player: {self.player.id})")
            self.stop() # Stop the view if its message is gone
        except discord.HTTPException as e:
            # Handle potential rate limits or other HTTP errors
            self.battle_handler.cog.logger.error(f"HTTP error updating starter battle view: {e}")
            # Consider stopping the view or trying again later?
            self.stop()
        except Exception as e:
            self.battle_handler.cog.logger.error(f"Unexpected error updating starter battle view: {e}", exc_info=True)
            self.stop()

    async def on_timeout(self):
        """Handles the case where the battle view times out due to inactivity."""
        if self.message and not self.winner_id: # Only timeout if battle wasn't finished
            embed = self.create_battle_embed()
            embed.description = "Battle timed out due to inactivity."
            embed.color = discord.Color.dark_grey()
            try:
                await self.message.edit(embed=embed, view=None) # Remove buttons on timeout
            except discord.NotFound: pass # Ignore if message was deleted
            except Exception as e: self.battle_handler.cog.logger.error(f"Error editing starter battle message on timeout: {e}")
        self.stop()

# --- Starter Battle Logic Handler (Adapted from starter_battle.py) ---

class AcademyNPC:
    """Represents the basic NPC opponent for the Academy Test."""
    # Define default stats for the NPC
    DEFAULT_STATS = {
        "name": "Academy Proctor", "level": 1, "rank": "Academy Student", "clan": "Konoha Academy",
        "max_hp": 30, "max_chakra": 20, "max_stamina": 25,
        "strength": 5, "speed": 4, "defense": 3, "intelligence": 5,
        "perception": 4, "willpower": 6, "chakra_control": 5,
        "ninjutsu": 3, "taijutsu": 4, "genjutsu": 2,
        "inventory": {}, "jutsu": ["Basic Punch", "Substitute"], # Example starter jutsu
        "status_effects": [], "specialization": None, "rarity": "Common"
    }

    def __init__(self, **kwargs):
        """Initializes the NPC, overriding defaults with provided kwargs."""
        base_stats = self.DEFAULT_STATS.copy()
        base_stats.update(kwargs) # Apply overrides

        # Set attributes dynamically based on the final stats dictionary
        for key, value in base_stats.items():
            setattr(self, key, value)

        # Ensure current HP/Chakra/Stamina are set based on max values
        self.hp = getattr(self, 'max_hp')
        self.chakra = getattr(self, 'max_chakra')
        self.stamina = getattr(self, 'max_stamina')
        self.id = getattr(self, 'id', self.name.lower().replace(" ", "_")) # Generate ID if not provided

    def to_character(self) -> Character:
        """Converts the NPC data to a Character object suitable for battle systems."""
        # Create a dictionary of attributes from the NPC instance
        char_attrs = {key: getattr(self, key) for key in self.DEFAULT_STATS.keys() if hasattr(self, key)}
        # Add required fields if missing defaults
        char_attrs.setdefault('id', self.id)
        char_attrs.setdefault('exp', 0)
        char_attrs.setdefault('stat_points', 0)
        char_attrs.setdefault('wins', 0)
        char_attrs.setdefault('losses', 0)
        char_attrs.setdefault('draws', 0)
        char_attrs.setdefault('titles', set())
        char_attrs.setdefault('achievements', set())
        char_attrs.setdefault('equipped_title', None)

        # Ensure list/dict attributes are copied
        char_attrs['inventory'] = char_attrs['inventory'].copy()
        char_attrs['jutsu'] = char_attrs['jutsu'].copy()
        char_attrs['status_effects'] = char_attrs['status_effects'].copy()

        # Remove attributes not expected by Character.__init__
        char_attrs.pop('rarity', None)

        return Character(**char_attrs) # Unpack attributes into Character constructor

class AcademyLoot:
    """Handles potential loot drops for the starter battle."""
    # Simplified loot table example
    LOOT_TABLE = {
        "win": [
            {"item_id": "practice_kunai", "chance": 0.8, "min_qty": 1, "max_qty": 3},
            {"item_id": "ryo_small_pouch", "chance": 0.6, "min_qty": 1, "max_qty": 1},
            #{"item_id": "academy_headband", "chance": 0.2, "min_qty": 1, "max_qty": 1}
        ],
        "lose": [
            #{"item_id": "ryo_tiny_pouch", "chance": 0.5, "min_qty": 1, "max_qty": 1}
        ]
    }

    @staticmethod
    def roll_loot(outcome: str = "win") -> Dict[str, int]:
        """Rolls for loot based on the battle outcome (win/lose)."""
        loot_drops: Dict[str, int] = {}
        table = AcademyLoot.LOOT_TABLE.get(outcome.lower(), [])
        for item_info in table:
            if random.random() < item_info["chance"]:
                quantity = random.randint(item_info["min_qty"], item_info["max_qty"])
                loot_drops[item_info["item_id"]] = loot_drops.get(item_info["item_id"], 0) + quantity
        return loot_drops

class StarterBattleHandler:
    """Manages the setup and post-battle logic for the Academy Entrance Test."""
    def __init__(self, cog: 'CharacterCommands', interaction: discord.Interaction):
        self.cog = cog
        self.interaction = interaction # Store the interaction for sending followup messages
        # Get required services from the main cog
        self.character_system: CharacterSystem = cog.character_system
        self.currency_system: Optional[CurrencySystem] = cog.currency_system
        self.progression_engine: Optional[ShinobiProgressionEngine] = cog.progression_engine
        self.loot_system: Optional[LootSystem] = getattr(cog.bot.services, 'loot_system', None) # Get loot system if available
        if not self.loot_system:
            self.cog.logger.warning("LootSystem service not found. No loot will be awarded for starter battle.")

    async def start_entrance_battle(self, character: Character):
        """Creates the NPC, sets up the BattleView, and sends the initial battle message."""
        if not character:
            self.cog.logger.error("Starter battle cannot start: Invalid character provided.")
            return

        # Create the Academy Proctor NPC opponent
        opponent_npc = AcademyNPC()
        opponent_char = opponent_npc.to_character() # Use the conversion method

        # Instantiate the battle view
        view = StarterBattleView(self, character, opponent_char)

        # Send the battle interface message (publicly in the interaction channel)
        embed = view.create_battle_embed()
        try:
            # Use interaction.channel.send to send a new message
            # The original /create interaction might be ephemeral or already finished
            battle_message = await self.interaction.channel.send(
                content=f"{self.interaction.user.mention}, your Academy Entrance Test begins!",
                embed=embed,
                view=view
            )
            view.message = battle_message # Assign the sent message to the view
            self.cog.logger.info(f"Started Academy Entrance Test for {character.name} ({character.id}) in channel {self.interaction.channel.id}")
        except discord.Forbidden:
            self.cog.logger.error(f"Bot missing permissions to send message in channel {self.interaction.channel_id} for starter battle.")
            # Attempt to notify the user via followup if possible
            try: await self.interaction.followup.send("Error: I couldn't start the battle in this channel. Do I have permission?", ephemeral=True)
            except: pass
        except Exception as e:
            self.cog.logger.error(f"Error sending initial starter battle message: {e}", exc_info=True)
            try: await self.interaction.followup.send("An error occurred starting the Academy Entrance Test.", ephemeral=True)
            except: pass

    async def handle_battle_end(self, player: Character, opponent: Character, winner_id: Optional[str]):
        """Applies rewards (XP, Ryo, Loot) based on the battle outcome."""
        outcome = "win" if winner_id == player.id else "lose" if winner_id == opponent.id else "fled"
        xp_gain = 0
        ryo_gain = 0
        loot_gained: Dict[str, int] = {}
        result_lines = [f"**Academy Entrance Test Result: {outcome.upper()}**"]

        if outcome == "win":
            xp_gain = 50 # Base XP
            ryo_gain = 100 # Base Ryo
            loot_gained = AcademyLoot.roll_loot("win")
            result_lines.append(f"Congratulations, {player.name}! You passed the test.")
            result_lines.append(f"You earned: {xp_gain} XP, {ryo_gain} Ryō.")
            # Potentially grant the 'Genin' rank or an achievement here
            if self.progression_engine:
                 pass # Example: await self.progression_engine.grant_achievement(player.id, "passed_academy_test")

        elif outcome == "lose":
            xp_gain = 10 # Consolation
            ryo_gain = 20
            loot_gained = AcademyLoot.roll_loot("lose")
            result_lines.append(f"You were defeated, {player.name}. Train harder and try again!" )
            result_lines.append(f"You earned: {xp_gain} XP, {ryo_gain} Ryō.")
        else: # Fled
            result_lines.append(f"{player.name}, you fled the test. Return when you are ready.")

        # Apply rewards
        save_required = False
        if self.progression_engine and xp_gain > 0:
            # Assuming gain_experience updates the character object directly or handles saving
            await self.progression_engine.gain_experience(player.id, xp_gain)
            save_required = True # Assume progression engine doesn't save character itself
        if self.currency_system and ryo_gain > 0:
            self.currency_system.add_balance_and_save(player.id, ryo_gain) # Assumes this saves
        if self.loot_system and loot_gained:
            for item_id, qty in loot_gained.items():
                # Assume add_item_to_inventory updates the character object directly
                await self.loot_system.add_item_to_inventory(player.id, item_id, qty)
            save_required = True # Assume loot system doesn't save character itself
            # Format loot message
            loot_str_parts = []
            for item_id, qty in loot_gained.items():
                item_name = self.loot_system.get_item_name(item_id) or item_id
                loot_str_parts.append(f"{item_name} x{qty}")
            if loot_str_parts: result_lines.append(f"Loot obtained: {', '.join(loot_str_parts)}")

        # Save character if XP or Loot was gained (and systems don't auto-save)
        if save_required:
            await self.character_system.save_character(player) # Save potentially modified character

        # Send result message
        result_message = "\n".join(result_lines)
        try:
            # Send the result in the same channel the battle started
            await self.interaction.channel.send(f"{self.interaction.user.mention}\n{result_message}")
        except Exception as e:
            self.cog.logger.error(f"Error sending starter battle result message: {e}", exc_info=True)

# --- Main Cog ---
class CharacterCommands(commands.Cog):
    """Commands related to character management, progression, and creation."""

    def __init__(self, bot: "HCShinobiBot"):
        self.bot = bot
        # Access services safely
        self.character_system: Optional[CharacterSystem] = getattr(bot.services, 'character_system', None)
        self.clan_assignment_engine: Optional[ClanAssignmentEngine] = getattr(bot.services, 'clan_assignment_engine', None)
        self.ollama_client: Optional[OllamaClient] = getattr(bot.services, 'ollama_client', None)
        self.progression_engine: Optional[ShinobiProgressionEngine] = getattr(bot.services, 'progression_engine', None)
        self.item_registry: Optional[ItemRegistry] = getattr(bot.services, 'item_registry', None)
        self.jutsu_system: Optional[JutsuSystem] = getattr(bot.services, 'jutsu_system', None)
        self.currency_system: Optional[CurrencySystem] = getattr(bot.services, 'currency_system', None)

        self.logger = logging.getLogger(__name__)

        # Log missing services
        if not self.character_system: self.logger.error("CharacterSystem service not found.")
        if not self.clan_assignment_engine: self.logger.error("ClanAssignmentEngine service not found.")
        if not self.progression_engine: self.logger.warning("ProgressionEngine service not found. Progression commands might fail.")
        if not self.item_registry: self.logger.warning("ItemRegistry service not found. Inventory formatting might be basic.")
        if not self.jutsu_system: self.logger.warning("JutsuSystem service not found. Jutsu formatting might be basic.")
        if not self.currency_system: self.logger.warning("CurrencySystem service not found. Balances may not display.")
        if not self.ollama_client: self.logger.warning("OllamaClient service not found.")

    # --- Helper Methods ---
    async def _get_character_or_error(self, interaction: discord.Interaction, user_id: Optional[str] = None, ephemeral: bool = True) -> Optional[Character]:
        """Gets character for user_id (or interaction user) and sends error if not found."""
        if not self.character_system:
            await interaction.response.send_message("Character system is unavailable.", ephemeral=True)
            return None

        target_user_id = user_id or str(interaction.user.id)
        character = await self.character_system.get_character(target_user_id)
        if not character:
            message = "You don't have a character yet! Use `/create` to start your journey." if target_user_id == str(interaction.user.id) else f"User <@{target_user_id}> does not have a character."
            try:
                # Handle if interaction already responded to (e.g., deferred)
                if interaction.response.is_done():
                    # Ensure ephemeral is passed to followup
                    await interaction.followup.send(message, ephemeral=ephemeral)
                else:
                    await interaction.response.send_message(message, ephemeral=ephemeral)
            except discord.HTTPException as e:
                self.logger.warning(f"Failed to send 'no character' error: {e}")
            return None
        return character

    async def _format_inventory(self, inventory: Any) -> str:
        """Formats inventory dict/list using ItemRegistry."""
        if not inventory: return "Empty"
        formatted_items = []
        item_counts: Dict[str, int] = {}

        if isinstance(inventory, dict):
            item_counts = inventory
        elif isinstance(inventory, list):
            for item_id in inventory:
                item_counts[item_id] = item_counts.get(item_id, 0) + 1
        else:
            self.logger.warning(f"Inventory in unexpected format: {type(inventory)}")
            return "Inventory data is corrupted."

        # Use item_registry if available
        registry = self.item_registry if self.item_registry else None

        for item_id, quantity in item_counts.items():
            item_details = registry.get_item(item_id) if registry else None
            if item_details:
                name = item_details.get("name", item_id)
                rarity = item_details.get("rarity", "Common")
                description = item_details.get("description", "") # Get description
                formatted_items.append(f"**{name} ({rarity})**: {quantity} - {description}") # Match test format
            else:
                formatted_items.append(f"**Unknown Item ID: {item_id}**: {quantity}") # Match test format style

        return "\n".join(formatted_items) if formatted_items else "Empty"

    async def _format_jutsu_list(self, jutsu_ids: List[str]) -> str:
        """Formats list of jutsu IDs using JutsuSystem."""
        if not jutsu_ids: return "None learned"
        if not self.jutsu_system: return "Jutsu data unavailable."

        formatted_jutsu = []
        for jutsu_id in jutsu_ids:
            jutsu_data = self.jutsu_system.get_jutsu(jutsu_id)
            if jutsu_data:
                name = jutsu_data.get("name", jutsu_id)
                rank = jutsu_data.get("rank", "?")
                desc = jutsu_data.get("description", "No description.")[:60] # Short desc
                formatted_jutsu.append(f"**{name}** (Rank {rank}): *{desc}...*")
            else:
                formatted_jutsu.append(f"Unknown Jutsu ID: {jutsu_id}")

        return "\n".join(formatted_jutsu) if formatted_jutsu else "None learned"

    async def _create_titles_embed(self, character: Character) -> discord.Embed:
        """Helper to create the embed for the /titles command."""
        embed = discord.Embed(
            title=f"🎖️ {character.name}'s Titles",
            color=discord.Color.dark_gold()
        )
        if not self.progression_engine:
            embed.description = "Title data service is currently unavailable."
            return embed

        earned_titles = character.titles
        equipped_title = getattr(character, 'equipped_title', None)
        all_titles_data = self.progression_engine.get_all_titles()

        if not earned_titles:
            embed.description = "No titles earned yet."
        else:
            title_lines = []
            # Sort titles, put equipped first
            sorted_titles = sorted(list(earned_titles), key=lambda t: (t != equipped_title, t))

            for title_key in sorted_titles:
                title_data = all_titles_data.get(title_key)
                if title_data:
                    name = title_data.get('name', title_key)
                    description = title_data.get('description', 'No description available.')
                    bonus_desc = title_data.get('bonus_description', '')
                    prefix = "➡️ " if title_key == equipped_title else "• "
                    bonus_text = f" ({bonus_desc})" if bonus_desc else ""
                    title_lines.append(f"{prefix}**{name}**: {description}{bonus_text}")
                else:
                    prefix = "➡️ " if title_key == equipped_title else "• "
                    title_lines.append(f"{prefix}**{title_key}** (Data missing)")

            embed.description = "\n".join(title_lines)
        return embed

    async def _handle_specialization_roles(self, guild: Optional[discord.Guild], user: discord.Member, character: Character):
        """Adds/removes specialization roles based on character data."""
        if not guild or not character.specialization:
            self.logger.debug("_handle_specialization_roles: No guild or no specialization set.")
            return

        spec_role_name = f"Specialist: {character.specialization.title()}"
        target_role = discord.utils.get(guild.roles, name=spec_role_name)

        # Remove other specialization roles first
        current_spec_roles = [r for r in user.roles if r.name.startswith("Specialist: ")]
        roles_to_remove = [r for r in current_spec_roles if r.name != spec_role_name]

        if roles_to_remove:
            try:
                await user.remove_roles(*roles_to_remove, reason="Changed specialization")
                self.logger.info(f"Removed roles {[r.name for r in roles_to_remove]} from {user.id} for spec change.")
            except discord.Forbidden:
                self.logger.warning(f"Missing permissions to remove roles from {user.id} in guild {guild.id}")
            except discord.HTTPException as e:
                self.logger.error(f"Failed to remove roles from {user.id}: {e}")

        # Add the target role if it exists and user doesn't have it
        if target_role and target_role not in current_spec_roles: # Check if target role already present
            try:
                await user.add_roles(target_role, reason=f"Chose {character.specialization} specialization")
                self.logger.info(f"Added role {target_role.name} to {user.id}")
            except discord.Forbidden:
                self.logger.warning(f"Missing permissions to add role {target_role.name} to {user.id} in guild {guild.id}")
            except discord.HTTPException as e:
                self.logger.error(f"Failed to add role {target_role.name} to {user.id}: {e}")
        elif not target_role:
             self.logger.warning(f"Specialization role '{spec_role_name}' not found in guild {guild.id}.")

    # --- Commands ---

    @app_commands.command(name="create", description="Create your Shinobi character.")
    async def create(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_id = str(interaction.user.id)
        user_name = interaction.user.display_name

        self.logger.info(f"/create command initiated by {user_name} ({user_id}).")

        try:
            # Check if character already exists
            existing_char = await self.character_system.get_character(user_id)
            if existing_char:
                await interaction.followup.send("You already have a Shinobi character! Use `/profile`.", ephemeral=True)
                self.logger.warning(f"Character creation attempt failed for {user_name} ({user_id}): Already exists.")
                return

            # Assign clan using the engine (support sync or async)
            if self.clan_assignment_engine:
                self.logger.debug(f"Attempting clan assignment for {user_name} ({user_id})")
                raw = self.clan_assignment_engine.assign_clan(player_id=user_id, player_name=user_name)
                assignment_result = await raw if inspect.isawaitable(raw) else raw
                if "error" in assignment_result:
                    assigned_clan = None
                    self.logger.error(f"Clan assignment failed for {user_id}: {assignment_result['error']}")
                else:
                    assigned_clan = assignment_result.get("assigned_clan")
                    self.logger.info(f"Clan assigned via engine: {assigned_clan} for {user_id}")
            else:
                # Fallback or default clan if engine not available
                assigned_clan = random.choice(["Uchiha", "Senju", "Uzumaki", "Hyuga", "Nara", "Yamanaka", "Akimichi", "Aburame", "Inuzuka"])
                self.logger.warning(f"ClanAssignmentEngine not available. Assigning random fallback clan: {assigned_clan} for {user_id}")

            # Create the character with the assigned clan
            new_char = await self.character_system.create_character(user_id=user_id, name=user_name, clan=assigned_clan)

            if new_char:
                self.logger.info(f"Successfully created character for {user_name} ({user_id}) with clan {assigned_clan}.")
                embed = self._create_character_success_embed(new_char)
                view = View()  # placeholder view for E2E tests
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                self.logger.error(f"Character creation failed unexpectedly for {user_name} ({user_id}) after clan assignment.")
                await interaction.followup.send("❌ An error occurred during character creation.", ephemeral=True)

        except Exception as e:
            self.logger.exception(f"General error during /create for user {user_id}: {e}")
            await interaction.followup.send("❌ An internal error occurred. Please try again later.", ephemeral=True)

    @app_commands.command(name="profile", description="View your Shinobi character profile.")
    async def profile(self, interaction: discord.Interaction):
        """Displays the user's character profile."""
        await interaction.response.defer(ephemeral=True, thinking=True) # Ephemeral response
        user_id = str(interaction.user.id)

        if not self.character_system:
            await interaction.followup.send("Sorry, the character system is unavailable. Please contact an admin.")
            return

        try:
            character = await self.character_system.get_character(user_id)

            if not character:
                # Use followup since we deferred
                await interaction.followup.send("You don't have a character yet! Use `/create` to start your journey.", ephemeral=True) # Add ephemeral=True
                return

            # Get clan info from the character object itself
            clan_name = character.clan or "Clanless" 
            # if self.clan_assignment_engine: # Remove dependency on clan_assignment_engine here
            #      clan_name = self.clan_assignment_engine.get_player_clan(user_id) or "Clanless"
                 
            # --- Build Embed --- 
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Shinobi Profile",
                color=discord.Color.blue() # Or use clan color if available
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            # Basic Info
            embed.add_field(name="👤 Name", value=character.name, inline=True)
            embed.add_field(name="⚜️ Clan", value=clan_name, inline=True)
            embed.add_field(name="📈 Level", value=str(character.level), inline=True)
            
            # Stats - Use correct attribute names (hp, stamina, speed, defense, etc.)
            stats_text = (
                f"**HP:** {character.hp}/{character.max_hp}\n"
                f"**STA:** {character.stamina}/{character.max_stamina}\n"
                f"**STR:** {character.strength}\n"
                f"**SPD:** {character.speed}\n"
                f"**DEF:** {character.defense}\n"
                f"**WP:** {character.willpower}\n"
                f"**CC:** {character.chakra_control}\n"
                f"**INT:** {character.intelligence}"
            )
            embed.add_field(name="📊 Stats", value=stats_text, inline=True)
            
            # Combat Stats
            combat_stats_str = (
                f"🥋 **Taijutsu:** {character.taijutsu}\n"
                f"🥷 **Ninjutsu:** {character.ninjutsu}\n"
                f"👻 **Genjutsu:** {character.genjutsu}"
            )
            embed.add_field(name="Combat Stats", value=combat_stats_str, inline=True)

            # Progression & Currency (Check if attributes exist)
            progression_text = (
                 f"**XP:** {getattr(character, 'xp', 0)} / {getattr(character, 'xp_needed', 'N/A')}\n"
                 f"**Rank:** {getattr(character, 'rank', 'Genin')}"
            )
            embed.add_field(name="🌟 Progression", value=progression_text, inline=True)

            # Fetch currency and tokens, supporting both async and sync methods
            ryo = 0
            tokens = 0
            currency_system = getattr(self.bot.services, 'currency_system', None)
            token_system = getattr(self.bot.services, 'token_system', None)
            if currency_system:
                raw_ryo = currency_system.get_player_balance(user_id)
                ryo = await raw_ryo if inspect.isawaitable(raw_ryo) else raw_ryo
            if token_system:
                raw_tokens = token_system.get_player_tokens(user_id)
                tokens = await raw_tokens if inspect.isawaitable(raw_tokens) else raw_tokens
            embed.add_field(name="💰 Currency", value=f"**Ryō:** {ryo}\n**Tokens:** {tokens}", inline=True)

            # Add other relevant fields if available (e.g., location, status)
            # embed.add_field(name="📍 Location", value=character.location, inline=True)
            # embed.add_field(name="Status", value=character.status, inline=True)

            # Equipment (Example - Adapt based on actual implementation)
            equipment_text = "None" # Placeholder
            embed.add_field(name="🛡️ Equipment", value=equipment_text, inline=False)

            # Add footer instructions
            embed.set_footer(text="Use /stats for detailed stats and battle record.")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error during /profile command for user {user_id}: {e}", exc_info=True)
            await interaction.followup.send("An error occurred while fetching your profile. Please contact an admin.")

    @app_commands.command(name="stats", description="View detailed stats and battle record for a character.")
    @app_commands.describe(user="The user whose stats to view (optional, defaults to yourself)")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Displays detailed stats and battle record."""
        target_user = user or interaction.user
        is_self = target_user.id == interaction.user.id
        await interaction.response.defer(ephemeral=is_self)

        character = await self._get_character_or_error(interaction, str(target_user.id), ephemeral=True)
        if not character: return

        try:
            rarity = getattr(character, 'rarity', 'Common')
            embed = discord.Embed(title=f"📊 {character.name}'s Stats & Record", color=get_rarity_color(rarity))
            if target_user.display_avatar: embed.set_thumbnail(url=target_user.display_avatar.url)

            stats_str = (
                f"❤️ **HP:** {character.hp}/{character.max_hp}\n"
                f"🌀 **Chakra:** {character.chakra}/{character.max_chakra}\n"
                f"🏃 **Stamina:** {character.stamina}/{character.max_stamina}\n"
                f"💪 **Strength:** {character.strength}\n"
                f"💨 **Speed:** {character.speed}\n"
                f"🛡️ **Defense:** {character.defense}\n"
                f"🧠 **Intelligence:** {character.intelligence}\n"
                f"👁️ **Perception:** {character.perception}\n"
                f"💖 **Willpower:** {character.willpower}\n"
                f"✨ **Chakra Control:** {character.chakra_control}"
            )
            embed.add_field(name="Core Stats", value=stats_str, inline=True)

            combat_stats_str = (
                f"🥋 **Taijutsu:** {character.taijutsu}\n"
                f"🥷 **Ninjutsu:** {character.ninjutsu}\n"
                f"👻 **Genjutsu:** {character.genjutsu}"
            )
            embed.add_field(name="Combat Stats", value=combat_stats_str, inline=True)

            wins = getattr(character, 'wins', 0)
            losses = getattr(character, 'losses', 0)
            draws = getattr(character, 'draws', 0)
            total_battles = wins + losses + draws
            win_rate = (wins / total_battles * 100) if total_battles > 0 else 0
            record_str = (
                f"🏆 **Wins:** {wins}\n"
                f"☠️ **Losses:** {losses}\n"
                f"⚖️ **Draws:** {draws}\n"
                f"📈 **Win Rate:** {win_rate:.1f}%"
            )
            embed.add_field(name="Battle Record", value=record_str, inline=False)

            wins_vs_rank = getattr(character, 'wins_against_rank', {})
            if wins_vs_rank:
                 wins_vs_rank_str = "\n".join([f"- vs {rank}: {count}" for rank, count in sorted(wins_vs_rank.items())])
                 embed.add_field(name="Wins vs Rank", value=wins_vs_rank_str, inline=False)

            embed.set_footer(text=f"ID: {character.id}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error viewing stats for {target_user.id}: {e}", exc_info=True)
            message = "❌ An error occurred retrieving your stats." if is_self else "❌ An error occurred retrieving stats."
            await interaction.followup.send(message, ephemeral=True)

    @app_commands.command(name="delete", description="Permanently delete your Shinobi character.")
    async def delete(self, interaction: discord.Interaction):
        """Initiates the character deletion process."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        character = await self._get_character_or_error(interaction)
        if not character: return

        try:
            view = DeleteConfirmationView(self, interaction.user, character)
            # Send the confirmation view
            message = await interaction.followup.send(
                f"🚨 **Warning!** Are you sure you want to delete your character **{character.name}**? This action cannot be undone.",
                view=view,
                ephemeral=True
            )
            view.message = message
        except Exception as e:
            self.logger.error(f"Error initiating delete character for {interaction.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred starting the deletion process.", ephemeral=True)

    @app_commands.command(name="inventory", description="View your character's inventory.")
    async def inventory(self, interaction: discord.Interaction):
        """Displays the character's inventory."""
        await interaction.response.defer(ephemeral=True)
        character = await self._get_character_or_error(interaction)
        if not character: return

        try:
            inventory_text = await self._format_inventory(character.inventory)
            rarity = getattr(character, 'rarity', 'Common')
            embed = discord.Embed(title=f"🎒 {character.name}'s Inventory", description=inventory_text, color=get_rarity_color(rarity))
            if interaction.user.display_avatar: embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error viewing inventory for {interaction.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred retrieving your inventory.", ephemeral=True)

    @app_commands.command(name="jutsu", description="View your character's known jutsu.")
    async def jutsu(self, interaction: discord.Interaction):
        """Displays the character's learned jutsu."""
        await interaction.response.defer(ephemeral=True)
        character = await self._get_character_or_error(interaction)
        if not character: return

        try:
            jutsu_list = getattr(character, 'jutsu', [])
            jutsu_text = await self._format_jutsu_list(jutsu_list)
            rarity = getattr(character, 'rarity', 'Common')
            embed = discord.Embed(title=f"📜 {character.name}'s Known Jutsu", description=jutsu_text, color=get_rarity_color(rarity))
            if interaction.user.display_avatar: embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error viewing jutsu for {interaction.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred retrieving your jutsu list.", ephemeral=True)

    @app_commands.command(name="status", description="View your character's current status effects.")
    async def status(self, interaction: discord.Interaction):
        """Displays current status effects affecting the character."""
        await interaction.response.defer(ephemeral=True)
        character = await self._get_character_or_error(interaction)
        if not character: return

        try:
            status_effects = getattr(character, 'status_effects', [])
            if not status_effects:
                status_text = "No active status effects."
            else:
                formatted_effects = []
                for effect in status_effects:
                    if isinstance(effect, dict):
                        name = effect.get('name', 'Unknown Effect')
                        duration = effect.get('duration', None)
                        desc = effect.get('description', '')
                        line = f"**{name}**"
                        if duration: line += f" ({duration} turns left)"
                        if desc: line += f": *{desc}*"
                        formatted_effects.append(line)
                    elif isinstance(effect, str):
                        formatted_effects.append(f"**{effect}**")
                    else:
                         formatted_effects.append("Unknown effect format")
                status_text = "\n".join(formatted_effects)

            rarity = getattr(character, 'rarity', 'Common')
            embed = discord.Embed(title=f"🌀 {character.name}'s Status", description=status_text, color=get_rarity_color(rarity))
            if interaction.user.display_avatar: embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error viewing status for {interaction.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred retrieving your status.", ephemeral=True)

    @app_commands.command(name="achievements", description="View earned achievements.")
    @app_commands.describe(user="The user whose achievements to view (optional, defaults to yourself)")
    async def achievements(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Displays earned achievements for a character."""
        target_user = user or interaction.user
        is_self = target_user.id == interaction.user.id
        await interaction.response.defer(ephemeral=is_self)

        character = await self._get_character_or_error(interaction, str(target_user.id), ephemeral=True)
        if not character: return

        try:
            embed = discord.Embed(title=f"🏆 {character.name}'s Achievements", color=discord.Color.gold())
            if target_user.display_avatar: embed.set_thumbnail(url=target_user.display_avatar.url)

            if not self.progression_engine:
                 await interaction.followup.send("❌ Achievement data service is unavailable.", ephemeral=True)
                 return

            earned_keys = getattr(character, 'achievements', set()) # Default to empty set
            all_ach_data = self.progression_engine.get_all_achievements()

            if not earned_keys:
                embed.description = "No achievements earned yet."
            else:
                earned_list = []
                for ach_key in sorted(list(earned_keys)):
                    ach_data = all_ach_data.get(ach_key)
                    if ach_data:
                        name = ach_data.get('name', ach_key)
                        description = ach_data.get('description', 'No description.')
                        exp_reward = ach_data.get('exp_reward', 0)
                        entry = f"**{name}**: {description}"
                        if exp_reward > 0: entry += f" (+{exp_reward} XP)"
                        earned_list.append(f"• {entry}")
                    else:
                        earned_list.append(f"• {ach_key} (Data missing)")
                embed.description = "\n".join(earned_list) if earned_list else "No achievements earned yet."

            await interaction.followup.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Error viewing achievements for {target_user.id}: {e}", exc_info=True)
            message = "❌ An error occurred retrieving achievements."
            await interaction.followup.send(message, ephemeral=True)

    @app_commands.command(name="titles", description="View earned titles and equip one.")
    @app_commands.describe(user="The user whose titles to view (optional, defaults to yourself)")
    async def titles(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Displays earned titles and allows equipping for self."""
        target_user = user or interaction.user
        is_self = target_user.id == interaction.user.id
        await interaction.response.defer(ephemeral=is_self)

        character = await self._get_character_or_error(interaction, str(target_user.id), ephemeral=True)
        if not character: return

        try:
            embed = await self._create_titles_embed(character)
            if target_user.display_avatar: embed.set_thumbnail(url=target_user.display_avatar.url)

            view = None
            if is_self and character.titles and self.progression_engine:
                all_titles_data = self.progression_engine.get_all_titles()
                options = []
                equipped_title = getattr(character, 'equipped_title', None)
                for title_key in sorted(list(character.titles)):
                     title_data = all_titles_data.get(title_key)
                     if title_data:
                         name = title_data.get('name', title_key)
                         desc = title_data.get('bonus_description', '') or title_data.get('description', '')
                         options.append(discord.SelectOption(label=name[:100], description=desc[:100], value=title_key, default=(title_key == equipped_title)))
                     else:
                         options.append(discord.SelectOption(label=title_key, description="(Data missing)", value=title_key, default=(title_key == equipped_title)))

                if options:
                     view = TitleEquipView(self, character, options[:25])

            await interaction.followup.send(embed=embed, view=view if is_self else None)
        except Exception as e:
            self.logger.error(f"Error viewing titles for {target_user.id}: {e}", exc_info=True)
            message = "❌ An error occurred retrieving titles."
            await interaction.followup.send(message, ephemeral=True)

    @app_commands.command(name="specialize", description="Choose a specialization path for your character.")
    async def specialize(self, interaction: discord.Interaction):
        """Allows a character to choose a specialization."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        character = await self._get_character_or_error(interaction)
        if not character: return

        # Check if already specialized
        if getattr(character, 'specialization', None):
             await interaction.followup.send(f"You have already specialized in **{character.specialization.title()}**.", ephemeral=True)
             return

        # Check prerequisites (e.g., level)
        required_level = 10 # Make this configurable if needed
        if getattr(character, 'level', 0) < required_level:
            await interaction.followup.send(f"You must be at least level {required_level} to specialize.", ephemeral=True)
            return

        # Get available specializations (ensure progression_engine exists)
        if not self.progression_engine:
             await interaction.followup.send("Specialization data service is unavailable.", ephemeral=True)
             return

        # Assuming progression_engine has a method like get_available_specializations()
        # If not, define a default list here.
        try:
            available_specs = self.progression_engine.get_available_specializations(character) # Pass character for potential checks
        except AttributeError:
            self.logger.warning("ProgressionEngine does not have get_available_specializations method. Using default list.")
            available_specs = ["Ninjutsu", "Taijutsu", "Genjutsu", "Medical", "Sensory"] # Default list
        except Exception as e:
            self.logger.error(f"Error getting available specializations: {e}", exc_info=True)
            await interaction.followup.send("Error fetching available specializations.", ephemeral=True)
            return

        if not available_specs:
             await interaction.followup.send("No specializations are currently available for you.", ephemeral=True)
             return

        view = SpecializationChoiceView(self, character, available_specs)
        embed = discord.Embed(
            title="✨ Choose Your Specialization",
            description="Select a path to focus your training. This choice is permanent!",
            color=discord.Color.purple()
        )
        # Optionally add descriptions for each spec
        # spec_details = self.progression_engine.get_specialization_details() # Example
        # for spec in available_specs: embed.add_field(name=spec, value=spec_details.get(spec, {}).get('description', '...'))

        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = message # Store message for the view

    def _create_character_success_embed(self, character: Character) -> discord.Embed:
        """Builds the embed sent when a character is successfully created."""
        clan_name = character.clan or "Clanless"
        embed = discord.Embed(
            title="Character Created!",
            description=f"Welcome, {character.name} of the {clan_name} clan!",
            color=discord.Color.green()
        )
        # Add Rank and Level fields
        embed.add_field(name="Rank", value=character.rank, inline=True)
        embed.add_field(name="Level", value=str(character.level), inline=True)
        return embed

# --- Setup Function ---
async def setup(bot: "HCShinobiBot"):
    """Sets up the CharacterCommands cog."""
    # Ensure core services are present
    required_services = ["character_system", "clan_assignment_engine", "progression_engine"]
    missing = [svc for svc in required_services if not hasattr(bot.services, svc)]
    if missing:
        raise AttributeError(f"Bot.services is missing required attributes for CharacterCommands: {missing}")

    await bot.add_cog(CharacterCommands(bot))
    logger.info("CharacterCommands Cog loaded successfully.") 