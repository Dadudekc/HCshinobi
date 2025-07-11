from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional

@dataclass
class Character:
    id: str
    name: str
    clan: str = ""
    level: int = 1
    rank: str = "Genin"
    hp: int = 100
    max_hp: int = 100
    chakra: int = 50
    max_chakra: int = 50
    stamina: int = 50
    max_stamina: int = 50
    strength: int = 10
    defense: int = 5
    speed: int = 5
    ninjutsu: int = 5
    genjutsu: int = 5
    taijutsu: int = 5
    wins: int = 0
    losses: int = 0
    draws: int = 0
    wins_against_rank: Dict[str, int] = field(default_factory=dict)
    
    # Additional fields to match existing character files
    exp: int = 0
    specialization: Optional[str] = None
    willpower: int = 10
    chakra_control: int = 10
    intelligence: int = 10
    perception: int = 10
    jutsu: List[str] = field(default_factory=list)
    equipment: Dict[str, Any] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    is_active: bool = True
    status_effects: List[str] = field(default_factory=list)
    active_effects: Dict[str, Any] = field(default_factory=dict)
    status_conditions: Dict[str, Any] = field(default_factory=dict)
    buffs: Dict[str, Any] = field(default_factory=dict)
    debuffs: Dict[str, Any] = field(default_factory=dict)
    achievements: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    completed_missions: List[str] = field(default_factory=list)
    jutsu_mastery: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_daily_claim: Optional[str] = None
    active_mission_id: Optional[str] = None
