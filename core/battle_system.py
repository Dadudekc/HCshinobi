"""
Battle system for managing character combat.
"""
import random
import logging
import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone

from .character import Character
from .character_system import CharacterSystem
from .progression_engine import ShinobiProgressionEngine
from .constants import BATTLES_SUBDIR, ACTIVE_BATTLES_FILENAME, BATTLE_HISTORY_FILENAME
from ..utils.file_io import load_json, save_json

# Import from new battle module
from .battle import (
    BattleState,
    deserialize_battle_state,
    StatusEffect,
    tick_status_durations,
    apply_status_effects,
    can_player_act,
    add_status_effect,
    resolve_basic_attack,
    resolve_jutsu_action,
    resolve_flee_action,
    resolve_defend_action,
    get_effective_stat,
    initialize_battle
)

# Import resolve_attack directly from its source using the correct relative path
from .battle_actions import resolve_attack

from .battle.persistence import BattlePersistence
from .battle.lifecycle import BattleLifecycle
from .battle.turn import process_turn
from .battle.types import BattleLogCallback

logger = logging.getLogger(__name__)


class BattleSystem:
    """System for managing character battles."""

    def __init__(
        self,
        character_system: CharacterSystem,
        data_dir: Optional[str] = None,
        progression_engine: Optional[ShinobiProgressionEngine] = None,
        master_jutsu_data: Optional[Dict[str, Dict]] = None
    ):
        """
        Initialize the battle system.

        Args:
            character_system: Character system for managing characters
            data_dir: Directory for storing battle-related data (optional)
            progression_engine: Instance of the progression engine (optional)
            master_jutsu_data: Dictionary containing all loaded jutsu definitions (optional)
        """
        self.persistence = BattlePersistence(data_dir)
        self.lifecycle = BattleLifecycle(
            character_system=character_system,
            persistence=self.persistence,
            progression_engine=progression_engine,
            master_jutsu_data=master_jutsu_data
        )
        # Store services reference
        self.services: Optional[ServiceContainer] = None

    async def process_turn(
        self,
        battle_id: str,
        player_id: str,
        action: Dict[str, Any]
    ) -> Tuple[Optional['BattleState'], str]:
        """
        Process a single turn in an ongoing battle.

        Args:
            battle_id: ID of the battle
            player_id: ID of the player taking the turn
            action: Action to perform

        Returns:
            Tuple of (updated battle state, result message)
        """
        # Check for services first
        if not self.services:
            logger.critical(f"BattleSystem.process_turn called before services were initialized!")
            return None, "Error: Battle system services not ready."

        battle = self.persistence.active_battles.get(battle_id)
        if not battle:
            return None, "Battle not found."

        # Process the turn
        updated_battle, message = await process_turn(
            battle,
            player_id,
            action,
            self.lifecycle._add_to_battle_log
        )

        # Handle battle end if needed
        if updated_battle and not updated_battle.is_active:
            await self.lifecycle.handle_battle_end(updated_battle, battle_id)

        return updated_battle, message

    async def ready_hook(self, bot: Any) -> None:
        """
        Hook called when the bot is ready.

        Args:
            bot: Discord bot instance
        """
        from HCshinobi.bot.services import ServiceContainer

        # Store services from bot
        if hasattr(bot, 'services') and isinstance(bot.services, ServiceContainer):
            self.services = bot.services
        else:
            logger.error("BattleSystem ready_hook: Could not get ServiceContainer from bot object!")
            # Handle error: perhaps raise an exception or log critical failure

        # Load saved state
        await self.persistence.load_active_battles()
        await self.persistence.load_battle_history()

        # Initialize lifecycle
        await self.lifecycle.ready_hook(bot)

    async def shutdown(self) -> None:
        """Clean up when shutting down."""
        await self.lifecycle.shutdown()

    def _add_to_battle_log(self, battle: BattleState, message: str) -> None:
        """Add a message to the battle log."""
        battle.battle_log.append(f"{datetime.now(timezone.utc).isoformat()} - {message}")
        self.logger.info(f"Battle {battle.id}: {message}")

    async def _handle_battle_end(self, battle: BattleState, battle_id: str) -> None:
        """Handle cleanup when a battle ends."""
        # Save battle to history
        if battle_id not in self.battle_history:
            self.battle_history[battle_id] = []
        self.battle_history[battle_id].extend(battle.battle_log)

        # Remove from active battles
        if battle_id in self.active_battles:
            del self.active_battles[battle_id]

        # Cancel any ongoing battle task
        if battle_id in self.battle_tasks:
            self.battle_tasks[battle_id].cancel()
            del self.battle_tasks[battle_id]

        # Save changes
        await self.save_active_battles()
        await self._save_battle_history()

    async def _save_battle_history(self) -> None:
        """Save battle history to disk."""
        try:
            await save_json(self.battle_history_file, self.battle_history)
            self.logger.info(f"Saved battle history with {len(self.battle_history)} battles")
        except Exception as e:
            self.logger.error(f"Error saving battle history: {e}", exc_info=True)

    async def process_turn(
        self,
        battle_id: str,
        player_id: str,
        action: Dict[str, Any]
    ) -> Tuple[Optional['BattleState'], str]:
        """
        Processes a single turn in an ongoing battle, including effects and actions.
        """
        # Check for services first
        if not self.services:
            logger.critical(f"BattleSystem.process_action called before services were initialized!")
            return None, "Error: Battle system services not ready."
            
        battle = self.persistence.active_battles.get(battle_id)
        if not battle or not battle.is_active:
            logger.warning(f"process_turn called for inactive/non-existent battle: {battle_id}")
            return None, "Battle not found or is inactive."

        if player_id != battle.current_turn_player_id:
            logger.warning(
                f"process_turn called by wrong player: {player_id} "
                f"(expected {battle.current_turn_player_id}) in battle {battle_id}"
            )
            return battle, "It's not your turn."

        logger.info(f"--- Battle {battle_id} | Turn {battle.turn_number} | Player {player_id} ---")

        # 1. Apply Start-of-Turn Effects
        apply_status_effects(battle, 'start_turn', self._add_to_battle_log)

        # 2. Check for Early End (from Start Effects)
        if battle.attacker_hp <= 0 or battle.defender_hp <= 0:
            battle.winner_id = battle.defender.id if battle.attacker_hp <= 0 else battle.attacker.id
            battle.is_active = False
            winner_name = battle.defender.name if battle.attacker_hp <= 0 else battle.attacker.name
            loser_name = battle.attacker.name if battle.attacker_hp <= 0 else battle.defender.name
            end_message = f"{loser_name} succumbed to an effect at the start of the turn! {winner_name} wins!"
            self._add_to_battle_log(battle, end_message)
            logger.info(f"Battle {battle_id} ended due to start-of-turn effects.")
            await self._handle_battle_end(battle, battle_id)
            return battle, end_message

        # 3. Check if Player Can Act (Stun, etc.)
        can_act_now = can_player_act(battle, player_id, self._add_to_battle_log)
        action_result_message = ""
        action_ended_battle = False

        # 4. Execute Action (if not stunned)
        if can_act_now:
            action_type = action.get('type', 'pass')
            logger.info(f"Player {player_id} action: {action_type} with args {action}")

            is_p1_turn = (player_id == battle.attacker.id)
            current_attacker = battle.attacker if is_p1_turn else battle.defender
            current_defender = battle.defender if is_p1_turn else battle.attacker

            action_successful = False

            if action_type == 'basic_attack':
                action_successful = resolve_basic_attack(
                    battle,
                    current_attacker,
                    current_defender,
                    self._add_to_battle_log,
                    self.master_jutsu_data
                )
                action_result_message = battle.battle_log[-1] if battle.battle_log else "Basic attack resolved."

            elif action_type == 'jutsu':
                jutsu_name = action.get('jutsu_name')
                if jutsu_name:
                    action_successful = resolve_jutsu_action(
                        battle,
                        current_attacker,
                        current_defender,
                        jutsu_name,
                        self._add_to_battle_log,
                        self.master_jutsu_data
                    )
                    action_result_message = battle.battle_log[-1] if battle.battle_log else "Jutsu resolved."
                else:
                    fail_msg = f"{current_attacker.name} attempts a jutsu but forgets the name!"
                    self._add_to_battle_log(battle, fail_msg)
                    action_result_message = fail_msg

            elif action_type == 'flee':
                flee_success = resolve_flee_action(
                    battle,
                    current_attacker,
                    self._add_to_battle_log
                )
                action_result_message = battle.battle_log[-1] if battle.battle_log else "Flee attempt resolved."
                if flee_success:
                    action_ended_battle = True
                action_successful = flee_success

            elif action_type == 'defend':
                action_successful = resolve_defend_action(
                    battle,
                    current_attacker,
                    self._add_to_battle_log
                )
                action_result_message = battle.battle_log[-1] if battle.battle_log else "Defend action resolved."

            else:  # Pass or unknown
                pass_msg = f"{current_attacker.name} passes the turn."
                self._add_to_battle_log(battle, pass_msg)
                action_result_message = pass_msg
                action_successful = True

            battle.last_action = datetime.now(timezone.utc)
            battle.update_last_action(datetime.now(timezone.utc))

            # 5. Check for Battle End (Post-Action)
            if not action_ended_battle:
                if battle.attacker_hp <= 0:
                    battle.winner_id = battle.defender.id
                    battle.is_active = False
                    action_ended_battle = True
                    self._add_to_battle_log(battle, f"{battle.defender.name} defeated {battle.attacker.name}!")
                elif battle.defender_hp <= 0:
                    battle.winner_id = battle.attacker.id
                    battle.is_active = False
                    action_ended_battle = True
                    self._add_to_battle_log(battle, f"{battle.attacker.name} defeated {battle.defender.name}!")
        else:
            # Player was stunned
            if battle.battle_log and "cannot act" in battle.battle_log[-1]:
                action_result_message = battle.battle_log[-1]
            else:
                action_result_message = f"{player_id} is stunned!"
            logger.info(f"Player {player_id} skipped action due to stun.")

        # 6. Apply End-of-Turn Effects
        if battle.is_active:
            apply_status_effects(battle, 'end_turn', self._add_to_battle_log)
            # 7. Check for Battle End after End-of-Turn Effects
            if battle.attacker_hp <= 0:
                battle.winner_id = battle.defender.id
                battle.is_active = False
                action_ended_battle = True
                self._add_to_battle_log(
                    battle,
                    f"{battle.attacker.name} succumbed to an effect at the end of the turn!"
                )
            elif battle.defender_hp <= 0:
                battle.winner_id = battle.attacker.id
                battle.is_active = False
                action_ended_battle = True
                self._add_to_battle_log(
                    battle,
                    f"{battle.defender.name} succumbed to an effect at the end of the turn!"
                )

        # 8. Tick Durations
        tick_status_durations(battle, self._add_to_battle_log)

        # 9. End or Switch
        if action_ended_battle:
            logger.info(f"Battle {battle_id} ended on turn {battle.turn_number}. Winner ID: {battle.winner_id}")
            await self._handle_battle_end(battle, battle_id)
            final_message = battle.battle_log[-1] if battle.battle_log else "Battle has ended."
            return battle, final_message
        else:
            battle.turn_number += 1
            next_player_id = battle.defender.id if player_id == battle.attacker.id else battle.attacker.id
            battle.current_turn_player_id = next_player_id
            next_player_name = (
                battle.defender.name if player_id == battle.attacker.id else battle.attacker.name
            )
            switch_message = f"Turn ends. Next turn {battle.turn_number}: {next_player_name}"
            self._add_to_battle_log(battle, switch_message)
            logger.info(f"Battle {battle_id}: Switching turn to {next_player_id} for turn {battle.turn_number}.")
            await self.save_battle_state()
            return battle, action_result_message

    async def _handle_battle_end(self, battle: BattleState, battle_id: str) -> List[str]:
        """Handles the logic after a battle concludes (XP, saving, etc.)."""
        logger.info(f"Handling end of battle: {battle_id}. Winner: {battle.winner_id}")
        progression_messages = []
        winner_id = battle.winner_id
        loser_id = None
        
        if winner_id == battle.attacker.id:
            loser_id = battle.defender.id
        elif winner_id == battle.defender.id:
            loser_id = battle.attacker.id
        # If winner_id is None (draw, flee, timeout), loser_id remains None
        
        winner = None
        loser = None

        # Load winner and loser characters if IDs exist
        if winner_id:
            winner = await self.character_system.get_character(winner_id)
        if loser_id:
            loser = await self.character_system.get_character(loser_id)

        # Update winner's stats and progression
        if winner and loser:
            winner.wins += 1
            # Add exp calculation
            base_exp_gain = 50 # Example base XP
            level_diff = loser.level - winner.level
            exp_gain = max(10, base_exp_gain + level_diff * 5)
            leveled_up = await self.progression_engine.add_experience(winner_id, exp_gain)
            if leveled_up:
                 progression_messages.append(f"Leveled up! Now Level {winner.level}.")
            progression_messages.append(f"Gained {exp_gain} EXP.")
            # Record win against rank
            loser_rank = loser.rank
            winner.wins_against_rank[loser_rank] = winner.wins_against_rank.get(loser_rank, 0) + 1
            await self.character_system.save_character(winner)
            self.logger.info(f"Winner {winner_id} stats updated. EXP Gained: {exp_gain}, Wins: {winner.wins}")

        # Update loser's stats and HANDLE PERMADEATH
        if loser:
            loser.losses += 1
            self.logger.info(f"Loser {loser_id} losses updated to: {loser.losses}")
            
            # --- PERMADEATH LOGIC --- #
            self.logger.warning(f"PERMADEATH: Character {loser.name} ({loser_id}) lost the battle and will be deleted.")
            # Delete character data
            delete_success = await self.character_system.delete_character(loser_id)
            if delete_success:
                self.logger.info(f"Character {loser_id} successfully deleted due to battle loss.")
                progression_messages.append(f" tragically lost the battle and their journey ends here...") # Append to winner messages
            else:
                self.logger.error(f"Failed to delete character {loser_id} after battle loss!")
            # Note: We don't save the loser character since they are being deleted.
            # --- END PERMADEATH LOGIC --- #
            
        elif winner_id is None: # Handle draws/timeouts (no winner/loser)
             p1 = await self.character_system.get_character(battle.attacker.id)
             p2 = await self.character_system.get_character(battle.defender.id)
             if p1:
                 p1.draws += 1
                 await self.character_system.save_character(p1)
             if p2:
                 p2.draws += 1
                 await self.character_system.save_character(p2)
             self.logger.info(f"Battle {battle_id} ended in a draw/timeout. Draw stats updated.")

        # --- Remove battle from active list --- #
        if battle_id in self.active_battles:
            del self.active_battles[battle_id]
            logger.info(f"Battle {battle_id} removed from active battles.")
        else:
             logger.warning(f"Attempted to remove battle {battle_id} from active list, but it was already gone.")
        # --- End Remove --- #

        # Save history (consider adding more details like turns, etc.)
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "player1": battle.attacker.id,
            "player2": battle.defender.id,
            "winner_id": winner_id, # Can be None for draw/timeout
            "reason": battle.battle_log[-1] if battle.battle_log else "Battle Ended" # Last log message as reason
        }
        # Assume _save_battle_history exists and handles appending to player histories
        # await self._save_battle_history(history_entry)

        # Cancel any background task for this battle
        task = self.battle_tasks.pop(battle_id, None)
        if task:
            task.cancel()
            logger.info(f"Cancelled background task for completed battle {battle_id}.")

        # Save the updated active battle states (now excluding the ended one)
        await self.save_battle_state()
        
        return progression_messages # Return messages for the winner

    async def load_battle_state(self):
        """Load battle state from file, reconstructing as BattleState objects."""
        try:
            async with self._load_lock:
                if not os.path.exists(self.active_battles_file):
                    self.logger.info(
                        f"Active battles file not found: {self.active_battles_file}. Starting with empty state."
                    )
                    self.active_battles = {}
                    return

                self.logger.debug(f"Loading battle state from {self.active_battles_file}...")
                try:
                    # Use load_json synchronously, not with await
                    try:
                        battle_data = load_json(self.active_battles_file, use_async=True) or {}
                    except TypeError:
                        battle_data = load_json(self.active_battles_file) or {}
                except json.JSONDecodeError:
                    self.logger.error(
                        f"Invalid JSON in {self.active_battles_file}. Starting with empty state."
                    )
                    self.active_battles = {}
                    return

            temp_active_battles = {}
            loaded_count = 0

            # Deserialize each battle state
            for battle_id, state_dict in battle_data.items():
                battle_obj = await self._deserialize_battle_state(state_dict)
                if battle_obj and battle_obj.is_active:
                    # Only load active battles
                    temp_active_battles[battle_id] = battle_obj
                    loaded_count += 1
                elif battle_obj and not battle_obj.is_active:
                    self.logger.debug(f"Skipping load of inactive battle {battle_id}.")

            self.active_battles = temp_active_battles
            self.logger.info(f"Loaded {loaded_count} active battles from {self.active_battles_file}.")

        except FileNotFoundError:
            self.logger.info(
                f"Active battles file not found: {self.active_battles_file}. Starting with no active battles."
            )
            self.active_battles = {}
        except Exception as e:
            self.logger.error(
                f"Error loading battle state from {self.active_battles_file}: {e}",
                exc_info=True
            )
            self.active_battles = {}

    async def validate_battle_states(self):
        """
        Validates all active battle states and removes any that are invalid or corrupted.
        Called after loading battle states to ensure the system doesn't crash due to bad data.
        """
        try:
            invalid_battles = []
            
            for battle_id, battle_state in list(self.active_battles.items()):
                is_valid = True
                errors = []
                
                # Check if attacker and defender are properly loaded
                if not hasattr(battle_state, 'attacker') or not battle_state.attacker:
                    errors.append("Missing attacker")
                    is_valid = False
                
                if not hasattr(battle_state, 'defender') or not battle_state.defender:
                    errors.append("Missing defender")
                    is_valid = False
                
                # Verify HP values are valid
                if not hasattr(battle_state, 'attacker_hp') or not isinstance(battle_state.attacker_hp, (int, float)):
                    errors.append("Invalid attacker HP")
                    is_valid = False
                
                if not hasattr(battle_state, 'defender_hp') or not isinstance(battle_state.defender_hp, (int, float)):
                    errors.append("Invalid defender HP")
                    is_valid = False
                
                # Verify chakra values are valid
                if not hasattr(battle_state, 'attacker_chakra') or not isinstance(battle_state.attacker_chakra, (int, float)):
                    errors.append("Invalid attacker chakra")
                    is_valid = False
                    
                if not hasattr(battle_state, 'defender_chakra') or not isinstance(battle_state.defender_chakra, (int, float)):
                    errors.append("Invalid defender chakra")
                    is_valid = False
                
                # Verify timestamps are valid datetime objects
                if not hasattr(battle_state, 'start_timestamp') or not isinstance(battle_state.start_timestamp, datetime.datetime):
                    errors.append("Invalid start timestamp")
                    is_valid = False
                    
                if not hasattr(battle_state, 'last_action_timestamp') or not isinstance(battle_state.last_action_timestamp, datetime.datetime):
                    errors.append("Invalid last action timestamp")
                    is_valid = False
                
                # Check if battle has been inactive for too long (over 7 days)
                try:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    max_inactive = datetime.timedelta(days=7)
                    
                    if hasattr(battle_state, 'last_action_timestamp') and isinstance(battle_state.last_action_timestamp, datetime.datetime):
                        if (now - battle_state.last_action_timestamp) > max_inactive:
                            errors.append(f"Battle inactive for over 7 days (last action: {battle_state.last_action_timestamp.isoformat()})")
                            is_valid = False
                except Exception as e:
                    self.logger.error(f"Error checking battle timestamps: {e}")
                    errors.append("Error checking battle timestamps")
                    is_valid = False
                
                # If any validation failed, mark for removal
                if not is_valid:
                    invalid_battles.append((battle_id, errors))
            
            # Remove invalid battles
            for battle_id, errors in invalid_battles:
                self.logger.warning(f"Removing invalid battle {battle_id}: {', '.join(errors)}")
                if battle_id in self.active_battles:
                    del self.active_battles[battle_id]
            
            # Log summary
            if invalid_battles:
                self.logger.warning(f"Removed {len(invalid_battles)} invalid battles during validation")
                # Save the cleaned state
                await self.save_battle_state()
            else:
                self.logger.info("All active battles passed validation")
                
            return len(invalid_battles)
        except Exception as e:
            self.logger.error(f"Error in validate_battle_states: {e}", exc_info=True)
            return 0

    async def save_battle_state(self):
        """Atomically saves the state of all active battles."""
        battles_to_save = {
            battle_id: battle.to_dict()
            for battle_id, battle in self.active_battles.items()
            if battle.is_active
        }
        try:
            success = save_json(self.active_battles_file, battles_to_save)
            if success:
                logger.info(
                    f"Saved {len(battles_to_save)} active battles to {self.active_battles_file}"
                )
            else:
                logger.error(f"Failed to save active battles to {self.active_battles_file}")
        except Exception as e:
            logger.error(f"Failed to save active battles: {e}", exc_info=True)

    async def battle_timeout_check(self) -> None:
        """
        Background task to check for battle timeouts.
        """
        logger.debug("Running periodic battle cleanup task...")
        for battle_id, battle in self.active_battles.items():
            if not battle.is_active:
                continue

            if battle.last_action:
                time_since_last_action = (
                    datetime.now(timezone.utc) - battle.last_action.replace(tzinfo=timezone.utc)
                )
                if time_since_last_action > timedelta(minutes=5):
                    logger.info(
                        f"Battle {battle_id} timed out due to inactivity ({time_since_last_action})."
                    )
                    await self.end_battle(battle_id, winner_id=None, reason="Battle Timed Out")
            else:
                time_since_start = (
                    datetime.now(timezone.utc) - battle.start_time.replace(tzinfo=timezone.utc)
                )
                if time_since_start > timedelta(minutes=10):
                    logger.warning(
                        f"Battle {battle_id} timed out shortly after start (no actions)."
                    )
                    await self.end_battle(battle_id, winner_id=None, reason="Battle Timed Out")

    async def shutdown(self):
        """
        Perform any cleanup needed for the BattleSystem.
        """
        logger.info("BattleSystem shutting down...")

    async def cleanup_timed_out_battles(self):
        """
        Checks for and ends battles that have timed out.
        """
        now = datetime.now(timezone.utc)
        timed_out_ids = []
        # If you have a config-based self.battle_timeout, use that instead
        for battle_id, state in self.active_battles.items():
            if state.is_active and (now - state.last_action) > timedelta(minutes=5):
                timed_out_ids.append(battle_id)
                logger.info(f"Battle {battle_id} timed out.")

        for battle_id in timed_out_ids:
            await self.end_battle(battle_id, winner_id=None)

    async def process_action(
        self,
        battle_id: str,
        actor_id: str,
        action_type: str,
        **kwargs
    ) -> Tuple[Optional['BattleState'], str]:
        """
        Processes a player's action (attack, jutsu, etc.).
        
        Returns the updated BattleState and a message summarizing the action/outcome.
        """
        # Check for services first
        if not self.services:
            logger.critical(f"BattleSystem.process_action called before services were initialized!")
            return None, "Error: Battle system services not ready."
            
        battle = self.persistence.active_battles.get(battle_id)
        if not battle or not battle.is_active:
            warning_msg = f"Process action failed: Battle {battle_id} not found or inactive."
            logger.warning(warning_msg)
            return None, warning_msg

        if battle.current_turn_player_id != actor_id:
            warning_msg = (
                f"Process action failed: Not player {actor_id}'s turn in battle {battle_id} "
                f"(Current: {battle.current_turn_player_id})."
            )
            logger.warning(warning_msg)
            return battle, warning_msg

        if not can_player_act(battle, actor_id, self._add_to_battle_log):
            msg = f"Player {actor_id} cannot act due to status effects."
            logger.warning(msg)
            return battle, msg

        actor = battle.attacker if actor_id == battle.attacker.id else battle.defender
        defender = battle.defender if actor_id == battle.attacker.id else battle.attacker
        action_result = ""

        if action_type == 'basic_attack':
            success = resolve_basic_attack(
                battle, actor, defender, self._add_to_battle_log, self.master_jutsu_data
            )
            action_result = battle.battle_log[-1] if battle.battle_log else "Basic attack used."
            if not success:
                action_result += " (Attack missed or had no effect.)"

        elif action_type == 'use_jutsu':
            jutsu_name = kwargs.get('jutsu_name')
            if not jutsu_name:
                error_msg = (
                    f"Process action 'use_jutsu' failed: Missing 'jutsu_name' in kwargs for battle {battle_id}."
                )
                logger.error(error_msg)
                return battle, error_msg

            # Attempt to resolve jutsu
            success = resolve_jutsu_action(
                battle,
                actor,
                defender,
                jutsu_name,
                self._add_to_battle_log,
                self.master_jutsu_data
            )
            action_result = battle.battle_log[-1] if battle.battle_log else f"Used jutsu: {jutsu_name}"
            if not success:
                action_result += " (Jutsu failed or was invalid.)"

        elif action_type == 'flee':
            fled = resolve_flee_action(battle, actor, self._add_to_battle_log)
            action_result = battle.battle_log[-1] if battle.battle_log else "Attempted to flee."
            if fled:
                logger.info(f"Battle {battle_id} ended after {actor_id} fled.")
                await self._handle_battle_end(battle, battle_id)
                return battle, action_result

        elif action_type == 'defend':
            action_successful = resolve_defend_action(
                battle,
                actor,
                self._add_to_battle_log
            )
            action_result = battle.battle_log[-1] if battle.battle_log else "Defend action resolved."

        else:
            msg = f"Unknown action_type '{action_type}' for battle {battle_id}."
            logger.warning(msg)
            return battle, msg

        battle.last_action = datetime.now(timezone.utc)

        # Check if the action ended the battle
        if battle.attacker_hp <= 0:
            battle.winner_id = battle.defender.id
            battle.is_active = False
            self._add_to_battle_log(battle, f"{battle.defender.name} defeated {battle.attacker.name}!")
            await self._handle_battle_end(battle, battle_id)
            return battle, action_result
        elif battle.defender_hp <= 0:
            battle.winner_id = battle.attacker.id
            battle.is_active = False
            self._add_to_battle_log(battle, f"{battle.attacker.name} defeated {battle.defender.name}!")
            await self._handle_battle_end(battle, battle_id)
            return battle, action_result

        # If still active, pass control to next turn
        old_turn_player = battle.current_turn_player_id
        battle.turn_number += 1
        battle.current_turn_player_id = defender.id if old_turn_player == actor.id else actor.id
        self._add_to_battle_log(battle, f"Turn ends. Next turn: Player {battle.current_turn_player_id}")
        await self.save_battle_state()

        return battle, action_result

    # --- History Load/Save --- #
    async def _load_battle_history(self):
        """Loads battle history from a file."""
        try:
            # Corrected: Call load_json synchronously
            history_data = load_json(self.battle_history_file)
            if history_data is None:
                logger.info(f"Battle history file not found or invalid: {self.battle_history_file}. Starting with empty history.")
                self.battle_history = {}
            elif isinstance(history_data, dict):
                # Optional: Validate structure if needed
                self.battle_history = history_data
                logger.info(f"Loaded {len(self.battle_history)} battle histories from {self.battle_history_file}.")
            else:
                logger.warning(f"Invalid format in {self.battle_history_file}, expected dict. Resetting history.")
                self.battle_history = {}
        except Exception as e:
            logger.error(f"Error loading battle history from {self.battle_history_file}: {e}", exc_info=True)
            self.battle_history = {}

    async def _save_battle_history(self):
        """Saves the current battle history to a file."""
        try:
            # Try with use_async=True first, then fall back to synchronous if needed
            try:
                success = save_json(self.battle_history_file, self.battle_history, use_async=True)
            except TypeError:
                success = save_json(self.battle_history_file, self.battle_history)
                
            if success:
                logger.info(f"Battle history saved successfully to {self.battle_history_file}")
            else:
                logger.error(f"Failed to save battle history to {self.battle_history_file}")
        except Exception as e:
            logger.error(f"Failed to save battle history: {e}", exc_info=True)
    # --- End History Load/Save ---

    def _calculate_exp_gain(self, battle_result: Dict[str, Any]) -> int:
        """Calculate EXP gain based on multiple factors.
        
        Factors considered:
        - Base EXP from enemy level
        - Battle difficulty (higher difficulty = more EXP)
        - Player's performance (health remaining, turns taken)
        - Enemy rarity/type
        - Random variation (±10%)
        """
        base_exp = battle_result["enemy_level"] * 10  # Base EXP from enemy level
        
        # Difficulty multiplier (1.0 to 1.5)
        difficulty_multiplier = 1.0 + (battle_result.get("difficulty", 0) * 0.1)
        
        # Performance multiplier based on health remaining (0.8 to 1.2)
        health_percentage = battle_result.get("player_health_remaining", 100) / 100
        performance_multiplier = 0.8 + (health_percentage * 0.4)
        
        # Enemy type/rarity multiplier (1.0 to 1.3)
        enemy_type = battle_result.get("enemy_type", "normal")
        rarity_multiplier = {
            "normal": 1.0,
            "elite": 1.15,
            "boss": 1.3
        }.get(enemy_type, 1.0)
        
        # Calculate final EXP with all multipliers
        final_exp = int(base_exp * difficulty_multiplier * performance_multiplier * rarity_multiplier)
        
        # Add random variation (±10%)
        variation = random.uniform(-0.1, 0.1)
        final_exp = int(final_exp * (1 + variation))
        
        # Ensure minimum EXP gain
        return max(1, final_exp)

    async def cleanup_inactive_battles(self):
        """Checks for and ends battles that have been inactive for too long.
        This should be called periodically as a background task."""
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            inactive_timeout = datetime.timedelta(hours=24)  # Battles inactive for 24 hours will be ended
            battles_to_end = []
            
            for battle_id, battle_state in self.active_battles.items():
                if not battle_state.is_active:
                    continue
                    
                # Skip battles that have just started (first turn not completed)
                if battle_state.turn_number < 1:
                    continue
                    
                last_active = battle_state.last_action_timestamp
                if (now - last_active) > inactive_timeout:
                    self.logger.warning(
                        f"Battle {battle_id} has been inactive for over 24 hours. "
                        f"Last action: {last_active.isoformat()}. Auto-ending."
                    )
                    battles_to_end.append(battle_id)
            
            # Process all inactive battles
            for battle_id in battles_to_end:
                battle_state = self.active_battles.get(battle_id)
                if not battle_state:
                    continue
                    
                # End as a tie without triggering permadeath
                attacker = battle_state.attacker
                defender = battle_state.defender
                
                self.logger.info(f"Auto-ending inactive battle between {attacker.name} and {defender.name}")
                
                # Set as inactive and update timestamps
                battle_state.is_active = False
                battle_state.end_timestamp = now
                battle_state.battle_log.append(f"Battle automatically ended due to inactivity.")
                
                # Save to history but don't update character stats
                if battle_id not in self.battle_history:
                    self.battle_history[battle_id] = []
                
                # Create history record with tie result
                history_record = {
                    "attacker_id": str(attacker.id),
                    "defender_id": str(defender.id),
                    "winner_id": None,  # None indicates a tie
                    "turns": battle_state.turn_number,
                    "timestamp": now.isoformat(),
                    "battle_log": battle_state.battle_log
                }
                
                self.battle_history[battle_id].append(history_record)
                
                # Remove from active battles
                del self.active_battles[battle_id]
                
                # Try to notify players
                try:
                    await self.notify_players_battle_timeout(attacker.id, defender.id)
                except Exception as e:
                    self.logger.error(f"Failed to notify players about battle timeout: {e}")
            
            # Save state if any battles were ended
            if battles_to_end:
                await self.save_battle_state()
                await self._save_battle_history()
                
        except Exception as e:
            self.logger.error(f"Error in cleanup_inactive_battles: {e}", exc_info=True)
    
    async def notify_players_battle_timeout(self, attacker_id, defender_id):
        """Notify players that their battle has timed out due to inactivity."""
        try:
            # This helper requires the bot instance to send DMs
            if not hasattr(self, "bot") or self.bot is None:
                self.logger.warning("Cannot notify players: bot instance not available")
                return
                
            message = (
                "Your battle has been automatically ended due to inactivity (no actions for 24+ hours).\n"
                "The battle has been recorded as a tie with no penalties applied."
            )
            
            for player_id in [attacker_id, defender_id]:
                try:
                    user = await self.bot.fetch_user(player_id)
                    if user:
                        dm_channel = await user.create_dm()
                        await dm_channel.send(message)
                except Exception as e:
                    self.logger.error(f"Failed to notify player {player_id} about battle timeout: {e}")
        except Exception as e:
            self.logger.error(f"Error in notify_players_battle_timeout: {e}", exc_info=True)

    async def create_battle(
        self,
        attacker: Character,
        defender: Character,
        is_duel: bool = False # Parameter unused for now, but kept for potential future use
    ) -> str:
        """
        Initializes and starts a new battle between two characters.

        Args:
            attacker: The attacking character.
            defender: The defending character.
            is_duel: Whether the battle is a duel (currently unused).

        Returns:
            The ID of the newly created battle.

        Raises:
            Exception: If battle initialization fails.
        """
        logger.info(f"Attempting to create battle between {attacker.name} ({attacker.id}) and {defender.name} ({defender.id})")
        try:
            battle_id, battle_state = await initialize_battle(
                attacker=attacker,
                defender=defender,
                persistence=self.persistence,
                add_to_battle_log=self._add_to_battle_log
            )
            logger.info(f"Battle {battle_id} initialized successfully.")
            # The battle state should already be added to persistence by initialize_battle
            return battle_id
        except Exception as e:
            logger.exception(f"Failed to initialize battle between {attacker.id} and {defender.id}")
            raise Exception(f"Could not start battle: {e}") from e
