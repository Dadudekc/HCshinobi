"""
Module for handling status effects within the battle system.
Provides functions to tick durations, apply effects, check action eligibility,
and add new status effects with stacking rules.
"""

import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Data Model for Status Effects
# ──────────────────────────────────────────────

@dataclass
class StatusEffect:
    """
    Represents a temporary status effect active during battle.
    
    Attributes:
        name (str): The name of the effect.
        effect_type (str): Type of effect (e.g., 'dot', 'hot', 'stat_mod', 'stun').
        magnitude (float): The strength of the effect (damage, healing, etc.).
        duration (int): The number of turns remaining.
        source_player_id (Optional[str]): Who applied the effect.
        target_stat (Optional[str]): Stat to modify for 'stat_mod' effects.
        tick_timing (str): When the effect ticks ('start_turn' or 'end_turn').
        applied_turn (Optional[int]): Turn when effect was applied.
    """
    name: str
    effect_type: str
    magnitude: float
    duration: int
    source_player_id: Optional[str] = None
    target_stat: Optional[str] = None
    tick_timing: str = 'end_turn'
    applied_turn: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the status effect to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusEffect':
        """Deserialize a status effect from a dictionary."""
        return cls(**data)


# ──────────────────────────────────────────────
# Core Functions
# ──────────────────────────────────────────────

def tick_status_durations(battle_state, add_log_func):
    """
    Decrement the duration of each status effect and remove those that expire.
    
    Args:
        battle_state: The current battle state containing attacker and defender effects.
        add_log_func: Function to log messages to the battle log.
    """
    expired_log = []

    # Process both attacker and defender effects in a loop
    for side in ['attacker', 'defender']:
        player = getattr(battle_state, side)
        effects = getattr(battle_state, f"{side}_effects")
        for effect in effects[:]:  # iterate over a copy to safely remove items
            effect.duration -= 1
            logger.debug(f"[Tick] {effect.name} on {player.name}: {effect.duration} turns left")
            if effect.duration <= 0:
                effects.remove(effect)
                expired_log.append(f"{player.name}'s {effect.name} wore off.")
                logger.debug(f"[Remove] {effect.name} expired on {player.name}")

    for msg in expired_log:
        add_log_func(battle_state, msg)


def apply_status_effects(battle_state, timing: str, add_log_func):
    """
    Apply status effects that are scheduled to tick at a specific time.
    
    Args:
        battle_state: The current battle state.
        timing (str): When to apply the effects ('start_turn' or 'end_turn').
        add_log_func: Function to log messages to the battle log.
    """
    logger.debug(f"[Apply] Effects for timing: {timing}")
    
    # Determine whose turn it is.
    is_attacker_turn = battle_state.current_turn_player_id == battle_state.attacker.id
    active = ("attacker", "attacker_hp") if is_attacker_turn else ("defender", "defender_hp")
    opponent = ("defender", "defender_hp") if is_attacker_turn else ("attacker", "attacker_hp")
    
    summaries: List[str] = []
    _apply_effects_to_target(battle_state, active, timing, summaries)
    _apply_effects_to_target(battle_state, opponent, timing, summaries)

    for summary in summaries:
        add_log_func(battle_state, summary)


def _apply_effects_to_target(battle_state, target: tuple, timing: str, log: List[str]):
    """
    Helper function to process effects on a target (attacker or defender).
    
    Args:
        battle_state: The current battle state.
        target (tuple): A tuple (side, hp_attribute).
        timing (str): Tick timing ('start_turn' or 'end_turn').
        log (List[str]): List to append log messages.
    """
    side, hp_attr = target
    player = getattr(battle_state, side)
    effects = getattr(battle_state, f"{side}_effects")
    current_hp = getattr(battle_state, hp_attr)
    max_hp = getattr(player, "max_hp", current_hp)

    for effect in effects:
        if effect.tick_timing != timing:
            continue

        logger.debug(f"[Process] {effect.name} ({effect.effect_type}) on {player.name}")
        if effect.effect_type == "hot":
            heal = int(effect.magnitude)
            new_hp = min(max_hp, current_hp + heal)
            actual_heal = new_hp - current_hp
            if actual_heal > 0:
                setattr(battle_state, hp_attr, new_hp)
                log.append(f"{player.name} recovers {actual_heal} HP from {effect.name}. (HP: {new_hp})")
                logger.debug(f"[HoT] {player.name} healed {actual_heal} HP from {effect.name}")
        elif effect.effect_type == "dot":
            damage = int(effect.magnitude)
            new_hp = max(0, current_hp - damage)
            actual_damage = current_hp - new_hp
            if actual_damage > 0:
                setattr(battle_state, hp_attr, new_hp)
                log.append(f"{player.name} takes {actual_damage} damage from {effect.name}. (HP: {new_hp})")
                logger.debug(f"[DoT] {player.name} took {actual_damage} damage from {effect.name}")


def can_player_act(battle_state, player_id: str, add_log_func) -> bool:
    """
    Determine if a player can act based on current status effects.
    
    Args:
        battle_state: The current battle state.
        player_id (str): The ID of the player.
        add_log_func: Function to log messages to the battle log.
        
    Returns:
        bool: True if the player can act, False otherwise.
    """
    effects = (battle_state.attacker_effects if player_id == battle_state.attacker.id 
               else battle_state.defender_effects)
    for effect in effects:
        if effect.effect_type == 'stun':
            name = (battle_state.attacker.name if player_id == battle_state.attacker.id 
                    else battle_state.defender.name)
            add_log_func(battle_state, f"{name} is stunned by {effect.name} and cannot act!")
            logger.debug(f"[Stun] {name} is prevented from acting due to {effect.name}")
            return False
    return True


def add_status_effect(battle_state, target_player_id: str, effect: StatusEffect, add_log_func):
    """
    Add a new status effect to a player, refreshing duration if already active.
    
    Args:
        battle_state: The battle state to modify.
        target_player_id (str): The ID of the player receiving the effect.
        effect (StatusEffect): The status effect to add.
        add_log_func: Function to log messages to the battle log.
    """
    if not battle_state or not battle_state.is_active:
        logger.warning("Cannot add status effect: Battle state is invalid or inactive.")
        return

    is_attacker = target_player_id == battle_state.attacker.id
    target = battle_state.attacker if is_attacker else battle_state.defender
    effects_list = battle_state.attacker_effects if is_attacker else battle_state.defender_effects

    for existing_effect in effects_list:
        if existing_effect.name == effect.name:
            # Refresh duration if effect already exists.
            existing_effect.duration = max(existing_effect.duration, effect.duration)
            add_log_func(battle_state, f"{target.name}'s {effect.name} duration refreshed.")
            logger.debug(f"[Refresh] {effect.name} on {target.name} refreshed to {existing_effect.duration} turns")
            return

    effects_list.append(effect)
    add_log_func(battle_state, f"{target.name} is now affected by {effect.name} ({effect.duration} turns).")
    logger.debug(f"[Add] {effect.name} applied to {target.name} for {effect.duration} turns")
