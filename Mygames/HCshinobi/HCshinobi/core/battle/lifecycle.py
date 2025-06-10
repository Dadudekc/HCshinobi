"""
Battle lifecycle management.
"""
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
import uuid

from .state import BattleState, BattleParticipant
from .persistence import BattlePersistence
from .types import BattleLogCallback
from ..character import Character
from ..character_system import CharacterSystem
from ..progression_engine import ShinobiProgressionEngine

logger = logging.getLogger(__name__)

class BattleLifecycle:
    """Manages the lifecycle of battles."""

    def __init__(
        self,
        character_system: CharacterSystem,
        persistence: BattlePersistence,
        progression_engine: Optional[ShinobiProgressionEngine] = None,
        master_jutsu_data: Optional[Dict[str, Dict]] = None,
        battle_timeout: int = 300  # 5 minutes in seconds
    ):
        """
        Initialize battle lifecycle manager.

        Args:
            character_system: Character system for managing characters
            persistence: Battle persistence manager
            progression_engine: Instance of the progression engine (optional)
            master_jutsu_data: Dictionary containing all loaded jutsu definitions (optional)
            battle_timeout: Time in seconds before a battle is considered inactive
        """
        self.character_system = character_system
        self.persistence = persistence
        self.progression_engine = progression_engine
        self.master_jutsu_data = master_jutsu_data or {}
        self.battle_timeout = battle_timeout

        self.battle_tasks: Dict[str, asyncio.Task] = {}
        self.bot = None  # Will be set in ready_hook

    def _add_to_battle_log(self, battle: BattleState, message: str) -> None:
        """Add a message to the battle log."""
        battle.battle_log.append(f"{datetime.now(timezone.utc).isoformat()} - {message}")
        logger.info(f"Battle {battle.id}: {message}")

    async def handle_battle_end(self, battle: BattleState, battle_id: str) -> None:
        """
        Handle cleanup when a battle ends.

        Args:
            battle: Battle state that ended
            battle_id: ID of the battle
        """
        # Save battle to history
        await self.persistence.add_battle_to_history(battle_id, battle)

        # Remove from active battles
        await self.persistence.remove_active_battle(battle_id)

        # Cancel any ongoing battle task
        if battle_id in self.battle_tasks:
            self.battle_tasks[battle_id].cancel()
            del self.battle_tasks[battle_id]

        # Award experience if progression engine is available
        if self.progression_engine and battle.winner_id:
            exp_gain = self._calculate_exp_gain(battle)
            if exp_gain > 0:
                winner = battle.attacker if battle.winner_id == battle.attacker.id else battle.defender
                await self.progression_engine.award_battle_experience(winner.id, exp_gain)
                self._add_to_battle_log(battle, f"{winner.character.name} gained {exp_gain} experience!")

    def _calculate_exp_gain(self, battle: BattleState) -> int:
        """
        Calculate experience gain for winning a battle.

        Args:
            battle: Completed battle state

        Returns:
            Amount of experience to award
        """
        if not battle.winner_id:
            return 0

        winner = battle.attacker if battle.winner_id == battle.attacker.id else battle.defender
        loser = battle.defender if battle.winner_id == battle.attacker.id else battle.attacker

        # Base experience
        base_exp = 100

        # Level difference modifier (Access level via participant.character)
        level_diff = loser.character.level - winner.character.level
        level_mod = 1.0 + (0.1 * level_diff)  # 10% more/less per level difference
        level_mod = max(0.5, min(1.5, level_mod))  # Cap between 50% and 150%

        # Turn count modifier - reward faster victories
        turn_mod = 1.0 - (0.05 * (battle.turn_number - 1))  # -5% per turn after first
        turn_mod = max(0.5, turn_mod)  # Don't go below 50%

        # Calculate final experience
        exp_gain = int(base_exp * level_mod * turn_mod)
        return max(1, exp_gain)  # Ensure at least 1 exp

    async def cleanup_inactive_battles(self) -> None:
        """Clean up battles that have timed out."""
        now = datetime.now(timezone.utc)
        timeout_threshold = now - timedelta(seconds=self.battle_timeout)

        for battle_id, battle in list(self.persistence.active_battles.items()):
            if not battle.is_active:
                continue

            if not battle.last_action or battle.last_action < timeout_threshold:
                logger.info(f"Battle {battle_id} timed out after {self.battle_timeout} seconds of inactivity")
                
                # Set battle as inactive
                battle.is_active = False
                battle.end_reason = "timeout"
                
                # Notify players if bot is available
                if self.bot:
                    await self.notify_players_battle_timeout(
                        battle.attacker.id,
                        battle.defender.id
                    )
                
                # Handle battle end
                await self.handle_battle_end(battle, battle_id)

    async def notify_players_battle_timeout(self, attacker_id: str, defender_id: str) -> None:
        """
        Notify players that their battle has timed out.

        Args:
            attacker_id: ID of the attacker
            defender_id: ID of the defender
        """
        if not self.bot:
            return

        message = "Your battle has timed out due to inactivity!"
        
        try:
            attacker = await self.bot.fetch_user(attacker_id)
            if attacker:
                await attacker.send(message)
        except Exception as e:
            logger.error(f"Error notifying attacker {attacker_id}: {e}")

        try:
            defender = await self.bot.fetch_user(defender_id)
            if defender:
                await defender.send(message)
        except Exception as e:
            logger.error(f"Error notifying defender {defender_id}: {e}")

    async def ready_hook(self, bot: Any) -> None:
        """
        Hook called when the bot is ready.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        
        # Start battle timeout check task
        asyncio.create_task(self._battle_timeout_check())

    async def _battle_timeout_check(self) -> None:
        """Background task to check for timed out battles."""
        while True:
            try:
                await self.cleanup_inactive_battles()
            except Exception as e:
                logger.error(f"Error in battle timeout check: {e}", exc_info=True)
            
            await asyncio.sleep(60)  # Check every minute

    async def shutdown(self) -> None:
        """Clean up when shutting down."""
        # Cancel all battle tasks
        for task in self.battle_tasks.values():
            task.cancel()
        
        # Save current state
        await self.persistence.save_active_battles()
        await self.persistence.save_battle_history()

async def initialize_battle(
    attacker: Character,
    defender: Character,
    persistence: BattlePersistence,
    add_to_battle_log: Optional[BattleLogCallback] = None
) -> Tuple[str, BattleState]:
    """
    Initialize a new battle between two characters.

    Args:
        attacker: Character initiating the battle
        defender: Character being attacked
        persistence: Battle persistence manager
        add_to_battle_log: Optional callback for logging battle events

    Returns:
        Tuple of (battle_id, battle_state)
    """
    battle_id = str(uuid.uuid4())
    
    battle = BattleState(
        id=battle_id,
        attacker=BattleParticipant(
            id=attacker.id,
            name=attacker.name,
            level=attacker.level,
            max_hp=attacker.max_hp
        ),
        defender=BattleParticipant(
            id=defender.id,
            name=defender.name,
            level=defender.level,
            max_hp=defender.max_hp
        ),
        turn_number=1,
        current_turn_player_id=attacker.id,
        is_active=True,
        battle_log=[],
        attacker_hp=attacker.max_hp,
        defender_hp=defender.max_hp,
        attacker_effects=[],
        defender_effects=[],
        last_action=datetime.now(timezone.utc)
    )

    if add_to_battle_log:
        add_to_battle_log(battle, f"Battle initiated between {attacker.name} and {defender.name}!")

    await persistence.add_active_battle(battle_id, battle)
    return battle_id, battle

async def cleanup_battle(
    battle_id: str,
    persistence: BattlePersistence
) -> None:
    """
    Clean up a battle's resources.

    Args:
        battle_id: ID of the battle to clean up
        persistence: Battle persistence manager
    """
    # Get the battle state
    battle = persistence.active_battles.get(battle_id)
    if not battle:
        return

    # Add to history and remove from active battles
    await persistence.add_battle_to_history(battle_id, battle)
    await persistence.remove_active_battle(battle_id) 