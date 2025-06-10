"""
Module for handling the resolution of actions within the battle system.
Includes basic attacks, jutsu usage, fleeing, and calculating effective stats.
"""
import logging
import random
from typing import Dict, List, Optional, Tuple, Any

# Assuming BattleState, Character, StatusEffect are defined and imported
# Need to import necessary types - adjust paths if needed
from .character import Character 
from .battle_types import BattleState
from .battle_effects import StatusEffect, add_status_effect # Need this for applying effects from jutsu

logger = logging.getLogger(__name__)

# --- Effective Stat Calculation (Moved from BattleSystem) --- #
def get_effective_stat(battle_state: BattleState, player_id: str, base_stat_name: str) -> float:
    """Calculates the effective value of a stat considering status effects.
    
    Args:
        battle_state: The current BattleState.
        player_id: The ID of the player whose stat is being calculated.
        base_stat_name: The name of the stat attribute (e.g., 'speed').
        
    Returns:
        The effective value of the stat.
    """
    player = battle_state.attacker if player_id == battle_state.attacker.id else battle_state.defender
    effects_list = battle_state.attacker_effects if player_id == battle_state.attacker.id else battle_state.defender_effects

    base_value = getattr(player, base_stat_name, 0.0)
    if not isinstance(base_value, (int, float)):
         logger.warning(f"Base stat '{base_stat_name}' for player {player_id} is not a number: {base_value}. Defaulting to 0.")
         base_value = 0.0

    total_multiplier = 1.0
    total_flat_modifier = 0.0

    stat_mult_key = f"{base_stat_name}_mult"
    stat_add_key = f"{base_stat_name}_add"

    for effect in effects_list:
        effect_mods = effect.effects # This is the dictionary like {'defense_mult': 1.5}
        if isinstance(effect_mods, dict):
             # Apply multipliers
             if stat_mult_key in effect_mods:
                  multiplier = effect_mods[stat_mult_key]
                  if isinstance(multiplier, (int, float)):
                      total_multiplier *= multiplier
                  else:
                      logger.warning(f"Invalid multiplier value '{multiplier}' for {stat_mult_key} in effect '{effect.name}'")

             # Apply flat additions/subtractions
             if stat_add_key in effect_mods:
                  adder = effect_mods[stat_add_key]
                  if isinstance(adder, (int, float)):
                      total_flat_modifier += adder
                  else:
                      logger.warning(f"Invalid flat modifier value '{adder}' for {stat_add_key} in effect '{effect.name}'")

    # Prevent multiplier from making stat zero or negative unreasonably
    # Allow reduction, but maybe not below a certain fraction?
    total_multiplier = max(0.1, total_multiplier) # Clamp multiplier floor

    effective_value = (base_value * total_multiplier) + total_flat_modifier
    # Prevent final stats from going below a minimum threshold (e.g., 1)
    effective_value = max(1.0, effective_value)

    # Optional: Round to integer if stats are typically whole numbers?
    # effective_value = int(round(effective_value))

    logger.debug(f"Effective stat for {player.name} ({player_id}) - '{base_stat_name}': Base={base_value}, Mult={total_multiplier:.2f}, Flat={total_flat_modifier:.2f} -> Effective={effective_value:.2f}")
    return effective_value

