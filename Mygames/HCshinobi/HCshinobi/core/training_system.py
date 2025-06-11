"""Training system for the HCshinobi Discord bot."""
from typing import Dict, Optional, Tuple, List, Any, Set, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
import logging
import json
import os
import asyncio
import aiofiles
import aiofiles.os
import random
import discord
from discord.ext import tasks
from dataclasses import asdict, is_dataclass

from .character import Character
from .currency_system import CurrencySystem

logger = logging.getLogger(__name__)

class TrainingAchievement:
    """Represents a training achievement."""
    def __init__(self, name: str, description: str, condition: str, reward: int):
        self.name = name
        self.description = description
        self.condition = condition
        self.reward = reward

class TrainingIntensity:
    """Represents different training intensity levels."""
    LIGHT = "light"      # 1.0x cost, 1.0x gain
    MODERATE = "moderate"  # 1.5x cost, 1.8x gain
    INTENSE = "intense"    # 2.5x cost, 2.5x gain
    EXTREME = "extreme"    # 4.0x cost, 3.0x gain

    @staticmethod
    def get_multipliers(intensity: str) -> Tuple[float, float]:
        """Get cost and gain multipliers for intensity level.
        
        Light:    1.0x cost, 1.0x gain (base training)
        Moderate: 1.5x cost, 1.8x gain (efficient training)
        Intense:  2.5x cost, 2.5x gain (challenging training)
        Extreme:  4.0x cost, 3.0x gain (risky training)
        """
        multipliers = {
            TrainingIntensity.LIGHT: (1.0, 1.0),
            TrainingIntensity.MODERATE: (1.5, 1.8),
            TrainingIntensity.INTENSE: (2.5, 2.5),
            TrainingIntensity.EXTREME: (4.0, 3.0)
        }
        return multipliers.get(intensity, (1.0, 1.0))

class TrainingSession:
    """Represents an active training session."""
    def __init__(self, user_id: str, attribute: str, duration_hours: int, cost_per_hour: int, intensity: str):
        self.user_id = user_id
        self.attribute = attribute
        self.start_time = datetime.now(timezone.utc)
        self.end_time = self.start_time + timedelta(hours=duration_hours)
        self.cost_per_hour = cost_per_hour
        self.total_cost = int(cost_per_hour * duration_hours * TrainingIntensity.get_multipliers(intensity)[0])
        self.intensity = intensity
        self.completed = False
        self.duration_hours = duration_hours

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'attribute': self.attribute,
            'duration_hours': self.duration_hours,
            'cost_per_hour': self.cost_per_hour,
            'intensity': self.intensity,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'completed': self.completed,
            'total_cost': self.total_cost
        }

    @classmethod
    def from_dict(cls, data):
        cost_per_hour = data.get('cost_per_hour', 0)
        instance = cls(
            data['user_id'],
            data['attribute'],
            data['duration_hours'],
            cost_per_hour,
            data['intensity']
        )
        instance.start_time = datetime.fromisoformat(data['start_time']).replace(tzinfo=timezone.utc)
        instance.end_time = datetime.fromisoformat(data['end_time']).replace(tzinfo=timezone.utc)
        instance.completed = data.get('completed', False)
        instance.total_cost = data.get('total_cost', instance.total_cost)
        return instance

