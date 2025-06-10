"""
Battle actions resolution logic.
"""
import logging
import random
import asyncio
from typing import Dict, Optional, Tuple, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum, auto

from ..character import Character
from ..progression_engine import ShinobiProgressionEngine
from .state import BattleState, BattleParticipant
from .effects import add_status_effect
# from HCshinobi.bot.services import ServiceContainer # Remove direct import
from HCshinobi.core.item_manager import ItemManager
from HCshinobi.core.constants import ELEMENTAL_CHART
from HCshinobi.utils.ollama_client import generate_ollama_response

# Forward reference for type hinting if needed inside functions
if TYPE_CHECKING:
    from HCshinobi.bot.services import ServiceContainer # Keep TYPE_CHECKING import (adjusted path)

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Types of battle actions."""
    BASIC_ATTACK = auto()
    JUTSU = auto()
    ITEM = auto()
    FLEE = auto()
    DEFEND = auto()

@dataclass
class BattleAction:
    """Base class for battle actions."""
    type: ActionType
    user_id: str
    target_id: Optional[str] = None
    
    def resolve(self, battle: BattleState, add_to_battle_log: callable) -> Tuple[str, Any]:
        """Resolve the action."""
        raise NotImplementedError

@dataclass
class BasicAttack(BattleAction):
    """Basic attack action."""
    def __init__(self, user_id: str, target_id: str):
        super().__init__(ActionType.BASIC_ATTACK, user_id, target_id)
    
    def resolve(self, battle: BattleState, add_to_battle_log: callable) -> Tuple[str, int]:
        return resolve_basic_attack(battle, self.user_id, add_to_battle_log)

@dataclass
class JutsuAction(BattleAction):
    """Jutsu action."""
    type: ActionType = field(default=ActionType.JUTSU)
    user_id: str = field(default="")
    target_id: Optional[str] = field(default=None)
    jutsu_id: str = field(default="")
    
    def __init__(self, user_id: str, target_id: str, jutsu_id: str):
        self.type = ActionType.JUTSU
        self.user_id = user_id
        self.target_id = target_id
        self.jutsu_id = jutsu_id
    
    def resolve(self, battle: BattleState, add_to_battle_log: callable, services: 'ServiceContainer') -> Tuple[str, int]:
        return resolve_jutsu_action(battle, self.user_id, self.jutsu_id, add_to_battle_log, services)

@dataclass
class ItemAction(BattleAction):
    """Item action."""
    type: ActionType = field(default=ActionType.ITEM)
    user_id: str = field(default="")
    target_id: Optional[str] = field(default=None)
    item_id: str = field(default="")
    
    def __init__(self, user_id: str, target_id: str, item_id: str):
        self.type = ActionType.ITEM
        self.user_id = user_id
        self.target_id = target_id
        self.item_id = item_id
    
    def resolve(self, battle: BattleState, add_to_battle_log: callable, services: 'ServiceContainer') -> Tuple[str, bool]:
        # --- Item Resolution Logic --- #
        user = battle.get_player(self.user_id)
        if not user:
            return "Error: User not found in battle.", False

        # --- Get Services --- #
        # Services are now passed directly
        item_manager: ItemManager = services.item_manager
        if not item_manager:
            logger.critical("Cannot resolve item action: Required services missing.")
            return "Error: Core systems unavailable for item use.", False

        # --- Get Item Definition --- #
        item_def = item_manager.get_item_definition(self.item_id)
        if not item_def:
            # Check if it was a placeholder item from previous implementation
            placeholder_ids = {"basic_healing_salve", "smoke_bomb", "flash_bomb", "explosive_tag", "soldier_pill", "food_rations"}
            if self.item_id in placeholder_ids:
                 logger.warning(f"Attempted to use placeholder item ID '{self.item_id}' after ItemManager integration.")
                 return f"Item '{self.item_id}' definition missing.", False
            else:
                 return f"Item '{self.item_id}' not found.", False

        item_name = item_def.get("name", self.item_id)

        # --- Check Inventory --- #
        # Assuming character object inventory is Dict[str, int]
        if user.id == battle.attacker.id:
            char_obj = battle.attacker 
        else:
            char_obj = battle.defender

        # Check if character has the item and quantity > 0
        if not hasattr(char_obj, 'inventory') or not isinstance(char_obj.inventory, dict) or char_obj.inventory.get(self.item_id, 0) <= 0:
            return f"You do not have any {item_name}.", False

        # --- Consume Item --- #
        try:
            # Decrement item count
            char_obj.inventory[self.item_id] -= 1
            # Remove if count reaches 0
            if char_obj.inventory[self.item_id] <= 0:
                del char_obj.inventory[self.item_id]
                
            # Schedule the character save asynchronously
            asyncio.create_task(character_system.save_character(char_obj))
            logger.info(f"Consumed item '{self.item_id}' from {user.name}'s inventory. Save scheduled.")
        except KeyError: # Should not happen due to check above, but handle defensively
            logger.error(f"Item '{self.item_id}' key error during consumption for {user.name}.")
            return f"Error consuming {item_name}.", False
        except Exception as e:
             logger.error(f"Error updating inventory or scheduling save: {e}")
             return f"Error consuming {item_name}.", False

        # --- Apply Effect --- #
        effect = item_def.get("effect")
        if not effect or not isinstance(effect, dict):
            # Add log before returning
            add_to_battle_log(battle, f"{user.name} used {item_name}, but it had no defined effect.")
            return f"{item_name} used, but it had no defined effect.", True # Consumed but no effect

        effect_type = effect.get("type")
        
        # --- Determine Target --- #
        # Default to user if target_id is not provided or matches user_id
        if not self.target_id or self.target_id == self.user_id:
            target = user 
        else: # Otherwise, target is specified by target_id (should be opponent in 1v1)
            target = battle.get_player(self.target_id)
            
        if not target: # Check if target resolution failed
            logger.error(f"ItemAction: Could not resolve target with id {self.target_id} for user {self.user_id}")
            return f"Error: Invalid target specified for {item_name}.", False

        # Use opponent specifically if needed for logs or logic
        opponent = battle.get_opponent(self.user_id)

        message = f"{user.name} used {item_name}!"
        success = True

        try:
            # --- Apply Specific Effects --- #
            if effect_type == "heal_hp": # Simplified from heal_hp_self / heal_hp_target
                amount = effect.get("amount", 0)
                target_current_hp = battle.get_hp(target.id)
                target_max_hp = getattr(target, 'max_hp', target_current_hp) # Get max_hp
                new_hp = min(target_max_hp, target_current_hp + amount)
                battle.set_hp(target.id, new_hp)
                healed_amount = new_hp - target_current_hp
                if target.id == user.id:
                    message += f" Restored {healed_amount} HP." 
                else:
                    message += f" Restored {healed_amount} HP for {target.name}."
            
            # TODO: Add similar logic for restore_chakra - REMOVED TODO (Implemented)
            elif effect_type == "restore_chakra": 
                amount = effect.get("amount", 0)
                target_current_chakra = battle.get_chakra(target.id)
                target_max_chakra = getattr(target, 'max_chakra', target_current_chakra)
                new_chakra = min(target_max_chakra, target_current_chakra + amount)
                battle.set_chakra(target.id, new_chakra)
                restored_amount = new_chakra - target_current_chakra
                if target.id == user.id:
                    message += f" Restored {restored_amount} Chakra." 
                else:
                    message += f" Restored {restored_amount} Chakra for {target.name}."

            # TODO: Add similar logic for restore_stamina - REMOVED TODO (Implemented)
            elif effect_type == "restore_stamina": 
                amount = effect.get("amount", 0)
                target_current_stamina = battle.get_stamina(target.id)
                target_max_stamina = getattr(target, 'max_stamina', target_current_stamina)
                new_stamina = min(target_max_stamina, target_current_stamina + amount)
                battle.set_stamina(target.id, new_stamina)
                restored_amount = new_stamina - target_current_stamina
                if target.id == user.id:
                    message += f" Restored {restored_amount} Stamina." 
                else:
                    message += f" Restored {restored_amount} Stamina for {target.name}."
            
            elif effect_type == "damage": # Simplified from damage_target
                if target.id == user.id: # Prevent self-damage from items intended for opponent
                    message += " Cannot target self with this item."
                    success = False
                else:
                    amount = effect.get("amount", 0)
                    # Apply damage calculation (can enhance later with stats/defense)
                    target_def = get_effective_stat(battle, target.id, 'defense')
                    target_effects_list = battle.defender_effects if target.id == battle.defender.id else battle.attacker_effects
                    # Using amount directly as attacker_str for simplicity now
                    damage_dealt = calculate_damage(amount, target_def, target_effects_list)
                    
                    target_current_hp = battle.get_hp(target.id)
                    battle.set_hp(target.id, max(0, target_current_hp - damage_dealt))
                    message += f" Dealt {damage_dealt} damage to {target.name}."
                    if target_effects_list and 'Defense Stance' in target_effects_list and target_effects_list['Defense Stance'].is_active():
                         message += " (Defended)"

            elif effect_type == "apply_status": # Simplified from apply_status_self / apply_status_target
                status_effect = StatusEffect(
                    name=effect.get("status", "Unknown Effect"),
                    duration=effect.get("duration", 1),
                    potency=effect.get("potency", 1.0),
                    # Read timing from effect data, default to passive
                    effect_type=effect.get("effect_timing", "passive"), 
                    description=f"Effect from {item_name}",
                    stats=effect.get("stats", {}) 
                )
                add_status_effect(battle, target.id, status_effect, add_to_battle_log)
                if target.id == user.id:
                     message += f" Gained {status_effect.name}."
                else:
                     message += f" Inflicted {target.name} with {status_effect.name}."
            else:
                 message += " But it had no recognizable effect."
                 success = False # Or True if consuming is the main success factor
                 
            add_to_battle_log(battle, message)    
            return message, success

        except Exception as e:
            logger.error(f"Error applying item effect for {self.item_id}: {e}", exc_info=True)
            add_to_battle_log(battle, f"{user.name} used {item_name}, but an error occurred applying the effect.")
            return f"Error applying effect for {item_name}.", False # Consumed, but effect failed

@dataclass
class FleeAction(BattleAction):
    """Flee action."""
    def __init__(self, user_id: str):
        super().__init__(ActionType.FLEE, user_id)
    
    def resolve(self, battle: BattleState, add_to_battle_log: callable) -> Tuple[str, bool]:
        return resolve_flee_action(battle, self.user_id, add_to_battle_log)

def get_effective_stat(battle: BattleState, character_id: str, stat_name: str) -> int:
    """
    Get a character's effective stat value, accounting for status effects.
    Args:
        battle: The current BattleState.
        character_id: The ID of the character whose stat to calculate.
        stat_name: Name of the base stat to get (e.g., 'strength', 'defense').
    Returns:
        Effective stat value after applying status effect modifications.
    """
    character = battle.get_player(character_id)
    if not character:
        logger.error(f"get_effective_stat: Character not found with ID {character_id}")
        return 1 # Default value if character not found
        
    # Ensure character has the base stat attribute
    if not hasattr(character, stat_name):
        logger.warning(f"Character {character_id} missing base stat attribute: {stat_name}")
        return 1 # Return a default minimum value

    base_stat = getattr(character, stat_name, 0)
    stat_modifier = 0
    
    # Get the character's list of effect dictionaries from BattleState
    effects_list = battle.attacker_effects if character_id == battle.attacker.id else battle.defender_effects

    # Iterate through active status effects and apply stat modifications
    for effect_data in effects_list:
        try:
            effect = StatusEffect.from_dict(effect_data) # Recreate StatusEffect object
            if effect.is_active(): # Only apply active effects
                if stat_name in effect.stats:
                    stat_modifier += effect.stats[stat_name]
                    logger.debug(f"Applying stat mod: {effect.name} adds {effect.stats[stat_name]} to {stat_name} for {character_id}")
        except Exception as e:
            logger.error(f"Error processing status effect {effect_data.get('name', '?')} for stat calc: {e}")

    # Calculate effective stat
    effective_stat = base_stat + stat_modifier
    logger.debug(f"Effective {stat_name} for {character_id}: Base={base_stat}, Mod={stat_modifier}, Final={max(1, effective_stat)}")
    
    return max(1, effective_stat)  # Ensure stat is at least 1

def calculate_damage(
    attacker_id: str,
    defender_id: str,
    base_stat: int, # Attacker's relevant stat (strength, ninjutsu, etc.)
    defense_stat: int, # Defender's relevant defense
    battle: BattleState, # Need BattleState to get crit stats and effects
    attack_element: Optional[str] = None, # Element of the incoming attack
    defender_element: Optional[str] = None # Base element/affinity of the defender (optional)
) -> Tuple[int, bool]: # Return damage and is_crit flag
    """
    Calculate damage based on attacker stats and defender defense, applying effects, crits, and elements.
    Args:
        attacker_id: ID of the attacking player
        defender_id: ID of the defending player
        base_stat: Attacker's relevant stat (strength, ninjutsu, etc.)
        defense_stat: Defender's relevant defense
        battle: Current battle state
        attack_element: Element of the attack (e.g., "Fire")
        defender_element: Element of the defender (for resistance/weakness)
    Returns:
        Calculated damage and a boolean indicating if it was a critical hit.
    """
    # Base damage formula (using passed stats)
    defense_mitigation = defense_stat / (defense_stat + 50)  # Diminishing returns
    base_damage = max(1, round(base_stat * (1 - defense_mitigation)))

    # Apply damage reduction from effects (e.g., Defend Stance)
    final_damage = base_damage
    defender_effects_list = battle.defender_effects if defender_id == battle.defender.id else battle.attacker_effects
    if defender_effects_list:
        for effect_data in defender_effects_list:
            try:
                effect = StatusEffect.from_dict(effect_data)
                # Specifically check for Defense Stance
                if effect.name == 'Defense Stance' and effect.is_active():
                    reduction_multiplier = 1.0 - effect.potency # potency 0.5 means 50% reduction
                    final_damage = max(0, round(final_damage * reduction_multiplier)) 
                    logger.debug(f"Defense Stance active. Reducing damage by {effect.potency*100}%. Original: {base_damage}, Final: {final_damage}")
                    break # Assume only one defense stance can be active/relevant
            except Exception as e:
                 logger.error(f"Error processing defender effect {effect_data.get('name', '?')} for damage calc: {e}")

    # TODO: Add other damage modifications (critical hits, elemental weakness/resistance) 
    # - Basic elemental interaction implemented (Attack Element vs Defender Affinity).
    # - Future: Consider equipment-based resistances, multi-element interactions.
    # --- Elemental Interaction --- #
    elemental_multiplier = 1.0
    if attack_element:
        attacker_chart = ELEMENTAL_CHART.get(attack_element, ELEMENTAL_CHART["default"])
        # Use defender_element if provided, otherwise assume neutral interaction for the defender
        elemental_multiplier = attacker_chart.get(defender_element, attacker_chart["default"])
        if elemental_multiplier != 1.0:
             logger.info(f"Elemental Interaction: {attack_element} vs {defender_element}. Multiplier: {elemental_multiplier}")
             final_damage = round(final_damage * elemental_multiplier)
             
    # --- Critical Hit Check --- #
    is_crit = False
    attacker = battle.get_player(attacker_id)
    if attacker:
        # Get effective crit chance (could be modified by effects later)
        crit_chance = get_effective_stat(battle, attacker_id, 'crit_chance') 
        crit_damage_multiplier = get_effective_stat(battle, attacker_id, 'crit_damage')
        
        if random.random() < crit_chance:
            is_crit = True
            final_damage = round(final_damage * crit_damage_multiplier)
            logger.info(f"Critical Hit! Attacker {attacker_id} crit chance: {crit_chance:.2f}, multiplier: {crit_damage_multiplier:.2f}")
    else:
         logger.error(f"calculate_damage: Could not find attacker {attacker_id} for crit check.")

    return final_damage, is_crit

def check_hit(battle: BattleState, attacker_id: str, defender_id: str) -> bool:
    """
    Check if an attack hits based on accuracy and evasion.
    Args:
        battle: The current BattleState.
        attacker_id: The ID of the attacker.
        defender_id: The ID of the defender.
    Returns:
        True if the attack hits, False otherwise.
    """
    # TODO: Define accuracy and evasion stats on characters or use existing ones (e.g., speed?) - REMOVED TODO (Implemented)
    attacker_acc = get_effective_stat(battle, attacker_id, 'accuracy') # Use accuracy stat
    defender_eva = get_effective_stat(battle, defender_id, 'evasion') # Use evasion stat

    # Basic hit chance formula: 85% base + difference modifier
    # Ensure modifier doesn't swing too wildly
    diff_modifier = (attacker_acc - defender_eva) * 0.01 # 1% per point difference
    hit_chance = 0.85 + diff_modifier
    hit_chance = max(0.10, min(0.95, hit_chance)) # Clamp between 10% and 95%

    roll = random.random()
    hit = roll < hit_chance
    logger.debug(f"Hit Check: Att({attacker_id}) Acc={attacker_acc} vs Def({defender_id}) Eva={defender_eva}. Chance={hit_chance:.2f}, Roll={roll:.2f}. Hit={hit}")
    return hit

def resolve_basic_attack(battle: BattleState, user_id: str, add_to_battle_log: callable) -> Dict:
    """
    Resolve a basic attack action.
    Args:
        battle: Current battle state
        attacker_id: ID of the attacking player
        add_to_battle_log: Function to add messages to battle log
    Returns:
        Tuple of (result message, damage dealt)
    """
    attacker = battle.get_player(user_id)
    defender = battle.get_opponent(user_id)
    if not attacker or not defender:
         logger.error("Could not resolve basic attack: Attacker or Defender not found.")
         return "Error: Attacker or Defender missing.", 0

    # --- Kamui Phasing Check --- #
    defender_buffs = battle.defender_effects if defender.id == battle.defender.id else battle.attacker_effects
    phasing_buff = defender_buffs.get("Phasing")
    if phasing_buff and phasing_buff.is_active(): 
        magnitude = getattr(phasing_buff, 'magnitude', 0) # Get magnitude (e.g., 80)
        if random.randint(1, 100) <= magnitude:
            message = f"🌀 {defender.name} phases through {attacker.name}'s attack!"
            # add_to_battle_log(battle, message) # Logging handled by process_turn based on returned dict
            logger.info(f"Attack negated by Phasing buff. Target: {defender.name}")
            # Return result indicating phase/negation
            narrative_context = { # Provide context for narrative generation
                "type": "basic_attack",
                "attacker": attacker.to_dict(include_stats=False), # Use simplified dicts
                "defender": defender.to_dict(include_stats=False),
                "outcome": {"hit": False, "phased": True, "damage": 0, "is_crit": False, "defended": False}
            }
            return {"message": message, "narrative_context": narrative_context}
    # --- End Phasing Check --- #

    # --- Check Hit --- #
    if not check_hit(battle, attacker.id, defender.id):
        message = f"{attacker.name} attacks {defender.name}, but misses!"
        add_to_battle_log(battle, message)
        return message, 0 # No damage on miss

    # Get effective stats using the updated function
    attacker_str = get_effective_stat(battle, attacker.id, 'strength') 
    defender_def = get_effective_stat(battle, defender.id, 'defense')
    
    # Get defender's raw effect list for damage calculation
    defender_effects_list = battle.defender_effects if defender.id == battle.defender.id else battle.attacker_effects
    defender_affinity = getattr(defender, 'elemental_affinity', None)
    
    # Calculate damage
    damage, is_crit = calculate_damage(attacker.id, defender.id, attacker_str, defender_def, battle, attack_element=None, defender_element=defender_affinity)
    
    # Apply damage
    defender_current_hp = battle.get_hp(defender.id)
    battle.set_hp(defender.id, max(0, defender_current_hp - damage))
    
    message = f"{attacker.name} attacks {defender.name}, dealing {damage} damage!"
    if is_crit:
         message += " **(Critical Hit!)**"
    
    # Add note if damage was reduced by defense (check from list again)
    defense_active = False
    if defender_effects_list:
        for effect_data in defender_effects_list:
            if effect_data.get('name') == 'Defense Stance' and effect_data.get('duration', 0) > 0:
                 defense_active = True
                 break
    if defense_active:
        message += " (Defended)"
        
    # Instead of logging, return context for narrative generation
    narrative_context = {
        "type": "basic_attack",
        "attacker": {"name": attacker.name, "hp": battle.get_hp(attacker.id), "max_hp": getattr(attacker, 'max_hp', '?')},
        "defender": {"name": defender.name, "hp": battle.get_hp(defender.id), "max_hp": getattr(defender, 'max_hp', '?')},
        "outcome": {
            "hit": True, # Since we are in the hit block
            "damage": damage,
            "is_crit": is_crit,
            "defended": defense_active
        }
    }
    
    return {"message": message, "narrative_context": narrative_context, "damage_dealt": damage}

def resolve_jutsu_action(
    battle: BattleState, 
    user_id: str, 
    jutsu_id: str, 
    add_to_battle_log: callable, 
    services: 'ServiceContainer'
) -> Dict:
    """
    Resolve a jutsu action.

    Args:
        battle: Current battle state.
        caster_id: ID of the casting player.
        jutsu_id: ID of the jutsu to cast.
        add_to_battle_log: Function to add messages to battle log.
        services: Service container for accessing managers.

    Returns:
        Tuple of (result message, damage dealt).
    """
    caster = battle.get_player(user_id)
    jutsu_manager = services.jutsu_manager
    if not jutsu_manager:
        logger.critical("JutsuManager service not available.")
        return "Error: Jutsu system unavailable.", 0
        
    jutsu_data = jutsu_manager.get_jutsu(jutsu_id) # Assumes returns object/dict
    if not jutsu_data:
        logger.warning(f"Attempted to resolve invalid jutsu ID: {jutsu_id}")
        return f"Unknown jutsu '{jutsu_id}'!", 0
    
    jutsu_name = getattr(jutsu_data, 'name', jutsu_id)
    target_type = getattr(jutsu_data, 'target_type', 'opponent') # Get target type, default opponent
    
    # --- Determine Target --- #
    target_id: Optional[str] = None
    if target_type == 'self':
        target_id = user_id
    elif target_type == 'opponent':
        opponent = battle.get_opponent(user_id)
        if opponent:
             target_id = opponent.id
    # 'utility' type might not need a traditional target, or effects handle it.
    
    # --- Check Costs (BEFORE Hit Check/Execution) --- #
    # Costs should be checked regardless of hitting or missing.
    chakra_cost = getattr(getattr(jutsu_data, 'cost', object()), 'chakra', 0)
    stamina_cost = getattr(getattr(jutsu_data, 'cost', object()), 'stamina', 0)
    caster_chakra = battle.get_chakra(user_id) # Use battle state getters
    caster_stamina = battle.get_stamina(user_id)
    
    if caster_chakra < chakra_cost:
        message = f"{caster.name} doesn't have enough chakra ({caster_chakra}/{chakra_cost}) to cast {jutsu_name}!"
        add_to_battle_log(battle, message)
        return message, 0 # Cannot cast, stop here
    if caster_stamina < stamina_cost:
        message = f"{caster.name} doesn't have enough stamina ({caster_stamina}/{stamina_cost}) to cast {jutsu_name}!"
        add_to_battle_log(battle, message)
        return message, 0 # Cannot cast, stop here
        
    # Deduct costs now that we know they can be paid.
    battle.set_chakra(caster.id, caster_chakra - chakra_cost)
    battle.set_stamina(caster.id, caster_stamina - stamina_cost)
    log_cost_msg = f"{caster.name} uses {chakra_cost} chakra and {stamina_cost} stamina for {jutsu_name}."
    # Add cost message to log *before* potential miss message for clarity
    add_to_battle_log(battle, log_cost_msg)

    # Check if target exists for opponent/self targeted jutsu
    target = battle.get_player(target_id) if target_id else None
    if target_type in ['opponent', 'self'] and not target:
        logger.error(f"Could not resolve jutsu '{jutsu_name}': Target ({target_type}) ID '{target_id}' not found.")
        # Cost already deducted, but jutsu fails
        message = f"{caster.name} uses {jutsu_name}, but the target is invalid!"
        add_to_battle_log(battle, message)
        return message, 0

    # --- Target Self/Utility Logic --- #
    if target_type in ["self", "utility"]:
        # Apply effects directly (including buffs like Phasing)
        if jutsu_effects:
            for effect_data in jutsu_effects:
                if effect_data.get("type") == "apply_buff":
                    # --- Apply Buff Logic --- #
                    buff_id = effect_data.get("buff_id")
                    duration = effect_data.get("duration", 1)
                    magnitude = effect_data.get("magnitude") # Optional
                    if buff_id:
                        buff = StatusEffect(
                            name=buff_id, 
                            duration=duration, 
                            potency=0.0, # Phasing doesn't use potency in the traditional sense
                            effect_type='buff', # Mark as buff explicitly
                            description=f"Effect from {jutsu_name}",
                            stats={}, # No direct stat changes
                            magnitude=magnitude # Store the 80% chance here
                        )
                        add_status_effect(battle, caster.id, buff, add_to_battle_log)
                        message += f" Gains {buff_id}!" # Append to message
                    # --- End Apply Buff --- #
                # TODO: Add logic for other self/utility effects (heal, cleanse, etc.)
        
        # Return result for self/utility jutsu
        narrative_context = { # Provide context for narrative generation
            "type": "jutsu",
            "caster": caster.to_dict(include_stats=False),
            "target": caster.to_dict(include_stats=False), # Target is self
            "jutsu": jutsu_data, 
            "outcome": {"applied_effects": [e.get("buff_id") for e in jutsu_effects if e.get("type") == "apply_buff"]} # List applied buffs
        }
        return {"message": message, "narrative_context": narrative_context}
    
    # --- Opponent Targeting Logic --- #
    # --- Kamui Phasing Check --- #
    target_buffs = battle.defender_effects if target.id == battle.defender.id else battle.attacker_effects
    phasing_buff = target_buffs.get("Phasing")
    if phasing_buff and phasing_buff.is_active():
        magnitude = getattr(phasing_buff, 'magnitude', 0)
        if random.randint(1, 100) <= magnitude:
            message = f"🌀 {target.name} phases through the {jutsu_name}!"
            # add_to_battle_log(battle, message)
            logger.info(f"Jutsu '{jutsu_name}' negated by Phasing buff. Target: {target.name}")
            narrative_context = { # Provide context for narrative generation
                "type": "jutsu",
                "caster": caster.to_dict(include_stats=False),
                "target": target.to_dict(include_stats=False),
                "jutsu": jutsu_data,
                "outcome": {"hit": False, "phased": True, "damage": 0, "applied_effects": []}
            }
            return {"message": message, "narrative_context": narrative_context}
    # --- End Phasing Check --- #

    # --- Check if Jutsu Can Miss --- #
    # ... (existing can_miss check)
    can_miss = jutsu_data.get('can_miss', True)
    hit = True
    if can_miss:
        # --- Check Hit --- #
        # ... (existing hit check logic using check_hit)
        hit = check_hit(battle, caster.id, target.id, jutsu_data.get('accuracy_bonus', 0))

    if hit:
        # --- Apply Jutsu Effects/Damage --- #
        # ... (existing damage calculation and effect application logic for hits)
        # Ensure this block has content or a pass statement
        # Placeholder until full logic is reviewed/restored
        damage = 0 # Placeholder
        is_crit = False # Placeholder
        elemental_msg = "" # Placeholder
        defense_active = False # Placeholder
        applied_effects_msg = [] # Placeholder
        message = f"{caster.name}'s {jutsu_name} hits {target.name}!" # Placeholder message
        
        # Example: Apply damage if calculated
        # target_current_hp = battle.get_hp(target.id)
        # battle.set_hp(target.id, max(0, target_current_hp - damage))
        # message += f" dealing {damage} damage."
        
        # Example: Apply effects
        # ... logic to apply effects based on jutsu_effects ...
        
        # Build narrative context for hit
        narrative_context = {
            "type": "jutsu",
            "caster": caster.to_dict(include_stats=False),
            "target": target.to_dict(include_stats=False),
            "jutsu": jutsu_data,
            "outcome": {
                "hit": True,
                "phased": False, # Added phased flag
                "damage": damage, # Use calculated damage
                "is_crit": is_crit,
                "elemental_effect": elemental_msg,
                "defended": defense_active,
                "applied_effects": applied_effects_msg
            }
        }

    else:
        # --- Handle Miss --- #
        # This block now needs to be indented
        message = f"{caster.name}'s {jutsu_name} misses {target.name}!"
        # add_to_battle_log(battle, message) # Logging handled by process_turn
        narrative_context = {
            "type": "jutsu",
            "caster": caster.to_dict(include_stats=False),
            "target": target.to_dict(include_stats=False),
            "jutsu": jutsu_data,
            "outcome": {"hit": False, "phased": False, "damage": 0, "applied_effects": []}
        }

    # --- Build Final Result --- #
    # This return should be at the function level, outside the if/else
    # Make sure it's correctly indented if the if/else was the end
    # (Assuming the if/else IS the end before returning)
    return {"message": message, "narrative_context": narrative_context}

def resolve_flee_action(
    battle: BattleState,
    player_id: str,
    add_to_battle_log: callable
) -> Tuple[str, bool]:
    """
    Resolve a flee action.

    Args:
        battle: Current battle state
        player_id: ID of the fleeing player
        add_to_battle_log: Function to add messages to battle log

    Returns:
        Tuple of (result message, success)
    """
    fleer = battle.attacker if player_id == battle.attacker.id else battle.defender
    opponent = battle.defender if player_id == battle.attacker.id else battle.attacker
    
    # Calculate flee chance based on speed difference
    fleer_speed = get_effective_stat(battle, fleer.id, 'speed')
    opponent_speed = get_effective_stat(battle, opponent.id, 'speed')
    speed_diff = fleer_speed - opponent_speed
    
    # Base 50% chance, modified by speed difference
    flee_chance = 0.5 + (speed_diff * 0.01)
    flee_chance = max(0.1, min(0.9, flee_chance))  # Clamp between 10% and 90%
    
    success = random.random() < flee_chance
    
    if success:
        message = f"{fleer.name} successfully fled from battle!"
        battle.winner_id = opponent.id
        battle.is_active = False
    else:
        message = f"{fleer.name} failed to flee from battle!"
    
    add_to_battle_log(battle, message)
    return message, success

def resolve_defend_action(
    battle: BattleState,
    player_id: str,
    add_to_battle_log: callable
) -> str:
    """
    Resolve a defend action.

    Args:
        battle: Current battle state
        player_id: ID of the defending player
        add_to_battle_log: Function to add messages to battle log

    Returns:
        Result message
    """
    defender = battle.attacker if player_id == battle.attacker.id else battle.defender
    
    # Add defense buff
    defense_buff = StatusEffect(
        name='Defense Stance',
        duration=1,
        potency=0.5,
        effect_type='start_turn',
        description='Takes reduced damage this turn'
    )
    add_status_effect(battle, defender.id, defense_buff, add_to_battle_log)
    
    message = f"{defender.name} takes a defensive stance!"
    add_to_battle_log(battle, message)
    return message 