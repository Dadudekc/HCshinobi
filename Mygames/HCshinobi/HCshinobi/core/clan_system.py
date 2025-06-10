"""
Core clan system implementation.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
from datetime import datetime

from .database import Database

# Add forward reference typing if needed
if TYPE_CHECKING:
    from .character_system import CharacterSystem
    from .progression_engine import ShinobiProgressionEngine

logger = logging.getLogger(__name__)

class ClanSystem:
    """Manages clan-related functionality."""

    def __init__(self, db: Database, character_system: 'CharacterSystem', progression_engine: 'ShinobiProgressionEngine'):
        """
        Initialize the clan system.

        Args:
            db: Database instance
            character_system: Character system instance
            progression_engine: Progression engine instance
        """
        self.db = db
        self.character_system = character_system
        self.progression_engine = progression_engine
        self.logger = logging.getLogger(__name__)

    async def get_clans(self, village: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all clans, optionally filtered by village.

        Args:
            village: Optional village to filter by

        Returns:
            List of clan dictionaries
        """
        query = "SELECT * FROM clans"
        params = []
        if village:
            query += " WHERE village = ?"
            params.append(village)
        
        return await self.db.fetch_all(query, params)

    async def join_clan(self, character: Dict[str, Any], clan_name: str) -> Tuple[bool, str]:
        """
        Attempt to have a character join a clan.

        Args:
            character: Character dictionary
            clan_name: Name of the clan to join

        Returns:
            Tuple of (success, message)
        """
        # Check if character is already in a clan
        if character.get('clan'):
            return False, "You are already in a clan! Leave your current clan first."

        # Get clan info
        clan = await self.db.fetch_one(
            "SELECT * FROM clans WHERE name = ?",
            [clan_name]
        )
        if not clan:
            return False, f"Clan '{clan_name}' not found!"

        # Check clan requirements
        if not await self._check_clan_requirements(character, clan):
            return False, f"You do not meet the requirements to join {clan_name}!"

        # Initialize clan progression data
        now = datetime.utcnow()
        character['clan'] = clan_name
        character['clan_joined_at'] = now

        # Update character's clan
        await self.db.execute(
            "UPDATE characters SET clan = ?, clan_joined_at = ? WHERE id = ?",
            [clan_name, now, character['id']]
        )

        # Update clan population
        await self.db.execute(
            "UPDATE clans SET population = population + 1 WHERE name = ?",
            [clan_name]
        )

        # Grant initial clan jutsu if available
        if clan.get('starting_jutsu'):
            for jutsu in clan['starting_jutsu']:
                await self.character_system.add_jutsu(character['id'], jutsu)

        # Check for clan-join achievements using progression engine
        if self.progression_engine:
            await self.progression_engine.check_clan_achievements(character)

        return True, f"Successfully joined the {clan_name} clan!"

    async def leave_clan(self, character: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Have a character leave their current clan.

        Args:
            character: Character dictionary

        Returns:
            Tuple of (success, message)
        """
        if not character.get('clan'):
            return False, "You are not in a clan!"

        clan_name = character['clan']

        # Update character
        await self.db.execute(
            "UPDATE characters SET clan = NULL, clan_joined_at = NULL WHERE id = ?",
            [character['id']]
        )

        # Update clan population
        await self.db.execute(
            "UPDATE clans SET population = population - 1 WHERE name = ?",
            [clan_name]
        )

        return True, f"Successfully left the {clan_name} clan!"

    async def get_clan_info(self, clan_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a clan.

        Args:
            clan_name: Name of the clan

        Returns:
            Clan dictionary or None if not found
        """
        return await self.db.fetch_one(
            "SELECT * FROM clans WHERE name = ?",
            [clan_name]
        )

    async def get_clan_members(self, clan_name: str) -> List[Dict[str, Any]]:
        """
        Get all members of a clan.

        Args:
            clan_name: Name of the clan

        Returns:
            List of character dictionaries
        """
        return await self.db.fetch_all(
            "SELECT * FROM characters WHERE clan = ? ORDER BY level DESC",
            [clan_name]
        )

    async def get_clan_rankings(self, village: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get clan rankings based on total power.

        Args:
            village: Optional village to filter by

        Returns:
            List of clan dictionaries with rankings
        """
        query = """
            SELECT c.*, 
                   (SELECT SUM(ch.level * (ch.strength + ch.speed + ch.defense + ch.chakra))
                    FROM characters ch 
                    WHERE ch.clan = c.name) as power
            FROM clans c
        """
        params = []
        if village:
            query += " WHERE c.village = ?"
            params.append(village)
        query += " ORDER BY power DESC"

        return await self.db.fetch_all(query, params)

    async def _check_clan_requirements(self, character: Dict[str, Any], clan: Dict[str, Any]) -> bool:
        """
        Check if a character meets the requirements to join a clan.

        Args:
            character: Character dictionary
            clan: Clan dictionary

        Returns:
            True if requirements are met, False otherwise
        """
        # Check village requirement if clan has one
        if clan.get('required_village'):
            if character['village'] != clan['required_village']:
                return False

        # Check minimum level requirement
        if clan.get('required_level', 0) > character['level']:
            return False

        # Check minimum stats requirements
        for stat in ['strength', 'speed', 'defense', 'chakra']:
            if clan.get(f'required_{stat}', 0) > character[stat]:
                return False

        return True 