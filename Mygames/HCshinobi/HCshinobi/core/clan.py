"""Clan model module."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Clan:
    """Clan model class."""
    
    name: str
    description: str
    rarity: str
    leader_id: Optional[str] = None
    members: List[int] = field(default_factory=list)
    level: int = 1
    xp: int = 0
    lore: Optional[str] = None
    base_weight: Optional[float] = None
    strength_bonus: int = 0
    defense_bonus: int = 0
    speed_bonus: int = 0
    suggested_personalities: Optional[List[str]] = None
    starting_jutsu: Optional[List[str]] = None
    village: Optional[str] = None
    kekkei_genkai: Optional[List[str]] = None
    traits: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert clan to dictionary.
        
        Returns:
            Dictionary representation of clan
        """
        return {
            'name': self.name,
            'description': self.description,
            'rarity': self.rarity,
            'leader_id': self.leader_id,
            'members': self.members,
            'level': self.level,
            'xp': self.xp,
            'lore': self.lore,
            'base_weight': self.base_weight,
            'strength_bonus': self.strength_bonus,
            'defense_bonus': self.defense_bonus,
            'speed_bonus': self.speed_bonus,
            'suggested_personalities': self.suggested_personalities,
            'starting_jutsu': self.starting_jutsu,
            'village': self.village,
            'kekkei_genkai': self.kekkei_genkai,
            'traits': self.traits
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Clan':
        """Create clan from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            Clan instance
        """
        return cls(
            name=data['name'],
            description=data['description'],
            rarity=data['rarity'],
            leader_id=data.get('leader_id'),
            members=data.get('members', []),
            level=data.get('level', 1),
            xp=data.get('xp', 0),
            lore=data.get('lore'),
            base_weight=data.get('base_weight'),
            strength_bonus=data.get('strength_bonus', 0),
            defense_bonus=data.get('defense_bonus', 0),
            speed_bonus=data.get('speed_bonus', 0),
            suggested_personalities=data.get('suggested_personalities'),
            starting_jutsu=data.get('starting_jutsu'),
            village=data.get('village'),
            kekkei_genkai=data.get('kekkei_genkai'),
            traits=data.get('traits')
        ) 