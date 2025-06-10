"""
Battle state management and serialization.
"""
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from ..character import Character

logger = logging.getLogger(__name__)

@dataclass
class BattleParticipant:
    """Represents a participant in a battle."""
    character: Character
    current_hp: int
    current_chakra: int
    effects: List[Dict] = field(default_factory=list)
    
    @property
    def id(self) -> str:
        """Get the participant's ID (same as character ID)."""
        return self.character.id
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert participant to dictionary for serialization."""
        return {
            'character': self.character.to_dict(),
            'current_hp': self.current_hp,
            'current_chakra': self.current_chakra,
            'effects': self.effects
        }
        
    @classmethod
    def from_character(cls, character: Character) -> 'BattleParticipant':
        """Create a battle participant from a character."""
        return cls(
            character=character,
            current_hp=character.hp,
            current_chakra=character.chakra
        )
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['BattleParticipant']:
        """Create a battle participant from dictionary data."""
        try:
            character = Character.from_dict(data['character'])
            return cls(
                character=character,
                current_hp=data.get('current_hp', character.hp),
                current_chakra=data.get('current_chakra', character.chakra),
                effects=data.get('effects', [])
            )
        except (KeyError, TypeError) as e:
            logger.error(f"Error creating BattleParticipant from dict: {e}")
            return None

@dataclass
class BattleState:
    """Represents the current state of a battle."""
    attacker: BattleParticipant
    defender: BattleParticipant
    current_turn_player_id: str
    turn_number: int = 1
    battle_log: List[str] = field(default_factory=list)
    winner_id: Optional[str] = None
    is_active: bool = True
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_action: Optional[datetime] = None
    end_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert battle state to dictionary for serialization."""
        return {
            'attacker': self.attacker.to_dict(),
            'defender': self.defender.to_dict(),
            'current_turn_player_id': self.current_turn_player_id,
            'turn_number': self.turn_number,
            'battle_log': self.battle_log,
            'winner_id': self.winner_id,
            'is_active': self.is_active,
            'start_time': self.start_time.isoformat(),
            'last_action': self.last_action.isoformat() if self.last_action else None,
            'end_reason': self.end_reason
        }

    @property
    def id(self) -> str:
        """Generate a unique battle ID from participants."""
        return f"{self.attacker.id}_{self.defender.id}"

    @classmethod
    def create_battle(cls, attacker: Character, defender: Character) -> 'BattleState':
        """Create a new battle state between two characters."""
        attacker_participant = BattleParticipant.from_character(attacker)
        defender_participant = BattleParticipant.from_character(defender)
        
        return cls(
            attacker=attacker_participant,
            defender=defender_participant,
            current_turn_player_id=attacker.id
        )

async def deserialize_battle_state(data: Dict) -> Optional[BattleState]:
    """
    Deserialize a dictionary back into a BattleState object.
    """
    try:
        # --- Reconstruct Battle Participants --- #
        attacker_data = data.get('attacker')
        defender_data = data.get('defender')
        
        if not attacker_data or not defender_data:
            logger.error("deserialize_battle_state: Missing attacker or defender data.")
            return None

        attacker = BattleParticipant.from_dict(attacker_data)
        defender = BattleParticipant.from_dict(defender_data)
        
        if not attacker or not defender:
            logger.error("deserialize_battle_state: Failed to reconstruct BattleParticipant objects.")
            return None
             
        # Handle last_action timestamp conversion
        last_action_str = data.get('last_action')
        last_action_dt = None
        if last_action_str:
            try:
                last_action_dt = datetime.fromisoformat(last_action_str).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                logger.warning(f"deserialize_battle_state: Could not parse last_action timestamp '{last_action_str}'.")
                
        # Handle start_time timestamp conversion
        start_time_str = data.get('start_time')
        start_time_dt = datetime.now(timezone.utc) # Default to now if missing/invalid
        if start_time_str:
            try:
                start_time_dt = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                logger.warning(f"deserialize_battle_state: Could not parse start_time timestamp '{start_time_str}'. Using current time.")
                
        # --- Create BattleState --- #
        state = BattleState(
            attacker=attacker,
            defender=defender,
            current_turn_player_id=data.get('current_turn_player_id'),
            turn_number=data.get('turn_number', 1),
            battle_log=data.get('battle_log', []),
            winner_id=data.get('winner_id'),
            is_active=data.get('is_active', False),
            start_time=start_time_dt,
            last_action=last_action_dt,
            end_reason=data.get('end_reason')
        )
        return state
        
    except Exception as e:
        logger.error(f"Error deserializing battle state: {e}", exc_info=True)
        return None