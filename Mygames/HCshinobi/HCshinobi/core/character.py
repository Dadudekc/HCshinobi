"""Character class for managing character data."""
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, fields
from datetime import datetime

@dataclass
class Character:
    """Represents a character in the game."""
    
    # Basic Info
    id: str
    name: str = ""
    clan: str = ""
    level: int = 1
    exp: int = 0
    # ryo: int = 0  # REMOVED: Currency is handled by CurrencySystem
    specialization: Optional[str] = None
    rank: str = "Academy Student"
    
    # Core stats
    hp: int = 100
    chakra: int = 100
    stamina: int = 100
    strength: int = 10
    speed: int = 10
    defense: int = 10
    willpower: int = 10
    chakra_control: int = 10
    intelligence: int = 10
    perception: int = 0
    stat_points: int = 0 # Added for level-up rewards
    
    # Combat stats
    ninjutsu: int = 0
    taijutsu: int = 10
    genjutsu: int = 10
    accuracy: int = 50  # Base accuracy
    evasion: int = 50   # Base evasion
    crit_chance: float = 0.05 # Base crit chance (5%)
    crit_damage: float = 1.5  # Base crit damage multiplier (150%)
    elemental_affinity: Optional[str] = None # Character's primary element for defense
    
    # Skills and Equipment
    jutsu: List[str] = field(default_factory=list)
    equipment: Dict[str, str] = field(default_factory=dict)
    inventory: Dict[str, int] = field(default_factory=dict)
    
    # Status
    is_active: bool = True
    status_effects: List[str] = field(default_factory=list)
    active_effects: Dict[str, Any] = field(default_factory=dict)
    status_conditions: Dict[str, Any] = field(default_factory=dict)
    buffs: Dict[str, Any] = field(default_factory=dict)
    debuffs: Dict[str, Any] = field(default_factory=dict)
    
    # Battle stats
    wins: int = 0
    losses: int = 0
    draws: int = 0
    wins_against_rank: Dict[str, int] = field(default_factory=dict)
    
    # Progression Fields
    achievements: Set[str] = field(default_factory=set)
    titles: List[str] = field(default_factory=list)
    equipped_title: Optional[str] = None
    
    # Mission tracking
    completed_missions: Set[str] = field(default_factory=set)
    
    # Clan Progression Fields
    clan_rank: str = "Initiate"  # Rank within the clan
    clan_exp: int = 0  # Experience earned for clan activities
    clan_achievements: Set[str] = field(default_factory=set)  # Clan-specific achievements
    clan_skills: Dict[str, int] = field(default_factory=dict)  # Clan-specific skill levels
    clan_jutsu_mastery: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Mastery of clan-specific jutsu
    clan_contribution_points: int = 0  # Points earned through clan activities
    clan_role: str = "Member"  # Role within the clan (e.g., Member, Elder, Leader)
    clan_joined_at: Optional[datetime] = None  # When the character joined their current clan
    
    # Derived stats
    max_hp: int = field(init=True, default=100)
    max_chakra: int = field(init=True, default=100)
    max_stamina: int = field(init=True, default=100)
    
    # New attributes
    jutsu_mastery: Dict[str, Dict[str, int]] = field(default_factory=dict)
    last_daily_claim: Optional[str] = None
    active_mission_id: Optional[str] = None
    
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
        
        # Initialize jutsu_mastery, defaulting to empty dict if not loaded
        self.jutsu_mastery = self.jutsu_mastery or {}
        
        # Ensure mastery exists for all known jutsu (for backward compatibility)
        for jutsu_name in self.jutsu:
            if jutsu_name not in self.jutsu_mastery:
                self.jutsu_mastery[jutsu_name] = {"level": 1, "gauge": 0}
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Return a mapping of character stats for update and lookup."""
        return {
            'hp': self.hp,
            'chakra': self.chakra,
            'stamina': self.stamina,
            'strength': self.strength,
            'speed': self.speed,
            'defense': self.defense,
            'willpower': self.willpower,
            'chakra_control': self.chakra_control,
            'intelligence': self.intelligence,
            'perception': self.perception,
            'ninjutsu': self.ninjutsu,
            'taijutsu': self.taijutsu,
            'genjutsu': self.genjutsu
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create a character from a dictionary.
        
        Args:
            data: Dictionary containing character data
            
        Returns:
            Character instance
        """
        # Ensure sets are correctly initialized from lists in the data
        data['achievements'] = set(data.get('achievements', []))
        data['completed_missions'] = set(data.get('completed_missions', []))
        # Titles are already a list
        # Ensure wins_against_rank is initialized
        data['wins_against_rank'] = data.get('wins_against_rank', {})
        
        # Add defaults for potentially missing fields for backward compatibility
        data["accuracy"] = data.get("accuracy", 50)
        data["evasion"] = data.get("evasion", 50)
        data["crit_chance"] = data.get("crit_chance", 0.05)
        data["crit_damage"] = data.get("crit_damage", 1.5)
        data["elemental_affinity"] = data.get("elemental_affinity", None)
        data["stat_points"] = data.get("stat_points", 0) # Added
        
        # Filter out keys not present in Character fields
        field_names = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary.
        
        Returns:
            Dictionary containing character data
        """
        data = {
            "id": self.id,
            "name": self.name,
            "clan": self.clan,
            "level": self.level,
            "exp": self.exp,
            # "ryo": self.ryo, # REMOVED
            "specialization": self.specialization,
            "rank": self.rank,
            "hp": self.hp,
            "chakra": self.chakra,
            "stamina": self.stamina,
            "strength": self.strength,
            "speed": self.speed,
            "defense": self.defense,
            "willpower": self.willpower,
            "chakra_control": self.chakra_control,
            "intelligence": self.intelligence,
            "perception": self.perception,
            "accuracy": self.accuracy,
            "evasion": self.evasion,
            "crit_chance": self.crit_chance,
            "crit_damage": self.crit_damage,
            "elemental_affinity": self.elemental_affinity,
            "ninjutsu": self.ninjutsu,
            "taijutsu": self.taijutsu,
            "genjutsu": self.genjutsu,
            "jutsu": self.jutsu,
            "equipment": self.equipment,
            "inventory": self.inventory,
            "is_active": self.is_active,
            "status_effects": self.status_effects,
            "active_effects": self.active_effects,
            "status_conditions": self.status_conditions,
            "buffs": self.buffs,
            "debuffs": self.debuffs,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "stat_points": self.stat_points, # Added
            "wins_against_rank": self.wins_against_rank,
            "max_hp": self.max_hp,
            "max_chakra": self.max_chakra,
            "max_stamina": self.max_stamina,
            "completed_missions": sorted(list(self.completed_missions)),
            "jutsu_mastery": self.jutsu_mastery,
            "last_daily_claim": self.last_daily_claim,
            "active_mission_id": self.active_mission_id,
            "achievements": sorted(list(self.achievements)),
            "titles": self.titles,
            "equipped_title": self.equipped_title,
            "clan_rank": self.clan_rank,
            "clan_exp": self.clan_exp,
            "clan_achievements": sorted(list(self.clan_achievements)),
            "clan_skills": self.clan_skills,
            "clan_jutsu_mastery": self.clan_jutsu_mastery,
            "clan_contribution_points": self.clan_contribution_points,
            "clan_role": self.clan_role,
            "clan_joined_at": self.clan_joined_at.isoformat() if self.clan_joined_at else None,
        }
        return data
    
    def add_exp(self, amount: int) -> bool:
        """Add experience points to the character.
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            True if character leveled up at least once
        """
        self.exp += amount
        leveled_up = False
        while self.exp >= self.level * 100:
            if self.level_up():
                leveled_up = True
        return leveled_up
    
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
    
    def add_item(self, item_id: str, quantity: int = 1) -> bool:
        """Add an item (or stack) to the character's inventory.
        
        Args:
            item_id: ID of item to add
            quantity: Number of items to add (default: 1)
            
        Returns:
            True (always succeeds for now)
        """
        if quantity <= 0:
            return False  # Cannot add zero or negative quantity
        
        current_quantity = self.inventory.get(item_id, 0)
        self.inventory[item_id] = current_quantity + quantity
        logger.debug(f"Added {quantity} of {item_id} to {self.id}. New count: {self.inventory[item_id]}")
        return True
    
    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """Remove an item (or stack) from the character's inventory.
        
        Args:
            item_id: ID of item to remove
            quantity: Number of items to remove (default: 1)
            
        Returns:
            True if items were successfully removed, False otherwise.
        """
        if quantity <= 0:
            return False  # Cannot remove zero or negative quantity
        
        current_quantity = self.inventory.get(item_id, 0)
        
        if current_quantity < quantity:
            logger.warning(f"Cannot remove {quantity} of {item_id} from {self.id}. Only has {current_quantity}")
            return False  # Not enough items to remove
        
        new_quantity = current_quantity - quantity
        if new_quantity <= 0:
            del self.inventory[item_id]
            logger.debug(f"Removed {quantity} of {item_id} from {self.id}. Item removed from inventory.")
        else:
            self.inventory[item_id] = new_quantity
            logger.debug(f"Removed {quantity} of {item_id} from {self.id}. New count: {new_quantity}")
        
        return True
    
    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Check if the character has at least a certain quantity of an item.
        
        Args:
            item_id: ID of item to check
            quantity: Number of items to check for
            
        Returns:
            True if the character has at least the specified quantity of the item, False otherwise.
        """
        return self.inventory.get(item_id, 0) >= quantity
    
    def equip_item(self, item_id: str, slot: str) -> bool:
        """Equip an item to a slot.
        
        Assumes the item exists in inventory.
        
        Args:
            item_id: ID of item to equip
            slot: Equipment slot to use (e.g., 'weapon', 'chest')
            
        Returns:
            True if item was equipped, False otherwise.
        """
        if not self.has_item(item_id):
            logger.warning(f"Attempted to equip {item_id} for {self.id}, but item not in inventory.")
            return False
        
        # Unequip existing item in the slot, if any
        if slot in self.equipment:
            old_item_id = self.equipment[slot]
            self.add_item(old_item_id, 1)  # Add previously equipped item back to inventory
            logger.debug(f"Unequipped {old_item_id} from {slot} for {self.id} to equip {item_id}.")
        
        # Remove one count of the item from inventory and equip it
        if self.remove_item(item_id, 1):
            self.equipment[slot] = item_id
            logger.info(f"Equipped {item_id} to {slot} for {self.id}.")
            return True
        else:
            # Should not happen if has_item passed, but log defensively
            logger.error(f"Failed to remove {item_id} from inventory during equip for {self.id}, despite has_item check passing.")
            # Need to potentially revert adding the old item back? Complex state.
            return False
    
    def unequip_item(self, slot: str) -> bool:
        """Unequip an item from a slot.
        
        Args:
            slot: Equipment slot to unequip from
            
        Returns:
            True if item was unequipped, False if slot was empty.
        """
        if slot not in self.equipment:
            return False
        
        item_id = self.equipment[slot]
        del self.equipment[slot]
        self.add_item(item_id, 1)  # Add unequipped item back to inventory
        logger.info(f"Unequipped {item_id} from {slot} for {self.id}.")
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
    
    def record_battle_result(self, result: str, opponent_rank: Optional[str] = None):
        """Records the result of a battle (win, loss, draw).
        
        Args:
            result: 'win', 'loss', or 'draw'.
            opponent_rank: The rank of the opponent (used for win tracking).
        """
        if result == 'win':
            self.wins += 1
            if opponent_rank:
                current_count = self.wins_against_rank.get(opponent_rank, 0)
                self.wins_against_rank[opponent_rank] = current_count + 1
        elif result == 'loss':
            self.losses += 1
        elif result == 'draw':
            self.draws += 1
        else:
            logger.warning(f"Unknown battle result '{result}' passed to record_battle_result for {self.id}") 