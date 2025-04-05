"""
Clan Assignment Engine for the Naruto MMO Discord game.
Main module that handles player clan assignment with weighted probabilities.
"""
import json
import os
import random
import time
import logging
import asyncio # Added import
from typing import Dict, List, Optional, Tuple, Any

# Use absolute imports for core modules and constants
from HCshinobi.core.constants import (
    RarityTier,
    DEFAULT_RARITY_WEIGHTS as RARITY_WEIGHTS, # Assuming constants uses DEFAULT_
    UNDERPOPULATED_BONUS,
    OVERPOPULATED_PENALTY_MILD,
    OVERPOPULATED_PENALTY_SEVERE,
    TOKEN_BOOST_PER_TOKEN,
    MAX_TOKEN_BOOST,
    # Import path constants
    CLAN_POPULATION_FILE,
    LOG_DIR,
    # Import directory/file constants
    DATA_DIR,
    CLANS_SUBDIR,
    CLANS_FILE,
    ASSIGNMENT_HISTORY_FILE,
    DEFAULT_CLAN_WEIGHT
)
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.personality_modifiers import PersonalityModifiers
from HCshinobi.core.npc_manager import NPCManager

# Set up logging
# Remove the basicConfig call below, it conflicts with the root setup
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("logs/clan_assignment.log"),
#         logging.StreamHandler()
#     ]
# )
logger = logging.getLogger("clan_assignment_engine") # Logger will inherit root config

