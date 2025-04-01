"""
Clan Assignment Engine module for the HCshinobi project.
Handles the core logic for clan assignments, history, and population tracking.
"""
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

# Use centralized constants, utils, and core dependencies
from .constants import ASSIGNMENT_HISTORY_FILE, RarityTier # Import RarityTier if needed for stats
from .clan_data import ClanData
from .personality_modifiers import PersonalityModifiers
from ..utils.file_io import load_json, save_json
from ..utils.logging import get_logger, log_event # Keep logging

logger = get_logger(__name__)

class ClanAssignmentEngine:
    """
    Engine responsible for assigning clans to players based on various factors
    (randomness, personality, token boosts) and tracks assignment history.
    """

    def __init__(self, clan_data: ClanData, personality_modifiers: PersonalityModifiers):
        """
        Initialize the clan assignment engine.

        Args:
            clan_data: An instance of ClanData.
            personality_modifiers: An instance of PersonalityModifiers.
        """
        # Dependencies are now injected
        self.clan_data = clan_data
        self.personality_modifiers = personality_modifiers
        self.assignment_history: Dict[str, List[Dict[str, Any]]] = {}
        self._load_history()

    def _load_history(self):
        """Load assignment history from ASSIGNMENT_HISTORY_FILE."""
        loaded_history = load_json(ASSIGNMENT_HISTORY_FILE)
        if loaded_history is not None and isinstance(loaded_history, dict):
            self.assignment_history = loaded_history
            logger.info(f"Loaded assignment history for {len(self.assignment_history)} players from {ASSIGNMENT_HISTORY_FILE}")
        else:
            logger.warning(f"Assignment history file {ASSIGNMENT_HISTORY_FILE} not found or invalid. Starting with empty history.")
            self.assignment_history = {}
            # Optionally save the empty history immediately
            # self._save_history()

    def _save_history(self):
        """Save the current assignment history to ASSIGNMENT_HISTORY_FILE."""
        save_json(ASSIGNMENT_HISTORY_FILE, self.assignment_history)
        # logger.debug(f"Saved assignment history to {ASSIGNMENT_HISTORY_FILE}") # Use debug level

    def get_clan_weights(
        self,
        personality: Optional[str] = None,
        token_boost_clan: Optional[str] = None,
        token_count: int = 0
    ) -> Dict[str, float]:
        """
        Calculate weights for clan selection based on various factors.

        Uses base weights from ClanData, applies personality modifiers, and token boosts.

        Args:
            personality: Optional personality trait affecting clan weights.
            token_boost_clan: Optional clan name to boost with tokens.
            token_count: Number of tokens spent on boosting (e.g., 1-3).

        Returns:
            Dict[str, float]: Dictionary mapping clan names to their selection weights.
                       Returns empty dict if ClanData is unavailable.
        """
        if not self.clan_data:
            logger.error("ClanData not available in ClanAssignmentEngine.")
            return {}

        # Start with base weights from clan data
        weights = self.clan_data.get_clan_base_weights()
        if not weights:
             logger.warning("No base weights retrieved from ClanData.")
             return {}

        # Apply personality modifiers if specified and valid
        if personality and self.personality_modifiers:
            # Validate personality first
            if personality in self.personality_modifiers.get_all_personalities():
                modifiers = self.personality_modifiers.get_clan_modifiers(personality)
                for clan_name, modifier in modifiers.items():
                    if clan_name in weights:
                        weights[clan_name] *= modifier
                        # logger.debug(f"Applied personality modifier {modifier} to {clan_name} for personality {personality}")
            else:
                 logger.warning(f"Personality '{personality}' provided but not found in PersonalityModifiers.")

        # Apply token boost if specified and valid
        if token_boost_clan and token_boost_clan in weights and token_count > 0:
            # Define boost factor (consider moving to constants)
            TOKEN_BOOST_FACTOR_PER_TOKEN = 0.3 # e.g., 30% increase per token
            MAX_BOOST_TOKENS = 3 # e.g., max 3 tokens for boost

            boost_multiplier = 1.0 + (TOKEN_BOOST_FACTOR_PER_TOKEN * min(token_count, MAX_BOOST_TOKENS))
            weights[token_boost_clan] *= boost_multiplier
            # logger.debug(f"Applied token boost multiplier {boost_multiplier} to {token_boost_clan} for {token_count} tokens.")
        elif token_boost_clan and token_boost_clan not in weights:
             logger.warning(f"Token boost requested for unknown clan: {token_boost_clan}")

        # Ensure no negative weights (shouldn't happen with multipliers, but good practice)
        weights = {clan: max(0, weight) for clan, weight in weights.items()}

        return weights

    def assign_clan(
        self,
        player_id: str,
        player_name: str,
        personality: Optional[str] = None,
        token_boost_clan: Optional[str] = None,
        token_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Assign a clan to a player based on calculated weights.
        Records the assignment in history and logs the event.

        Args:
            player_id: Unique identifier for the player (e.g., Discord ID).
            player_name: Display name of the player.
            personality: Optional personality trait influencing weights.
            token_boost_clan: Optional clan name boosted with tokens.
            token_count: Number of tokens used for the boost.

        Returns:
            Optional[Dict[str, Any]]: Clan assignment result (including full clan data) 
                                     or None if assignment fails (e.g., no clans available).
        """
        if self.get_player_clan(player_id):
             logger.warning(f"Player {player_id} ({player_name}) attempted to roll clan but already has one.")
             # Consider raising an error or returning specific status
             return None # Or raise PlayerAlreadyHasClanError()

        weights = self.get_clan_weights(
            personality=personality,
            token_boost_clan=token_boost_clan,
            token_count=token_count
        )

        if not weights or sum(weights.values()) <= 0:
            logger.error(f"Cannot assign clan for player {player_id}: No valid clans or weights available.")
            return None

        # Convert to list of (clan_name, weight) for random.choices()
        clans = list(weights.keys())
        weight_values = list(weights.values())

        try:
            selected_clan_name = random.choices(clans, weights=weight_values, k=1)[0]
        except ValueError as e:
             logger.error(f"Error during weighted random choice for player {player_id}: {e} (Weights: {weights})", exc_info=True)
             return None

        # Get full clan data from ClanData instance
        selected_clan_data = self.clan_data.get_clan_by_name(selected_clan_name)
        if not selected_clan_data:
            logger.error(f"Selected clan '{selected_clan_name}' not found in ClanData during assignment for player {player_id}. This should not happen.")
            return None

        # Record assignment in history
        timestamp = datetime.now().isoformat()
        assignment_record = {
            "timestamp": timestamp,
            "player_name": player_name, # Store name at time of assignment
            "clan": selected_clan_name,
            "personality": personality,
            "token_boost": token_boost_clan,
            "token_count": token_count,
            "weights_snapshot": weights # Optional: store weights used for roll
        }

        # Store in history under player ID
        if player_id not in self.assignment_history:
            self.assignment_history[player_id] = []
        self.assignment_history[player_id].append(assignment_record)
        self._save_history()

        # Log the event
        log_event(
            "clan_assignment",
            player_id=player_id,
            player_name=player_name,
            assigned_clan=selected_clan_name,
            rarity=selected_clan_data.get('rarity', 'Unknown'),
            personality=personality,
            token_boost=token_boost_clan,
            token_count=token_count
        )
        logger.info(f"Assigned clan '{selected_clan_name}' to player {player_id} ({player_name})")

        # Return assignment details including the full clan data
        return {
            "player_id": player_id,
            "player_name": player_name,
            "clan": selected_clan_data, # Return the full dict
            "timestamp": timestamp,
            "personality": personality,
            "token_boost": token_boost_clan,
            "token_count": token_count
        }

    def get_player_clan(self, player_id: str) -> Optional[str]:
        """
        Get the name of the currently assigned clan for a player.

        Args:
            player_id: Unique identifier for the player.

        Returns:
            Optional[str]: Name of the latest assigned clan, or None if no assignment found.
        """
        player_history = self.assignment_history.get(player_id)
        if not player_history:
            return None

        # Get the most recent assignment based on timestamp
        try:
            latest_assignment = max(player_history, key=lambda x: datetime.fromisoformat(x["timestamp"]))
            return latest_assignment.get("clan")
        except (ValueError, KeyError) as e:
             logger.error(f"Error parsing latest assignment for player {player_id}: {e}", exc_info=True)
             return None

    def get_clan_population(self, clan_name: str) -> int:
        """
        Gets the current population count for a specific clan based on history.
        NOTE: This reflects players ever assigned, not necessarily currently active.
              Needs integration with NPCManager/PlayerStatus for active count.

        Args:
            clan_name: The name of the clan.

        Returns:
            int: The number of players whose latest assignment is this clan.
        """
        count = 0
        for player_id in self.assignment_history.keys():
            assigned_clan = self.get_player_clan(player_id)
            if assigned_clan and assigned_clan.lower() == clan_name.lower():
                 # TODO: Check if player_id is currently active (not an NPC)
                 count += 1
        return count

    def get_all_clan_populations(self) -> Dict[str, int]:
        """
        Gets the current population count for all clans based on history.
        NOTE: Reflects latest assignment, not necessarily active players.

        Returns:
            Dict[str, int]: Dictionary mapping clan names to their population count.
        """
        if not self.clan_data:
             logger.error("ClanData not available for population calculation.")
             return {}

        all_clan_names = [c['name'] for c in self.clan_data.get_all_clans()]
        population = {name: 0 for name in all_clan_names}

        for player_id in self.assignment_history.keys():
            clan_name = self.get_player_clan(player_id)
            if clan_name and clan_name in population:
                # TODO: Check if player_id is currently active (not an NPC)
                 population[clan_name] += 1

        return population

    def get_rarity_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate statistics about clan assignments grouped by rarity tier.
        Includes total weight, population count, and actual assignment percentage.

        Returns:
            Dict[str, Dict[str, Any]]: Statistics dictionary keyed by rarity tier value.
                                     Structure: {rarity_value: {'weight', 'population', 'chance'}}
        """
        if not self.clan_data:
             logger.error("ClanData not available for rarity statistics.")
             return {}

        all_clans = self.clan_data.get_all_clans()
        populations = self.get_all_clan_populations()
        total_population = sum(populations.values())

        # Use DEFAULT_RARITY_WEIGHTS from constants
        rarity_stats = {tier.value: {"weight": DEFAULT_RARITY_WEIGHTS.get(tier.value, 0), "population": 0, "clans": []} for tier in RarityTier}

        for clan in all_clans:
            rarity = clan.get('rarity')
            if rarity in rarity_stats:
                clan_name = clan['name']
                clan_pop = populations.get(clan_name, 0)
                rarity_stats[rarity]["population"] += clan_pop
                rarity_stats[rarity]["clans"].append(clan_name)
            else:
                 logger.warning(f"Clan '{clan.get('name')}' has unknown rarity '{rarity}' when calculating stats.")

        # Calculate chance based on population
        for rarity, stats in rarity_stats.items():
            if total_population > 0:
                stats["chance"] = stats["population"] / total_population
            else:
                stats["chance"] = 0
            # logger.debug(f"Rarity Stats for {rarity}: {stats}")

        return rarity_stats 