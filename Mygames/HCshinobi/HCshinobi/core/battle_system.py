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

# Imports from battle_effects
from .battle_effects import (
    StatusEffect,
    tick_status_durations,
    apply_status_effects,
    can_player_act,
    add_status_effect
)

# Imports from battle_actions
from .battle_actions import (
    resolve_basic_attack,
    resolve_jutsu_action,
    resolve_flee_action,
    resolve_defend_action,
    resolve_attack,
    get_effective_stat
)

# Data class or enum from battle_types
from .battle_types import BattleState

logger = logging.getLogger(__name__)


class BattleSystem:
    """System for managing character battles."""

    def __init__(
        self,
        character_system: CharacterSystem,
        data_dir: Optional[str] = None,
        progression_engine: Optional[Any] = None,
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
        # Set up logger first to ensure it's available everywhere
        self.logger = logging.getLogger(__name__)
        
        # Set up data directories with default if not specified
        self.base_data_dir = data_dir or "data"
        self.battles_data_dir = os.path.join(self.base_data_dir, BATTLES_SUBDIR)
        os.makedirs(self.battles_data_dir, exist_ok=True)

        self.active_battles_file = os.path.join(self.battles_data_dir, ACTIVE_BATTLES_FILENAME)
        self.battle_history_file = os.path.join(self.battles_data_dir, BATTLE_HISTORY_FILENAME)

        self.character_system = character_system
        self.progression_engine = progression_engine
        self.master_jutsu_data = master_jutsu_data or {}

        self.active_battles: Dict[str, BattleState] = {}
        self.battle_history: Dict[str, List[str]] = {}
        self.battle_tasks: Dict[str, asyncio.Task] = {}
        self._load_lock = asyncio.Lock()
        
        # Store reference to bot (will be set in ready_hook)
        self.bot = None

        self.logger.info(f"BattleSystem initialized. Data dir: {self.battles_data_dir}")

    async def _deserialize_battle_state(self, data: Dict) -> Optional[BattleState]:
        """
        Deserialize a dictionary back into a BattleState object.
        """
        try:
            # --- Reconstruct Character Objects --- #
            attacker_data = data.get('attacker')
            defender_data = data.get('defender')
            
            if not attacker_data or not defender_data:
                self.logger.error("_deserialize_battle_state: Missing attacker or defender data.")
                return None

            # Use Character.from_dict to reconstruct
            attacker = Character.from_dict(attacker_data)
            defender = Character.from_dict(defender_data)
            
            if not attacker or not defender:
                self.logger.error("_deserialize_battle_state: Failed to reconstruct Character objects.")
                return None
            # --- End Character Reconstruction --- #
                 
            # Handle last_action timestamp conversion
            last_action_str = data.get('last_action')
            last_action_dt = None
            if last_action_str:
                try:
                    last_action_dt = datetime.fromisoformat(last_action_str).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    self.logger.warning(f"_deserialize_battle_state: Could not parse last_action timestamp '{last_action_str}'.")
                    
            # Handle start_time timestamp conversion
            start_time_str = data.get('start_time')
            start_time_dt = datetime.now(timezone.utc) # Default to now if missing/invalid
            if start_time_str:
                try:
                    start_time_dt = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    self.logger.warning(f"_deserialize_battle_state: Could not parse start_time timestamp '{start_time_str}'. Using current time.")
                    
            # --- Create BattleState --- #
            state = BattleState(
                attacker=attacker,
                defender=defender,
                attacker_hp=data.get('attacker_hp', attacker.hp), # Use character HP if missing
                defender_hp=data.get('defender_hp', defender.hp),
                attacker_chakra=data.get('attacker_chakra', attacker.chakra), # Use character chakra if missing
                defender_chakra=data.get('defender_chakra', defender.chakra), # Use character chakra if missing
                current_turn_player_id=data.get('current_turn_player_id'),
                turn_number=data.get('turn_number', 1),
                battle_log=data.get('battle_log', []), # Default to empty list
                attacker_effects=data.get('attacker_effects', []), # Default to empty list
                defender_effects=data.get('defender_effects', []), # Default to empty list
                winner_id=data.get('winner_id'),
                is_active=data.get('is_active', False), # Assume inactive if missing
                start_time=start_time_dt, 
                last_action=last_action_dt, 
                end_reason=data.get('end_reason')
            )
            return state
            # --- End Create BattleState --- #
            
        except Exception as e:
            self.logger.error(f"Error deserializing battle state: {e}", exc_info=True)
            return None

    async def process_turn(
        self,
        battle_id: str,
        player_id: str,
        action: Dict[str, Any]
    ) -> Tuple[Optional[BattleState], str]:
        """
        Processes a single turn in an ongoing battle, including effects and actions.
        """
        battle = self.active_battles.get(battle_id)
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

    async def ready_hook(self):
        """Called when the bot is ready to set up systems that depend on it."""
        self.logger.info("Battle system ready hook called")
        
        # Load battle states
        await self.load_battle_state()
        self.logger.info(f"Loaded {len(self.active_battles)} active battles")
        
        # Validate battle states and clean up any problematic ones
        invalid_count = await self.validate_battle_states()
        if invalid_count > 0:
            self.logger.warning(f"Removed {invalid_count} invalid battles during validation on startup")
        
        # Load battle history
        await self._load_battle_history()
        total_history = sum(len(battles) for battles in self.battle_history.values())
        self.logger.info(f"Loaded {total_history} battle history records")

    def _add_to_battle_log(self, battle: BattleState, message: str):
        """Adds a message to the battle log."""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        # Limit log size
        if len(battle.battle_log) > 50:
            battle.battle_log = battle.battle_log[-50:]
        battle.battle_log.append(f"[{timestamp}] {message}")

    async def start_battle(self, attacker_id: str, defender_id: str) -> Optional[BattleState]:
        """
        Start a new battle.
        """
        attacker = await self.character_system.get_character(attacker_id)
        defender = await self.character_system.get_character(defender_id)

        if not attacker or not defender:
            logger.warning(
                f"Attempted to start battle, but character not found. "
                f"Att: {attacker_id}, Def: {defender_id}"
            )
            return None
        if attacker_id == defender_id:
            logger.warning(f"Attempted to start battle with self: {attacker_id}")
            return None

        p_ids = sorted([attacker_id, defender_id])
        battle_id = f"{p_ids[0]}_{p_ids[1]}"

        if battle_id in self.active_battles and self.active_battles[battle_id].is_active:
            logger.warning(f"Battle {battle_id} already active. Returning existing state.")
            return self.active_battles[battle_id]

        # Check if either player is already in another active battle
        for existing_id, state in self.active_battles.items():
            if state.is_active and (
                state.attacker.id == attacker_id
                or state.defender.id == attacker_id
                or state.attacker.id == defender_id
                or state.defender.id == defender_id
            ):
                logger.warning(
                    f"Cannot start battle {battle_id}: Player {attacker_id if (state.attacker.id == attacker_id or state.defender.id == attacker_id) else defender_id} "
                    f"is already in battle {existing_id}."
                )
                return None

        battle = BattleState(
            attacker=attacker,
            defender=defender,
            attacker_hp=attacker.hp,
            defender_hp=defender.hp,
            attacker_chakra=attacker.chakra,  # Initialize attacker chakra
            defender_chakra=defender.chakra,  # Initialize defender chakra
            current_turn_player_id=attacker_id,
            turn_number=1
        )
        self._add_to_battle_log(battle, f"Battle started: {attacker.name} vs {defender.name}.")

        # Check if the battle ended immediately
        if await self.check_battle_end(battle):
            logger.info(f"Battle {battle_id} ended immediately due to start-of-battle effects.")
            self.active_battles[battle_id] = battle
            await self.save_battle_state()
            return battle

        # For demonstration, assume first player can act
        self._add_to_battle_log(battle, f"Turn {battle.turn_number} begins. It's {attacker.name}'s turn.")

        self.active_battles[battle_id] = battle
        logger.info(f"[BattleSystem] Battle {battle_id} created and added to active_battles dict. State: {battle}")
        await self.save_battle_state()
        logger.info(f"Battle started successfully: {battle_id}. Current Turn: {battle.current_turn_player_id}")
        return battle

    async def check_battle_end(self, battle: BattleState) -> bool:
        """
        Check if battle has ended and update state if it has.
        Returns True if battle ended, False otherwise.
        """
        if not battle.is_active:
            return True

        winner_id = None
        if battle.attacker_hp <= 0:
            winner_id = battle.defender.id
        elif battle.defender_hp <= 0:
            winner_id = battle.attacker.id

        if winner_id:
            winner = battle.attacker if winner_id == battle.attacker.id else battle.defender
            loser = battle.defender if winner_id == battle.attacker.id else battle.attacker
            self._add_to_battle_log(battle, f"Battle Ended! Winner: {winner.name}")
            battle.is_active = False
            battle.winner_id = winner_id
            await self.save_battle_state()
            return True

        return False

    async def end_battle(
        self,
        battle_id: str,
        winner_id: Optional[str] = None,
        reason: str = "Battle Concluded"
    ) -> Tuple[bool, str]:
        """Ends an active battle, updates character stats, and cleans up."""
        if battle_id not in self.active_battles:
            logger.warning(f"Attempted to end non-existent battle: {battle_id}")
            return False, "Battle not found."

        battle_state = self.active_battles[battle_id]
        if not battle_state.is_active:
            logger.warning(f"Attempted to end already inactive battle: {battle_id}")
            return False, "Battle already ended."

        # Mark battle as inactive and set winner/reason
        battle_state.is_active = False
        battle_state.winner_id = winner_id
        battle_state.end_reason = reason
        battle_state.battle_log.append(f"🏁 {reason}")
        if winner_id:
            winner = battle_state.attacker if str(battle_state.attacker.id) == winner_id else battle_state.defender
            battle_state.battle_log.append(f"🏆 Winner: {winner.name}")

        self.logger.info(f"Ending battle {battle_id}. Reason: {reason}. Winner ID: {winner_id}")

        # --- Store Battle Log --- #
        if battle_state.battle_log: # Ensure there is a log to store
            self.battle_history[battle_id] = battle_state.battle_log[:]
            # Limit history size if needed
            max_history = 100 # Example limit
            if len(self.battle_history) > max_history:
                # Simple FIFO removal
                oldest_battle_id = next(iter(self.battle_history))
                del self.battle_history[oldest_battle_id]
                self.logger.info(f"Removed oldest battle log ({oldest_battle_id}) to maintain history size.")
        await self._save_battle_history() # Save history after modification
        # ------------------------ #

        # Update character wins/losses
        if winner_id:
            loser_id = str(battle_state.defender.id) if str(battle_state.attacker.id) == winner_id else str(battle_state.attacker.id)
            await self._handle_battle_end(battle_state, battle_id)
        else:
             # Handle draws or other outcomes if necessary
             pass

        # Remove from active battles *after* processing
        # Keep state temporarily if needed? For now, remove immediately.
        # Consider potential race condition if another request tries to access the ended battle
        # For simplicity, we remove it here. A short delay or different state might be safer.
        if battle_id in self.active_battles: # Check again in case of concurrent modification
            del self.active_battles[battle_id]

        return True, f"{reason}"

    def get_battle_state(self, battle_id: str) -> Optional[BattleState]:
        """Get the current state of a battle."""
        state = self.active_battles.get(battle_id)
        logger.debug(f"[BattleSystem] get_battle_state called for ID {battle_id}. State found: {state is not None}")
        if state is None:
             logger.warning(f"[BattleSystem] get_battle_state failed to find state for ID {battle_id}. Current active battles: {list(self.active_battles.keys())}")
        return state

    def get_battle_id_for_player(self, player_id: str) -> Optional[str]:
        """Find the battle ID for an active battle involving the specified player."""
        for battle_id, state in self.active_battles.items():
            if state.is_active and (str(state.attacker.id) == player_id or str(state.defender.id) == player_id):
                return battle_id
        return None
        
    def is_user_in_battle(self, user_id: str) -> bool:
        """Check if a user ID is involved in any active battle."""
        return self.get_battle_id_for_player(user_id) is not None

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
    ) -> Tuple[Optional[BattleState], str]:
        """
        Processes a player's action (attack, jutsu, etc.).
        
        Returns the updated BattleState and a message summarizing the action/outcome.
        """
        battle = self.active_battles.get(battle_id)
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
