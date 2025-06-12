"""
Shared types and interfaces for the battle module.
"""
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

class StatusEffectType(Enum):
    """Types of status effects."""
    START_TURN = "start_turn"
    END_TURN = "end_turn"
    CONTINUOUS = "continuous"
    TRIGGER = "trigger"

class StatusEffectModifier(Enum):
    """Status effect modifiers."""
    DAMAGE = "damage"
    HEAL = "heal"
    STUN = "stun"
    BUFF = "buff"
    DEBUFF = "debuff"

@runtime_checkable
class BattleLogCallback(Protocol):
    """Protocol for battle log callback functions."""
    def __call__(self, battle: 'BattleState', message: str) -> None:
        ...

@dataclass
class StatusEffect:
    """Represents a status effect in battle."""
    name: str
    duration: int
    potency: float
    effect_type: str
    description: str
    stats: Dict[str, int] = field(default_factory=dict)
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Stacking fields
    max_stacks: Optional[int] = None 
    current_stacks: int = 1
    # Add magnitude field for effects like Phasing (percentage chance)
    magnitude: Optional[float] = None 

    def is_active(self) -> bool:
        """Check if the effect is currently active (duration > 0)."""
        return self.duration > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert status effect to dictionary for serialization."""
        return {
            'name': self.name,
            'duration': self.duration,
            'potency': self.potency,
            'effect_type': self.effect_type,
            'description': self.description,
            'stats': self.stats,
            'applied_at': self.applied_at.isoformat(),
            # Stacking fields
            'max_stacks': self.max_stacks,
            'current_stacks': self.current_stacks,
            # Add magnitude to serialization
            'magnitude': self.magnitude 
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusEffect':
        """Create status effect from dictionary."""
        applied_at = datetime.fromisoformat(data['applied_at']) if 'applied_at' in data else datetime.now(timezone.utc)
        return cls(
            name=data.get('name', 'Unknown Effect'),
            duration=data.get('duration', 0),
            potency=data.get('potency', 0.0),
            effect_type=data.get('effect_type', 'passive'),
            description=data.get('description', ''),
            stats=data.get('stats', {}),
            applied_at=applied_at,
            # Stacking fields
            max_stacks=data.get('max_stacks', None),
            current_stacks=data.get('current_stacks', 1),
            # Add magnitude from deserialization
            magnitude=data.get('magnitude', None) 
        ) 