class ClanAssignmentEngine:
    """
    Main engine for assigning clans to players based on weighted probabilities,
    adjusted by population, personality traits, and token boosts.
    Handles persistence of clan population data.
    """
    
    def __init__(self, clan_data_service: ClanData, personality_modifiers_service: PersonalityModifiers):
        """Initialize the clan assignment engine.

        Args:
            clan_data_service: Initialized ClanData service instance.
            personality_modifiers_service: Initialized PersonalityModifiers service instance.
        """
        # self.data_dir = data_dir # No longer needed if paths come from constants
        self.log_dir = LOG_DIR # Use constant
        self.clan_data = clan_data_service # Use injected service
        self.personality_modifiers = personality_modifiers_service # Use injected service
        self.player_clans = {} # Consider removing if clan is stored on Character object
        self.clan_populations = {}
        # Construct the full path for the population file
        self.clan_population_file_path = os.path.join(DATA_DIR, CLAN_POPULATION_FILE)

    async def ready_hook(self):
        """Initialize ClansAssignmentEngine with clan data."""
        try:
            # Load clans from ClanData service
            clans = self.clan_data.get_all_clans()
            # Type-check to avoid string index errors
            if isinstance(clans, dict):
                logger.info(f"Successfully loaded {len(clans)} clans from ClanData")
            else:
                logger.warning(f"Unexpected data type from ClanData.get_all_clans(): {type(clans)}. Expected dict.")
        except Exception as e:
            logger.error(f"Error loading clans from ClanData: {e}")
            
        # Load clan population data
        self.clan_populations = self._load_clan_population_data()
        
        # Ensure logs directory exists using constant
        os.makedirs(self.log_dir, exist_ok=True)
        logger.info(f"Ensured log directory exists: {self.log_dir}")
        logger.info(f"ClanAssignmentEngine ready_hook finished. Initialized populations for {len(self.clan_populations)} clans.")
    
    def _load_clan_population_data(self) -> Dict[str, int]:
        """
        Load clan population data from the specified file path.
        If file doesn't exist, initialize with zero counts for all defined clans.
        Filters loaded data to only include currently defined clans.
        """
        # Filter population data to only include currently defined clans
        try:
            # Iterate over the values (clan dictionaries) instead of keys
            defined_clan_names = {clan["name"] for clan in self.clan_data.get_all_clans().values()}
        except AttributeError:
             # Handle case where clan_data might not be fully initialized or get_all_clans is missing
            logger.error("Failed to get clan names from clan_data. Check clan_data initialization.")
            defined_clan_names = set()
            
        # Use the full path variable
        file_path = self.clan_population_file_path

        # Ensure directory exists
        pop_dir = os.path.dirname(file_path)
        if pop_dir:
            os.makedirs(pop_dir, exist_ok=True)

        if not os.path.exists(file_path):
            logger.info(f"Clan population file {file_path} not found. Initializing.")
            populations = {clan_name: 0 for clan_name in defined_clan_names}
            self._save_clan_population_data(populations) # Save the initialized data
            return populations
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f: 
                loaded_populations = json.load(f)
                if not isinstance(loaded_populations, dict):
                     raise ValueError("Population file does not contain a valid dictionary.")
                     
                # Filter to only include clans currently defined
                filtered_populations = {
                    clan: count 
                    for clan, count in loaded_populations.items() 
                    if clan in defined_clan_names
                }
                # Add missing clans with 0 count
                updated = False
                for clan_name in defined_clan_names:
                    if clan_name not in filtered_populations:
                        filtered_populations[clan_name] = 0
                        logger.info(f"Added missing clan '{clan_name}' to population data with count 0.")
                        updated = True
                
                # Log if filtering removed any clans
                removed_clans = set(loaded_populations.keys()) - set(filtered_populations.keys())
                if removed_clans:
                     logger.warning(f"Loaded population data contained clans not currently defined: {removed_clans}. Filtered count: {len(filtered_populations)}. Consider cleaning {file_path}")
                     updated = True # Mark for potential resave if desired
                
                # Optional: Save the cleaned/updated data back
                # if updated:
                #     self._save_clan_population_data(filtered_populations)
                     
                return filtered_populations
        except (json.JSONDecodeError, FileNotFoundError, IOError, ValueError) as e:
            # Use the full path variable (Corrected log line)
            logger.error(f"Error loading or processing clan population file {file_path}: {e}. Re-initializing.", exc_info=True)
            populations = {clan_name: 0 for clan_name in defined_clan_names}
            self._save_clan_population_data(populations)
            return populations
    
    def _save_clan_population_data(self, clan_populations: Dict[str, int]) -> None:
        """Save clan population data to self.clan_population_file."""
        # Use the full path variable
        file_path = self.clan_population_file_path

        # Ensure directory exists (redundant if done in init/load, but safe)
        pop_dir = os.path.dirname(file_path)
        if pop_dir:
            os.makedirs(pop_dir, exist_ok=True)
            
        with open(file_path, 'w') as f:
            json.dump(clan_populations, f, indent=2)
        # logger.debug(f"Saved clan populations to {file_path}")
    
    def _calculate_base_weights(self) -> Dict[str, float]:
        """
        Calculate the base weights for all clans based on their rarity tier.
        Uses the base_weight pre-calculated in ClanData.
        
        Returns:
            Dict[str, float]: Dictionary mapping clan names to their base weights
        """
        try:
            all_clans = self.clan_data.get_all_clans()
            
            # Handle if all_clans is a dictionary where keys are clan IDs/names and values are clan data
            if isinstance(all_clans, dict):
                base_weights = {}
                for clan_id, clan in all_clans.items():
                    # Determine clan name based on structure
                    if isinstance(clan, dict) and "name" in clan:
                        clan_name = clan["name"]
                        base_weight = clan.get("base_weight", DEFAULT_CLAN_WEIGHT)
                    else:
                        # Use the key as name if clan is not a dict or doesn't have 'name'
                        clan_name = clan_id
                        base_weight = DEFAULT_CLAN_WEIGHT
                    base_weights[clan_name] = base_weight
            # For other return types (like a list), use a simpler approach
            else:
                logger.warning(f"Unexpected data type from get_all_clans: {type(all_clans)}. Using empty weights.")
                base_weights = {}
                
            # Log clans with zero base weight
            zero_weight_clans = [name for name, weight in base_weights.items() if weight == 0]
            if zero_weight_clans:
                logger.warning(f"Clans with zero base weight calculated: {zero_weight_clans}")
            return base_weights
        except Exception as e:
            logger.error(f"Error calculating base weights: {e}", exc_info=True)
            return {}
    
    def _apply_population_adjustments(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Apply adjustments based on current clan populations.
        
        Args:
            weights: Dictionary mapping clan names to their current weights
            
        Returns:
            Dict[str, float]: Updated weights with population adjustments
        """
        adjusted_weights = weights.copy()
        
        for clan, population in self.clan_populations.items():
            # Boost underpopulated clans
            if population < 3:
                adjusted_weights[clan] += UNDERPOPULATED_BONUS
                logger.debug(f"Boosting {clan} by {UNDERPOPULATED_BONUS}% due to underpopulation")
            
            # Reduce overpopulated clans
            elif population > 15:
                adjusted_weights[clan] += OVERPOPULATED_PENALTY_SEVERE
                logger.debug(f"Reducing {clan} by {OVERPOPULATED_PENALTY_SEVERE}% due to severe overpopulation")
            elif population > 10:
                adjusted_weights[clan] += OVERPOPULATED_PENALTY_MILD
                logger.debug(f"Reducing {clan} by {OVERPOPULATED_PENALTY_MILD}% due to mild overpopulation")
        
        return adjusted_weights
    
    def _apply_token_boost(
        self, 
        weights: Dict[str, float], 
        target_clan: Optional[str], 
        token_count: int
    ) -> Dict[str, float]:
        """
        Apply token-based boost to a specific clan.
        
        Args:
            weights: Dictionary mapping clan names to their current weights
            target_clan: The clan to boost (or None if no boost)
            token_count: Number of tokens to spend (1-3)
            
        Returns:
            Dict[str, float]: Updated weights with token boost applied
        """
        if not target_clan or target_clan not in weights or token_count <= 0:
            return weights
        
        # Cap token count to prevent excessive boosting
        capped_tokens = min(token_count, MAX_TOKEN_BOOST // TOKEN_BOOST_PER_TOKEN)
        
        # Calculate the boost amount
        boost_amount = capped_tokens * TOKEN_BOOST_PER_TOKEN
        
        # Apply the boost
        adjusted_weights = weights.copy()
        adjusted_weights[target_clan] += boost_amount
        
        logger.info(f"Applied token boost of {boost_amount}% to {target_clan} from {token_count} tokens")
        
        return adjusted_weights
    
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize weights to ensure they sum to 100%.
        Also ensures no weight goes below 0.1% to maintain some chance.
        
        Args:
            weights: Dictionary mapping clan names to their current weights
            
        Returns:
            Dict[str, float]: Normalized weights that sum to 100%
        """
        # Ensure minimum weight
        adjusted_weights = {clan: max(0.1, weight) for clan, weight in weights.items()}
        
        # Calculate sum of all weights
        total_weight = sum(adjusted_weights.values())
        
        # Normalize to 100%
        normalized_weights = {
            clan: (weight / total_weight) * 100
            for clan, weight in adjusted_weights.items()
        }
        
        return normalized_weights
    
    def _apply_personality_modifiers(self, weights: Dict[str, float], personality: Optional[str]) -> Dict[str, float]:
        """
        Apply personality-based modifiers to clan weights.

        Args:
            weights: Dictionary mapping clan names to their current weights.
            personality: The player's chosen personality trait.

        Returns:
            Dict[str, float]: Updated weights with personality adjustments.
        """
        if not personality:
            return weights

        modifiers = self.personality_modifiers.get_clan_modifiers(personality)
        if not modifiers:
            logger.debug(f"No modifiers found for personality: {personality}")
            return weights

        adjusted_weights = weights.copy()
        for clan, modifier in modifiers.items():
            if clan in adjusted_weights:
                original_weight = adjusted_weights[clan]
                # Apply modifier multiplicatively
                adjusted_weights[clan] *= modifier
                logger.debug(f"Applied personality modifier {modifier:.2f} to {clan} (Personality: {personality}). Weight: {original_weight:.2f} -> {adjusted_weights[clan]:.2f}")
            else:
                logger.warning(f"Clan '{clan}' from personality modifier '{personality}' not found in current weights.")

        return adjusted_weights
    
    def assign_clan(
        self,
        player_id: str,
        player_name: str,
        personality: Optional[str] = None,
        token_boost_clan: Optional[str] = None,
        token_count: int = 0
    ) -> Dict[str, Any]:
        """
        Assign a clan to a player based on various factors.

        Args:
            player_id: Unique identifier for the player (e.g., Discord ID).
            player_name: Name of the player.
            personality: Optional personality trait chosen by the player.
            token_boost_clan: Optional clan the player wants to boost using tokens.
            token_count: Number of tokens the player is spending (0-3).

        Returns:
            Dict[str, Any]: Details about the assignment, including the assigned clan.
        """
        start_time = time.time()

        # 1. Calculate Base Weights
        base_weights = self._calculate_base_weights()
        if not base_weights:
            logger.error("Base weights calculation resulted in empty dict. Cannot assign clan.")
            # Handle error appropriately, maybe return a default or raise exception
            return {"error": "Failed to calculate base weights"}
        logger.debug(f"Initial base weights: {base_weights}")

        # 2. Apply Personality Modifiers
        modified_weights = self._apply_personality_modifiers(base_weights, personality)
        logger.debug(f"Weights after personality '{personality}': {modified_weights}")

        # 3. Apply Population Adjustments
        population_adjusted_weights = self._apply_population_adjustments(modified_weights)
        logger.debug(f"Weights after population adjustment: {population_adjusted_weights}")

        # 4. Apply Token Boost
        token_boosted_weights = self._apply_token_boost(
            population_adjusted_weights,
            token_boost_clan,
            token_count
        )
        logger.debug(f"Weights after token boost ('{token_boost_clan}', {token_count}): {token_boosted_weights}")

        # 5. Normalize Weights
        final_weights = self._normalize_weights(token_boosted_weights)
        logger.debug(f"Final normalized weights: {final_weights}")

        # 6. Select Clan
        clans = list(final_weights.keys())
        probabilities = list(final_weights.values())
        
        # Ensure probabilities sum close to 100
        if not (99.9 < sum(probabilities) < 100.1):
             logger.warning(f"Final probabilities do not sum to 100 ({sum(probabilities)}). Check normalization.")
             # Optional: Re-normalize if needed, though _normalize_weights should handle this.

        try:
            assigned_clan = random.choices(clans, weights=probabilities, k=1)[0]
        except ValueError as e:
             logger.error(f"Error during random.choices: {e}. Weights: {final_weights}")
             # Handle error - maybe assign a default common clan?
             # For now, re-raise or return error state
             return {"error": f"Failed to select clan due to weight issues: {e}"}
        
        # 7. Update Population Count
        self.clan_populations[assigned_clan] = self.clan_populations.get(assigned_clan, 0) + 1
        self._save_clan_population_data(self.clan_populations)

        # 8. Get Clan Rarity
        clan_details = self.clan_data.get_clan_by_name(assigned_clan)
        assigned_clan_rarity = clan_details.get("rarity", "Unknown") if clan_details else "Unknown"

        # 9. Log Assignment
        end_time = time.time()
        assignment_details = {
            "assigned_clan": assigned_clan,
            "clan_rarity": assigned_clan_rarity,
            "player_id": player_id,
            "player_name": player_name,
            "personality": personality,
            "token_boost_clan": token_boost_clan,
            "token_count": token_count,
            "timestamp": time.time(),
            "duration_ms": (end_time - start_time) * 1000,
            "final_weights": {k: round(v, 4) for k, v in final_weights.items()} # Store rounded weights
        }
        
        # Log structured JSON data
        log_data = {
            "event_type": "clan_assignment",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": assignment_details
        }
        logger.info(json.dumps(log_data, ensure_ascii=False))
        
        return assignment_details

    def mark_player_death(
        self,
        player_id: str,
        player_name: str,
        clan: str,
        **kwargs # Allow passing other player data for NPC conversion
    ) -> Optional[Dict[str, Any]]:
        """
        Mark a player as deceased, decrease clan population, and convert to NPC.

        Args:
            player_id: Unique identifier of the player.
            player_name: Name of the player.
            clan: The clan the player belonged to.
            **kwargs: Additional player data (like personality) for NPC creation.

        Returns:
            Dict[str, Any]: Data of the newly created NPC, or None if conversion failed.
        """
        # Decrease population count for the player's clan
        if clan in self.clan_populations:
            if self.clan_populations[clan] > 0:
                self.clan_populations[clan] -= 1
                self._save_clan_population_data(self.clan_populations)
                logger.info(f"Decreased population for clan {clan} due to player {player_id} death. New count: {self.clan_populations[clan]}")
            else:
                logger.warning(f"Attempted to decrease population for clan {clan} (Player: {player_id}), but count was already 0.")
        else:
            logger.warning(f"Clan {clan} not found in population data when marking player {player_id} death.")

        # Convert player to NPC using NPCManager instance
        logger.info(f"Converting player {player_id} ({player_name}, Clan: {clan}) to NPC.")
        npc_data = self.npc_manager.convert_player_to_npc(
            player_discord_id=player_id,
            player_name=player_name,
            clan_name=clan,
            # Pass through relevant kwargs like personality
            personality=kwargs.get("personality"),
            death_details=kwargs.get("death_details", "Fell in battle."),
            location=kwargs.get("location"),
            appearance=kwargs.get("appearance"),
            skills=kwargs.get("skills"),
            relationships=kwargs.get("relationships")
        )

        if npc_data:
            logger.info(f"Successfully converted player {player_id} to NPC {npc_data['id']}.")
        else:
            logger.error(f"Failed to convert player {player_id} to NPC (maybe limit reached or already NPC?).")

        return npc_data

    def get_player_clan(self, player_id: str) -> Optional[str]:
        """
        Get the clan assigned to a player.
        
        Args:
            player_id: The Discord ID of the player.
            
        Returns:
            Optional[str]: The name of the clan assigned to the player, or None if no clan is assigned.
        """
        # Check if player exists in assignment history
        if player_id not in self.assignment_history:
            return None
        
        # Get the most recent assignment
        player_history = self.assignment_history[player_id]
        if not player_history:
            return None
        
        # Sort by timestamp and get the most recent
        latest_assignment = max(player_history, key=lambda x: x["timestamp"])
        return latest_assignment.get("clan")

# --- Simulation Function ---

def simulate_clan_assignment(
    clan_population_file: str = "data/sim_clan_data.json", # Separate file for sim populations
    clan_defs_file: Optional[str] = None,
    npc_file: Optional[str] = None,
    modifiers_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Simulate a single clan assignment without affecting actual data.
    Useful for testing or providing previews.
    Accepts the same arguments as ClanAssignmentEngine.assign_clan, plus file paths.
    """
    # Create a temporary engine instance using the same paths as the real one would use
    # (or specific sim paths if desired)
    sim_engine = ClanAssignmentEngine(
        clan_population_file=clan_population_file, 
        clan_defs_file=clan_defs_file, 
        npc_file=npc_file, 
        modifiers_file=modifiers_file
    )
    
    # We need the current *real* populations for accurate simulation
    # Instantiate a separate engine to load real population data
    # This assumes default paths for the real engine unless overridden
    # This could be inefficient if called frequently - consider caching real pops
    real_engine = ClanAssignmentEngine()
    sim_engine.clan_populations = real_engine.clan_populations.copy()

    # Perform the assignment steps without saving population changes
    base_weights = sim_engine._calculate_base_weights()
    modified_weights = sim_engine._apply_personality_modifiers(base_weights, kwargs.get("personality"))
    population_adjusted_weights = sim_engine._apply_population_adjustments(modified_weights)
    token_boosted_weights = sim_engine._apply_token_boost(
        population_adjusted_weights,
        kwargs.get("token_boost_clan"),
        kwargs.get("token_count", 0)
    )
    final_weights = sim_engine._normalize_weights(token_boosted_weights)

    # Select clan based on simulated weights
    clans = list(final_weights.keys())
    probabilities = list(final_weights.values())
    
    if not clans: # Handle case where final_weights is empty
        return {"error": "No clans available for assignment after filtering/weighting."}
        
    try:
        assigned_clan = random.choices(clans, weights=probabilities, k=1)[0]
    except ValueError as e:
         # Handle potential errors if weights are invalid (e.g., all zero, negative sum)
         return {"error": f"Weight calculation error during simulation: {e}", "final_weights": final_weights}

    # Get clan rarity
    clan_details = sim_engine.clan_data.get_clan_by_name(assigned_clan)
    assigned_clan_rarity = clan_details.get("rarity", "Unknown") if clan_details else "Unknown"

    # Return simulation details
    sim_details = {
        "assigned_clan": assigned_clan,
        "clan_rarity": assigned_clan_rarity,
        "player_id": kwargs.get("player_id", "123456789"), # Use default/provided ID
        "player_name": kwargs.get("player_name", "TestPlayer"), # Use default/provided name
        "personality": kwargs.get("personality"),
        "token_boost_clan": kwargs.get("token_boost_clan"),
        "token_count": kwargs.get("token_count", 0),
        "final_weights": {k: round(v, 4) for k, v in final_weights.items()}
    }
    return sim_details


if __name__ == "__main__":
    # Example usage
    result = simulate_clan_assignment(
        player_name="TestNinja",
        personality="Strategist",
        token_boost_clan="Uchiha",
        token_count=2
    )
    print(f"Assigned clan: {result['assigned_clan']}")
    print(f"Clan rarity: {result['clan_rarity']}")
    print(f"Final weights (sample):", {k: round(v, 2) for k, v in list(result['final_weights'].items())[:5]}) 