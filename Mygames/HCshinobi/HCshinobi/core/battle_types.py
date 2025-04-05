"""
Defines shared data structures and types for the battle system.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

# Need imports for types used within BattleState
from .character import Character
from .battle_effects import StatusEffect
# Removed CharacterSystem import as from_dict logic might move or be handled differently

logger = logging.getLogger(__name__)

@dataclass
class BattleState:
    """Represents the state of a battle."""
    attacker: Character
    defender: Character
    attacker_hp: int
    defender_hp: int
    attacker_chakra: int  # Add attacker chakra tracking
    defender_chakra: int  # Add defender chakra tracking
    current_turn_player_id: Optional[str] = None
    turn_number: int = 1 # Start at turn 1
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    winner_id: Optional[str] = None
    last_action: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attacker_effects: List[StatusEffect] = field(default_factory=list)
    defender_effects: List[StatusEffect] = field(default_factory=list)
    battle_log: List[str] = field(default_factory=list)
    
    def update_start_time(self, new_time: datetime) -> None:
        """Update the battle start time."""
        self.start_time = new_time
        
    def update_last_action(self, new_time: datetime) -> None:
        """Update the last action time."""
        self.last_action = new_time
    
    def __hash__(self):
        """Make BattleState hashable for use as dict key."""
        # Ensure IDs are strings for consistency if needed
        return hash((str(self.attacker.id), str(self.defender.id), self.start_time))
    
    def __eq__(self, other):
        """Define equality for BattleState."""
        if not isinstance(other, BattleState):
            return False
        return (
            str(self.attacker.id) == str(other.attacker.id) and
            str(self.defender.id) == str(other.defender.id) and
            self.start_time == other.start_time
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert battle state to dictionary for serialization."""
        return {
            # Store full character data as dicts
            'attacker': asdict(self.attacker), 
            'defender': asdict(self.defender),
            # Keep IDs for potential quick lookups if needed elsewhere
            'attacker_id': str(self.attacker.id), 
            'defender_id': str(self.defender.id),
            'attacker_hp': self.attacker_hp,
            'defender_hp': self.defender_hp,
            'attacker_chakra': self.attacker_chakra,
            'defender_chakra': self.defender_chakra,
            'current_turn_player_id': str(self.current_turn_player_id) if self.current_turn_player_id else None,
            'turn_number': self.turn_number,
            'start_time': self.start_time.isoformat(),
            'is_active': self.is_active,
            'winner_id': str(self.winner_id) if self.winner_id else None,
            'last_action': self.last_action.isoformat(),
            'attacker_effects': [eff.to_dict() for eff in self.attacker_effects],
            'defender_effects': [eff.to_dict() for eff in self.defender_effects],
            'battle_log': self.battle_log,
            'end_reason': getattr(self, 'end_reason', None) # Add end_reason if exists
        }
    
    # Note: The from_dict method requires CharacterSystem, which would recreate the circular dependency.
    # This method should be moved to BattleSystem where CharacterSystem is available,
    # or CharacterSystem should be passed directly when calling from_dict.
    # For now, removing it from here to resolve the immediate import cycle.
    # @classmethod
    # async def from_dict(cls, data: Dict, character_system: 'CharacterSystem') -> 'BattleState':
    #     ... 