"""Battle system for managing character combat."""
import random
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .character import Character
from .character_system import CharacterSystem

logger = logging.getLogger(__name__)

@dataclass
class BattleState:
    """Represents the state of a battle."""
    attacker: Character
    defender: Character
    attacker_hp: int
    defender_hp: int
    start_time: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    winner: Optional[str] = None
    last_action: datetime = field(default_factory=datetime.now)
    
    def update_start_time(self, new_time: datetime) -> None:
        """Update the battle start time.
        
        Args:
            new_time: New start time
        """
        self.start_time = new_time
        
    def update_last_action(self, new_time: datetime) -> None:
        """Update the last action time.
        
        Args:
            new_time: New last action time
        """
        self.last_action = new_time
    
    def __hash__(self):
        """Make BattleState hashable for use as dict key."""
        return hash((self.attacker.id, self.defender.id, self.start_time))
    
    def __eq__(self, other):
        """Define equality for BattleState."""
        if not isinstance(other, BattleState):
            return False
        return (self.attacker.id == other.attacker.id and
                self.defender.id == other.defender.id and
                self.start_time == other.start_time)
    
    def to_dict(self) -> Dict:
        """Convert battle state to dictionary."""
        return {
            'attacker_id': self.attacker.id,
            'defender_id': self.defender.id,
            'attacker_hp': self.attacker_hp,
            'defender_hp': self.defender_hp,
            'start_time': self.start_time.isoformat(),
            'is_active': self.is_active,
            'winner_id': self.winner,
            'last_action': self.last_action.isoformat()
        }
    
    @classmethod
    async def from_dict(cls, data: Dict, character_system: CharacterSystem) -> 'BattleState':
        """Create battle state from dictionary."""
        attacker = await character_system.get_character(data['attacker_id'])
        defender = await character_system.get_character(data['defender_id'])
        
        return cls(
            attacker=attacker,
            defender=defender,
            attacker_hp=data['attacker_hp'],
            defender_hp=data['defender_hp'],
            start_time=datetime.fromisoformat(data['start_time']),
            is_active=data['is_active'],
            winner=data['winner_id'],
            last_action=datetime.fromisoformat(data['last_action'])
        )

