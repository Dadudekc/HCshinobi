"""
Battle turn processing logic.
"""
import logging
from typing import Dict, Optional, Tuple, Any, TYPE_CHECKING
from datetime import datetime, timezone, timedelta
from enum import Enum
import math
from HCshinobi.bot.services import ServiceContainer
from ...utils.ollama_client import generate_ollama_response

class TurnPhase(Enum):
    """Battle turn phases."""
    START = "start"
    ACTION = "action"
    END = "end"

class TurnState:
    """Represents the current state of a turn."""
    def __init__(self, phase: TurnPhase = TurnPhase.START):
        self.phase = phase
        self.action_resolved = False
        self.effects_applied = False

from .state import BattleState, BattleParticipant
from .effects import (
    apply_status_effects,
    can_player_act,
    tick_status_durations
)
from .actions import (
    resolve_basic_attack,
    resolve_jutsu_action,
    resolve_flee_action,
    resolve_defend_action,
)
from ..character import Character
from ..character_system import CharacterSystem

if TYPE_CHECKING:
    from ..battle_system import BattleSystem

logger = logging.getLogger(__name__)

async def process_turn(
    battle: BattleState,
    player_id: str,
    action: Dict[str, Any],
    add_to_battle_log: callable,
    services: ServiceContainer
) -> Tuple[Optional[BattleState], str]:
    """
    Process a single turn in an ongoing battle.

    Args:
        battle: Current battle state
        player_id: ID of the player taking the turn
        action: Action to perform
        add_to_battle_log: Function to add messages to battle log
        services: ServiceContainer for passing services

    Returns:
        Tuple of (updated battle state, result message)
    """
    if not battle.is_active:
        logger.warning(f"process_turn called for inactive battle")
        return None, "Battle is not active."

    if player_id != battle.current_turn_player_id:
        logger.warning(
            f"process_turn called by wrong player: {player_id} "
            f"(expected {battle.current_turn_player_id})"
        )
        return battle, "It's not your turn."

    logger.info(f"--- Battle {battle.id} | Turn {battle.turn_number} | Player {player_id} ---")

    # 1. Apply Start-of-Turn Effects
    apply_status_effects(battle, 'start_turn', add_to_battle_log)

    # 2. Check for Early End (from Start Effects)
    if battle.attacker_hp <= 0 or battle.defender_hp <= 0:
        battle.winner_id = battle.defender.id if battle.attacker_hp <= 0 else battle.attacker.id
        battle.is_active = False
        winner_name = battle.defender.name if battle.attacker_hp <= 0 else battle.attacker.name
        loser_name = battle.attacker.name if battle.attacker_hp <= 0 else battle.defender.name
        end_message = f"{loser_name} succumbed to an effect at the start of the turn! {winner_name} wins!"
        add_to_battle_log(battle, end_message)
        logger.info(f"Battle {battle.id} ended due to start-of-turn effects.")
        return battle, end_message

    # 3. Check if Player Can Act (Stun, etc.)
    can_act_now = can_player_act(battle, player_id, add_to_battle_log)
    action_result_message = ""
    action_ended_battle = False
    narrative_context = None

    # 4. Execute Action (if not stunned)
    if can_act_now:
        action_type = action.get('type', 'pass')
        logger.info(f"Player {player_id} action: {action_type} with args {action}")

        action_resolution_result: Optional[Dict] = None

        if action_type == 'attack':
            action_resolution_result = resolve_basic_attack(battle, player_id, add_to_battle_log)
            if battle.attacker_hp <= 0 or battle.defender_hp <= 0:
                action_ended_battle = True
        elif action_type == 'jutsu':
            jutsu_id = action.get('jutsu_id')
            if jutsu_id:
                action_resolution_result = resolve_jutsu_action(
                    battle, player_id, jutsu_id, add_to_battle_log, services=services
                )
            else:
                action_result_message = "No Jutsu ID provided."
                logger.warning(f"Jutsu action by {player_id} missing jutsu_id.")
                
            if action_resolution_result and (battle.attacker_hp <= 0 or battle.defender_hp <= 0):
                action_ended_battle = True
        elif action_type == 'item':
            item_id = action.get('item_id')
            target_id = action.get('target_id')
            if item_id:
                action_result_message, success = resolve_item_action(
                    battle, player_id, item_id, target_id, add_to_battle_log, services
                )
            else:
                action_result_message = "No item specified."
                logger.warning(f"Item action requested by {player_id} without item_id.")
        elif action_type == 'flee':
            action_result_message, success = resolve_flee_action(battle, player_id, add_to_battle_log)
            if success:
                action_ended_battle = True
        elif action_type == 'defend':
            action_result_message = resolve_defend_action(battle, player_id, add_to_battle_log)
        else:
            action_result_message = "Invalid action type or passed turn."
            logger.warning(f"Invalid action type or pass: {action_type}")
            
        # --- Process Action Result & Generate Narrative ---
        if action_resolution_result:
            action_result_message = action_resolution_result.get("message", "Action resolved with no message.")
            narrative_context = action_resolution_result.get("narrative_context")
        
        # Log the factual message IF narrative generation is skipped/fails
        # Logging is now handled after potential narrative generation
        # if action_result_message and not narrative_context: # Only log if no narrative planned
        #    add_to_battle_log(battle, action_result_message)

    # --- Narrative Generation (If context available) --- #
    final_log_message = action_result_message # Default to factual message
    if narrative_context:
        prompt = ""
        # Build prompt based on context type
        if narrative_context.get("type") == "basic_attack":
             attacker = narrative_context.get("attacker", {})
             defender = narrative_context.get("defender", {})
             outcome = narrative_context.get("outcome", {})
             prompt = (
                 f"You are a battle narrator for a Naruto-themed game. Describe the following action vividly and concisely (1-2 sentences). Respond ONLY with JSON containing a 'narrative' key.\n\n"
                 f"Context:\n"
                 f"Attacker: {attacker.get('name', '?')} (HP: {attacker.get('hp', '?')}/{attacker.get('max_hp', '?')})\n"
                 f"Defender: {defender.get('name', '?')} (HP: {defender.get('hp', '?')}/{defender.get('max_hp', '?')})\n"
                 f"Action: Basic Attack\n"
                 f"Outcome: {'HIT' if outcome.get('hit') else 'MISS'}. Deals {outcome.get('damage', 0)} damage. Crit: {outcome.get('is_crit', False)}. Defended: {outcome.get('defended', False)}.\n\n"
                 f"Example JSON response:\n"
                 f'{{ "narrative": "{attacker.get("name", "?")} lunges forward, striking {defender.get("name", "?")} with a powerful blow!" }}'
             )
        elif narrative_context.get("type") == "jutsu":
            caster = narrative_context.get("caster", {})
            target = narrative_context.get("target", {})
            jutsu = narrative_context.get("jutsu", {})
            outcome = narrative_context.get("outcome", {})
            outcome_str_parts = []
            if outcome.get("hit"):
                 outcome_str_parts.append(f"HIT. Deals {outcome.get('damage', 0)} damage.")
                 if outcome.get("is_crit"): outcome_str_parts.append("(Critical Hit!)")
                 if outcome.get("elemental_effect"): outcome_str_parts.append(outcome["elemental_effect"])
                 if outcome.get("defended"): outcome_str_parts.append("(Defended)")
                 if outcome.get("applied_effects"): outcome_str_parts.append(f"Applied: {', '.join(outcome['applied_effects']) if outcome['applied_effects'] else 'None'}.")
            else:
                 outcome_str_parts.append("MISS.")
            outcome_str = " ".join(outcome_str_parts)
            
            prompt = (
                f"You are a battle narrator for a Naruto-themed game. Describe the following action vividly and concisely (1-2 sentences). Respond ONLY with JSON containing a 'narrative' key.\n\n"
                f"Context:\n"
                f"Caster: {caster.get('name', '?')} (HP: {caster.get('hp', '?')}/{caster.get('max_hp', '?')})\n"
                f"Target: {target.get('name', '?')} (HP: {target.get('hp', '?')}/{target.get('max_hp', '?')})\n"
                f"Action: Uses Jutsu '{jutsu.get('name', '?')}' (Element: {jutsu.get('element')}, Type: {jutsu.get('type')})\n"
                f"Outcome: {outcome_str}\n\n"
                f"Example JSON response:\n"
                f'{{ "narrative": "{caster.get("name", "?")} channels {jutsu.get("element") or "chakra"}, unleashing {jutsu.get("name", "?")}! {target.get("name", "?")} is struck!" }}'
            )
        # Add prompts for other action types here if needed

        if prompt:
            narrative = None
            try:
                # Make the await call here in the async process_turn function
                narrative = await generate_ollama_response(prompt)
                if narrative:
                     final_log_message = f"{narrative}\n{action_result_message}" # Prepend narrative
                else:
                     logger.warning("Ollama generation returned None or empty string.")
            except Exception as e:
                logger.error(f"Ollama narrative generation failed during process_turn: {e}", exc_info=False)
                # Fallback to factual message if Ollama fails
                final_log_message = action_result_message
        else:
             # No context or unknown type, use factual message
             final_log_message = action_result_message 
             
    # --- Log Final Message --- #
    if final_log_message:
        # Pass the final combined message (or original factual one) to the logging function
        add_to_battle_log(battle, final_log_message)

    # --- Post-Action Processing --- #

    # 5. Apply End-of-Turn Effects
    apply_status_effects(battle, 'end_turn', add_to_battle_log)

    # 6. Check for End (from End Effects or Action)
    if battle.attacker_hp <= 0 or battle.defender_hp <= 0 or action_ended_battle:
        if not battle.winner_id:  # Only set if not already set
            battle.winner_id = battle.defender.id if battle.attacker_hp <= 0 else battle.attacker.id
        battle.is_active = False
        winner_name = battle.defender.name if battle.attacker_hp <= 0 else battle.attacker.name
        loser_name = battle.attacker.name if battle.attacker_hp <= 0 else battle.defender.name
        end_message = f"{loser_name} has been defeated! {winner_name} wins!"
        add_to_battle_log(battle, end_message)
        logger.info(f"Battle {battle.id} ended.")
        return battle, f"{action_result_message}\n{end_message}"

    # 7. Update Turn State
    battle.turn_number += 1
    battle.current_turn_player_id = battle.defender.id if player_id == battle.attacker.id else battle.attacker.id
    battle.last_action = datetime.now(timezone.utc)

    # 8. Tick Status Effect Durations
    tick_status_durations(battle, add_to_battle_log)

    return battle, action_result_message 