# --- Core Attack Resolution (Based on removed _resolve_attack) --- #
def resolve_attack(
    battle_state: BattleState,
    attacker: Character, 
    defender: Character, 
    add_log_func, # Function to add logs (e.g., BattleSystem._add_to_battle_log)
    master_jutsu_data: Dict[str, Dict], 
    jutsu_name: Optional[str] = None
) -> Tuple[int, str]:
    """Resolves an attack (basic or jutsu), calculating hit/miss, crit, and damage.
    Logs the outcome to the battle log via add_log_func.
    
    Args:
        battle_state: The current BattleState.
        attacker: The attacking Character.
        defender: The defending Character.
        add_log_func: Function to add messages to the battle log.
        master_jutsu_data: Dictionary containing all loaded jutsu definitions.
        jutsu_name: The name of the jutsu being used, if any.
        
    Returns:
         Tuple[int, str]: (damage_dealt, outcome_string ['miss', 'hit', 'crit'])
    """
    # 1. Get Effective Stats relevant for the attack
    accuracy_stat = get_effective_stat(battle_state, attacker.id, 'perception') 
    evasion_stat = get_effective_stat(battle_state, defender.id, 'speed')
    crit_chance_stat = get_effective_stat(battle_state, attacker.id, 'perception') 

    # --- Determine Action Properties --- #
    base_damage = 0
    attack_stat_name = None
    defense_stat_name = None
    action_name = "Unknown Action"
    jutsu_data = None

    if jutsu_name:
        action_name = jutsu_name
        jutsu_data = master_jutsu_data.get(jutsu_name)
        if jutsu_data:
            base_damage = jutsu_data.get('base_damage', 0)
            attack_stat_name = jutsu_data.get('attack_stat', 'ninjutsu') 
            defense_stat_name = jutsu_data.get('defense_stat', 'defense') 
        else:
            # This case should ideally be caught before calling resolve_attack
            logger.error(f"resolve_attack: Jutsu data not found for '{jutsu_name}'!")
            add_log_func(battle_state, f"{attacker.name} tries to use {action_name}, but fails to recall it!")
            return 0, 'miss' 
    else: # Basic Attack
        action_name = "Basic Attack"
        base_damage = 10 # Base damage for basic attack (or retrieve from constants/config)
        attack_stat_name = 'taijutsu'
        defense_stat_name = 'defense'
    # --- End Determine Action Properties --- #
            
    # Ensure we have stats to work with if the action involves them
    effective_attack_power = 1.0
    effective_defense_power = 1.0
    if attack_stat_name:
        effective_attack_power = get_effective_stat(battle_state, attacker.id, attack_stat_name)
    if defense_stat_name:
        effective_defense_power = get_effective_stat(battle_state, defender.id, defense_stat_name)
        
    # Avoid division by zero
    effective_attack_power = max(1.0, effective_attack_power)
    effective_defense_power = max(1.0, effective_defense_power)

    # --- Hit/Miss Calculation --- #
    # Simple hit chance formula (example)
    base_hit_chance = 90.0 
    hit_modifier = (accuracy_stat - evasion_stat) * 0.25 # Example: 1 point diff = 0.25% change
    hit_chance_pct = max(10.0, min(99.0, base_hit_chance + hit_modifier)) # Clamp between 10% and 99%

    hit_roll = random.uniform(0, 100)
    
    logger.debug(f"Resolve Attack: {action_name}. Hit Chance: {hit_chance_pct:.2f}%, Roll: {hit_roll:.2f}")
    
    if hit_roll > hit_chance_pct:
        add_log_func(battle_state, f"{attacker.name}'s {action_name} misses {defender.name}!")
        return 0, 'miss'
            
    # --- Damage Calculation (Only if base_damage > 0) --- #
    final_damage = 0
    outcome = 'hit' # Default outcome if hit
    if base_damage > 0:
        # Crit Calculation
        # Simple crit chance based on stat (e.g., 1 perception = 0.1% crit chance? Needs tuning) 
        base_crit_chance = 5.0 # Base % crit chance
        crit_modifier = crit_chance_stat * 0.1 # Example: 10 perception = +1% crit
        final_crit_chance = max(1.0, min(50.0, base_crit_chance + crit_modifier))
        crit_roll = random.uniform(0, 100)
        is_crit = False
        crit_multiplier = 1.0 # No crit
        
        logger.debug(f" Crit Chance: {final_crit_chance:.2f}%, Roll: {crit_roll:.2f}")
        if crit_roll < final_crit_chance:
            crit_multiplier = 1.5 # Actual damage multiplier for crit
            is_crit = True

        # Damage Calculation (Using assumed utility function)
        # Example damage formula
        damage_multiplier = effective_attack_power / effective_defense_power
        random_factor = random.uniform(0.85, 1.15)
        raw_damage = base_damage * damage_multiplier * random_factor * crit_multiplier
        final_damage = int(raw_damage)

        final_damage = max(1, final_damage) # Ensure at least 1 damage on hit
        
        crit_text = " CRITICAL HIT!" if is_crit else ""
        add_log_func(battle_state, f"{attacker.name}'s {action_name} hits {defender.name} for {final_damage} damage!{crit_text}")
        outcome = 'crit' if is_crit else 'hit'
        logger.debug(f" Attack Hit! Damage Dealt: {final_damage}{crit_text}")
    elif base_damage <= 0 and jutsu_name: # Non-damaging jutsu
         add_log_func(battle_state, f"{attacker.name} uses {action_name}.")
         outcome = 'hit' # Still counts as a successful action
    else: # Basic attack somehow has 0 base damage? Log warning.
         logger.warning(f"{action_name} from {attacker.name} hit but base_damage was zero.")
         add_log_func(battle_state, f"{attacker.name}'s {action_name} hits {defender.name}, but deals no damage.")
         outcome = 'hit'
             
    return final_damage, outcome