class BattleSystem:
    """System for managing character battles."""
    
    def __init__(self, character_system: CharacterSystem):
        """Initialize the battle system.
        
        Args:
            character_system: Character system for managing characters
        """
        self.character_system = character_system
        self.active_battles: Dict[str, BattleState] = {}
        self.battle_history: Dict[str, BattleState] = {}
        self.battle_timeout = timedelta(minutes=5)
    
    async def start_battle(self, attacker_id: str, defender_id: str) -> Optional[BattleState]:
        """Start a new battle.
        
        Args:
            attacker_id: Attacker's user ID
            defender_id: Defender's user ID
            
        Returns:
            Battle state if successful, None if invalid
        """
        attacker = await self.character_system.get_character(attacker_id)
        defender = await self.character_system.get_character(defender_id)
        
        if not attacker or not defender:
            return None
            
        battle_id = f"{attacker_id}_{defender_id}"
        if battle_id in self.active_battles:
            return None
            
        battle = BattleState(
            attacker=attacker,
            defender=defender,
            attacker_hp=attacker.hp,
            defender_hp=defender.hp
        )
        
        self.active_battles[battle_id] = battle
        return battle
    
    def calculate_damage(self, attacker: Character, defender: Character, jutsu_name: str) -> int:
        """Calculate battle damage.
        
        Args:
            attacker: Attacking character
            defender: Defending character
            jutsu_name: Name of jutsu used
            
        Returns:
            Calculated damage
        """
        # Base damage calculation
        base_damage = 10
        
        # Apply stat modifiers
        attack_power = (attacker.strength + attacker.ninjutsu) / 2
        defense_power = (defender.defense + defender.willpower) / 2
        
        # Calculate final damage
        damage = int(base_damage * (attack_power / defense_power))
        return max(1, damage)  # Minimum 1 damage
    
    async def apply_damage(self, battle_id: str, damage: int, target: str) -> bool:
        """Apply damage in battle.
        
        Args:
            battle_id: Battle identifier
            damage: Amount of damage
            target: Target (attacker/defender)
            
        Returns:
            True if damage was applied
        """
        battle = self.active_battles.get(battle_id)
        if not battle or not battle.is_active:
            return False
            
        if target == 'attacker':
            new_hp = max(0, battle.attacker_hp - damage)
            new_state = BattleState(
                attacker=battle.attacker,
                defender=battle.defender,
                attacker_hp=new_hp,
                defender_hp=battle.defender_hp,
                start_time=battle.start_time,
                is_active=True,
                winner=None if new_hp > 0 else battle.defender.id,
                last_action=datetime.now()
            )
        else:
            new_hp = max(0, battle.defender_hp - damage)
            new_state = BattleState(
                attacker=battle.attacker,
                defender=battle.defender,
                attacker_hp=battle.attacker_hp,
                defender_hp=new_hp,
                start_time=battle.start_time,
                is_active=True,
                winner=None if new_hp > 0 else battle.attacker.id,
                last_action=datetime.now()
            )
            
        self.active_battles[battle_id] = new_state
        
        return True
    
    def check_battle_end(self, battle_id: str) -> bool:
        """Check if battle has ended.
        
        Args:
            battle_id: Battle identifier
            
        Returns:
            True if battle has ended
        """
        battle = self.active_battles.get(battle_id)
        if not battle or not battle.is_active:
            return True
            
        # Check for defeated character
        if battle.attacker_hp <= 0:
            battle = BattleState(
                attacker=battle.attacker,
                defender=battle.defender,
                attacker_hp=0,
                defender_hp=battle.defender_hp,
                start_time=battle.start_time,
                is_active=False,
                winner=battle.defender.id,
                last_action=battle.last_action
            )
            self.active_battles[battle_id] = battle
            return True
            
        if battle.defender_hp <= 0:
            battle = BattleState(
                attacker=battle.attacker,
                defender=battle.defender,
                attacker_hp=battle.attacker_hp,
                defender_hp=0,
                start_time=battle.start_time,
                is_active=False,
                winner=battle.attacker.id,
                last_action=battle.last_action
            )
            self.active_battles[battle_id] = battle
            return True
            
        # Check for timeout
        time_since_last = datetime.now() - battle.last_action
        if time_since_last > self.battle_timeout:
            battle = BattleState(
                attacker=battle.attacker,
                defender=battle.defender,
                attacker_hp=battle.attacker_hp,
                defender_hp=battle.defender_hp,
                start_time=battle.start_time,
                is_active=False,
                winner=None,
                last_action=battle.last_action
            )
            self.active_battles[battle_id] = battle
            return True
            
        return False
    
    async def end_battle(self, battle_id: str) -> Optional[str]:
        """End a battle.
        
        Args:
            battle_id: Battle identifier
            
        Returns:
            Winning character if any
        """
        battle = self.active_battles.get(battle_id)
        if not battle:
            return None
            
        battle = BattleState(
            attacker=battle.attacker,
            defender=battle.defender,
            attacker_hp=battle.attacker_hp,
            defender_hp=battle.defender_hp,
            start_time=battle.start_time,
            is_active=False,
            winner=battle.winner,
            last_action=battle.last_action
        )
        
        self.battle_history[battle_id] = battle
        del self.active_battles[battle_id]
        
        return battle.winner
    
    async def get_battle_status(self, battle_id: str) -> Optional[BattleState]:
        """Get current battle status.
        
        Args:
            battle_id: Battle identifier
            
        Returns:
            Current battle state if exists
        """
        return self.active_battles.get(battle_id)
    
    async def use_jutsu(self, battle_id: str, user_id: str, jutsu_name: str) -> Tuple[bool, str]:
        """Use a jutsu in battle.
        
        Args:
            battle_id: Battle identifier
            user_id: User's ID
            jutsu_name: Name of jutsu to use
            
        Returns:
            Success status and message
        """
        battle = self.active_battles.get(battle_id)
        if not battle or not battle.is_active:
            return False, "No active battle found"
            
        # Determine attacker and defender
        is_attacker = battle.attacker.id == user_id
        if not is_attacker and battle.defender.id != user_id:
            return False, "Not a participant in this battle"
            
        character = battle.attacker if is_attacker else battle.defender
        target = battle.defender if is_attacker else battle.attacker
        
        # Check if it's user's turn
        current_turn_player = battle.attacker if battle.turn % 2 == 1 else battle.defender
        if current_turn_player.id != user_id:
            return False, "Not your turn"
            
        # Check if character has the jutsu
        if jutsu_name not in character.jutsu:
            return False, f"You don't know {jutsu_name}"
            
        # Calculate and apply damage
        damage = self.calculate_damage(character, target, jutsu_name)
        target.take_damage(damage)
        
        # Update battle state
        battle.turn += 1
        battle.last_action = datetime.now()
        
        # Check if battle has ended
        if self.check_battle_end(battle_id):
            winner = self.end_battle(battle_id)
            if winner:
                return True, f"{winner} has won the battle!"
            return True, "Battle has ended in a draw"
            
        return True, f"{character.name} used {jutsu_name} for {damage} damage!"
    
    async def battle_timeout_check(self) -> None:
        """Background task to check for battle timeouts."""
        while True:
            for battle_id in list(self.active_battles.keys()):
                battle = self.active_battles[battle_id]
                if datetime.now() - battle.start_time > self.battle_timeout:
                    logger.info(f"Battle {battle_id} timed out")
                    self.end_battle(battle_id)
            await asyncio.sleep(60)  # Check every minute 