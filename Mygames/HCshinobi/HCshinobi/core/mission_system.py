"""Mission system for the HCShinobi Discord bot.

Manages loading, offering, accepting, and completing missions. This includes:
- Reading mission definitions from JSON files in the data directory
- Tracking active missions per user
- Enforcing mission requirements (e.g., level, items, jutsu)
- Handling time limits, rewards, and progression updates
- Periodically offering missions to eligible players via DM
"""

import os
import json
import random
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone

import aiofiles
import aiofiles.os
import discord
from discord.ext import tasks

# Imports from HCshinobi
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.constants import RANK_ORDER
from .progression_engine import ShinobiProgressionEngine
from .constants import (
    MISSIONS_SUBDIR, 
    ACTIVE_MISSIONS_FILENAME,
    COMPLETED_MISSIONS_FILE,
    MISSION_DEFINITIONS_FILE
)
from HCshinobi.utils.file_io import load_json, save_json
from .d20_mission import (
    D20MissionRunner, D20Mission, D20Challenge, 
    SkillType, ChallengeType, DifficultyLevel
)

logger = logging.getLogger(__name__)


class MissionSystem:
    """Manages missions using a consolidated data structure."""

    def __init__(
        self,
        character_system: CharacterSystem,
        data_dir: str,
        currency_system: CurrencySystem,
        progression_engine: ShinobiProgressionEngine,
    ):
        self.character_system = character_system
        self.currency_system = currency_system
        self.progression_engine = progression_engine

        self.base_data_dir = data_dir
        # Construct specific path for mission files
        self.missions_data_dir = os.path.join(data_dir, MISSIONS_SUBDIR)
        os.makedirs(self.missions_data_dir, exist_ok=True)
        
        # Construct full file paths using the specific subdirectory
        self.active_missions_file = os.path.join(self.missions_data_dir, ACTIVE_MISSIONS_FILENAME)
        self.completed_missions_file = os.path.join(self.missions_data_dir, COMPLETED_MISSIONS_FILE)
        self.mission_definitions_file = os.path.join(self.missions_data_dir, MISSION_DEFINITIONS_FILE)
        
        # Initialize state containers
        self.mission_definitions: Dict[str, Dict] = {} # Key: mission_id, Value: mission definition dict
        self.active_missions: Dict[str, Dict] = {}  # Key: user_id_str, Value: { "mission_id": str, "start_time": iso_str }
        self.completed_missions: Dict[str, List[str]] = {}  # Key: user_id_str, Value: List[completed_mission_id]

        logger.info(f"MissionSystem initialized. Data dir: {self.missions_data_dir}")
        # Loading is deferred to ready_hook

        # Initialize D20 mission runner
        self.d20_runner = D20MissionRunner()

    async def load_mission_data(self) -> None:
        """Loads mission definitions, active, and completed missions from specific files."""
        # Load Definitions
        try:
            defs_data = load_json(self.mission_definitions_file) # Corrected call
            if defs_data is None:
                logger.warning(f"Mission definitions file not found or invalid: {self.mission_definitions_file}. Creating default.")
                self.mission_definitions = {
                    "tutorial_fetch": {"name": "Tutorial: Fetch Quest", "rank": "D", "description": "Fetch 5 herbs.", "reward": {"ryo": 50, "exp": 20}, "achievement_key": "first_mission"}
                }
                # Use SYNCHRONOUS save_json for initial default
                save_json(self.mission_definitions_file, self.mission_definitions)
            elif not isinstance(defs_data, dict):
                logger.warning(f"Invalid format in {self.mission_definitions_file}, expected dict. Resetting.")
                self.mission_definitions = {}
            else:
                self.mission_definitions = defs_data
            logger.info(f"Loaded {len(self.mission_definitions)} mission definitions.")
        except Exception as e:
            logger.error(f"Error loading mission definitions from {self.mission_definitions_file}: {e}", exc_info=True)
            self.mission_definitions = {} # Reset on error

        # Load Active Missions
        try:
            active_data = load_json(self.active_missions_file) # Corrected call
            if active_data is None:
                 logger.info(f"Active missions file not found or invalid: {self.active_missions_file}. Starting fresh.")
                 self.active_missions = {}
            elif not isinstance(active_data, dict):
                 logger.warning(f"Invalid format in {self.active_missions_file}, expected dict. Resetting.")
                 self.active_missions = {}
            else:
                 self.active_missions = active_data
            logger.info(f"Loaded active missions for {len(self.active_missions)} users.")
        except Exception as e:
            logger.error(f"Error loading active missions from {self.active_missions_file}: {e}", exc_info=True)
            self.active_missions = {} # Reset on error

        # Load Completed Missions
        try:
            completed_data = load_json(self.completed_missions_file) # Corrected call
            if completed_data is None:
                logger.info(f"Completed missions file not found or invalid: {self.completed_missions_file}. Starting fresh.")
                self.completed_missions = {}
            elif not isinstance(completed_data, dict):
                logger.warning(f"Invalid format in {self.completed_missions_file}, expected dict. Resetting.")
                self.completed_missions = {}
            else:
                # Ensure values are lists
                self.completed_missions = {k: v if isinstance(v, list) else [] for k, v in completed_data.items()}
            logger.info(f"Loaded completed missions for {len(self.completed_missions)} users.")
        except Exception as e:
            logger.error(f"Error loading completed missions from {self.completed_missions_file}: {e}", exc_info=True)
            self.completed_missions = {} # Reset on error

    async def _save_active_missions(self):
        """Saves the current active missions to a file."""
        try:
            # Removed await, using synchronous save_json
            success = save_json(self.active_missions_file, self.active_missions)
            if success:
                logger.info("Active missions saved successfully.")
            else:
                logger.error("Failed to save active missions.")
        except Exception as e:
            logger.error(f"Error saving active missions: {e}", exc_info=True)

    async def _save_completed_missions(self):
        """Saves the completed missions history to a file."""
        try:
            # Removed await, using synchronous save_json
            success = save_json(self.completed_missions_file, self.completed_missions)
            if success:
                logger.info("Completed missions saved successfully.")
            else:
                logger.error("Failed to save completed missions.")
        except Exception as e:
            logger.error(f"Error saving completed missions: {e}", exc_info=True)

    async def ready_hook(self) -> None:
        """ Hook called when the bot is ready and cog is added. Loads data. """
        # Parameter removed as it was unused
        await self.load_mission_data()
        # Remove the task loop for offering missions for now, can be added back later
        # self.offer_mission_task.start()
        logger.info(
            f"MissionSystem ready. Loaded {len(self.mission_definitions)} definitions, "
            f"{len(self.active_missions)} active, {len(self.completed_missions)} users with completed missions."
        )

    # Removed offer_mission_task and its loop for simplicity in refactor scope

    async def assign_mission(self, character: Character, mission_id: str) -> Tuple[bool, str]:
        """Assigns a mission to a character if valid and not already active."""
        user_id_str = str(character.id)

        if user_id_str in self.active_missions:
            active_mission_id = self.active_missions[user_id_str].get("mission_id", "Unknown")
            active_mission_name = self.mission_definitions.get(active_mission_id, {}).get("name", active_mission_id)
            return False, f"You already have an active mission: '{active_mission_name}'."

        if mission_id not in self.mission_definitions:
            logger.warning(f"Attempted to assign non-existent mission ID: {mission_id}")
            return False, f"Mission '{mission_id}' does not exist."

        mission_details = self.mission_definitions[mission_id]
        mission_name = mission_details.get("name", mission_id)

        # Level Check
        required_level = mission_details.get("requirements", {}).get("level", 0)
        if character.level < required_level:
            return False, f"Mission '{mission_name}' requires level {required_level}, you are level {character.level}."
        
        # Rank Check
        required_rank = mission_details.get("rank")
        if required_rank:
            try:
                if RANK_ORDER.index(character.rank) < RANK_ORDER.index(required_rank):
                    return False, f"Mission '{mission_name}' requires rank {required_rank}, you are rank {character.rank}."
            except ValueError:
                # Handle cases where character rank or mission rank isn't in RANK_ORDER
                logger.warning(f"Could not perform rank check for mission {mission_id} or character {user_id_str}. Ranks: Char='{character.rank}', Mission='{required_rank}'")
                # Decide if this should prevent assignment or just log
                # return False, f"Invalid rank specified for mission or character."
                
        # Jutsu Check
        required_jutsu = mission_details.get("requirements", {}).get("jutsu", [])
        if required_jutsu:
            if not hasattr(character, 'jutsu') or not character.jutsu:
                 return False, f"Mission '{mission_name}' requires jutsu: {', '.join(required_jutsu)}. You have none."
            missing_jutsu = [j for j in required_jutsu if j not in character.jutsu]
            if missing_jutsu:
                return False, f"Mission '{mission_name}' requires jutsu: {', '.join(required_jutsu)}. You are missing: {', '.join(missing_jutsu)}."
        
        self.active_missions[user_id_str] = {
            "mission_id": mission_id,
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        await self._save_active_missions()
        logger.info(f"Assigned mission '{mission_id}' ({mission_name}) to user {user_id_str}")
        return True, f"Mission '{mission_name}' accepted!"

    async def complete_mission(self, character: Character) -> Optional[Dict[str, Any]]:
        """Completes the active mission, grants rewards, updates state, checks progression."""
        user_id_str = str(character.id)

        if user_id_str not in self.active_missions:
            logger.warning(f"User {user_id_str} tried to complete a mission, but none is active.")
            return None

        active_info = self.active_missions[user_id_str]
        mission_id = active_info["mission_id"]
        start_time = datetime.fromisoformat(active_info["start_time"])

        if mission_id not in self.mission_definitions:
            logger.error(f"Active mission {mission_id} for user {user_id_str} not found in definitions! Removing active mission.")
            del self.active_missions[user_id_str]
            await self._save_active_missions()
            return None

        mission_details = self.mission_definitions[mission_id]
        mission_name = mission_details.get("name", mission_id)

        # Check time limit (if applicable)
        duration_str = mission_details.get("duration") # Assuming duration is stored in defs
        if duration_str:
            try:
                # Assuming duration is stored as string like "1h", "30m"
                # This needs a robust parsing function
                # duration = parse_duration(duration_str)
                duration = timedelta(hours=1) # Placeholder - needs proper parsing or storage format
                if datetime.now(timezone.utc) > start_time + duration:
                    logger.info(f"Mission '{mission_id}' ({mission_name}) expired for user {user_id_str}.")
                    del self.active_missions[user_id_str]
                    await self._save_active_missions()
                    return None # Indicate failure due to expiration
            except Exception as e:
                 logger.error(f"Error checking time limit for mission {mission_id}: {e}")
                 # Decide how to handle parse errors - fail safe?
                 # return None

        # Grant rewards
        rewards = mission_details.get("reward", {})
        granted_rewards = {}
        if "exp" in rewards:
            exp_reward = rewards["exp"]
            await self.progression_engine.grant_experience(user_id_str, exp_reward)
            granted_rewards["exp"] = exp_reward
            logger.info(f"Granted {exp_reward} EXP to {user_id_str} for mission {mission_id}")
        if "ryo" in rewards:
            ryo_reward = rewards["ryo"]
            await self.currency_system.add_ryo(user_id_str, ryo_reward)
            granted_rewards["ryo"] = ryo_reward
            logger.info(f"Granted {ryo_reward} Ryo to {user_id_str} for mission {mission_id}")

        # Grant item rewards
        item_rewards = rewards.get("items", [])
        granted_items = []
        if item_rewards:
            # Need the character object to modify inventory
            character = await self.character_system.get_character(user_id_str)
            if character:
                if not hasattr(character, 'inventory') or character.inventory is None:
                    character.inventory = [] # Initialize inventory if missing
                
                for item_id in item_rewards:
                    if isinstance(item_id, str):
                        character.inventory.append(item_id.lower()) # Add item to inventory list
                        granted_items.append(item_id)
                        logger.info(f"Granted item '{item_id}' to {user_id_str} for mission {mission_id}")
                    else:
                        logger.warning(f"Invalid item_id format in mission reward for {mission_id}: {item_id}")
                
                # Save the character with the updated inventory
                await self.character_system.save_character(character)
                granted_rewards["items"] = granted_items # Add granted items to the rewards dict
            else:
                logger.error(f"Could not grant items for mission {mission_id}: Character {user_id_str} not found.")

        # Check for achievements
        achievement_key = mission_details.get("achievement_key")
        if achievement_key:
            await self.progression_engine.check_achievement(user_id_str, achievement_key)

        # Update state: remove from active, add to completed
        del self.active_missions[user_id_str]
        if user_id_str not in self.completed_missions:
            self.completed_missions[user_id_str] = []
        self.completed_missions[user_id_str].append(mission_id)

        await self._save_active_missions()
        await self._save_completed_missions()

        logger.info(f"User {user_id_str} completed mission '{mission_id}' ({mission_name}). Rewards: {granted_rewards}")
        return granted_rewards

    def get_active_mission(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Returns the active mission details for a user, or None if no mission is active."""
        user_id_str = str(user_id) # Convert int to str for lookup
        active_info = self.active_missions.get(user_id_str)
        if not active_info:
            return None
        
        mission_id = active_info.get("mission_id")
        if not mission_id or mission_id not in self.mission_definitions:
            return None # Or log error if definition is missing
        
        mission_details = self.mission_definitions[mission_id].copy() # Return a copy
        mission_details["start_time"] = active_info["start_time"]
        # Add progress if tracked: mission_details["progress"] = active_info.get("progress", {})
        return mission_details

    def get_completed_missions(self, user_id: int) -> List[str]:
        """Gets the list of completed mission IDs for a user."""
        return self.completed_missions.get(str(user_id), [])

    def get_available_missions(self, character: Character) -> List[Dict[str, Any]]:
        """Returns a list of mission definitions available to the character."""
        available = []
        user_id_str = str(character.id)
        completed_ids = set(self.get_completed_missions(character.id))
        has_active_mission = user_id_str in self.active_missions

        # Cannot take new missions if one is active (current design)
        if has_active_mission:
            return []

        for mission_id, details in self.mission_definitions.items():
            # Cannot repeat completed missions
            if mission_id in completed_ids:
                continue

            # Check rank requirement (using character.rank which should be kept up-to-date)
            required_rank = details.get("rank", "D")
            try:
                # Need RANK_ORDER imported for this check
                if RANK_ORDER.index(character.rank) < RANK_ORDER.index(required_rank):
                   continue
            except (ValueError, AttributeError):
                 # Handle cases where rank is invalid or RANK_ORDER not set up correctly
                 logger.warning(f"Could not perform rank check for mission {mission_id} or character {user_id_str}. Ranks: Char='{character.rank}', Mission='{required_rank}'")
                 continue # Skip mission if rank check fails

            # Add other checks here (e.g., prerequisite missions based on completed_ids)
            # Example prerequisite check:
            # required_prereq = details.get("requires_mission")
            # if required_prereq and required_prereq not in completed_ids:
            #     continue

            # If all checks pass, add mission definition to available list
            # Return a copy of the definition dict including the ID
            mission_info = details.copy()
            mission_info["id"] = mission_id # Add id for easy reference
            available.append(mission_info)

        # Optional: Sort available missions (e.g., by rank)
        available.sort(key=lambda m: RANK_ORDER.index(m.get("rank", "Z"))) # Sort by rank order, put unknowns last

        return available

    # Removed old methods like abandon_mission, mission_status etc. if they weren't in the original snippet
    # or need specific refactoring based on the new structure.

    def _convert_to_d20_mission(self, mission_data):
        """
        Convert a standard mission definition to a D20Mission object.
        
        Args:
            mission_data: The mission definition from JSON
            
        Returns:
            D20Mission object
        """
        # Convert challenges
        challenges = []
        for challenge_data in mission_data.get('challenges', []):
            # Convert primary and secondary skills
            primary_skill = SkillType(challenge_data.get('primary_skill', 'STRENGTH').lower())
            secondary_skill = None
            if 'secondary_skill' in challenge_data:
                secondary_skill = SkillType(challenge_data.get('secondary_skill').lower())
                
            # Convert difficulty
            difficulty_name = challenge_data.get('difficulty', 'MODERATE').upper()
            difficulty = DifficultyLevel[difficulty_name]
            
            # Convert challenge type
            challenge_type_name = challenge_data.get('type', 'COMBAT').upper()
            challenge_type = ChallengeType[challenge_type_name]
            
            # Create the challenge
            challenge = D20Challenge(
                challenge_id=challenge_data.get('id', f"challenge_{len(challenges)}"),
                title=challenge_data.get('title', 'Challenge'),
                description=challenge_data.get('description', ''),
                difficulty=difficulty,
                primary_skill=primary_skill,
                secondary_skill=secondary_skill,
                challenge_type=challenge_type,
                enemy_level=challenge_data.get('enemy_level'),
                enemy_stats=challenge_data.get('enemy_stats'),
                success_message=challenge_data.get('success_message', 'You succeeded in the challenge!'),
                failure_message=challenge_data.get('failure_message', 'You failed the challenge.'),
                critical_success_message=challenge_data.get('critical_success_message'),
                critical_failure_message=challenge_data.get('critical_failure_message'),
                rewards=challenge_data.get('rewards', {}),
                required_items=challenge_data.get('required_items', [])
            )
            
            challenges.append(challenge)
        
        # Create the D20Mission
        return D20Mission(
            mission_id=mission_data.get('mission_id', 'unknown'),
            title=mission_data.get('title', 'Mission'),
            description=mission_data.get('description', ''),
            rank=mission_data.get('required_rank', 'Academy Student'),
            location=mission_data.get('location', 'Unknown'),
            challenges=challenges,
            time_limit=mission_data.get('time_limit', '1 day'),
            reward_exp=mission_data.get('reward_exp', 100),
            reward_ryo=mission_data.get('reward_ryo', 100),
            required_items=mission_data.get('required_items', []),
            required_jutsu=mission_data.get('required_jutsu', []),
            required_level=mission_data.get('required_level', 1),
            required_rank=mission_data.get('required_rank', 'Academy Student')
        )

    def update_mission_progress(self, character_id, progress=None, objective=None):
        """
        Update a character's mission progress.
        
        Args:
            character_id: ID of the character
            progress: New progress value (0.0 to 1.0) or None
            objective: Objective to mark as complete or None
            
        Returns:
            Tuple of (success, message)
        """
        # Check if character has an active mission
        mission_data = self.active_missions.get(str(character_id))
        if not mission_data:
            return False, "You don't have an active mission."
            
        # Update progress if provided
        if progress is not None:
            mission_data['progress'] = min(1.0, max(0.0, progress))
            
        # Add completed objective if provided
        if objective is not None and objective not in mission_data['objectives_complete']:
            mission_data['objectives_complete'].append(objective)
            
        # Save changes
        self._save_active_missions()
        
        # Get mission definition for message
        mission_id = mission_data.get('mission_id')
        mission = self.mission_definitions.get(mission_id)
        mission_title = mission.get('title', mission_id) if mission else mission_id
        
        return True, f"Mission progress updated for '{mission_title}'."

    def roll_d20(self) -> int:
        """Roll a d20 dice."""
        return random.randint(1, 20)

    def skill_check(self, character: Character, skill_name: str, difficulty: int) -> Dict[str, Any]:
        """
        Perform a skill check using the D20 system.
        
        Args:
            character: The character performing the check
            skill_name: Name of the skill to check (strength, speed, etc.)
            difficulty: Difficulty class (DC) of the check
            
        Returns:
            Dict with check results
        """
        try:
            # Convert skill name to SkillType
            skill = SkillType(skill_name.lower())
            
            # Convert difficulty to DifficultyLevel
            difficulty_level = None
            for level in DifficultyLevel:
                if level.value == difficulty:
                    difficulty_level = level
                    break
                    
            if not difficulty_level:
                # Find closest difficulty level
                difficulty_levels = sorted([(level, abs(level.value - difficulty)) for level in DifficultyLevel], key=lambda x: x[1])
                difficulty_level = difficulty_levels[0][0]
            
            # Perform the skill check
            return self.d20_runner.skill_check(character, difficulty_level, skill)
        except Exception as e:
            logger.error(f"Error in skill check: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "roll": self.roll_d20(),
                "difficulty": difficulty
            }

    def process_d20_challenge(self, character_id):
        """
        Process the current D20 challenge for a character's active mission.
        
        Args:
            character_id: ID of the character
            
        Returns:
            Dict with challenge results
        """
        character = self.character_system.get_character(character_id)
        if not character:
            return {
                "success": False,
                "message": "Character not found."
            }
            
        # Check if the character has an active mission
        mission_data = self.active_missions.get(str(character_id))
        if not mission_data:
            return {
                "success": False,
                "message": "You don't have an active mission."
            }
            
        # Check if it's a D20 mission
        if not mission_data.get('is_d20_mission', False):
            return {
                "success": False,
                "message": "This is not a D20 mission."
            }
            
        # Process the challenge
        result = self.d20_runner.process_current_challenge(character)
        
        # Check if mission is complete
        if result.get('success', False) and 'mission_complete' in result and result['mission_complete']:
            # Complete the mission
            completion_result = self.complete_mission(character_id)
            result['mission_completion'] = completion_result
        else:
            # Update mission data with latest D20 state
            mission_data['d20_mission_state'] = {
                'current_challenge_index': self.d20_runner.active_missions.get(str(character_id), {}).get('current_challenge_index', 0),
                'completed_challenges': self.d20_runner.active_missions.get(str(character_id), {}).get('completed_challenges', []),
                'mission_log': self.d20_runner.active_missions.get(str(character_id), {}).get('mission_log', [])
            }
            
            # Calculate overall progress
            mission = self.mission_definitions.get(mission_data['mission_id'])
            if mission and 'challenges' in mission:
                total_challenges = len(mission['challenges'])
                completed_challenges = len(mission_data['d20_mission_state']['completed_challenges'])
                mission_data['progress'] = completed_challenges / total_challenges
                
            self._save_active_missions()
            
        return result
