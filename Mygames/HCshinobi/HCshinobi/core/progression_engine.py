"""
Engine for managing player progression, ranks, achievements, and titles.
"""
import logging
import json
import os
from typing import Optional, List, Dict, Any

# Import constants for subdirs and filenames
from .constants import PROGRESSION_SUBDIR, RANKS_FILE, ACHIEVEMENTS_FILE, TITLES_FILE
from .character_system import CharacterSystem
from .character import Character

logger = logging.getLogger(__name__)

# --- REMOVED Hardcoded Data --- #
# RANKS = { ... }
# ACHIEVEMENTS = { ... }
# TITLES = { ... }
# --- End Removed Hardcoded Data --- #

class ShinobiProgressionEngine:
    """Handles EXP gain, rank progression, achievements, and titles."""

    def __init__(self, character_system: CharacterSystem, data_dir: str):
        """Initialize the progression engine."""
        self.character_system = character_system
        # Store the base data dir
        self.base_data_dir = data_dir
        # Construct the specific path for progression data
        self.progression_data_dir = os.path.join(data_dir, PROGRESSION_SUBDIR)
        # Ensure the directory exists
        os.makedirs(self.progression_data_dir, exist_ok=True)
        
        self.ranks_data: Dict[str, Dict] = {}
        self.achievements_data: Dict[str, Dict] = {}
        self.titles_data: Dict[str, Dict] = {}
        
        self.rank_order = {} # Initialize empty, generated in ready_hook
             
        logger.info("ShinobiProgressionEngine initialized.")

    # --- NEW: Async Ready Hook --- #
    async def ready_hook(self):
        """Loads progression data and generates rank order."""
        logger.info("ProgressionEngine ready hook: Loading data...")
        # NOTE: _load_progression_data uses sync file I/O
        self._load_progression_data() 
        self.rank_order = self._generate_rank_order(self.ranks_data)
        if not self.rank_order:
             logger.error("Failed to generate rank order during ready_hook!")
        logger.info("ProgressionEngine ready hook completed.")
    # --- END NEW --- #

    def _load_progression_data(self):
        """Loads ranks, achievements, and titles from JSON files in the progression data directory."""
        files_to_load = {
            "ranks": (RANKS_FILE, "ranks_data"),
            "achievements": (ACHIEVEMENTS_FILE, "achievements_data"),
            "titles": (TITLES_FILE, "titles_data")
        }

        for data_key, (filename, attr_name) in files_to_load.items():
            # Use the specific progression data dir
            filepath = os.path.join(self.progression_data_dir, filename)
            try:
                logger.debug(f"Attempting to load {data_key} data from {filepath}")
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    setattr(self, attr_name, data)
                    logger.info(f"Successfully loaded {len(data)} {data_key} entries from {filename}.")
                else:
                    logger.error(f"Failed to load {data_key}: Data in {filename} is not a dictionary.")
                    setattr(self, attr_name, {}) # Fallback to empty dict
            except FileNotFoundError:
                logger.warning(f"{data_key} data file not found: {filepath}. Using empty defaults.")
                setattr(self, attr_name, {}) # Fallback to empty dict
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {filepath}: {e}")
                setattr(self, attr_name, {}) # Fallback to empty dict
            except Exception as e:
                logger.exception(f"An unexpected error occurred loading {filepath}: {e}")
                setattr(self, attr_name, {}) # Fallback to empty dict

    def _generate_rank_order(self, ranks_data: Dict) -> Dict[str, int]:
        """Generates a dictionary mapping rank names to their order index."""
        # --- Fallback if ranks_data is empty --- #
        if not ranks_data:
            logger.warning("ranks_data is empty (likely missing ranks.json). Using default rank order.")
            default_order = ["Academy Student", "Genin", "Chunin", "Special Jonin", "Jonin", "Anbu", "Kage"]
            order_map = {rank: i for i, rank in enumerate(default_order)}
            logger.info(f"Generated default rank order mapping: {order_map}")
            return order_map
        # --- End Fallback --- #
            
        order_map = {}
        # Determine the likely base rank (one not listed as a next_rank)
        all_next_ranks = {v.get("next_rank") for v in ranks_data.values() if v.get("next_rank")}
        possible_base_ranks = [r for r in ranks_data if r not in all_next_ranks]
        
        if len(possible_base_ranks) != 1:
             # Fallback or default assumption if base rank isn't clear
             logger.warning(f"Could not definitively determine base rank. Found {len(possible_base_ranks)} candidates: {possible_base_ranks}. Assuming 'Academy Student'.")
             base_rank = "Academy Student"
             if base_rank not in ranks_data:
                  logger.error("Default base rank 'Academy Student' not found in ranks_data. Cannot generate order.")
                  return {}
        else:
             base_rank = possible_base_ranks[0]
             logger.info(f"Determined base rank: {base_rank}")

        current_rank = base_rank
        index = 0
        visited_ranks = set()
        while current_rank and current_rank in ranks_data:
            if current_rank in visited_ranks: # Detect cycle
                 logger.error(f"Cycle detected in rank progression at '{current_rank}'. Aborting rank order generation.")
                 return {}
            visited_ranks.add(current_rank)
            order_map[current_rank] = index
            current_rank = ranks_data[current_rank].get("next_rank")
            index += 1
            
        logger.info(f"Generated rank order mapping: {order_map}")
        return order_map

    async def grant_exp(self, character_id: str, amount: int, source: str, character: Optional[Character]=None, messages: Optional[List[str]]=None) -> Optional[List[str]]:
        """Grants EXP to a character, checks for rank up, and saves.
        
        Args:
            character_id: The ID of the character receiving EXP.
            amount: The amount of EXP to grant.
            source: A string indicating the source of the EXP (e.g., 'mission', 'battle', 'achievement').
            character: Optional pre-loaded character object to avoid re-fetch.
            messages: Optional list to append progression messages to.

        Returns:
            The passed-in messages list (or a new list if None was passed) 
            with added progression messages, or None if character not found.
        """
        if not character:
            character = await self.character_system.get_character(character_id)
        
        if not character:
            logger.warning(f"grant_exp: Character not found with ID {character_id}")
            return None

        if amount <= 0:
            return messages or [] # Return existing or new empty list

        # Initialize messages list if it wasn't passed
        if messages is None:
            messages = []
            
        logger.info(f"Granting {amount} EXP to {character.name} (ID: {character_id}) from {source}.")
        character.exp += amount
        
        # Use a more user-friendly format, perhaps less verbose
        messages.append(f"✨ Gained {amount} EXP from {source}!")

        # --- Check for Rank Up --- #
        rank_changed = False
        while True: # Loop in case of multiple rank ups from massive EXP gain
            current_rank_info = self.ranks_data.get(character.rank)
            if not current_rank_info or not current_rank_info.get("next_rank"):
                break # No next rank defined or current rank invalid

            required_exp = current_rank_info.get("exp_required", float('inf'))
            # Check required EXP relative to the *start* of the current rank (which is 0 after reset)
            if character.exp >= required_exp:
                next_rank_name = current_rank_info["next_rank"]
                if next_rank_name in self.ranks_data:
                    logger.info(f"Character {character.name} meets EXP requirement ({required_exp}) for {next_rank_name}.")
                    character.rank = next_rank_name
                    character.exp -= required_exp # Subtract cost for rank up
                    # Ensure EXP doesn't go negative if exact amount was met
                    character.exp = max(0, character.exp)
                    messages.append(f"🌟 **Rank Up!** You are now a **{next_rank_name}**! 🌟")
                    logger.info(f"Character {character.name} (ID: {character_id}) ranked up to {next_rank_name}. Remaining EXP: {character.exp}")
                    rank_changed = True
                    # Check for achievements tied to this specific new rank (using formatted key)
                    rank_ach_key = f"{next_rank_name.lower().replace(' ', '_')}_rank"
                    await self.award_achievement(character_id, rank_ach_key, character=character, messages=messages)
                else:
                    logger.error(f"Rank up failed for {character.name}: Next rank '{next_rank_name}' not found in ranks_data.")
                    break # Stop checking if data is inconsistent
            else:
                break # Not enough EXP for the next rank
        # --- End Rank Up Check Loop --- #

        # Save only if rank changed or EXP was added
        await self.character_system.save_character(character)
        return messages # Return the (potentially modified) list

    async def award_achievement(self, character_id: str, achievement_key: str, character: Optional[Character]=None, messages: Optional[List[str]]=None) -> bool:
        """Awards an achievement to a character if they meet the criteria and haven't earned it yet."""
        if not character:
            character = await self.character_system.get_character(character_id)
        
        if not character:
            logger.warning(f"award_achievement: Character {character_id} not found.")
            return False
        
        if achievement_key in character.achievements:
            # logger.debug(f"Character {character_id} already has achievement {achievement_key}.")
            return False # Already has it
            
        achievement_data = self.achievements_data.get(achievement_key)
        if not achievement_data:
             logger.warning(f"Attempted to check non-existent achievement key: {achievement_key}")
             return False

        # --- Check Criteria --- #
        criteria = achievement_data.get("criteria")
        if not isinstance(criteria, dict):
            # Maybe some achievements are awarded manually/directly?
            # Or log error if criteria are expected?
            logger.warning(f"No valid criteria found for achievement '{achievement_key}'. Cannot award based on state.")
            return False # Cannot check qualification based on state

        criteria_type = criteria.get("type")
        qualified = False
        try:
            if criteria_type == "first_mission":
                qualified = self._check_first_mission(character, criteria)
            elif criteria_type == "stat_threshold":
                qualified = self._check_stat_threshold(character, criteria)
            elif criteria_type == "rank":
                qualified = self._check_rank(character, criteria)
            elif criteria_type == "battle_wins":
                 qualified = self._check_battle_wins(character, criteria)
            # Add more criteria type checks here
            else:
                logger.warning(f"Unknown criteria type '{criteria_type}' for achievement '{achievement_key}'.")

        except Exception as e:
            logger.error(f"Error checking criteria for achievement '{achievement_key}' for character {character.id}: {e}", exc_info=True)
            qualified = False
        # --- End Criteria Check --- #

        if not qualified:
            # logger.debug(f"Character {character_id} did not qualify for achievement {achievement_key}.")
            return False

        # --- Award Achievement --- #
        character.achievements.add(achievement_key)
        achievement_name = achievement_data.get("name", achievement_key)
        logger.info(f"Character {character.name} (ID: {character_id}) earned achievement: {achievement_name}")
        
        # Consistent Achievement Message Format
        message = f"🏆 **Achievement Unlocked:** {achievement_name}!" 
        desc = achievement_data.get('description', '')
        if desc: message += f" ({desc})" # Optionally add description
        
        if messages is not None:
             messages.append(message)
        # else: Send DM or other notification?

        # Grant EXP reward if applicable
        exp_reward = achievement_data.get("exp_reward", 0)
        if exp_reward > 0:
            # Pass messages list to potentially add rank up messages from exp gain
            # grant_exp handles saving the character after adding EXP
            await self.grant_exp(character_id, exp_reward, f"achievement: {achievement_name}", character=character, messages=messages)
            # We might need to save again here IF grant_exp didn't run (e.g., 0 exp reward)
            # to ensure the achievement itself is saved.
            await self.character_system.save_character(character)
        else:
            # Save if no EXP was granted (grant_exp didn't save)
            await self.character_system.save_character(character)
            
        return True

    async def check_and_assign_titles(self, character: Character) -> List[str]:
        """Checks if a character qualifies for any titles based on their current state.
        Returns a list of user-facing messages for newly assigned titles.
        """
        if not character:
            logger.warning("check_and_assign_titles called with None character.")
            return []

        new_title_messages = [] # Changed from newly_assigned names list
        character_titles_set = set(character.titles)

        for title_key, title_data in self.titles_data.items():
            title_name = title_data.get("name", title_key)
            if title_name in character_titles_set:
                 continue

            criteria = title_data.get("criteria")
            if not criteria or not isinstance(criteria, dict):
                logger.warning(f"Title '{title_key}' has invalid or missing criteria. Skipping.")
                continue

            criteria_type = criteria.get("type")
            qualified = False

            try:
                if criteria_type == "wins_vs_rank":
                    qualified = self._check_wins_vs_rank(character, criteria)
                elif criteria_type == "mission_completions":
                    qualified = self._check_mission_completions(character, criteria)
                elif criteria_type == "known_jutsu":
                    qualified = self._check_known_jutsu(character, criteria)
                # Add calls to other helper checks here
                # elif criteria_type == "training_level":
                #     qualified = self._check_training_level(character, criteria)
                else:
                    logger.warning(f"Unknown criteria type '{criteria_type}' for title '{title_key}'. Skipping.")

            except Exception as e:
                 logger.error(f"Error checking criteria for title '{title_key}' for character {character.id}: {e}", exc_info=True)
                 qualified = False # Ensure no title awarded on error

            if qualified:
                # --- Assign Title and Create Message --- #
                character.titles.append(title_name)
                character_titles_set.add(title_name) # Update the set for this run
                
                # Consistent Title Message Format
                title_message = f"🎖️ **Title Earned:** {title_name}!"
                bonus_desc = title_data.get('bonus_description')
                if bonus_desc: title_message += f" ({bonus_desc})" # Add bonus description
                
                new_title_messages.append(title_message)
                logger.info(f"Character {character.name} (ID: {character.id}) qualified for title: {title_name}")
                # --- End Assign Title --- #

        if new_title_messages:
            logger.info(f"Assigning {len(new_title_messages)} new titles to {character.name}: {[t.split(': ')[1].split('!')[0] for t in new_title_messages]}") # Log names
            await self.character_system.save_character(character)

        return new_title_messages # Return the list of messages

    # --- NEW: Method to check all achievements --- #
    async def check_all_achievements(self, character: Character, messages: List[str]) -> bool:
        """Checks all defined achievements against the character's current state and awards if qualified.

        Args:
            character: The Character object to check.
            messages: A list to append any notification messages for newly awarded achievements.

        Returns:
            True if at least one new achievement was awarded, False otherwise.
        """
        if not character:
            logger.warning("check_all_achievements called with None character.")
            return False
            
        logger.debug(f"Checking all achievements for character {character.id} ({character.name})...")
        any_new_achievement = False
        # Iterate through all known achievement keys
        for achievement_key in list(self.achievements_data.keys()): # Use list() in case dict changes during iteration (unlikely here)
            try:
                # award_achievement already handles checking if the character has it 
                # and if they meet the criteria. It returns True if newly awarded.
                was_newly_awarded = await self.award_achievement(
                    character_id=character.id, 
                    achievement_key=achievement_key, 
                    character=character, # Pass pre-loaded character
                    messages=messages      # Pass message list
                )
                if was_newly_awarded:
                    any_new_achievement = True
            except Exception as e:
                # Log error but continue checking other achievements
                logger.error(f"Error processing achievement '{achievement_key}' for character {character.id} in check_all_achievements: {e}", exc_info=True)

        if any_new_achievement:
             logger.info(f"Finished checking achievements for {character.name}. New achievements were awarded.")
        else:
             logger.debug(f"Finished checking achievements for {character.name}. No new achievements awarded.")
             
        # Note: award_achievement handles saving the character if an achievement (and potentially EXP) is granted.
        # We don't need an extra save here unless we want to guarantee a save even if nothing changed.

        return any_new_achievement
    # --- End check_all_achievements --- #

    # --- Internal Criteria Check Helpers ---

    def _check_wins_vs_rank(self, character: Character, criteria: Dict[str, Any]) -> bool:
        """Checks if the character has enough wins against a specific rank."""
        required_rank = criteria.get("rank")
        required_count = criteria.get("count", 1)

        if not required_rank:
            logger.warning(f"Criteria 'wins_vs_rank' missing 'rank'. Title criteria: {criteria}")
            return False

        # Use the new specific tracking dictionary
        actual_wins_vs_rank = character.wins_against_rank.get(required_rank, 0)
        logger.debug(f"Checking 'wins_vs_rank' for rank '{required_rank}' (req: {required_count}). Actual wins vs this rank: {actual_wins_vs_rank}.")

        return actual_wins_vs_rank >= required_count

    def _check_mission_completions(self, character: Character, criteria: Dict[str, Any]) -> bool:
        """Checks if the character has completed enough missions."""
        required_count = criteria.get("count", 1)

        # Assumes character.completed_missions is a set/list of mission IDs
        actual_completions = len(character.completed_missions)
        logger.debug(f"Checking 'mission_completions' (req: {required_count}). Actual: {actual_completions}.")

        return actual_completions >= required_count

    def _check_known_jutsu(self, character: Character, criteria: Dict[str, Any]) -> bool:
        """Checks if the character knows enough jutsu."""
        required_count = criteria.get("count", 1)

        # Assumes character.jutsu or character.known_jutsu is the list of learned jutsu
        # Let's assume it's character.jutsu based on Character class
        actual_known_jutsu = len(character.jutsu)
        logger.debug(f"Checking 'known_jutsu' (req: {required_count}). Actual: {actual_known_jutsu}.")

        return actual_known_jutsu >= required_count

    # --- Internal Achievement Criteria Check Helpers ---

    def _check_first_mission(self, character: Character, criteria: Dict[str, Any]) -> bool:
        """Checks if the character has completed at least one mission."""
        return len(character.completed_missions) >= 1

    def _check_stat_threshold(self, character: Character, criteria: Dict[str, Any]) -> bool:
        """Checks if a specific character stat meets a threshold."""
        stat_name = criteria.get("stat")
        required_value = criteria.get("value")

        if not stat_name or required_value is None:
            logger.warning(f"Invalid 'stat_threshold' criteria: {criteria}")
            return False
        
        # Use getattr to safely access the character's attribute
        actual_value = getattr(character, stat_name, 0) 
        # Ensure comparison works even if stat is None/missing (defaults to 0)
        if not isinstance(actual_value, (int, float)):
             actual_value = 0 # Treat non-numeric as 0 for comparison

        logger.debug(f"Checking 'stat_threshold' for {stat_name} >= {required_value}. Actual: {actual_value}.")
        return actual_value >= required_value
    
    def _check_rank(self, character: Character, criteria: Dict[str, Any]) -> bool:
        """Checks if the character has achieved a specific rank or higher."""
        required_rank = criteria.get("rank")
        if not required_rank:
            logger.warning(f"Invalid 'rank' criteria: Missing rank. {criteria}")
            return False
        
        # Get numerical order/index for ranks
        current_rank_index = self.rank_order.get(character.rank)
        required_rank_index = self.rank_order.get(required_rank)
        
        if current_rank_index is None:
             logger.warning(f"Character {character.id} has unknown rank '{character.rank}' not found in rank order.")
             return False
        if required_rank_index is None:
             logger.warning(f"Required rank '{required_rank}' not found in rank order for achievement criteria: {criteria}")
             return False

        logger.debug(f"Checking 'rank' for {required_rank} (index {required_rank_index}) or higher. Actual: {character.rank} (index {current_rank_index}).")
        # Check if current rank index is greater than or equal to required
        return current_rank_index >= required_rank_index

    def _check_battle_wins(self, character: Character, criteria: Dict[str, Any]) -> bool:
        """Checks if the character has achieved a specific number of wins."""
        required_count = criteria.get("count", 1)
        actual_wins = character.wins
        logger.debug(f"Checking 'battle_wins' (req: {required_count}). Actual: {actual_wins}.")
        return actual_wins >= required_count

    # Add more achievement helper checks here... 