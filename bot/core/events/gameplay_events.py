import logging
from typing import Optional, List
from .event_trigger_engine import EventTriggerEngine

logger = logging.getLogger(__name__)

class GameplayEventHandler:
    """Handles automatic triggering of lore and announcements during gameplay."""
    
    def __init__(self, event_engine: EventTriggerEngine):
        """Initialize the gameplay event handler.
        
        Args:
            event_engine: Event trigger engine for sending lore and announcements
        """
        self.event_engine = event_engine
        
    async def handle_character_creation(self, character_name: str, clan: Optional[str] = None) -> None:
        """Handle character creation event.
        
        Args:
            character_name: Name of the created character
            clan: Optional clan the character belongs to
        """
        try:
            # Trigger character creation lore
            await self.event_engine.trigger_event(
                event_type="character_creation",
                target_clans=[clan] if clan else None,
                ping_everyone=False
            )
            
            logger.info(f"Character creation event handled for {character_name}")
            
        except Exception as e:
            logger.error(f"Error handling character creation event: {e}")
            
    async def handle_training_complete(
        self,
        character_name: str,
        technique_name: str,
        clan: Optional[str] = None
    ) -> None:
        """Handle training completion event.
        
        Args:
            character_name: Name of the character
            technique_name: Name of the completed technique
            clan: Optional clan the character belongs to
        """
        try:
            # Trigger training completion lore
            await self.event_engine.trigger_event(
                event_type="training_complete",
                target_clans=[clan] if clan else None,
                ping_everyone=False
            )
            
            logger.info(f"Training completion event handled for {character_name} - {technique_name}")
            
        except Exception as e:
            logger.error(f"Error handling training completion event: {e}")
            
    async def handle_battle_outcome(
        self,
        winner_name: str,
        loser_name: str,
        winner_clan: Optional[str] = None,
        loser_clan: Optional[str] = None
    ) -> None:
        """Handle battle outcome event.
        
        Args:
            winner_name: Name of the victorious character
            loser_name: Name of the defeated character
            winner_clan: Optional clan of the winner
            loser_clan: Optional clan of the loser
        """
        try:
            # Trigger victory lore for winner's clan
            if winner_clan:
                await self.event_engine.trigger_event(
                    event_type="battle_victory",
                    target_clans=[winner_clan],
                    ping_everyone=False
                )
                
            # Trigger defeat lore for loser's clan
            if loser_clan:
                await self.event_engine.trigger_event(
                    event_type="battle_defeat",
                    target_clans=[loser_clan],
                    ping_everyone=False
                )
                
            logger.info(f"Battle outcome event handled - Winner: {winner_name}, Loser: {loser_name}")
            
        except Exception as e:
            logger.error(f"Error handling battle outcome event: {e}")
            
    async def handle_quest_completion(
        self,
        character_name: str,
        quest_name: str,
        clan: Optional[str] = None
    ) -> None:
        """Handle quest completion event.
        
        Args:
            character_name: Name of the character
            quest_name: Name of the completed quest
            clan: Optional clan the character belongs to
        """
        try:
            # Trigger quest completion lore
            await self.event_engine.trigger_event(
                event_type="quest_complete",
                target_clans=[clan] if clan else None,
                ping_everyone=False
            )
            
            logger.info(f"Quest completion event handled for {character_name} - {quest_name}")
            
        except Exception as e:
            logger.error(f"Error handling quest completion event: {e}")
            
    async def handle_clan_change(
        self,
        character_name: str,
        old_clan: Optional[str],
        new_clan: Optional[str]
    ) -> None:
        """Handle clan change event.
        
        Args:
            character_name: Name of the character
            old_clan: Previous clan (if any)
            new_clan: New clan (if any)
        """
        try:
            # Trigger clan leave lore for old clan
            if old_clan:
                await self.event_engine.trigger_event(
                    event_type="clan_leave",
                    target_clans=[old_clan],
                    ping_everyone=False
                )
                
            # Trigger clan join lore for new clan
            if new_clan:
                await self.event_engine.trigger_event(
                    event_type="clan_join",
                    target_clans=[new_clan],
                    ping_everyone=False
                )
                
            logger.info(f"Clan change event handled for {character_name} - Old: {old_clan}, New: {new_clan}")
            
        except Exception as e:
            logger.error(f"Error handling clan change event: {e}") 