# --- Individual Action Resolvers (Based on removed BattleSystem methods) --- #

def resolve_basic_attack(
    battle_state: BattleState, 
    attacker: Character, 
    defender: Character, 
    add_log_func, 
    master_jutsu_data: Dict[str, Dict] # Pass this even if unused, for consistency with resolve_attack
) -> bool:
    """Resolves a basic attack, applying damage if it hits.
    
    Args:
        battle_state: The current BattleState (will be modified with damage).
        attacker: The attacking Character.
        defender: The defending Character.
        add_log_func: Function to log messages.
        master_jutsu_data: Master jutsu dictionary (unused here but kept for signature).
        
    Returns:
        True if the attack hit, False otherwise.
    """
    damage_dealt, outcome = resolve_attack(
        battle_state, attacker, defender, add_log_func, master_jutsu_data, jutsu_name=None
    )
    
    if outcome != 'miss':
        # Apply damage to the BattleState
        if defender.id == battle_state.defender.id:
            battle_state.defender_hp = max(0, battle_state.defender_hp - damage_dealt)
        else: # Attacker is being attacked (e.g., self-damage, confusion?) - unlikely for basic attack
            battle_state.attacker_hp = max(0, battle_state.attacker_hp - damage_dealt)
        return True
    else:
        return False

