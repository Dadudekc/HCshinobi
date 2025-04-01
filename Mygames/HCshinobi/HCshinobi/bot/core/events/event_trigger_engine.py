import json
import logging
from typing import Optional, Dict, List
from pathlib import Path
from ..notifications.notification_dispatcher import NotificationDispatcher
from ..notifications.templates import lore_drop, Theme

logger = logging.getLogger(__name__)

class EventTriggerEngine:
    """Handles event-driven lore drops and announcements."""
    
    def __init__(self, notification_dispatcher: NotificationDispatcher):
        """Initialize the event trigger engine.
        
        Args:
            notification_dispatcher: Notification dispatcher for sending announcements
        """
        self.dispatcher = notification_dispatcher
        self.lore_registry = self._load_lore_registry()
        self.trigger_types = self.lore_registry.get("trigger_types", [])
        
    def _load_lore_registry(self) -> Dict:
        """Load the lore registry from JSON file."""
        try:
            registry_path = Path(__file__).parent.parent.parent / "data" / "lore_registry.json"
            with open(registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load lore registry: {e}")
            return {"lore_entries": [], "trigger_types": []}
            
    def get_lore_for_trigger(self, trigger: str) -> Optional[Dict]:
        """Get lore entry for a specific trigger.
        
        Args:
            trigger: Event trigger type
            
        Returns:
            Matching lore entry or None if not found
        """
        for entry in self.lore_registry.get("lore_entries", []):
            if entry.get("trigger") == trigger:
                return entry
        return None
        
    async def trigger_event(
        self,
        event_type: str,
        target_clans: Optional[List[str]] = None,
        ping_everyone: bool = False
    ) -> bool:
        """Trigger an event and send associated lore/announcements.
        
        Args:
            event_type: Type of event to trigger
            target_clans: Optional list of clans to target
            ping_everyone: Whether to ping everyone
            
        Returns:
            True if event was handled successfully
        """
        if event_type not in self.trigger_types:
            logger.warning(f"Unknown event type: {event_type}")
            return False
            
        try:
            # Get associated lore
            lore_entry = self.get_lore_for_trigger(event_type)
            if lore_entry:
                # Create lore drop embed
                embed = lore_drop(
                    title=lore_entry["title"],
                    snippet=lore_entry["snippet"],
                    chapter=lore_entry.get("chapter"),
                    image_url=lore_entry.get("image_url")
                )
                
                # Dispatch notification
                await self.dispatcher.dispatch(
                    embed=embed,
                    ping_everyone=ping_everyone,
                    target_clans=target_clans
                )
                
                logger.info(f"Triggered lore drop for event: {event_type}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error triggering event {event_type}: {e}")
            return False
            
    def get_available_triggers(self) -> List[str]:
        """Get list of available event triggers."""
        return self.trigger_types.copy()
        
    def get_lore_by_tags(self, tags: List[str]) -> List[Dict]:
        """Get lore entries matching specific tags.
        
        Args:
            tags: List of tags to match
            
        Returns:
            List of matching lore entries
        """
        matching_entries = []
        for entry in self.lore_registry.get("lore_entries", []):
            entry_tags = entry.get("tags", [])
            if any(tag in entry_tags for tag in tags):
                matching_entries.append(entry)
        return matching_entries 