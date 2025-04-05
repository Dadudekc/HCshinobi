"""
Battle commands for the HCshinobi Discord bot.

Provides commands for challenging players to battles, handling the acceptance flow,
and creating interactive battle views with attack, jutsu, and flee options.
"""

import discord
from discord.ext import commands
from discord import app_commands, ui
import logging
import random
from typing import Dict, Optional, Tuple, Any, List
from datetime import datetime

from HCshinobi.core.battle_system import BattleSystem, BattleState
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.utils.embed_utils import get_rarity_color
from ..core.constants import RarityTier
from HCshinobi.core.battle_manager import BattleManager

# Import the new battle UI components
from ..utils.battle_ui import BattleSystemView

# Store pending duels in memory: {challenged_user_id: (challenger_user_id, discord.Interaction)}
pending_duels: Dict[int, Tuple[int, discord.Interaction]] = {}

# --------------------------------------------------------------------------------
#                                 Duel Invite View
# --------------------------------------------------------------------------------

class DuelInviteView(ui.View):
    """
    Presents Accept/Decline buttons to the challenged user.
    If accepted, it signals the Cog to start the battle.
    If declined or timed out, the duel is aborted.
    """
    def __init__(
        self,
        cog: 'BattleCommands',
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


# --------------------------------------------------------------------------------
#                                  Jutsu Select
# --------------------------------------------------------------------------------

class JutsuSelect(ui.Select):
    """
    A dropdown that shows all jutsu the current player knows,
    allowing them to select a jutsu to use.
    """
    def __init__(self, battle_view: 'BattleView'):
        self.battle_view = battle_view
        player_id = self.battle_view.battle_state.current_turn_player_id
        # Determine if the attacker or defender is the active player
        if player_id == self.battle_view.battle_state.attacker.id:
            player = self.battle_view.battle_state.attacker
        else:
            player = self.battle_view.battle_state.defender

        master_jutsu_data = self.battle_view.battle_system.master_jutsu_data
        options = []

        # Build list of jutsu the player knows
        if player.jutsu:
            for jutsu_name in player.jutsu:
                jutsu_info = master_jutsu_data.get(jutsu_name)
                if jutsu_info:
                    jutsu_type = jutsu_info.get('type', 'Unknown')
                    jutsu_cost = jutsu_info.get('cost', {})
                    cost_parts = []
                    if 'chakra' in jutsu_cost:
                        cost_parts.append(f"{jutsu_cost['chakra']} Chakra")
                    if 'stamina' in jutsu_cost:
                        cost_parts.append(f"{jutsu_cost['stamina']} Stamina")
                    cost_str = ", ".join(cost_parts) if cost_parts else "No Cost"
                    description = f"{jutsu_type} - Cost: {cost_str}"
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
                label="Error Loading Jutsu",
                description="Could not load jutsu list.",
                value="_error_"
            ))

        super().__init__(
            placeholder="Choose a Jutsu...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="jutsu_select"
        )

    async def callback(self, interaction: discord.Interaction):
        """Called when the player selects a jutsu from the dropdown."""
        if not await self.battle_view.interaction_check(interaction):
            return
        
        selected_jutsu = self.values[0]
        if selected_jutsu in ("_none_", "_error_"):
            await interaction.response.send_message(
                f"Invalid selection: {selected_jutsu}", ephemeral=True
            )
            return
        
        action_dict = {
            'type': 'jutsu',
            'jutsu_name': selected_jutsu
        }
        await self.battle_view.handle_action(interaction, action_dict)


# --------------------------------------------------------------------------------
#                                  Battle View
# --------------------------------------------------------------------------------