class TrainingSystem:
    """Manages character training sessions."""
    
    def __init__(self, data_dir: str, character_system, currency_system):
        """
        Initialize the training system. Data loading is deferred to `initialize`.
        
        Args:
            data_dir: Directory for storing training data
            character_system: The character system instance
            currency_system: The currency system instance
        """
        self.data_dir = data_dir
        self.character_system = character_system
        self.currency_system = currency_system
        self.logger = logging.getLogger(__name__)
        
        self.training_data_dir = os.path.join(data_dir, "training")
        os.makedirs(self.training_data_dir, exist_ok=True)

        self.sessions_file = os.path.join(self.training_data_dir, "active_sessions.json")
        self.history_file = os.path.join(self.training_data_dir, "training_history.json")
        self.achievements_file = os.path.join(self.training_data_dir, "training_achievements.json")

        self.active_sessions: Dict[str, TrainingSession] = {}
        self.cooldowns: Dict[str, datetime] = {}
        self.user_achievements: Dict[str, List[str]] = {}
        self.training_history: Dict[str, List[Dict]] = {}
        
        self.cooldown_hours = 1  # 1 hour cooldown between sessions
        self.achievements = self._initialize_achievements()

        self.logger.warning(f">>> [Service Init] TrainingSystem initialized. Instance ID: {id(self)}")
    
    async def initialize(self):
        """Asynchronously load initial data and start background tasks."""
        self.logger.warning(f">>> [Service Init] TrainingSystem initialize() called. Instance ID: {id(self)}")
        self.logger.info("Initializing TrainingSystem asynchronously...")
        try:
            await self._load_active_sessions_async()
            await self._load_history_async()
            await self._load_achievements_async()
            
            if not self.check_training_completion.is_running():
                self.check_training_completion.start()
            self.logger.info("TrainingSystem asynchronous initialization complete.")
        except Exception as e:
            self.logger.critical(f"CRITICAL Error during TrainingSystem asynchronous initialization: {e}", exc_info=True)
            # Consider raising the exception to halt bot startup if loading fails
            raise

    def _initialize_achievements(self) -> List[TrainingAchievement]:
        """Initialize the list of training achievements."""
        return [
            TrainingAchievement(
                "Novice Trainer",
                "Complete your first training session",
                "sessions >= 1",
                100
            ),
            TrainingAchievement(
                "Dedicated Student",
                "Complete 10 training sessions",
                "sessions >= 10",
                500
            ),
            TrainingAchievement(
                "Training Master",
                "Complete 50 training sessions",
                "sessions >= 50",
                2000
            ),
            TrainingAchievement(
                "Intense Training",
                "Complete a training session with intense intensity",
                "intense_sessions >= 1",
                300
            ),
            TrainingAchievement(
                "Extreme Dedication",
                "Complete a training session with extreme intensity",
                "extreme_sessions >= 1",
                500
            ),
            TrainingAchievement(
                "Attribute Specialist",
                "Train a single attribute for 100 points",
                "attribute_points >= 100",
                1000
            ),
            TrainingAchievement(
                "Well-Rounded",
                "Train all attributes at least once",
                "unique_attributes >= 10",
                1500
            ),
            TrainingAchievement(
                "Training Marathon",
                "Complete a 24-hour training session",
                "max_duration >= 24",
                1000
            ),
            TrainingAchievement(
                "Efficient Training",
                "Gain 50 points in a single session",
                "max_points >= 50",
                800
            ),
            TrainingAchievement(
                "Training Veteran",
                "Spend 10,000 Ryō on training",
                "total_cost >= 10000",
                2000
            )
        ]
    
    async def _load_json_file(self, filepath: str, default: Any = None) -> Any:
        """Helper to load a JSON file asynchronously, returning default if not found or error."""
        if default is None: default = {} # Default to empty dict if not specified
        try:
            if not await aiofiles.os.path.exists(filepath):
                self.logger.warning(f"Data file not found: {filepath}. Returning default.")
                return default
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            self.logger.error(f"Error loading data from {filepath}: {e}", exc_info=True)
            return default # Return default on error

    async def _load_active_sessions_async(self):
        """Load and validate active training sessions from file asynchronously."""
        self.logger.warning(f">>> [Service LoadSessions] _load_active_sessions_async called. Clearing sessions. Instance ID: {id(self)}")
        self.active_sessions.clear()
        sessions_data = await self._load_json_file(self.sessions_file, default={})
        loaded_count = 0
        valid_sessions = {}
        now = datetime.now(timezone.utc)
        for user_id, session_data in sessions_data.items():
            try:
                session = TrainingSession.from_dict(session_data)
                if now < session.end_time + timedelta(days=1): # Ignore sessions ended > 1 day ago
                    valid_sessions[user_id] = session
                    loaded_count += 1
                else:
                    self.logger.warning(f"Ignoring stale session for user {user_id} loaded from {self.sessions_file} (ended: {session.end_time}).")
            except Exception as e:
                self.logger.error(f"Error parsing session for user {user_id} from {self.sessions_file}: {e}")
        self.active_sessions = valid_sessions
        self.logger.info(f"Loaded {loaded_count} valid active training sessions from {self.sessions_file}.")

    async def _load_history_async(self):
        """Load training history from file asynchronously."""
        self.training_history = await self._load_json_file(self.history_file, default={})
        self.logger.info(f"Loaded training history for {len(self.training_history)} users from {self.history_file}.")

    async def _load_achievements_async(self):
        """Load user achievements from file asynchronously."""
        self.user_achievements = await self._load_json_file(self.achievements_file, default={})
        self.logger.info(f"Loaded achievements for {len(self.user_achievements)} users from {self.achievements_file}.")

    async def _save_json_file(self, filepath: str, data: Any):
        """Helper to save data to a JSON file asynchronously."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True) 
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, default=str)) 
        except Exception as e:
            self.logger.error(f"Error saving data to {filepath}: {e}", exc_info=True)

    async def save_active_sessions_async(self):
        """Save active training sessions to file asynchronously."""
        sessions_to_save = {uid: session.to_dict() for uid, session in self.active_sessions.items()}
        await self._save_json_file(self.sessions_file, sessions_to_save)
        self.logger.debug(f"Saved {len(self.active_sessions)} active sessions to {self.sessions_file}.")

    async def save_history_async(self):
        """Save training history to file asynchronously."""
        await self._save_json_file(self.history_file, self.training_history)
        self.logger.debug(f"Saved training history to {self.history_file}.")

    async def save_achievements_async(self):
        """Save user achievements to file asynchronously."""
        await self._save_json_file(self.achievements_file, self.user_achievements)
        self.logger.debug(f"Saved user achievements to {self.achievements_file}.")

    def check_achievements(self, user_id: str, stats: Dict) -> List[Tuple[str, str, int]]:
        """
        Check and award achievements based on training statistics.
        
        Returns:
            List of (achievement_name, description, reward) for newly earned achievements
        """
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = []
        
        earned_achievements = []
        current_earned_set = set(self.user_achievements[user_id])

        for achievement in self.achievements:
            if achievement.name in current_earned_set:
                continue # Already earned

            condition = achievement.condition
            try:
                parts = condition.split()
                if len(parts) == 3:
                    stat_key, op, value_str = parts
                    stat_value = stats.get(stat_key, 0)
                    required_value = int(value_str) # Assuming int for now
                    
                    met = False
                    if op == ">=" and stat_value >= required_value: met = True
                    elif op == "<=" and stat_value <= required_value: met = True
                    elif op == "==" and stat_value == required_value: met = True
                    elif op == ">" and stat_value > required_value: met = True
                    elif op == "<" and stat_value < required_value: met = True

                    if met:
                        self.user_achievements[user_id].append(achievement.name)
                        current_earned_set.add(achievement.name)
                        earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                        self.logger.info(f"User {user_id} earned achievement: {achievement.name}")
                else:
                     self.logger.warning(f"Unsupported achievement condition format: {condition}")

            except Exception as e:
                self.logger.error(f"Error checking achievement '{achievement.name}' for user {user_id}: {e}")

        if earned_achievements:
            asyncio.create_task(self.save_achievements_async()) 
        return earned_achievements
    
    def _update_training_history(self, user_id: str, session: TrainingSession, xp_gain: float, attribute_gain: float):
        """Update the training history for a user."""
        if user_id not in self.training_history:
            self.training_history[user_id] = []

        history_entry = {
            "attribute": session.attribute,
            "duration_hours": session.duration_hours,
            "intensity": session.intensity,
            "completion_time": datetime.now(timezone.utc).isoformat(),
            "xp_gain": xp_gain,
            "attribute_gain": attribute_gain,
            "cost": session.total_cost
        }
        self.training_history[user_id].append(history_entry)
        self.training_history[user_id] = self.training_history[user_id][-20:] 
        asyncio.create_task(self.save_history_async())

    def get_training_history_stats(self, user_id: str) -> Dict[str, Any]:
        """Calculate aggregated stats from a user's training history."""
        stats = {
            "sessions": 0,
            "total_hours": 0,
            "total_xp": 0,
            "total_cost": 0,
            "intense_sessions": 0,
            "extreme_sessions": 0,
            "attribute_points": 0, # Example: total points gained across all attributes
            "unique_attributes": 0,
            "max_duration": 0,
            "max_points": 0, # Max points gained in one session
            "attribute_counts": {}, # Count per attribute trained
        }
        history = self.training_history.get(user_id, [])
        trained_attributes = set()

        for entry in history:
            stats["sessions"] += 1
            stats["total_hours"] += entry.get("duration_hours", 0)
            stats["total_xp"] += entry.get("xp_gain", 0)
            stats["total_cost"] += entry.get("cost", 0)
            
            intensity = entry.get("intensity")
            if intensity == TrainingIntensity.INTENSE: stats["intense_sessions"] += 1
            if intensity == TrainingIntensity.EXTREME: stats["extreme_sessions"] += 1
            
            attr = entry.get("attribute")
            attr_gain = entry.get("attribute_gain", 0)
            if attr:
                trained_attributes.add(attr)
                stats["attribute_points"] += attr_gain
                stats["attribute_counts"][attr] = stats["attribute_counts"].get(attr, 0) + 1
            
            session_points = entry.get("attribute_gain", 0) # Approximation
            stats["max_points"] = max(stats["max_points"], session_points)
            stats["max_duration"] = max(stats["max_duration"], entry.get("duration_hours", 0))

        stats["unique_attributes"] = len(trained_attributes)
        return stats

    def _get_training_cost(self, attribute: str) -> int:
        """
        Get the base Ryō cost per hour for training a specific attribute.
        """
        base_costs = {
            'ninjutsu': 50,
            'taijutsu': 50,
            'genjutsu': 60,
            'strength': 40,
            'speed': 45,
            'stamina': 40,
            'chakra_control': 70,
            'perception': 55,
            'willpower': 65,
            'intelligence': 60
        }
        return base_costs.get(attribute.lower(), 50)

    def is_on_cooldown(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the user is on training cooldown.
        
        Returns:
            (Is on cooldown, Time remaining string)
        """
        # Normalize user ID to integer key
        user_key = int(user_id)
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        if user_key in self.cooldowns:
            expiry_time = self.cooldowns[user_key]
            if now < expiry_time:
                remaining = expiry_time - now
                return True, self._format_timedelta(remaining)
            else:
                # Cooldown expired, remove entries
                del self.cooldowns[user_key]
                if user_id in self.cooldowns:
                    del self.cooldowns[user_id]
                return False, None
        return False, None

    async def start_training(self, player_id: str, attribute: str, duration_hours: int, intensity: str) -> Tuple[bool, str]:
        """
        Starts a new training session for the player asynchronously.
        """
        # Normalize player ID key to integer
        user_key = int(player_id)
        self.logger.warning(f">>> [Service StartTrain] start_training called for {user_key}. Instance ID: {id(self)}")
        # 1. Check if already training
        if user_key in self.active_sessions:
            return False, "❌ You are already in a training session."

        # 2. Check cooldown
        on_cooldown, time_left = self.is_on_cooldown(player_id)
        if on_cooldown:
            return False, f"❌ Training is on cooldown. Time remaining: {time_left}"

        # 3. Validate inputs
        if duration_hours <= 0 or duration_hours > 72:
            return False, "❌ Invalid training duration (must be 1-72 hours)."
        valid_attributes = [
            'ninjutsu', 'taijutsu', 'genjutsu', 'strength', 'speed', 'stamina',
            'chakra_control', 'perception', 'willpower', 'intelligence'
        ]
        if attribute.lower() not in valid_attributes:
            return False, "❌ Invalid attribute selected."
        if intensity not in [
            TrainingIntensity.LIGHT,
            TrainingIntensity.MODERATE,
            TrainingIntensity.INTENSE,
            TrainingIntensity.EXTREME
        ]:
            return False, "❌ Invalid intensity selected."

        # 4. Calculate cost
        base_cost_per_hour = self._get_training_cost(attribute)
        cost_multiplier, _ = TrainingIntensity.get_multipliers(intensity)
        total_cost = int(base_cost_per_hour * duration_hours * cost_multiplier)

        # 5. Check funds
        if not self.currency_system.has_sufficient_funds(player_id, total_cost):
            current_balance = self.currency_system.get_player_balance(player_id)
            return False, f"❌ Insufficient Ryō! Cost: {total_cost:,}, Your Balance: {current_balance:,}."

        # 6. Deduct funds - Use add_balance_and_save if available
        funds_deducted = False
        if hasattr(self.currency_system, 'add_balance_and_save'):
            funds_deducted = self.currency_system.add_balance_and_save(player_id, -total_cost)
        else:
            # Fall back to old method + manual save if needed
            try:
                potential_result = self.currency_system.deduct_from_balance(player_id, total_cost)
                funds_deducted = potential_result
                
                if funds_deducted and hasattr(self.currency_system, 'save_currency_data'):
                    try:
                        self.currency_system.save_currency_data()
                    except Exception as e:
                        self.logger.error(f"Error saving currency data after deducting funds: {e}")
            except Exception as e:
                self.logger.error(f"Error deducting funds using legacy method: {e}")
                funds_deducted = False

        if not funds_deducted:
            current_balance = self.currency_system.get_player_balance(player_id)
            return False, f"❌ Failed to deduct Ryō! Cost: {total_cost:,}, Your Balance: {current_balance:,}. Please try again."

        # 7. Create and start session
        try:
            session = TrainingSession(
                user_id=str(player_id),
                attribute=attribute,
                duration_hours=duration_hours,
                cost_per_hour=base_cost_per_hour,
                intensity=intensity
            )
            # Store session under int key, session.user_id remains string
            self.active_sessions[user_key] = session
            # Mirror string key for tests
            self.active_sessions[str(player_id)] = session
            self.logger.warning(f">>> [Service StartTrain] Added session for {user_key} to active_sessions. Cache now: {list(self.active_sessions.keys())}")
            await self.save_active_sessions_async()

            self.logger.info(
                f"Training started for {player_id}: {attribute} ({intensity}) for {duration_hours}h. Cost: {total_cost} Ryō."
            )
            return (
                True,
                f"✅ Training session started! Training **{attribute.title()}** for **{duration_hours}** hours at **{intensity.title()}** intensity. Cost: {total_cost:,} Ryō."
            )
        except Exception as e:
            self.logger.error(f"Error creating TrainingSession object for {player_id}: {e}", exc_info=True)
            if hasattr(self.currency_system, 'add_balance_and_save'):
                self.currency_system.add_balance_and_save(player_id, total_cost)
            else:
                try:
                    self.currency_system.add_to_balance(player_id, total_cost)
                    if hasattr(self.currency_system, 'save_currency_data'):
                        self.currency_system.save_currency_data()
                except Exception as refund_error:
                    self.logger.error(f"Error refunding currency: {refund_error}")
                    
            return False, "❌ An internal error occurred while starting the session. Your Ryō has been refunded."
    
    async def complete_training(self, player_id: str, force_complete: bool = False):
        """
        Completes a training session for a player, calculates the results,
        and saves state.
        """
        # Normalize player ID to integer key
        user_key = int(player_id)
        if user_key not in self.active_sessions:
            return False, "❌ You are not currently training."

        session = self.active_sessions[user_key]
        now = datetime.now(timezone.utc)  # Not forcing timezone here, but you can if your environment uses UTC
        end_time = session.start_time + timedelta(hours=session.duration_hours)

        if not force_complete and now < end_time:
            time_left = end_time - now
            return False, f"⏳ Training is still in progress. Time remaining: {self._format_timedelta(time_left)}."

        try:
            # Handle partial completion if force_complete is True
            actual_duration_hours = (
                (now - session.start_time).total_seconds() / 3600
                if force_complete else session.duration_hours
            )

            results, xp_gain, injury_message = await self._calculate_training_results(
                player_id,
                session.attribute,
                actual_duration_hours,
                session.intensity
            )

            # Apply attribute stat results
            try:
                stats_map = results.get('stats', {})
                await self._apply_training_results(player_id, stats_map)
                # Apply XP gain to character and save
                xp_amount = results.get('xp', 0)
                character = await self.character_system.get_character(player_id)
                if character:
                    character.add_exp(xp_amount)
                    await self.character_system.save_character(character)
            except Exception as e:
                self.logger.error(f"Error applying training results or XP: {e}", exc_info=True)
                return False, "❌ Error applying training results to your character."

            # Remove session and save
            del self.active_sessions[user_key]
            # Remove mirrored string key
            if str(player_id) in self.active_sessions:
                del self.active_sessions[str(player_id)]
            await self.save_active_sessions_async()

            # Add to history and save
            self._update_training_history(player_id, session, xp_gain, results.get('stats', {}).get(session.attribute, 0))

            # Apply cooldown
            cooldown_duration_hours = self._get_cooldown_duration(session.intensity)
            # Store cooldown under integer key
            expiry = now + timedelta(hours=cooldown_duration_hours)
            self.cooldowns[user_key] = expiry
            # Mirror string key for tests
            self.cooldowns[str(player_id)] = expiry

            completion_message = (
                f"✅ Training session {'completed early' if force_complete else 'completed'}!\n"
                f"Trained: **{session.attribute.title()}**\n"
                f"Intensity: **{session.intensity.title()}**\n"
                f"Duration: **{round(actual_duration_hours, 1)}/{session.duration_hours} hours**\n"
                f"Points Gained: **{xp_gain:.2f}**"
            )
            if injury_message:
                completion_message += f"\n{injury_message}"

            self.logger.info(
                f"Training completed for {player_id}. Points: {xp_gain:.2f}. "
                f"Attribute: {session.attribute}"
            )
            return True, completion_message

        except Exception as e:
            self.logger.error(f"Error completing training for {player_id}: {e}", exc_info=True)
            return False, "❌ An internal error occurred while completing the session."

    async def _calculate_training_results(
        self,
        player_id: str,
        attribute: str,
        duration_hours: float,
        intensity: str
    ) -> Tuple[Dict, float, Optional[str]]:
        """
        Calculates training results asynchronously, including potential injuries.
        """
        character = await self.character_system.get_character(player_id)
        if not character:
            return {}, 0, "Character not found during result calculation."

        base_gain = self._get_base_gain(attribute)
        _, gain_multiplier = TrainingIntensity.get_multipliers(intensity)
        attribute_gain = base_gain * duration_hours * gain_multiplier
        xp_gain = attribute_gain * 5
        injury_chance, injury_severity = self._get_injury_params(intensity)
        injury_message = None
        if random.random() < injury_chance:
            injury_message = f"🤕 Ouch! Sustained injury. Gains reduced by {injury_severity*100:.0f}%."
            attribute_gain *= (1.0 - injury_severity)
            xp_gain *= (1.0 - injury_severity)
        results = {
            "stats": {attribute: round(attribute_gain, 2)},
            "xp": round(xp_gain)
        }
        return results, xp_gain, injury_message

    async def _apply_training_results(self, player_id: str, results: dict):
        """
        Applies training results to the character asynchronously.
        """
        character = await self.character_system.get_character(player_id)
        if not character:
            self.logger.warning(f"Could not apply training results: Character {player_id} not found.")
            return

        stat_updated = False
        for stat, increase in results.items():
            if increase > 0:
                success = await self.character_system.update_character_stat(player_id, stat, increase)
                if success:
                    stat_updated = True
                    self.logger.debug(f"Applied {increase:.2f} points to {stat} for {player_id}")
                else:
                    self.logger.error(f"Failed to update stat {stat} for {player_id}")

        if not stat_updated:
            self.logger.warning(
                f"No stats were updated for character {player_id} from results: {results}"
            )

    def get_training_status(self, player_id: str) -> Optional[dict]:
        """Get the status of the current training session or cooldown for a player."""
        # Try integer key first, then string
        session = None
        key_int = int(player_id)
        if key_int in self.active_sessions:
            session = self.active_sessions[key_int]
        elif player_id in self.active_sessions:
            session = self.active_sessions[player_id]

        # If a session is active, build its status
        if session:
            # Recalculate end_time and remaining
            end_time = session.start_time + timedelta(hours=session.duration_hours)
            now = datetime.now(timezone.utc)
            remaining = end_time - now
            status = {
                "attribute": session.attribute,
                "intensity": session.intensity,
                "start_time": session.start_time,
                "end_time": end_time,
                "duration_hours": session.duration_hours,
                "time_remaining": self._format_timedelta(remaining) if remaining > timedelta(0) else "Complete!",
                "is_complete": now >= end_time
            }
            self.logger.warning(f">>> [Service GetStatus] get_training_status for {player_id}. Found active session. Instance ID: {id(self)}")
            return status

        # No active session; check cooldown
        on_cooldown, time_left = self.is_on_cooldown(player_id)
        if on_cooldown:
            status = {"on_cooldown": True, "time_remaining": time_left}
            self.logger.warning(f">>> [Service GetStatus] get_training_status for {player_id}. On cooldown. Instance ID: {id(self)}")
            return status

        # Neither active nor on cooldown
        self.logger.warning(f">>> [Service GetStatus] get_training_status for {player_id}. No active session or cooldown. Instance ID: {id(self)}")
        return None
        
    def get_training_status_embed(self, user_id: str) -> Optional[discord.Embed]:
        """Generate an embed displaying the current training status."""
        status = self.get_training_status(user_id)
        # If no status or only on cooldown, do not show embed
        if not status or status.get('on_cooldown', False):
            return None

        # Wrap embed creation in try/except to catch errors
        try:
            embed = discord.Embed(
                title="🏋️ Training Status",
                color=discord.Color.blue()
            )
            
            # Add training detail fields
            embed.add_field(
                name="Attribute",
                value=status['attribute'].title(),
                inline=True
            )
            embed.add_field(
                name="Intensity",
                value=status['intensity'].title(),
                inline=True
            )
            
            # Calculate time remaining
            end_time = status['end_time']
            now = datetime.now(timezone.utc)
            time_remaining = end_time - now
            
            # Build description to include attribute and intensity
            if time_remaining.total_seconds() <= 0:
                # Training is complete
                desc = f"**Attribute:** {status['attribute'].title()}\n"
                desc += f"**Intensity:** {status['intensity'].title()}\n"
                desc += "✅ Your training is complete! Use `/complete` to claim your results."
                embed.description = desc
                embed.color = discord.Color.green()
            else:
                # Training is in progress
                time_str = self._format_timedelta(time_remaining)
                desc = f"**Attribute:** {status['attribute'].title()}\n"
                desc += f"**Intensity:** {status['intensity'].title()}\n"
                desc += f"⏳ Training in progress... {time_str} remaining"
                embed.description = desc
            
            # Add progress bar
            total_duration_seconds = status['duration_hours'] * 3600
            elapsed_seconds = (now - status['start_time']).total_seconds()
            progress = min(elapsed_seconds / total_duration_seconds, 1.0) if total_duration_seconds > 0 else 1.0
            
            progress_bar_length = 20
            filled_blocks = int(progress * progress_bar_length)
            empty_blocks = progress_bar_length - filled_blocks
            progress_bar = "█" * filled_blocks + "░" * empty_blocks
            embed.add_field(
                name="Progress",
                value=f"`{progress_bar}` {int(progress * 100)}%",
                inline=False
            )
            
            return embed
            
        except Exception as e:
            self.logger.error(f"Error CREATING training status embed for {user_id}: {e}", exc_info=True)
            # Log the session data that caused the error
            try:
                self.logger.error(f"Problematic session data: {status}")
            except Exception as serialize_e:
                self.logger.error(f"Could not serialize problematic session data: {serialize_e}")
            return None  # Return None if any error occurs during embed creation

    def get_training_history(self, user_id: str, limit: int = 10) -> Optional[Dict]:
        """
        Get a user's training history with detailed statistics.
        """
        if user_id not in self.training_history:
            return None
        
        history = self.training_history[user_id][-limit:]
        
        # Calculate detailed statistics
        stats = {
            'total_sessions': len(self.training_history[user_id]),
            'total_points': sum(entry['xp_gain'] for entry in self.training_history[user_id]),
            'total_cost': sum(entry['cost'] for entry in self.training_history[user_id]),
            'intense_sessions': sum(1 for entry in self.training_history[user_id] if entry['intensity'] == TrainingIntensity.INTENSE),
            'extreme_sessions': sum(1 for entry in self.training_history[user_id] if entry['intensity'] == TrainingIntensity.EXTREME),
            'max_duration': max(entry['duration_hours'] for entry in self.training_history[user_id]),
            'max_points': max(entry['xp_gain'] for entry in self.training_history[user_id]),
            'unique_attributes': len(set(entry['attribute'] for entry in self.training_history[user_id])),
            'attribute_points': {},
            'total_hours': sum(entry['duration_hours'] for entry in self.training_history[user_id]),
            'average_points_per_hour': sum(entry['xp_gain'] for entry in self.training_history[user_id]) / 
                                       sum(entry['duration_hours'] for entry in self.training_history[user_id]) if self.training_history[user_id] else 0
        }
        
        # Calculate points per attribute
        for entry in self.training_history[user_id]:
            if entry['attribute'] not in stats['attribute_points']:
                stats['attribute_points'][entry['attribute']] = 0
            stats['attribute_points'][entry['attribute']] += entry['xp_gain']
        
        stats['max_attribute_points'] = (
            max(stats['attribute_points'].values()) if stats['attribute_points'] else 0
        )
        
        # Check for new achievements
        earned_achievements = self.check_achievements(user_id, stats)
        
        return {
            'entries': history,
            'stats': stats,
            'earned_achievements': earned_achievements,
            'achievements': self.user_achievements.get(user_id, [])
        } 

    def _get_base_gain(self, attribute: str) -> float:
        """
        Define base gain per hour for each attribute.
        """
        gain_map = {
            "ninjutsu": 1.0,
            "taijutsu": 1.0,
            "genjutsu": 0.8,
            "intelligence": 0.7,
            "strength": 1.2,
            "speed": 1.1,
            "stamina": 1.5,
            "chakra_control": 0.9,
            "perception": 0.6,
            "willpower": 0.7
        }
        return gain_map.get(attribute.lower(), 1.0)

    def _get_injury_params(self, intensity: str) -> Tuple[float, float]:
        """
        Returns (chance_of_injury, severity_multiplier).
        """
        if intensity == TrainingIntensity.LIGHT:
            return 0.01, 0.5
        elif intensity == TrainingIntensity.MODERATE:
            return 0.05, 1.0
        elif intensity == TrainingIntensity.INTENSE:
            return 0.15, 1.5
        elif intensity == TrainingIntensity.EXTREME:
            return 0.30, 2.0
        return 0.0, 0.0

    def _get_cooldown_duration(self, intensity: str) -> float:
        """
        Returns cooldown duration in hours.
        """
        if intensity == TrainingIntensity.LIGHT:
            return 0.1      # 6 minutes
        if intensity == TrainingIntensity.MODERATE:
            return 0.25     # 15 minutes
        if intensity == TrainingIntensity.INTENSE:
            return 0.5      # 30 minutes
        if intensity == TrainingIntensity.EXTREME:
            return 1.0      # 1 hour
        return 0

    def _format_timedelta(self, delta: timedelta) -> str:
        """
        Formats a timedelta into a readable string (e.g., 1h 30m 15s).
        """
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            total_seconds = 0
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        return " ".join(parts)

    async def cancel_training(self, player_id: str) -> Tuple[bool, str]:
        """
        Cancels an ongoing training session.
        """
        if player_id not in self.active_sessions:
            return False, "❌ You are not currently training."

        session = self.active_sessions[player_id]
        try:
            del self.active_sessions[player_id]
            await self.save_sessions()
            self.logger.info(
                f"Training session cancelled for {player_id}. "
                f"Attribute: {session.attribute}, Intensity: {session.intensity}."
            )
            return True, (
                f"✅ Training session for **{session.attribute.title()}** cancelled. "
                "No Ryō refunded."
            )
        except Exception as e:
            self.logger.error(f"Error cancelling training for {player_id}: {e}", exc_info=True)
            return False, "❌ An error occurred while trying to cancel the session."

    # --- NEW: Background Task --- #
    @tasks.loop(minutes=5) # Check every 5 minutes
    async def check_training_completion(self):
        """Check for completed training sessions."""
        try:
            now = datetime.now(timezone.utc)
            for user_id, session in self.active_sessions.items():
                if session and not session.completed and now >= session.end_time:
                    # Training completed
                    session.completed = True
                    await self._handle_training_completion(user_id, session)
                    self.logger.info(f"Training completed for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error in training completion check: {e}", exc_info=True)

    async def _handle_training_completion(self, user_id: str, session: TrainingSession):
        """Handle a completed training session."""
        try:
            # Calculate results
            results, xp_gain, injury_message = await self._calculate_training_results(
                user_id,
                session.attribute,
                session.duration_hours,
                session.intensity
            )
            
            # Apply results
            await self._apply_training_results(user_id, results)
            
            # Update history
            self._update_training_history(user_id, session, xp_gain, results.get('attribute_gain', 0))
            
            # Save changes
            await self.save_history_async()
            await self.save_active_sessions_async()
            
            # Log completion
            self.logger.info(
                f"Training completed for {user_id}. "
                f"Attribute: {session.attribute}, "
                f"Intensity: {session.intensity}, "
                f"XP Gain: {xp_gain}"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling training completion for {user_id}: {e}", exc_info=True)

    @check_training_completion.before_loop
    async def before_check_training_completion(self):
        # This is where you might inject the bot dependency if needed for notifications
        # For now, just log that it's waiting for bot readiness
        # In a cog, you'd use self.bot.wait_until_ready()
        # Since this is a core system, direct bot access is harder.
        # We'll rely on the loop not running until services are initialized.
        self.logger.info('TrainingSystem background task waiting for services...')
        # Crude wait, assuming initialization takes some time.
        # A better approach might involve an event system or explicit ready signal.
        await asyncio.sleep(10) # Wait 10 seconds after init
        self.logger.info('TrainingSystem background task starting.')
        logger.info("Training completion check loop is ready.")
    # --- END NEW: Background Task --- #

    async def shutdown(self):
        """Cancel background tasks and perform cleanup."""
        self.logger.info("Shutting down TrainingSystem...")
        if self.check_training_completion.is_running():
            self.check_training_completion.cancel()
            self.logger.info("Cancelled training completion check task.")
        # Add any other cleanup if needed (e.g., final save of sessions?)
        # await self.save_sessions() # Consider if a final save is needed here
        self.logger.info("TrainingSystem shutdown complete.")