def resolve_jutsu_action(
    battle_state: BattleState, 
    attacker: Character, 
    defender: Character, 
    jutsu_name: str, 
    add_log_func,
    master_jutsu_data: Dict[str, Dict]
) -> bool:
    """Resolves a jutsu action, including validation, cost, damage, and effects.
    
    Args:
        battle_state: The current BattleState (will be modified).
        attacker: The attacking Character (will be modified for cost).
        defender: The defending Character.
        jutsu_name: The name of the jutsu being used.
        add_log_func: Function to log messages.
        master_jutsu_data: Dictionary containing all loaded jutsu definitions.
        
    Returns:
        True if the jutsu action was successfully initiated (cost paid, exists), 
        False if validation/cost fails early. Note: A 'miss' still counts as successful initiation.
    """
    logger.debug(f"resolve_jutsu_action: {attacker.name} attempts {jutsu_name}")
    
    # --- Jutsu Validation & Cost --- #
    jutsu_data = master_jutsu_data.get(jutsu_name)
    if not jutsu_data:
        logger.warning(f"Player {attacker.name} tried unknown jutsu '{jutsu_name}'.")
        add_log_func(battle_state, f"{attacker.name} tries to use {jutsu_name}, but it doesn't exist!")
        return False # Failed action

    if not hasattr(attacker, 'jutsu') or jutsu_name not in attacker.jutsu:
         logger.warning(f"Player {attacker.name} attempted unlearned jutsu '{jutsu_name}'.")
         add_log_func(battle_state, f"{attacker.name} hasn't learned {jutsu_name} yet!")
         return False # Failed action
         
    cost_type = jutsu_data.get('cost_type')
    cost_amount = jutsu_data.get('cost_amount', 0)
    
    # Check and deduct cost directly on the Character object
    can_afford = False
    current_resource_val = 0
    if cost_type and hasattr(attacker, cost_type):
        current_resource_val = getattr(attacker, cost_type)
        if current_resource_val >= cost_amount:
            can_afford = True
            setattr(attacker, cost_type, current_resource_val - cost_amount) # Deduct cost
            
            # Update the battle state chakra values
            if cost_type == 'chakra':
                if attacker.id == battle_state.attacker.id:
                    battle_state.attacker_chakra = max(0, battle_state.attacker_chakra - cost_amount)
                else:
                    battle_state.defender_chakra = max(0, battle_state.defender_chakra - cost_amount)
                    
            logger.debug(f"Deducted {cost_amount} {cost_type} from {attacker.name}. New value: {getattr(attacker, cost_type)}")
        else:
            logger.warning(f"{attacker.name} cannot afford {jutsu_name} (Needs {cost_amount} {cost_type}, has {current_resource_val}).")
            add_log_func(battle_state, f"{attacker.name} doesn't have enough {cost_type} ({current_resource_val}) to use {jutsu_name}!")
            return False # Failed action
    elif not cost_type or cost_amount == 0:
         can_afford = True # No cost
    else: # Cost type defined but not found on character?
         logger.error(f"Invalid cost_type '{cost_type}' for jutsu '{jutsu_name}' or attribute missing on {attacker.name}.")
         add_log_func(battle_state, f"{attacker.name} has an issue with the cost for {jutsu_name}!")
         return False
         
    # Log cost payment if applicable
    if cost_amount > 0:
         add_log_func(battle_state, f"{attacker.name} uses {cost_amount} {cost_type} for {jutsu_name}.")
    # --- End Jutsu Validation & Cost --- #

    # --- Resolve Damage Component --- #
    damage_dealt, outcome = resolve_attack(
        battle_state, attacker, defender, add_log_func, master_jutsu_data, jutsu_name=jutsu_name
    )
    
    if outcome != 'miss' and damage_dealt > 0:
        # Apply damage to the BattleState
        if defender.id == battle_state.defender.id:
            battle_state.defender_hp = max(0, battle_state.defender_hp - damage_dealt)
        else: # Target is attacker
            battle_state.attacker_hp = max(0, battle_state.attacker_hp - damage_dealt)
        # Log message is handled within resolve_attack
    # --- End Damage Component --- #

    # --- Apply Other Jutsu Effects --- #
    # Apply effects even if the damage component missed? Design Choice. Let's say yes for now.
    # Or apply only if outcome != 'miss'? Current code applies if cost was paid. Let's refine to apply only on hit/crit.
    if outcome != 'miss': 
        jutsu_effects = jutsu_data.get('effects', [])
        if jutsu_effects:
             logger.debug(f" Applying {len(jutsu_effects)} effects for {jutsu_name} after outcome: {outcome}")
             for effect_data in jutsu_effects:
                 target = effect_data.get('target', 'opponent') # Default target opponent
                 effect_target_id = defender.id if target == 'opponent' else attacker.id
                 
                 try:
                     # Create StatusEffect object from data dictionary
                     if all(k in effect_data for k in ('effect_name', 'effect_type', 'magnitude', 'duration')):
                         effect_to_apply = StatusEffect(
                             name=effect_data['effect_name'],
                             effect_type=effect_data['effect_type'],
                             magnitude=float(effect_data['magnitude']),
                             duration=int(effect_data['duration']),
                             source_player_id=attacker.id, 
                             target_stat=effect_data.get('target_stat'),
                             tick_timing=effect_data.get('tick_timing', 'end_turn'),
                             applied_turn=battle_state.turn_number # Use current turn from state
                         )
                         # Use the imported add_status_effect function
                         add_status_effect(battle_state, effect_target_id, effect_to_apply, add_log_func)
                     else:
                         logger.warning(f"Skipping invalid effect data in jutsu '{jutsu_name}': Missing required keys in {effect_data}")
                 except (ValueError, TypeError, KeyError) as e:
                      logger.error(f"Error creating/applying StatusEffect from data for jutsu '{jutsu_name}': {e}. Data: {effect_data}", exc_info=True)
    else:
        logger.debug(f"Skipping effects for {jutsu_name} due to outcome: {outcome}")
    # --- End Apply Other Jutsu Effects --- #
    
    # Jutsu was successfully initiated (cost paid, exists), even if it missed
    return True 

