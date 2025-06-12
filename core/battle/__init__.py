"""
Battle system module for managing character combat.
"""

from .actions import (
    BattleAction,
    BasicAttack,
    JutsuAction,
    ItemAction,
    FleeAction,
    resolve_basic_attack,
    resolve_jutsu_action,
    resolve_flee_action,
    resolve_defend_action,
    get_effective_stat
)

from .state import (
    BattleState,
    BattleParticipant,
    deserialize_battle_state
)

from .turn import (
    TurnPhase,
    TurnState,
    process_turn
)

from .types import (
    StatusEffectType,
    StatusEffectModifier,
    StatusEffect,
    BattleLogCallback
)

from .effects import (
    add_status_effect,
    apply_status_effects,
    tick_status_durations,
    can_player_act
)

from .persistence import BattlePersistence

from .lifecycle import (
    initialize_battle,
    cleanup_battle
)

__all__ = [
    # Core - Remove BattleSystem from here
    # 'BattleSystem',
    # 'resolve_attack', # If these are defined in battle_system.py, remove them too
    # 'get_element_effectiveness',
    
    # Actions
    'BattleAction',
    'BasicAttack',
    'JutsuAction',
    'ItemAction',
    'FleeAction',
    'resolve_basic_attack',
    'resolve_jutsu_action',
    'resolve_flee_action',
    'resolve_defend_action',
    'get_effective_stat',
    
    # State
    'BattleState',
    'BattleParticipant',
    'deserialize_battle_state',
    
    # Turn
    'TurnPhase',
    'TurnState',
    'process_turn',
    
    # Effects
    'StatusEffectType',
    'StatusEffectModifier',
    'StatusEffect',
    'add_status_effect',
    'apply_status_effects',
    'tick_status_durations',
    'can_player_act',
    
    # Persistence
    'BattlePersistence',
    
    # Lifecycle
    'initialize_battle',
    'cleanup_battle',
    
    # Types
    'BattleLogCallback'
] 