class BattleView(ui.View):
    """
    Main interactive View for an active battle. Provides buttons for
    Attack, Defend, Flee, and a JutsuSelect dropdown. Displays HP and updates each turn.
    """
    def __init__(
        self,
        battle_state: BattleState,
        battle_system: BattleSystem,
        character_system: CharacterSystem,
        battle_manager: BattleManager,
        interaction: discord.Interaction
    ):
        super().__init__(timeout=300)  # 5 minute default timeout
        self.battle_state = battle_state
        self.battle_system = battle_system
        self.character_system = character_system
        self.battle_manager = battle_manager
        self.interaction = interaction

        # Build a canonical battle_id
        sorted_ids = sorted([
            str(battle_state.attacker.id),
            str(battle_state.defender.id)
        ])
        self.battle_id = f"{sorted_ids[0]}_{sorted_ids[1]}"

        # Add UI components
        self.add_item(self.attack_button)
        self.add_item(self.defend_button)
        self.add_item(JutsuSelect(self))
        self.add_item(self.flee_button)

        self.update_buttons()

    def create_embed(self) -> discord.Embed:
        """
        Creates an embed reflecting the current state of the battle:
        - Player names and HP
        - Whose turn it is
        - End-of-battle info if concluded
        """
        p1 = self.battle_state.attacker
        p2 = self.battle_state.defender

        p1_hp = self.battle_state.attacker_hp
        p2_hp = self.battle_state.defender_hp
        turn_player_id = self.battle_state.current_turn_player_id
        turn_player = p1 if turn_player_id == p1.id else p2

        embed = discord.Embed(
            title=f"⚔️ Duel: {p1.name} vs {p2.name}",
            color=discord.Color.red()
        )
        embed.add_field(
            name=f"**{p1.name}**",
            value=f"HP: {p1_hp}/{p1.hp}",
            inline=True
        )
        embed.add_field(
            name=f"**{p2.name}**",
            value=f"HP: {p2_hp}/{p2.hp}",
            inline=True
        )

        if self.battle_state.is_active:
            embed.set_footer(text=f"Turn: {turn_player.name}")
        else:
            # If battle ended, show winner
            winner_id = self.battle_state.winner_id
            winner = p1 if winner_id == p1.id else p2
            embed.description = f"**Battle Ended! Winner: {winner.name}**"
            embed.color = discord.Color.green()
            embed.set_footer(text="Battle Concluded.")

        return embed

    def update_buttons(self):
        """
        Disables or enables all UI components based on whether the battle is active.
        """
        active = self.battle_state.is_active
        for item in self.children:
            item.disabled = not active

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Ensures the user clicking a button or select is a valid participant
        and that it's their turn (for Attack/Defend/Jutsu).
        """
        current_state = self.battle_system.get_battle_state(self.battle_id)
        if not current_state or not current_state.is_active:
            await interaction.response.send_message(
                "❌ This battle has already ended.", ephemeral=True
            )
            return False

        participant_ids = {
            int(self.battle_state.attacker.id),
            int(self.battle_state.defender.id)
        }
        if interaction.user.id not in participant_ids:
            await interaction.response.send_message(
                "❌ You are not part of this battle!", ephemeral=True
            )
            return False

        component_custom_id = interaction.data.get("custom_id")
        is_select = (interaction.data.get("component_type") == discord.ComponentType.select_menu.value)

        if (
            component_custom_id in ("battle_attack", "battle_defend") or
            (is_select and component_custom_id == "jutsu_select")
        ):
            # Check turn
            if interaction.user.id != int(self.battle_state.current_turn_player_id):
                await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
                return False

        return True

    async def handle_action(self, interaction: discord.Interaction, action_dict: Dict[str, Any]):
        """
        Called when a player performs an action (attack, defend, jutsu, flee).
        Delegates to the battle_manager for resolution, updates the UI, and triggers
        AI moves if the opponent is an NPC.
        """
        await interaction.response.defer()
        player_id = str(interaction.user.id)
        try:
            result = await self.battle_manager.process_player_action(
                player_id,
                action_dict,
                self.battle_id
            )
        except Exception as e:
            logging.error(f"[BattleView.handle_action] Error in process_player_action: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while processing your action.",
                ephemeral=True
            )
            return

        # result might be (BattleState, message) or something else
        final_state = None
        final_message = "Action processed."
        if isinstance(result, tuple) and len(result) == 2:
            current_state, final_message = result
            if isinstance(current_state, BattleState):
                final_state = current_state
            else:
                logging.error(f"Invalid state type returned: {type(current_state)} for battle {self.battle_id}")
                final_state = self.battle_system.get_battle_state(self.battle_id)
        else:
            logging.warning(f"Unexpected result from process_player_action: {result}")
            final_state = self.battle_system.get_battle_state(self.battle_id)  # fallback
            if final_state and final_state.battle_log:
                final_message = final_state.battle_log[-1]

        # Check for NPC turn if the battle is still active
        if final_state and final_state.is_active:
            # Identify if the next turn belongs to an NPC
            is_ai_opponent = await self._check_and_do_ai_turn(final_state, player_id)
            if is_ai_opponent:
                # The AI turn might have updated final_state
                final_state = self.battle_system.get_battle_state(self.battle_id) or final_state

        if final_state:
            self.battle_state = final_state
            self.update_buttons()
            try:
                await self.interaction.edit_original_response(
                    embed=self.create_embed(),
                    view=self
                )
            except discord.NotFound:
                logging.warning(f"[BattleView] Original battle message not found for {self.battle_id}.")
            except discord.HTTPException as http_err:
                logging.error(f"[BattleView] HTTP error editing message: {http_err}")

            if not self.battle_state.is_active:
                # If the battle ended after this action, stop the view
                logging.info(f"[BattleView] Battle {self.battle_id} ended. Stopping view.")
                self.stop()
        else:
            await interaction.followup.send(
                "❌ A critical error occurred; unable to update battle state.",
                ephemeral=True
            )
            self.stop()

    async def _check_and_do_ai_turn(self, state: BattleState, last_player_id: str) -> bool:
        """
        If the next turn belongs to an NPC, trigger AI logic.
        Returns True if an AI turn was triggered, False otherwise.
        """
        if state.defender and str(state.defender.id) == last_player_id:
            opponent_id_str = str(state.attacker.id)
        else:
            opponent_id_str = str(state.defender.id)

        npc_manager = getattr(self.battle_manager.bot.services, 'npc_manager', None)
        if not npc_manager:
            logging.warning(f"No NPCManager found; skipping AI logic for {self.battle_id}.")
            return False

        if npc_manager.is_npc(opponent_id_str) and str(state.current_turn_player_id) == opponent_id_str:
            logging.info(f"Triggering AI turn for {opponent_id_str} in battle {self.battle_id}.")
            try:
                ai_result = await self.battle_manager._process_ai_turn(self.battle_id)
                if isinstance(ai_result, tuple) and len(ai_result) == 2:
                    ai_state, _ai_message = ai_result
                    if not isinstance(ai_state, BattleState):
                        logging.error(f"Invalid AI state type: {type(ai_state)}")
                else:
                    logging.warning(f"Unexpected AI turn result: {ai_result}")
                return True
            except Exception as ai_e:
                logging.error(f"Error during AI turn for {self.battle_id}: {ai_e}", exc_info=True)

        return False

    @ui.button(label="Basic Attack", style=discord.ButtonStyle.primary, custom_id="battle_attack", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: ui.Button):
        """User clicked 'Attack'."""
        if not await self.interaction_check(interaction):
            return
        await self.handle_action(interaction, {'type': 'basic_attack'})

    @ui.button(label="Defend", style=discord.ButtonStyle.secondary, custom_id="battle_defend", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: ui.Button):
        """User clicked 'Defend'."""
        if not await self.interaction_check(interaction):
            return
        await self.handle_action(interaction, {'type': 'defend'})

    @ui.button(label="Flee", style=discord.ButtonStyle.danger, custom_id="battle_flee", row=1)
    async def flee_button(self, interaction: discord.Interaction, button: ui.Button):
        """User clicked 'Flee'."""
        participant_ids = {
            int(self.battle_state.attacker.id),
            int(self.battle_state.defender.id)
        }
        if interaction.user.id not in participant_ids:
            await interaction.response.send_message(
                "❌ You are not part of this battle!", ephemeral=True
            )
            return
        # Flee is immediate, no need for turn check
        if not interaction.response.is_done():
            await interaction.response.defer()
        await self.handle_action(interaction, {'type': 'flee'})

    async def on_timeout(self):
        """
        If no actions occur for 'timeout' seconds, end the battle in a draw.
        """
        current_state = self.battle_system.get_battle_state(self.battle_id)
        if current_state and current_state.is_active:
            final_state = await self.battle_system.end_battle(self.battle_id, winner_id=None)
            if final_state:
                self.battle_state = final_state
                self.update_buttons()
                try:
                    await self.interaction.edit_original_response(
                        embed=self.create_embed(),
                        view=self
                    )
                    await self.interaction.followup.send(
                        f"⌛ Battle **timed out**! It's a draw.",
                        ephemeral=True
                    )
                except discord.NotFound:
                    logging.warning(f"[BattleView.on_timeout] Original message not found for {self.battle_id}.")
        self.stop()


# --------------------------------------------------------------------------------
#                                Main Cog
# --------------------------------------------------------------------------------

class BattleCommands(commands.Cog):
    """
    Commands for initiating and managing battles and duels.
    """
    
    def __init__(
        self,
        bot: commands.Bot,
        battle_system: BattleSystem,
        character_system: CharacterSystem,
        battle_manager: BattleManager,
        training_system=None
    ):
        """Initialize battle commands cog."""
        self.bot = bot
        self.battle_system = battle_system
        self.character_system = character_system
        self.battle_manager = battle_manager
        self.training_system = training_system
        self.logger = logging.getLogger(__name__)
    
    @app_commands.command(name="duel", description="Challenge another player to a duel")
    @app_commands.describe(opponent="The player you want to challenge")
    async def duel(self, interaction: discord.Interaction, opponent: discord.Member):
        """
        Challenge another player to a duel.
        Duels are friendly matches that don't impact player stats.
        """
        # We'll reuse the battle command implementation but mark it as a duel
        await self._battle_command_impl(interaction, opponent, is_duel=True)
    
    @app_commands.command(name="battle", description="Challenge another player to a battle")
    @app_commands.describe(opponent="The player you want to battle against")
    async def battle(self, interaction: discord.Interaction, opponent: discord.Member):
        """
        Challenge another player to a battle.
        Battles impact player stats and provide rewards.
        """
        await self._battle_command_impl(interaction, opponent, is_duel=False)
    
    async def _battle_command_impl(self, interaction: discord.Interaction, opponent: discord.Member, is_duel: bool = False):
        """Implementation for both battle and duel commands."""
        # Defer response due to potentially slower character lookups
        await interaction.response.defer(ephemeral=False)
        
        challenger = interaction.user
        
        # Check if players have characters
        challenger_char = await self.character_system.get_character(str(challenger.id))
        if not challenger_char:
            await interaction.followup.send(
                f"❌ {challenger.mention}, you don't have a character! Use `/character create` first.",
                ephemeral=True
            )
            return
            
        opponent_char = await self.character_system.get_character(str(opponent.id))
        if not opponent_char:
            await interaction.followup.send(
                f"❌ {opponent.mention} doesn't have a character.",
                ephemeral=True
            )
            return
            
        # Check if either player is in a battle already
        challenger_battle = self._get_current_battle_for_user(str(challenger.id))
        if challenger_battle[0]:
            await interaction.followup.send(
                f"❌ {challenger.mention}, you're already in a battle! "
                "Finish that one first or use `/battle_surrender`.",
                ephemeral=True
            )
            return
            
        opponent_battle = self._get_current_battle_for_user(str(opponent.id))
        if opponent_battle[0]:
            await interaction.followup.send(
                f"❌ {opponent.mention} is already in a battle.",
                ephemeral=True
            )
            return
            
        # Create a duel invitation
        view = DuelInviteView(self, challenger, opponent)
        
        battle_type = "duel" if is_duel else "battle"
        message = await interaction.followup.send(
            f"⚔️ {challenger.mention} has challenged {opponent.mention} to a {battle_type}! "
            f"{opponent.mention}, do you accept?",
            view=view
        )
        view.message = message
        
        # Add to pending duels
        pending_duels[opponent.id] = (challenger.id, interaction)
        
        # Wait for response
        await view.wait()
        
        # Remove from pending duels
        if opponent.id in pending_duels:
            del pending_duels[opponent.id]
            
        # If accepted, start the battle
        if view.accepted:
            if is_duel:
                result = await self._start_duel_logic(interaction, challenger, opponent)
            else:
                result = await self._start_battle_logic(interaction, challenger, opponent)
                
            success, message = result
            if not success:
                await interaction.followup.send(
                    f"❌ Failed to start {battle_type}: {message}",
                    ephemeral=True
                )
    
    async def _start_battle_logic(self, interaction: discord.Interaction, challenger: discord.Member, opponent: discord.Member) -> Tuple[bool, str]:
        """Start a battle between two players."""
        try:
            # Start the battle in the battle system
            battle_state = await self.battle_system.start_battle(
                str(challenger.id),
                str(opponent.id)
            )
            
            if not battle_state:
                return False, "Failed to create battle state."
                
            # Determine the battle ID
            sorted_ids = sorted([
                str(challenger.id),
                str(opponent.id)
            ])
            battle_id = f"{sorted_ids[0]}_{sorted_ids[1]}"
            
            # Get character objects for both players
            challenger_char = await self.character_system.get_character(str(challenger.id))
            opponent_char = await self.character_system.get_character(str(opponent.id))
            
            # Create and send the battle view
            battle_view = BattleSystemView(
                battle_id=battle_id,
                player=challenger_char, 
                opponent=opponent_char,
                battle_manager=self.battle_manager,
                battle_system=self.battle_system
            )
            
            battle_embed = battle_view.create_battle_embed()
            message = await interaction.followup.send(embed=battle_embed, view=battle_view)
            battle_view.message = message
            
            return True, "Battle started successfully."
            
        except Exception as e:
            self.logger.error(f"Error starting battle: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    async def _start_duel_logic(self, interaction: discord.Interaction, challenger: discord.Member, opponent: discord.Member) -> Tuple[bool, str]:
        """Start a duel between two players."""
        return await self._start_battle_logic(interaction, challenger, opponent)
    
    @app_commands.command(name="battle_flee", description="Attempt to flee from your current battle.")
    async def battle_flee(self, interaction: discord.Interaction):
        """Attempt to flee from your current battle."""
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(interaction.user.id)
        
        # Check if the user is in a battle
        battle_id, other_player_id, battle_state = self._get_current_battle_for_user(user_id)
        
        if not battle_id:
            await interaction.followup.send("❌ You are not in a battle.", ephemeral=True)
            return
            
        # Attempt to flee
        action = {"type": "flee"}
        try:
            result = await self.battle_manager.process_player_action(
                user_id,
                action,
                battle_id
            )
            
            # Get updated battle state
            updated_state = self.battle_system.get_battle_state(battle_id)
            
            if not updated_state:
                await interaction.followup.send("✅ You have fled from the battle.", ephemeral=True)
                return
                
            # Check if the player successfully fled
            if not updated_state.is_active:
                await interaction.followup.send("✅ You have fled from the battle.", ephemeral=True)
            else:
                await interaction.followup.send(
                    "❌ You failed to flee. The battle continues.", 
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"Error in battle_flee: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="battle_surrender", description="Surrender your current battle.")
    async def battle_surrender(self, interaction: discord.Interaction):
        """Surrender your current battle."""
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(interaction.user.id)
        
        # Check if the user is in a battle
        battle_id, other_player_id, battle_state = self._get_current_battle_for_user(user_id)
        
        if not battle_id:
            await interaction.followup.send("❌ You are not in a battle.", ephemeral=True)
            return
            
        # End the battle with the opponent as winner
        try:
            await self.battle_system.end_battle(
                battle_id,
                other_player_id,
                "Player surrendered"
            )
            
            await interaction.followup.send("✅ You have surrendered the battle.", ephemeral=True)
            
            # Send a message to the other player if they're online
            try:
                other_member = interaction.guild.get_member(int(other_player_id))
                if other_member:
                    try:
                        await other_member.send(
                            f"🏳️ {interaction.user.name} has surrendered your battle!"
                        )
                    except discord.HTTPException:
                        # Couldn't DM, try to send to battle channel
                        if hasattr(self.bot, 'battle_channel_id'):
                            battle_channel = self.bot.get_channel(self.bot.battle_channel_id)
                            if battle_channel:
                                await battle_channel.send(
                                    f"🏳️ {interaction.user.mention} has surrendered their battle against {other_member.mention}!"
                                )
            except Exception as notify_err:
                self.logger.error(f"Error notifying opponent of surrender: {notify_err}")
                
        except Exception as e:
            self.logger.error(f"Error in battle_surrender: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    def _get_current_battle_for_user(self, user_id: str) -> Tuple[Optional[str], Optional[str], Optional[BattleState]]:
        """
        Get information about a user's current battle.
        Returns (battle_id, opponent_id, battle_state) or (None, None, None) if not in battle
        """
        if not self.battle_system:
            return None, None, None
            
        # Try to find the battle ID
        for battle_id, battle_state in self.battle_system.active_battles.items():
            if not battle_state.is_active:
                continue
                
            if user_id == battle_state.attacker.id:
                return battle_id, battle_state.defender.id, battle_state
            elif user_id == battle_state.defender.id:
                return battle_id, battle_state.attacker.id, battle_state
                
        return None, None, None
    
    @app_commands.command(name="battle_history", description="View your battle history")
    async def battle_history(self, interaction: discord.Interaction):
        """View your battle history."""
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(interaction.user.id)
        
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.followup.send(
                "❌ You don't have a character! Use `/character create` first.",
                ephemeral=True
            )
            return
            
        # Get battle history
        try:
            battle_history = self.battle_system.get_player_battle_history(user_id)
            
            if not battle_history:
                await interaction.followup.send(
                    "📜 You haven't participated in any battles yet.",
                    ephemeral=True
                )
                return
                
            # Create an embed to display battle history
            embed = discord.Embed(
                title="⚔️ Your Battle History",
                description=f"Showing your last {len(battle_history)} battles",
                color=discord.Color.blue()
            )
            
            for i, battle in enumerate(battle_history, 1):
                # Get opponent name
                opponent_id = battle.attacker.id if battle.defender.id == user_id else battle.defender.id
                opponent_name = battle.attacker.name if battle.defender.id == user_id else battle.defender.name
                
                # Determine result
                if battle.winner_id == user_id:
                    result = "**Victory**"
                    result_emoji = "🏆"
                elif battle.winner_id == opponent_id:
                    result = "**Defeat**"
                    result_emoji = "💀"
                else:
                    result = "**Draw**"
                    result_emoji = "🤝"
                    
                # Format timestamp
                battle_time = battle.end_time.strftime("%Y-%m-%d %H:%M") if battle.end_time else "Unknown"
                
                # Add field for this battle
                embed.add_field(
                    name=f"{result_emoji} Battle #{i} - {battle_time}",
                    value=f"**Opponent:** {opponent_name}\n"
                         f"**Result:** {result}\n"
                         f"**Turns:** {len(battle.battle_log) if battle.battle_log else 'Unknown'}",
                    inline=True
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error in battle_history: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="admin_clear_battle", description="[Admin] Force clear a player's active battle.")
    @app_commands.describe(user="The user whose battle to clear")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_clear_battle(self, interaction: discord.Interaction, user: discord.User):
        """Admin command to clear a player's active battle."""
        await interaction.response.defer(ephemeral=True)
        
        user_id = str(user.id)
        
        # Check if the user is in a battle
        battle_id, other_player_id, battle_state = self._get_current_battle_for_user(user_id)
        
        if not battle_id:
            await interaction.followup.send(
                f"❌ {user.name} is not in a battle.",
                ephemeral=True
            )
            return
            
        # End the battle with no winner
        try:
            if hasattr(self.battle_system, 'end_battle'):
                await self.battle_system.end_battle(
                    battle_id,
                    None,  # No winner
                    "Admin forced battle clear"
                )
            elif hasattr(self.battle_system, 'end_battle_session'):
                await self.battle_system.end_battle_session(
                    battle_id,
                    None,  # No winner
                    "Admin forced battle clear"
                )
            else:
                # Fall back to removing from active battles directly
                if battle_id in self.battle_system.active_battles:
                    del self.battle_system.active_battles[battle_id]
                await self.battle_system.save_battle_state()
                
            await interaction.followup.send(
                f"✅ Cleared {user.name}'s battle with {battle_state.attacker.name if user_id == battle_state.defender.id else battle_state.defender.name}.",
                ephemeral=True
            )
            
        except Exception as e:
            self.logger.error(f"Error in admin_clear_battle: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

# Setup function to add this cog to the bot
async def setup(bot: commands.Bot):
    """Add the BattleCommands cog to the bot."""
    try:
        # Get dependencies
        battle_system = bot.services.battle_system
        character_system = bot.services.character_system
        battle_manager = bot.services.battle_manager
        
        # Register cog
        await bot.add_cog(
            BattleCommands(
                bot,
                battle_system,
                character_system,
                battle_manager
            )
        )
        logging.info("[BattleCommands] Cog loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading BattleCommands cog: {e}", exc_info=True)
        raise