# --- Flee Action --- #
def resolve_flee_action(battle_state: BattleState, actor: Character, add_log_func) -> bool:
    """Resolves a flee attempt based on speed difference and status effects.
    
    Args:
        battle_state: The current BattleState.
        actor: The Character attempting to flee.
        add_log_func: Function to log messages.
        
    Returns:
        True if flee attempt is successful, False otherwise.
    """
    logger.debug(f"resolve_flee_action: {actor.name} attempts to flee.")
    
    # Determine opponent
    opponent = battle_state.defender if actor.id == battle_state.attacker.id else battle_state.attacker
    
    # Check for effects preventing flee (e.g., 'Bound')
    actor_effects = battle_state.attacker_effects if actor.id == battle_state.attacker.id else battle_state.defender_effects
    for effect in actor_effects:
        # Assume effects have a 'prevents_flee' boolean attribute or similar
        if getattr(effect, 'prevents_flee', False):
             add_log_func(battle_state, f"{actor.name} tries to flee, but is prevented by {effect.name}!")
             return False
             
    # Get effective speeds
    actor_speed = get_effective_stat(battle_state, actor.id, 'speed')
    opponent_speed = get_effective_stat(battle_state, opponent.id, 'speed')
    
    # Ensure speed is not zero to avoid division by zero
    actor_speed = max(1, actor_speed)
    opponent_speed = max(1, opponent_speed)
    
    # Calculate flee chance (Example formula, needs tuning)
    base_chance = 50.0 # Base % chance
    speed_ratio = actor_speed / opponent_speed
    modifier = (speed_ratio - 1.0) * 25.0 # Adjust the 25 to control sensitivity
    flee_chance_percent = max(10.0, min(95.0, base_chance + modifier)) # Clamp between 10% and 95%
    
    flee_roll = random.uniform(0, 100)
    
    logger.debug(f"Flee Attempt: {actor.name}. Actor Speed: {actor_speed:.1f}, Opponent Speed: {opponent_speed:.1f}. Chance: {flee_chance_percent:.1f}%, Roll: {flee_roll:.1f}")
    
    if flee_roll <= flee_chance_percent:
        add_log_func(battle_state, f"{actor.name} successfully fled from battle!")
        # Important: BattleSystem needs to handle the actual battle end logic when this returns True
        return True
    else:
        add_log_func(battle_state, f"{actor.name} tried to flee, but failed!")
        return False

# --- New Defend Action --- #
def resolve_defend_action(battle: 'BattleState', attacker: Character, log_func) -> bool:
    """Resolves the defend action, applying a temporary defense boost.
    
    Args:
        battle: The current BattleState.
        attacker: The Character attempting to defend.
        log_func: Function to log messages.
        
    Returns:
        True if the defend action was successfully initiated, False otherwise.
    """
    # Define the status effect for defending
    # Multipliers: 1.5 means +50% defense/resistance
    defending_effect = StatusEffect(
        name="Defending",
        description="Taking a defensive stance, increasing resilience.",
        duration=1, # Lasts until the start of the player's next turn (will be ticked down after this turn ends)
        effects={'defense_mult': 1.5, 'resistance_mult': 1.5}, # Key names match stat checks
        effect_type='buff' # Classify as buff
    )

    # Use the add_status_effect utility
    add_status_effect(battle, attacker.id, defending_effect, log_func)

    # The log function within add_status_effect should announce the effect application.
    # No need for an extra log here unless add_status_effect doesn't log adequately.

    # Defending always 'succeeds' in terms of taking the action
    return True 