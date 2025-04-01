"""Character class for managing character data."""
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

@dataclass
class Character:
    """Represents a character in the game."""
    
    # Basic Info
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    clan: str = ""
    level: int = 1
    exp: int = 0
    
    # Core stats
    hp: int = 100
    chakra: int = 100
    stamina: int = 100
    strength: int = 10
    speed: int = 10
    defense: int = 10
    willpower: int = 10
    chakra_control: int = 10
    
    # Combat stats
    ninjutsu: int = 10
    taijutsu: int = 10
    genjutsu: int = 10
    
    # Skills and Equipment
    jutsu: List[str] = field(default_factory=list)
    equipment: Dict[str, str] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    
    # Status
    is_active: bool = True
    status_effects: List[str] = field(default_factory=list)
    
    # Battle stats
    wins: int = 0
    losses: int = 0
    draws: int = 0
    
    # Derived stats
    max_hp: int = field(init=True, default=100)
    max_chakra: int = field(init=True, default=100)
    max_stamina: int = field(init=True, default=100)
    
    def __post_init__(self):
        """Initialize derived attributes."""
        # Set max stats based on level and base stats
        self.max_hp = self.hp
        self.max_chakra = self.chakra
        self.max_stamina = self.stamina
        
        # Ensure current stats don't exceed max
        self.hp = min(self.hp, self.max_hp)
        self.chakra = min(self.chakra, self.max_chakra)
        self.stamina = min(self.stamina, self.max_stamina)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create a character from a dictionary.
        
        Args:
            data: Dictionary containing character data
            
        Returns:
            Character instance
        """
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary.
        
        Returns:
            Dictionary containing character data
        """
        return {
            "id": self.id,
            "name": self.name,
            "clan": self.clan,
            "level": self.level,
            "exp": self.exp,
            "hp": self.hp,
            "chakra": self.chakra,
            "stamina": self.stamina,
            "strength": self.strength,
            "speed": self.speed,
            "defense": self.defense,
            "willpower": self.willpower,
            "chakra_control": self.chakra_control,
            "ninjutsu": self.ninjutsu,
            "taijutsu": self.taijutsu,
            "genjutsu": self.genjutsu,
            "jutsu": self.jutsu,
            "equipment": self.equipment,
            "inventory": self.inventory,
            "is_active": self.is_active,
            "status_effects": self.status_effects
        }
    
    def add_exp(self, amount: int) -> bool:
        """Add experience points to the character.
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            True if character leveled up
        """
        self.exp += amount
        if self.exp >= self.level * 100:
            return self.level_up()
        return False
    
    def level_up(self) -> bool:
        """Level up the character.
        
        Returns:
            True if successful
        """
        if self.exp < self.level * 100:
            return False
            
        self.level += 1
        self.exp = 0
        
        # Increase stats
        self.max_hp += 10
        self.max_chakra += 10
        self.max_stamina += 10
        self.hp = self.max_hp
        self.chakra = self.max_chakra
        self.stamina = self.max_stamina
        
        return True
    
    def heal(self, amount: int) -> int:
        """Heal the character.
        
        Args:
            amount: Amount to heal
            
        Returns:
            Amount actually healed
        """
        old_hp = self.hp
        self.hp = min(self.hp + amount, self.max_hp)
        return self.hp - old_hp
    
    def restore_chakra(self, amount: int) -> int:
        """Restore chakra to the character.
        
        Args:
            amount: Amount to restore
            
        Returns:
            Amount actually restored
        """
        old_chakra = self.chakra
        self.chakra = min(self.chakra + amount, self.max_chakra)
        return self.chakra - old_chakra
    
    def restore_stamina(self, amount: int) -> int:
        """Restore stamina to the character.
        
        Args:
            amount: Amount to restore
            
        Returns:
            Amount actually restored
        """
        old_stamina = self.stamina
        self.stamina = min(self.stamina + amount, self.max_stamina)
        return self.stamina - old_stamina
    
    def take_damage(self, amount: int) -> int:
        """Apply damage to the character.
        
        Args:
            amount: Amount of damage to take
            
        Returns:
            Amount of damage actually taken
        """
        old_hp = self.hp
        self.hp = max(0, self.hp - amount)
        return old_hp - self.hp
    
    def use_chakra(self, amount: int) -> bool:
        """Use chakra for an action.
        
        Args:
            amount: Amount of chakra to use
            
        Returns:
            True if chakra was used successfully
        """
        if self.chakra < amount:
            return False
        self.chakra -= amount
        return True
    
    def use_stamina(self, amount: int) -> bool:
        """Use stamina for an action.
        
        Args:
            amount: Amount of stamina to use
            
        Returns:
            True if stamina was used successfully
        """
        if self.stamina < amount:
            return False
        self.stamina -= amount
        return True
    
    def add_jutsu(self, jutsu: str) -> bool:
        """Add a jutsu to the character.
        
        Args:
            jutsu: Name of jutsu to add
            
        Returns:
            True if jutsu was added
        """
        if jutsu in self.jutsu:
            return False
        self.jutsu.append(jutsu)
        return True
    
    def remove_jutsu(self, jutsu: str) -> bool:
        """Remove a jutsu from the character.
        
        Args:
            jutsu: Name of jutsu to remove
            
        Returns:
            True if jutsu was removed
        """
        if jutsu not in self.jutsu:
            return False
        self.jutsu.remove(jutsu)
        return True
    
    def add_item(self, item: str) -> bool:
        """Add an item to the character's inventory.
        
        Args:
            item: Name of item to add
            
        Returns:
            True if item was added
        """
        self.inventory.append(item)
        return True
    
    def remove_item(self, item: str) -> bool:
        """Remove an item from the character's inventory.
        
        Args:
            item: Name of item to remove
            
        Returns:
            True if item was removed
        """
        if item not in self.inventory:
            return False
        self.inventory.remove(item)
        return True
    
    def equip_item(self, item: str, slot: str) -> bool:
        """Equip an item to a slot.
        
        Args:
            item: Name of item to equip
            slot: Equipment slot to use
            
        Returns:
            True if item was equipped
        """
        if item not in self.inventory:
            return False
        if slot in self.equipment:
            self.inventory.append(self.equipment[slot])
        self.equipment[slot] = item
        self.inventory.remove(item)
        return True
    
    def unequip_item(self, slot: str) -> bool:
        """Unequip an item from a slot.
        
        Args:
            slot: Equipment slot to unequip from
            
        Returns:
            True if item was unequipped
        """
        if slot not in self.equipment:
            return False
        self.inventory.append(self.equipment[slot])
        del self.equipment[slot]
        return True
    
    def add_status_effect(self, effect: str) -> bool:
        """Add a status effect to the character.
        
        Args:
            effect: Name of effect to add
            
        Returns:
            True if effect was added
        """
        if effect in self.status_effects:
            return False
        self.status_effects.append(effect)
        return True
    
    def remove_status_effect(self, effect: str) -> bool:
        """Remove a status effect from the character.
        
        Args:
            effect: Name of effect to remove
            
        Returns:
            True if effect was removed
        """
        if effect not in self.status_effects:
            return False
        self.status_effects.remove(effect)
        return True
    
    def record_battle_result(self, result: str) -> None:
        """Record the result of a battle.
        
        Args:
            result: Battle result ('win', 'loss', or 'draw')
        """
        if result == 'win':
            self.wins += 1
        elif result == 'loss':
            self.losses += 1
        elif result == 'draw':
            self.draws += 1 