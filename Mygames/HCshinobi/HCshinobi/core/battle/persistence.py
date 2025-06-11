"""
Battle state persistence and serialization.
"""
import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .state import BattleState, deserialize_battle_state
from ..constants import BATTLES_SUBDIR, ACTIVE_BATTLES_FILENAME, BATTLE_HISTORY_FILENAME
from HCshinobi.utils.file_io import async_load_json as load_json, async_save_json as save_json

logger = logging.getLogger(__name__)

class BattlePersistence:
    """Handles persistence of battle states and history."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize battle persistence.

        Args:
            data_dir: Directory for storing battle-related data (optional)
        """
        self.base_data_dir = data_dir or "data"
        self.battles_data_dir = os.path.join(self.base_data_dir, BATTLES_SUBDIR)
        os.makedirs(self.battles_data_dir, exist_ok=True)

        self.active_battles_file = os.path.join(self.battles_data_dir, ACTIVE_BATTLES_FILENAME)
        self.battle_history_file = os.path.join(self.battles_data_dir, BATTLE_HISTORY_FILENAME)
        
        self._load_lock = asyncio.Lock()
        self.active_battles: Dict[str, BattleState] = {}
        self.battle_history: Dict[str, List[str]] = {}

    async def load_active_battles(self) -> Dict[str, BattleState]:
        """
        Load active battles from disk.

        Returns:
            Dictionary of battle ID to BattleState
        """
        async with self._load_lock:
            try:
                data = await load_json(self.active_battles_file)
                if not data:
                    logger.info("No active battles found to load.")
                    return {}

                battles = {}
                for battle_id, battle_data in data.items():
                    battle_state = await deserialize_battle_state(battle_data)
                    if battle_state:
                        battles[battle_id] = battle_state
                        logger.info(f"Loaded battle {battle_id}")

                logger.info(f"Loaded {len(battles)} active battles")
                self.active_battles = battles
                return battles
            except Exception as e:
                logger.error(f"Error loading active battles: {e}", exc_info=True)
                return {}

    async def save_active_battles(self, battles: Optional[Dict[str, BattleState]] = None) -> None:
        """
        Save active battles to disk.

        Args:
            battles: Dictionary of battle ID to BattleState to save. If None, uses internal state.
        """
        async with self._load_lock:
            try:
                battles_to_save = battles if battles is not None else self.active_battles
                data = {
                    battle_id: battle_state.to_dict()
                    for battle_id, battle_state in battles_to_save.items()
                }
                await save_json(self.active_battles_file, data)
                logger.info(f"Saved {len(data)} active battles")
            except Exception as e:
                logger.error(f"Error saving active battles: {e}", exc_info=True)

    async def load_battle_history(self) -> Dict[str, List[str]]:
        """
        Load battle history from disk.

        Returns:
            Dictionary of battle ID to list of battle log messages
        """
        try:
            data = await load_json(self.battle_history_file)
            self.battle_history = data or {}
            logger.info(f"Loaded battle history with {len(self.battle_history)} battles")
            return self.battle_history
        except Exception as e:
            logger.error(f"Error loading battle history: {e}", exc_info=True)
            return {}

    async def save_battle_history(self, history: Optional[Dict[str, List[str]]] = None) -> None:
        """
        Save battle history to disk.

        Args:
            history: Dictionary of battle ID to list of battle log messages. If None, uses internal state.
        """
        try:
            history_to_save = history if history is not None else self.battle_history
            await save_json(self.battle_history_file, history_to_save)
            logger.info(f"Saved battle history with {len(history_to_save)} battles")
        except Exception as e:
            logger.error(f"Error saving battle history: {e}", exc_info=True)

    async def add_battle_to_history(self, battle_id: str, battle: BattleState) -> None:
        """
        Add a battle's log to the history.

        Args:
            battle_id: ID of the battle
            battle: Battle state to add to history
        """
        if battle_id not in self.battle_history:
            self.battle_history[battle_id] = []
        self.battle_history[battle_id].extend(battle.battle_log)
        await self.save_battle_history()

    async def remove_active_battle(self, battle_id: str) -> None:
        """
        Remove a battle from active battles.

        Args:
            battle_id: ID of the battle to remove
        """
        if battle_id in self.active_battles:
            del self.active_battles[battle_id]
            await self.save_active_battles()

    async def add_active_battle(self, battle_id: str, battle: BattleState) -> None:
        """
        Add a battle to active battles.

        Args:
            battle_id: ID of the battle
            battle: Battle state to add
        """
        self.active_battles[battle_id] = battle
        await self.save_active_battles() 