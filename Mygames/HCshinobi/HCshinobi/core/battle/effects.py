"""
Status effects handling for battles.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Updated imports for direct participant access
from .state import BattleState, BattleParticipant
from .types import StatusEffect, BattleLogCallback

# Forward declare Character if needed for type hints in handlers
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..character import Character

logger = logging.getLogger(__name__)

# --- Effect Handler Functions (Updated to use BattleParticipant) --- #

def _handle_poison(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character # Get character from participant
    damage = -int(character.max_hp * effect.potency * effect.current_stacks)
    if damage < 0:
        current_hp = participant.current_hp
        max_hp = character.max_hp
        new_hp = max(0, min(max_hp, current_hp + damage))
        if new_hp != current_hp:
            participant.current_hp = new_hp # Modify participant directly
            add_to_battle_log(battle, f"{character.name} took {-damage} poison damage! (Stacks: {effect.current_stacks})")

def _handle_burn(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character
    damage = -int(character.max_hp * effect.potency * effect.current_stacks)
    if damage < 0:
        current_hp = participant.current_hp
        max_hp = character.max_hp
        new_hp = max(0, min(max_hp, current_hp + damage))
        if new_hp != current_hp:
            participant.current_hp = new_hp # Modify participant directly
            add_to_battle_log(battle, f"{character.name} took {-damage} burn damage! (Stacks: {effect.current_stacks})")

def _handle_regeneration(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character
    heal = int(character.max_hp * effect.potency * effect.current_stacks)
    if heal > 0:
        current_hp = participant.current_hp
        max_hp = character.max_hp
        new_hp = max(0, min(max_hp, current_hp + heal))
        if new_hp != current_hp:
            participant.current_hp = new_hp # Modify participant directly
            add_to_battle_log(battle, f"{character.name} regenerated {heal} HP! (Stacks: {effect.current_stacks})")

def _handle_chakra_drain(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character
    drain = -int(character.max_chakra * effect.potency * effect.current_stacks)
    if drain < 0:
        current_chakra = participant.current_chakra
        max_chakra = character.max_chakra
        new_chakra = max(0, min(max_chakra, current_chakra + drain))
        if new_chakra != current_chakra:
            participant.current_chakra = new_chakra # Modify participant directly
            add_to_battle_log(battle, f"{character.name}'s chakra was drained by {-drain}! (Stacks: {effect.current_stacks})")

def _handle_chakra_restore(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character
    restore = int(character.max_chakra * effect.potency * effect.current_stacks)
    if restore > 0:
        current_chakra = participant.current_chakra
        max_chakra = character.max_chakra
        new_chakra = max(0, min(max_chakra, current_chakra + restore))
        if new_chakra != current_chakra:
            participant.current_chakra = new_chakra # Modify participant directly
            add_to_battle_log(battle, f"{character.name} restored {restore} chakra! (Stacks: {effect.current_stacks})")

def _handle_stamina_fatigue(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character
    drain = -int(character.max_stamina * effect.potency * effect.current_stacks)
    if drain < 0:
        current_stamina = participant.current_stamina
        max_stamina = character.max_stamina
        new_stamina = max(0, min(max_stamina, current_stamina + drain))
        if new_stamina != current_stamina:
            participant.current_stamina = new_stamina # Modify participant directly
            add_to_battle_log(battle, f"{character.name}'s stamina was depleted by {-drain}! (Stacks: {effect.current_stacks})")

def _handle_stamina_restore(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character
    restore = int(character.max_stamina * effect.potency * effect.current_stacks)
    if restore > 0:
        current_stamina = participant.current_stamina
        max_stamina = character.max_stamina
        new_stamina = max(0, min(max_stamina, current_stamina + restore))
        if new_stamina != current_stamina:
            participant.current_stamina = new_stamina # Modify participant directly
            add_to_battle_log(battle, f"{character.name} recovered {restore} stamina! (Stacks: {effect.current_stacks})")

def _handle_amaterasu_burn(effect: StatusEffect, participant: BattleParticipant, battle: BattleState, add_to_battle_log: BattleLogCallback):
    character = participant.character
    damage = -int(character.max_hp * effect.potency)
    if damage < 0:
        current_hp = participant.current_hp
        new_hp = max(0, current_hp + damage)
        if new_hp != current_hp:
            participant.current_hp = new_hp # Modify participant directly
            add_to_battle_log(battle, "⚫ {character.name} burns from Amaterasu, taking {-damage} damage! ⚫")

# --- Effect Registry --- #
EFFECT_HANDLERS = {
    "Poison": _handle_poison,
    "Burn": _handle_burn,
    "Regeneration": _handle_regeneration,
    "Chakra Drain": _handle_chakra_drain,
    "Chakra Restore": _handle_chakra_restore,
    "Stamina Fatigue": _handle_stamina_fatigue,
    "Stamina Restore": _handle_stamina_restore,
    "Amaterasu Burn": _handle_amaterasu_burn, # Register the new handler
    # Add handlers for other effects like Stun (though Stun is checked in can_player_act)
}

def add_status_effect(
    battle: BattleState,
    target_id: str,
    effect: StatusEffect,
    add_to_battle_log: BattleLogCallback
) -> None:
    """
    Add a status effect to a character in battle.

    Args:
        battle: Current battle state
        target_id: ID of the character to affect
        effect: Status effect to add
        add_to_battle_log: Function to add messages to battle log
    """
    target = battle.attacker if target_id == battle.attacker.id else battle.defender
    if not target:
        logger.error(f"add_status_effect: Target {target_id} not found in battle.")
        return

    effects_list = target.effects

    # --- Stacking Logic --- #
    # TODO: Implement more complex stacking rules (intensity, max stacks, etc.) - IMPLEMENTED (Basic Stacking)
    existing_effect_index = -1
    for i, existing_data in enumerate(effects_list):
        if existing_data.get('name') == effect.name:
            existing_effect_index = i
            break

    if existing_effect_index != -1:
        # Effect exists, apply stacking/refresh rules
        existing_data = effects_list[existing_effect_index]
        existing_effect_obj = StatusEffect.from_dict(existing_data) # Load for easier access
        
        new_stacks = existing_effect_obj.current_stacks
        stack_limit_reached = False
        
        # Check if the incoming effect defines max_stacks
        if effect.max_stacks is not None and effect.max_stacks > 0:
            if existing_effect_obj.current_stacks < effect.max_stacks:
                new_stacks += 1 # Increment stacks
                # Potency logic could be added here (e.g., stack additively/multiplicatively)
            else:
                stack_limit_reached = True # At max stacks
        # else: Effect is not stackable based on incoming effect data
        
        # Update stored data
        existing_data['duration'] = max(existing_effect_obj.duration, effect.duration) # Refresh duration
        existing_data['potency'] = effect.potency # Overwrite potency
        existing_data['applied_at'] = datetime.now(timezone.utc).isoformat() # Update timestamp
        existing_data['stats'] = effect.stats # Update stats dictionary
        existing_data['current_stacks'] = new_stacks # Store updated stack count
        existing_data['max_stacks'] = effect.max_stacks # Ensure max_stacks is updated if definition changes

        if stack_limit_reached:
            log_msg = f"{target.character.name}'s {effect.name} effect refreshed! (Max stacks: {new_stacks})"
        elif new_stacks > existing_effect_obj.current_stacks:
            log_msg = f"{target.character.name}'s {effect.name} effect stacked! (Stacks: {new_stacks})"
        else:
             log_msg = f"{target.character.name}'s {effect.name} effect was refreshed!"
             
        add_to_battle_log(battle, log_msg)
        logger.debug(f"Refreshed/Stacked status effect '{effect.name}' on {target_id}. New duration: {existing_data['duration']}, Stacks: {new_stacks}")
    else:
        # Add new effect if it doesn't exist (starts at 1 stack)
        effects_list.append(effect.to_dict()) # to_dict now includes stack info
        add_to_battle_log(
            battle,
            f"{target.character.name} was affected by {effect.name}! {effect.description}"
        )
        logger.debug(f"Added status effect '{effect.name}' to {target_id}.")

def apply_status_effects(
    battle: BattleState,
    phase: str,
    add_to_battle_log: BattleLogCallback
) -> None:
    """
    Apply all status effects for a given phase.

    Args:
        battle: Current battle state
        phase: Phase to apply effects for ('start_turn' or 'end_turn')
        add_to_battle_log: Function to add messages to battle log
    """
    # Updated: Iterate through participants directly
    for participant in [battle.attacker, battle.defender]:
        # Get character from participant
        character = participant.character
        # Get effects list from participant
        effects_list = participant.effects

        for effect_data in effects_list[:]: # Iterate over a copy
            try:
                effect = StatusEffect.from_dict(effect_data)

                if not effect.is_active() or effect.effect_type != phase:
                    continue

                handler = EFFECT_HANDLERS.get(effect.name)
                if handler:
                    # Updated: Pass participant instead of character
                    handler(effect, participant, battle, add_to_battle_log)
                else:
                    if effect.effect_type != 'passive':
                         logger.warning(f"No handler found for triggered effect '{effect.name}' in phase '{phase}'.")

            except Exception as e:
                logger.error(f"Error applying status effect {effect_data.get('name', '?')} in phase {phase}: {e}", exc_info=True)

def tick_status_durations(
    battle: BattleState,
    add_to_battle_log: BattleLogCallback
) -> None:
    """
    Decrease duration of all status effects by 1 turn.

    Args:
        battle: Current battle state
        add_to_battle_log: Function to add messages to battle log
    """
    # Updated: Iterate through participants
    for participant in [battle.attacker, battle.defender]:
        # Get effects from participant
        effects = participant.effects
        active_effects = []
        for effect_data in effects:
            try:
                effect = StatusEffect.from_dict(effect_data)

                # Don't tick infinite duration effects
                if effect.duration == -1: # Assuming -1 for infinite
                    active_effects.append(effect_data)
                    continue

                # Tick duration
                effect.duration -= 1

                if effect.duration > 0:
                    # Update duration in the dictionary and keep it
                    effect_data['duration'] = effect.duration
                    active_effects.append(effect_data)
                else:
                    # Effect expired, log it
                    add_to_battle_log(
                        battle,
                        f"{participant.character.name}'s {effect.name} effect wore off!"
                    )
                    logger.debug(f"Status effect '{effect.name}' expired for {participant.id}.")

            except Exception as e:
                logger.error(f"Error ticking status effect {effect_data.get('name', '?')}: {e}", exc_info=True)
                # Keep the effect if ticking failed, maybe log original duration?
                active_effects.append(effect_data)

        # Update the participant's effects list
        participant.effects = active_effects

def can_player_act(
    battle: BattleState,
    player_id: str,
    add_to_battle_log: BattleLogCallback
) -> bool:
    """
    Check if a player can act this turn.

    Args:
        battle: Current battle state
        player_id: ID of the player to check
        add_to_battle_log: Function to add messages to battle log

    Returns:
        True if player can act, False otherwise
    """
    player = battle.attacker if player_id == battle.attacker.id else battle.defender
    if not player:
        logger.warning(f"can_player_act called for unknown player_id {player_id}")
        return False # Should not happen

    effects_list = player.effects
    for effect_data in effects_list:
        try:
            effect = StatusEffect.from_dict(effect_data)
            # Check for action-preventing effects (e.g., 'Stun', based on name or a flag)
            # Simple check based on name for now:
            if effect.name == "Stun" and effect.is_active():
                add_to_battle_log(
                    battle,
                    f"{player.character.name} is stunned and cannot act!"
                )
                return False
            # Add checks for other action-preventing effects (e.g., Sleep, Freeze)
            # if effect.prevents_action and effect.is_active():
            #     add_to_battle_log(battle, f"{player.character.name} is affected by {effect.name} and cannot act!")
            #     return False

        except Exception as e:
            logger.error(f"Error checking status effect {effect_data.get('name', '?')} in can_player_act: {e}", exc_info=True)

    return True # Can act if no preventing effects found 