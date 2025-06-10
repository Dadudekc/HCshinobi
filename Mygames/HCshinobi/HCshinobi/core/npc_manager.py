"""
NPC Manager module for the HCshinobi project.
Handles NPC lifecycle management, data persistence, and related operations.
"""
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import asyncio # Added import

# Use centralized constants, utils
from .constants import NPC_FILE, MAX_NPC_COUNT, DEFAULT_NPC_STATUS
from ..utils.file_io import load_json, save_json
from ..utils.logging import get_logger, log_event

logger = get_logger(__name__)

class NPCManagerError(Exception):
    """Custom exception for NPC Manager errors."""
    pass

class NPCManager:
    """
    Manages NPC lifecycle, including player-to-NPC conversion,
    data storage, and NPC interaction capabilities.
    Enforces NPC limits (MAX_NPC_COUNT).
    """

    def __init__(self, data_dir: str):
        """Initialize the NPC manager by loading existing NPC data.

        Args:
            data_dir: Directory containing the NPC JSON file.
        """
        # Construct the path to the NPC file
        self.npc_file = os.path.join(data_dir, NPC_FILE)
        self.npcs: Dict[str, Dict[str, Any]] = {}
        # Loading is deferred to ready_hook

    async def ready_hook(self):
        """Asynchronously load NPC data after initialization."""
        logger.info("NPCManager ready_hook starting...")
        self._load_npcs()
        logger.info("NPCManager ready_hook finished. Loaded %d NPCs.", len(self.npcs))

    def _load_npcs(self) -> None:
        """Load NPC data from self.npc_file."""
        # Ensure parent directory exists before trying to load
        # This helps if the path is temporary and the dir was just created
        dir_path = os.path.dirname(self.npc_file)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            
        loaded_data = load_json(self.npc_file)
        if loaded_data is not None and isinstance(loaded_data, dict):
            # --- Validation Step Added ---
            valid_structure = True
            if not loaded_data: # Handle empty dictionary case
                 self.npcs = {}
                 logger.info(f"Loaded empty NPC data from {self.npc_file}")
                 return # Skip further validation if empty
                 
            for npc_id, npc_data in loaded_data.items():
                if not isinstance(npc_id, str) or not isinstance(npc_data, dict):
                    logger.error(f"Invalid structure in loaded NPC data! Expected Dict[str, Dict], but found key type {type(npc_id)} and value type {type(npc_data)} for key '{npc_id}'. File: {self.npc_file}")
                    valid_structure = False
                    break # Stop validation on first error
            # -----------------------------
            
            if valid_structure:
                self.npcs = loaded_data
                logger.info(f"Loaded data for {len(self.npcs)} NPCs from {self.npc_file}")
            else:
                 logger.error(f"Failed to load NPC data due to invalid structure in {self.npc_file}. Initializing with empty dict.")
                 self.npcs = {}
                 # Optionally: Backup the corrupted file?
        else:
            # Log if file exists but isn't a dict, or if load_json returned None
            if os.path.exists(self.npc_file) and loaded_data is not None:
                logger.error(f"NPC file {self.npc_file} exists but is not a valid dictionary (type: {type(loaded_data)}). Starting with empty NPC list.")
            elif loaded_data is None and os.path.exists(self.npc_file):
                 logger.error(f"Failed to load JSON data from {self.npc_file} (returned None). Starting with empty NPC list.")
            else: # File doesn't exist
                logger.info(f"NPC file {self.npc_file} not found. Starting with empty NPC list.") # Changed level to INFO
            self.npcs = {}
            # Optionally save the empty structure immediately if file didn't exist
            # if not os.path.exists(self.npc_file):
            #     self._save_npcs()

    def _save_npcs(self) -> None:
        """Save the current NPC data to self.npc_file."""
        save_json(self.npc_file, self.npcs)
        # logger.debug(f"Saved NPC data to {self.npc_file}")

    def _get_active_npc_count(self) -> int:
         """Counts the number of NPCs currently marked as active."""
         return len(self.get_active_npcs())

    def convert_player_to_npc(
        self,
        player_discord_id: str,
        player_name: str,
        clan_name: str,
        personality: Optional[str] = None,
        death_details: Optional[str] = "Fell in battle.",
        location: Optional[str] = "Last known location unknown",
        appearance: Optional[str] = None,
        skills: Optional[List[str]] = None,
        relationships: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Convert a player to an NPC, typically after death.
        Checks against MAX_NPC_COUNT before creating.

        Args:
            player_discord_id: The Discord ID of the player being converted.
            player_name: The name of the player.
            clan_name: The clan the player belonged to.
            personality: Optional personality trait.
            death_details: Optional story of the player's demise (becomes backstory).
            location: Optional last known location.
            appearance: Optional description.
            skills: Optional list of notable skills.
            relationships: Optional dictionary describing relationships.

        Returns:
            The newly created NPC data dictionary, or None if the NPC limit is reached
            or the player is already an NPC.
        """
        # Check if player is already an NPC
        if self.get_npc_by_former_player(player_discord_id):
             logger.warning(f"Attempted to convert player {player_discord_id} who is already an NPC.")
             return None # Indicate player is already converted

        # Check NPC limit
        current_npc_count = self._get_active_npc_count()
        if current_npc_count >= MAX_NPC_COUNT:
            logger.warning(f"NPC limit ({MAX_NPC_COUNT}) reached. Cannot convert player {player_discord_id}.")
            # Optional: Implement logic to deactivate oldest/least interacted NPC
            return None # Indicate limit reached

        # Generate a unique NPC ID
        npc_id = str(uuid.uuid4())

        # Create NPC record
        npc_data = {
            "id": npc_id,
            "name": f"{player_name} (NPC)", # Distinguish NPC name slightly
            "former_player_id": player_discord_id,
            "clan": clan_name,
            "personality": personality,
            "backstory": death_details or "A former shinobi with a mysterious past.",
            "created_at": datetime.now().isoformat(),
            "status": DEFAULT_NPC_STATUS, # Use constant for default status
            "location": location or "Unknown",
            "appearance": appearance or "No distinctive features noted.",
            "skills": skills or [],
            "relationships": relationships or {},
            "plot_hooks": [],
            "interaction_history": []
            # Add 'updated_at' field?
        }

        # Store NPC data
        self.npcs[npc_id] = npc_data
        self._save_npcs()

        # Log the conversion
        log_event(
            "player_to_npc_conversion",
            player_id=player_discord_id,
            player_name=player_name,
            npc_id=npc_id,
            npc_name=npc_data['name'],
            clan=clan_name
        )
        logger.info(f"Converted player {player_discord_id} ({player_name}) to NPC {npc_id} ({npc_data['name']}). Active NPCs: {self._get_active_npc_count()}/{MAX_NPC_COUNT}")

        return npc_data

    def get_npc(self, npc_id: str) -> Optional[Dict[str, Any]]:
        """Get an NPC's data by their unique ID. Returns a copy."""
        npc = self.npcs.get(npc_id)
        return npc.copy() if npc else None

    def get_npc_by_former_player(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get an NPC by their former player Discord ID. Returns a copy."""
        for npc_data in self.npcs.values():
            if npc_data.get("former_player_id") == player_id:
                return npc_data.copy() # Return a copy
        return None

    def get_all_npcs(self) -> List[Dict[str, Any]]:
        """Get a list of all NPCs (returns copies)."""
        return [npc.copy() for npc in self.npcs.values()]

    def get_npcs_by_clan(self, clan_name: str) -> List[Dict[str, Any]]:
        """Get all NPCs belonging to a specific clan (case-insensitive). Returns copies."""
        normalized_clan_name = clan_name.strip().lower()
        return [
            npc.copy() for npc in self.npcs.values()
            if npc.get("clan", "").lower() == normalized_clan_name
        ]

    def get_active_npcs(self) -> List[Dict[str, Any]]:
        """Get all NPCs whose status is currently active. Returns copies."""
        return [
            npc.copy() for npc in self.npcs.values()
            if npc.get("status") == DEFAULT_NPC_STATUS # Use constant
        ]

    def update_npc(self, npc_id: str, updated_data: Dict[str, Any]) -> bool:
        """
        Update an existing NPC's data. Protected fields ('id', 'former_player_id',
        'created_at') cannot be updated.

        Args:
            npc_id: Unique identifier for the NPC.
            updated_data: Dictionary containing fields to update.

        Returns:
            True if successful, False if NPC not found.
        """
        if npc_id not in self.npcs:
            logger.warning(f"Attempted to update non-existent NPC: {npc_id}")
            return False

        # Prevent updating protected fields
        protected_fields = ["id", "former_player_id", "created_at"]
        update_payload = updated_data.copy() # Work on a copy
        for field in protected_fields:
            if field in update_payload:
                logger.warning(f"Attempted to update protected field '{field}' for NPC {npc_id}. Ignoring.")
                del update_payload[field]

        if not update_payload:
            logger.info(f"No valid fields provided to update for NPC {npc_id}. Aborting update.")
            return False # Nothing to update

        # Update NPC data
        self.npcs[npc_id].update(update_payload)
        self.npcs[npc_id]["updated_at"] = datetime.now().isoformat()
        self._save_npcs()
        logger.info(f"Updated NPC {npc_id}. Fields updated: {list(update_payload.keys())}")
        return True

    def deactivate_npc(self, npc_id: str, reason: str = "No reason provided") -> bool:
        """
        Deactivate an NPC, marking them as inactive.

        Args:
            npc_id: Unique identifier for the NPC.
            reason: Reason for deactivation.

        Returns:
            True if successful, False if NPC not found.
        """
        if npc_id not in self.npcs:
            logger.warning(f"Attempted to deactivate non-existent NPC: {npc_id}")
            return False

        if self.npcs[npc_id]["status"] != DEFAULT_NPC_STATUS:
            logger.info(f"NPC {npc_id} is already inactive.")
            return True # Already in the desired state

        # Update status and record reason
        self.npcs[npc_id]["status"] = "inactive" # Consider a constant for inactive status?
        self.npcs[npc_id]["deactivation_reason"] = reason
        self.npcs[npc_id]["deactivated_at"] = datetime.now().isoformat()
        self.npcs[npc_id]["updated_at"] = self.npcs[npc_id]["deactivated_at"]
        self._save_npcs()

        # Log the deactivation
        log_event(
            "npc_deactivation",
            npc_id=npc_id,
            npc_name=self.npcs[npc_id].get("name", "Unknown"),
            reason=reason
        )
        logger.info(f"Deactivated NPC {npc_id} ({self.npcs[npc_id].get('name')}). Reason: {reason}. Active NPCs: {self._get_active_npc_count()}")
        return True

    def record_npc_interaction(
        self,
        npc_id: str,
        interaction_type: str,
        details: Dict[str, Any],
        player_id: Optional[str] = None
    ) -> bool:
        """
        Record an interaction event with an NPC.

        Args:
            npc_id: Unique identifier for the NPC.
            interaction_type: Type of interaction (e.g., "conversation", "quest").
            details: Dictionary containing interaction-specific details.
            player_id: Optional Discord ID of the player involved.

        Returns:
            True if successful, False if NPC not found.
        """
        if npc_id not in self.npcs:
            logger.warning(f"Attempted to record interaction for non-existent NPC: {npc_id}")
            return False

        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "type": interaction_type,
            "player_id": player_id,
            "details": details
        }

        if "interaction_history" not in self.npcs[npc_id]:
            self.npcs[npc_id]["interaction_history"] = []

        self.npcs[npc_id]["interaction_history"].append(interaction_record)
        # Optional: Limit history size
        MAX_INTERACTION_HISTORY = 50
        if len(self.npcs[npc_id]["interaction_history"]) > MAX_INTERACTION_HISTORY:
            self.npcs[npc_id]["interaction_history"] = self.npcs[npc_id]["interaction_history"][-MAX_INTERACTION_HISTORY:]

        self.npcs[npc_id]["updated_at"] = interaction_record["timestamp"]
        self._save_npcs()
        # logger.debug(f"Recorded interaction of type '{interaction_type}' for NPC {npc_id}")
        return True

    def add_plot_hook(self, npc_id: str, plot_hook: Dict[str, Any]) -> bool:
        """
        Add a potential plot hook associated with an NPC.

        Args:
            npc_id: The ID of the NPC the hook relates to.
            plot_hook: A dictionary describing the plot hook (e.g., {"description": "...", "status": "unused"}).

        Returns:
            True if added, False if NPC not found.
        """
        if npc_id not in self.npcs:
            logger.warning(f"Attempted to add plot hook for non-existent NPC: {npc_id}")
            return False

        if "plot_hooks" not in self.npcs[npc_id]:
            self.npcs[npc_id]["plot_hooks"] = []

        # Ensure hook has a status
        if "status" not in plot_hook:
            plot_hook["status"] = "unused"
        # Add a unique ID to the hook?
        # plot_hook["hook_id"] = str(uuid.uuid4())

        self.npcs[npc_id]["plot_hooks"].append(plot_hook)
        self.npcs[npc_id]["updated_at"] = datetime.now().isoformat()
        self._save_npcs()
        logger.info(f"Added plot hook to NPC {npc_id}: {plot_hook.get('description', 'No description')[:50]}...")
        return True

    def mark_plot_hook_used(self, npc_id: str, hook_index: int) -> bool:
        """
        Mark a specific plot hook for an NPC as used.

        Args:
            npc_id: The ID of the NPC.
            hook_index: The index of the hook in the NPC's plot_hooks list.

        Returns:
            True if marked used, False if NPC or hook index is invalid.
        """
        if npc_id not in self.npcs:
            logger.warning(f"Attempted to mark plot hook for non-existent NPC: {npc_id}")
            return False

        hooks = self.npcs[npc_id].get("plot_hooks", [])
        if not isinstance(hooks, list) or hook_index < 0 or hook_index >= len(hooks):
            logger.warning(f"Invalid hook index {hook_index} for NPC {npc_id}. Available hooks: {len(hooks)}")
            return False

        if hooks[hook_index].get("status") == "used":
             logger.info(f"Plot hook {hook_index} for NPC {npc_id} is already marked as used.")
             return True # Already in desired state

        hooks[hook_index]["status"] = "used"
        self.npcs[npc_id]["updated_at"] = datetime.now().isoformat()
        self._save_npcs()
        logger.info(f"Marked plot hook {hook_index} as used for NPC {npc_id}.")
        return True 