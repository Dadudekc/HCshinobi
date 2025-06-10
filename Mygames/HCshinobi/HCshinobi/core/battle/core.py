"""
Core battle system implementation.
"""
import logging
import asyncio
import os
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
import random

from ..character_system import CharacterSystem
from ..constants import BATTLES_SUBDIR, ACTIVE_BATTLES_FILENAME, BATTLE_HISTORY_FILENAME
from ...utils.file_io import load_json, save_json
from .state import BattleState, deserialize_battle_state

logger = logging.getLogger(__name__)

class BattleSystem:
    """System for managing character battles."""

    def __init__(
        self,
        character_system: CharacterSystem,
        data_dir: Optional[str] = None,
        progression_engine: Optional[Any] = None,
        master_jutsu_data: Optional[Dict[str, Dict]] = None
    ):
        """
        Initialize the battle system.

        Args:
            character_system: Character system for managing characters
            data_dir: Directory for storing battle-related data (optional)
            progression_engine: Instance of the progression engine (optional)
            master_jutsu_data: Dictionary containing all loaded jutsu definitions (optional)
        """
        # Set up logger first to ensure it's available everywhere
        self.logger = logging.getLogger(__name__)
        
        # Set up data directories with default if not specified
        self.base_data_dir = data_dir or "data"
        self.battles_data_dir = os.path.join(self.base_data_dir, BATTLES_SUBDIR)
        os.makedirs(self.battles_data_dir, exist_ok=True)

        self.active_battles_file = os.path.join(self.battles_data_dir, ACTIVE_BATTLES_FILENAME)
        self.battle_history_file = os.path.join(self.battles_data_dir, BATTLE_HISTORY_FILENAME)

        self.character_system = character_system
        self.progression_engine = progression_engine
        self.master_jutsu_data = master_jutsu_data or {}

        self.active_battles: Dict[str, BattleState] = {}
        self.battle_history: Dict[str, List[str]] = {}
        self.battle_tasks: Dict[str, asyncio.Task] = {}
        self._load_lock = asyncio.Lock()
        
        # Store reference to bot (will be set in ready_hook)
        self.bot = None

        self.logger.info(f"BattleSystem initialized. Data dir: {self.battles_data_dir}")

    async def load_active_battles(self) -> None:
        """Load active battles from disk."""
        async with self._load_lock:
            try:
                data = await load_json(self.active_battles_file)
                if not data:
                    self.logger.info("No active battles found to load.")
                    return

                self.active_battles = {}
                for battle_id, battle_data in data.items():
                    battle_state = await deserialize_battle_state(battle_data)
                    if battle_state:
                        self.active_battles[battle_id] = battle_state
                        self.logger.info(f"Loaded battle {battle_id}")

                self.logger.info(f"Loaded {len(self.active_battles)} active battles")
            except Exception as e:
                self.logger.error(f"Error loading active battles: {e}", exc_info=True)

    async def save_active_battles(self) -> None:
        """Save active battles to disk."""
        async with self._load_lock:
            try:
                data = {
                    battle_id: battle_state.to_dict()
                    for battle_id, battle_state in self.active_battles.items()
                }
                await save_json(self.active_battles_file, data)
                self.logger.info(f"Saved {len(data)} active battles")
            except Exception as e:
                self.logger.error(f"Error saving active battles: {e}", exc_info=True)

    def _add_to_battle_log(self, battle: BattleState, message: str) -> None:
        """Add a message to the battle log."""
        battle.battle_log.append(f"{datetime.now(timezone.utc).isoformat()} - {message}")
        self.logger.info(f"Battle {battle.id}: {message}")

    async def _handle_battle_end(self, battle: BattleState, battle_id: str) -> None:
        """Handle cleanup when a battle ends."""
        # Save battle to history
        if battle_id not in self.battle_history:
            self.battle_history[battle_id] = []
        self.battle_history[battle_id].extend(battle.battle_log)

        # Remove from active battles
        if battle_id in self.active_battles:
            del self.active_battles[battle_id]

        # Cancel any ongoing battle task
        if battle_id in self.battle_tasks:
            self.battle_tasks[battle_id].cancel()
            del self.battle_tasks[battle_id]

        # Save changes
        await self.save_active_battles()
        await self._save_battle_history()

    async def _save_battle_history(self) -> None:
        """Save battle history to disk."""
        try:
            await save_json(self.battle_history_file, self.battle_history)
            self.logger.info(f"Saved battle history with {len(self.battle_history)} battles")
        except Exception as e:
            self.logger.error(f"Error saving battle history: {e}", exc_info=True)

def resolve_attack(attacker: Dict, defender: Dict, attack_type: str = "basic") -> Dict:
    """
    Resolve an attack between two characters.
    
    Args:
        attacker: Dictionary containing attacker stats and state
        defender: Dictionary containing defender stats and state
        attack_type: Type of attack ("basic", "jutsu", etc.)
        
    Returns:
        Dict containing damage dealt, critical hit info, and effects
    """
    # Calculate base damage
    base_damage = attacker.get("attack", 10)
    defense = defender.get("defense", 5)
    
    # Apply type effectiveness
    type_multiplier = 1.0
    if attack_type == "jutsu":
        attacker_element = attacker.get("element", "none")
        defender_element = defender.get("element", "none")
        type_multiplier = get_element_effectiveness(attacker_element, defender_element)
    
    # Calculate critical hit
    crit_chance = attacker.get("critical_rate", 0.05)
    is_critical = random.random() < crit_chance
    crit_multiplier = 1.5 if is_critical else 1.0
    
    # Calculate final damage
    damage = max(1, int((base_damage - defense * 0.5) * type_multiplier * crit_multiplier))
    
    return {
        "damage": damage,
        "is_critical": is_critical,
        "type_multiplier": type_multiplier,
        "effects": []  # Status effects, if any
    }

def get_element_effectiveness(attacker_element: str, defender_element: str) -> float:
    """Get elemental effectiveness multiplier."""
    effectiveness = {
        "fire": {"wind": 1.5, "water": 0.5},
        "water": {"fire": 1.5, "earth": 0.5},
        "earth": {"lightning": 1.5, "wind": 0.5},
        "lightning": {"water": 1.5, "earth": 0.5},
        "wind": {"lightning": 1.5, "fire": 0.5}
    }
    
    return effectiveness.get(attacker_element, {}).get(defender_element, 1.0) 