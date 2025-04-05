"""Training system for the HCshinobi Discord bot."""
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import logging
import json
import os
import asyncio
import aiofiles
import random
import discord

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
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=duration_hours)
        self.cost_per_hour = cost_per_hour
        self.total_cost = cost_per_hour * duration_hours
        self.intensity = intensity
        self.completed = False
        self.duration_hours = duration_hours  # Keep for serialization

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'attribute': self.attribute,
            'duration_hours': self.duration_hours,
            'cost_per_hour': self.cost_per_hour,
            'intensity': self.intensity,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'completed': self.completed
        }

    @classmethod
    def from_dict(cls, data):
        instance = cls(
            data['user_id'],
            data['attribute'],
            data['duration_hours'],
            data['cost_per_hour'],
            data['intensity']
        )
        instance.start_time = datetime.fromisoformat(data['start_time'])
        instance.end_time = datetime.fromisoformat(data['end_time'])
        instance.completed = data['completed']
        return instance

class TrainingSystem:
    """Manages character training sessions."""
    
    def __init__(self, data_dir: str, character_system, currency_system):
        """
        Initialize the training system.
        
        Args:
            data_dir: Directory for storing training data
            character_system: The character system instance
            currency_system: The currency system instance
        """
        self.data_dir = data_dir
        self.character_system = character_system
        self.currency_system = currency_system
        self.logger = logging.getLogger(__name__)
        
        # Training data file
        self.training_file = os.path.join(data_dir, "training.json")
        self.training_data = self._load_training_data()
        self.active_sessions: Dict[str, TrainingSession] = {}

        # Files for training history and achievements
        self.history_file = os.path.join(data_dir, "training_history.json")
        self.achievements_file = os.path.join(data_dir, "training_achievements.json")

        # Cooldowns
        self.cooldowns: Dict[str, datetime] = {}
        self.cooldown_hours = 1  # 1 hour cooldown between sessions

        # Achievements
        self.achievements = self._initialize_achievements()
        self.user_achievements: Dict[str, List[str]] = {}

        # Load state
        self.load_sessions()
        self.load_history()
        self.load_achievements()
    
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
    
    def _load_training_data(self) -> dict:
        """Load training data from file."""
        if os.path.exists(self.training_file):
            try:
                with open(self.training_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading training data: {e}")
                return {}
        return {}
    
    def _save_training_data(self):
        """Save training data to file."""
        try:
            with open(self.training_file, 'w') as f:
                json.dump(self.training_data, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving training data: {e}")
    
    def load_achievements(self):
        """Load user achievements from file."""
        try:
            if os.path.exists(self.achievements_file):
                with open(self.achievements_file, 'r') as f:
                    self.user_achievements = json.load(f)
            else:
                self.user_achievements = {}
        except Exception as e:
            logger.error(f"Error loading achievements: {e}")
            self.user_achievements = {}
    
    def save_achievements(self):
        """Save user achievements to file."""
        try:
            with open(self.achievements_file, 'w') as f:
                json.dump(self.user_achievements, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving achievements: {e}")
    
    def check_achievements(self, user_id: str, stats: Dict) -> List[Tuple[str, str, int]]:
        """
        Check and award achievements based on training statistics.
        
        Returns:
            List of (achievement_name, description, reward) for newly earned achievements
        """
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = []
        
        earned_achievements = []
        for achievement in self.achievements:
            if achievement.name not in self.user_achievements[user_id]:
                # Evaluate each condition
                if achievement.condition == "sessions >= 1" and stats['total_sessions'] >= 1:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "sessions >= 10" and stats['total_sessions'] >= 10:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "sessions >= 50" and stats['total_sessions'] >= 50:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "intense_sessions >= 1" and stats['intense_sessions'] >= 1:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "extreme_sessions >= 1" and stats['extreme_sessions'] >= 1:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "attribute_points >= 100" and stats['max_attribute_points'] >= 100:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "unique_attributes >= 10" and stats['unique_attributes'] >= 10:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "max_duration >= 24" and stats['max_duration'] >= 24:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "max_points >= 50" and stats['max_points'] >= 50:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
                elif achievement.condition == "total_cost >= 10000" and stats['total_cost'] >= 10000:
                    earned_achievements.append((achievement.name, achievement.description, achievement.reward))
        
        # Award achievements and rewards
        for name, _, reward in earned_achievements:
            self.user_achievements[user_id].append(name)
            
            # Award the Ryō using add_balance_and_save with fallback
            if hasattr(self.currency_system, 'add_balance_and_save'):
                self.currency_system.add_balance_and_save(user_id, reward)
            else:
                # Fall back to old method
                try:
                    if hasattr(self.currency_system, 'add_ryo'):
                        self.currency_system.add_ryo(user_id, reward)
                    else:
                        self.currency_system.add_to_balance(user_id, reward)
                    
                    # Save currency data manually if needed
                    if hasattr(self.currency_system, 'save_currency_data'):
                        self.currency_system.save_currency_data()
                except Exception as e:
                    self.logger.error(f"Error adding achievement reward to player {user_id}: {e}")
        
        self.save_achievements()
        return earned_achievements
    
    def load_sessions(self):
        """Load active training sessions from file."""
        try:
            if os.path.exists(self.training_file):
                with open(self.training_file, 'r') as f:
                    data = json.load(f)
                    for user_id, session_data in data.items():
                        self.active_sessions[user_id] = TrainingSession.from_dict(session_data)
        except Exception as e:
            logger.error(f"Error loading training sessions: {e}")
            self.active_sessions = {}
    
    async def save_sessions(self):
        """Save active training sessions to file asynchronously."""
        try:
            data_to_save = {
                pid: s.to_dict() for pid, s in self.active_sessions.items()
            }
            async with aiofiles.open(self.training_file, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(data_to_save, indent=4))
            self.logger.debug(f"Training sessions saved to {self.training_file}")
        except Exception as e:
            self.logger.error(f"Failed to save training sessions: {e}", exc_info=True)
    
    def load_history(self):
        """Load training history from file."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
            else:
                self.history = {}
        except Exception as e:
            logger.error(f"Error loading training history: {e}")
            self.history = {}
    
    def save_history(self):
        """Save training history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving training history: {e}")
    
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
        last_session_end = self.cooldowns.get(user_id)
        if not last_session_end:
            return False, None
        
        cooldown_ends = last_session_end + timedelta(hours=self.cooldown_hours)
        now = datetime.now()
        
        if now < cooldown_ends:
            time_remaining = cooldown_ends - now
            minutes, seconds = divmod(int(time_remaining.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)
            return True, f"{hours}h {minutes}m {seconds}s"
        return False, None

    async def start_training(self, player_id: str, attribute: str, duration_hours: int, intensity: str) -> Tuple[bool, str]:
        """
        Starts a new training session for the player asynchronously.
        """
        # 1. Check if already training
        if player_id in self.active_sessions:
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
            # Use the new atomic method that saves immediately
            funds_deducted = self.currency_system.add_balance_and_save(player_id, -total_cost)
        else:
            # Fall back to old method + manual save if needed
            try:
                # Old style may be synchronous or asynchronous
                potential_result = self.currency_system.deduct_from_balance(player_id, total_cost)
                funds_deducted = potential_result
                
                # Manually save after old-style deduct_from_balance
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
                user_id=player_id,
                attribute=attribute,
                duration_hours=duration_hours,
                cost_per_hour=base_cost_per_hour,
                intensity=intensity
            )
            self.active_sessions[player_id] = session
            await self.save_sessions()

            self.logger.info(
                f"Training started for {player_id}: {attribute} ({intensity}) for {duration_hours}h. Cost: {total_cost} Ryō."
            )
            return (
                True,
                f"✅ Training session started! Training **{attribute.title()}** for **{duration_hours}** hours at **{intensity.title()}** intensity. Cost: {total_cost:,} Ryō."
            )
        except Exception as e:
            self.logger.error(f"Error creating TrainingSession object for {player_id}: {e}", exc_info=True)
            # Attempt to refund if session creation fails - Use add_balance_and_save if available
            if hasattr(self.currency_system, 'add_balance_and_save'):
                self.currency_system.add_balance_and_save(player_id, total_cost)
            else:
                try:
                    self.currency_system.add_to_balance(player_id, total_cost)
                    # Save after refund
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
        if player_id not in self.active_sessions:
            return False, "❌ You are not currently training."

        session = self.active_sessions[player_id]
        now = datetime.now()  # Not forcing timezone here, but you can if your environment uses UTC
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

            results, points_gained, injury_message = await self._calculate_training_results(
                player_id,
                session.attribute,
                actual_duration_hours,
                session.intensity
            )

            # Apply results to character
            try:
                await self._apply_training_results(player_id, results)
            except Exception as e:
                self.logger.error(f"Error applying training results: {e}", exc_info=True)
                return False, "❌ Error applying training results to your character."

            # Remove session and save
            del self.active_sessions[player_id]
            await self.save_sessions()

            # Add to history and save
            history_entry = {
                "timestamp": now.isoformat(),
                "attribute": session.attribute,
                "intensity": session.intensity,
                "duration_hours": session.duration_hours,
                "actual_duration_hours": round(actual_duration_hours, 2),
                "cost": session.cost_per_hour * session.duration_hours,
                "points_gained": points_gained,
                "outcome": "Completed Early" if force_complete else "Completed",
                "injury": injury_message if injury_message else "None"
            }
            if player_id not in self.history:
                self.history[player_id] = []
            self.history[player_id].append(history_entry)
            self.save_history()

            # Apply cooldown
            cooldown_duration_hours = self._get_cooldown_duration(session.intensity)
            self.cooldowns[player_id] = now + timedelta(hours=cooldown_duration_hours)

            completion_message = (
                f"✅ Training session {'completed early' if force_complete else 'completed'}!\n"
                f"Trained: **{session.attribute.title()}**\n"
                f"Intensity: **{session.intensity.title()}**\n"
                f"Duration: **{round(actual_duration_hours, 1)}/{session.duration_hours} hours**\n"
                f"Points Gained: **{points_gained:.2f}**"
            )
            if injury_message:
                completion_message += f"\n{injury_message}"

            self.logger.info(
                f"Training completed for {player_id}. Points: {points_gained:.2f}. "
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
        # Base gain
        base_gain_per_hour = self._get_base_gain(attribute)
        _, gain_multiplier = TrainingIntensity.get_multipliers(intensity)
        total_points_gained = base_gain_per_hour * duration_hours * gain_multiplier

        # Injury calculation
        injury_chance, injury_severity_multiplier = self._get_injury_params(intensity)
        injury_message = None
        injury_penalty_factor = 1.0

        if random.random() < injury_chance:
            # Apply injury penalty
            injury_penalty_factor = 1.0 - (random.uniform(0.1, 0.5) * injury_severity_multiplier)
            total_points_gained = max(0, total_points_gained * injury_penalty_factor)
            injury_message = "🩹 Ouch! You sustained an injury, reducing training gains."

            # Example: demonstrate how to add a more severe effect
            # If you want to penalize future sessions or add a 'wounded' status, do it here:
            # await self.character_system.apply_status_effect(player_id, "wounded", 24)  # pseudo-code
            self.logger.info(
                f"Player {player_id} sustained injury during {intensity} training. "
                f"Penalty factor: {injury_penalty_factor:.2f}"
            )

        final_points_gained = max(0, round(total_points_gained, 2))
        results = {attribute: final_points_gained}
        return results, final_points_gained, injury_message

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
        """Get the status of the current training session."""
        return self.active_sessions.get(player_id)
        
    def get_training_status_embed(self, user_id: str) -> Optional[discord.Embed]:
        """Generate an embed displaying the current training status."""
        session = self.active_sessions.get(str(user_id))
        if not session:
            return None

        # Wrap embed creation in try/except to catch errors
        try:
            embed = discord.Embed(
                title="🏋️ Training Status",
                color=discord.Color.blue()
            )
            
            # Add training details
            embed.add_field(
                name="Attribute",
                value=session.attribute.title(),
                inline=True
            )
            embed.add_field(
                name="Intensity",
                value=session.intensity.title(),
                inline=True
            )
            
            # Calculate time remaining
            end_time = session.end_time
            now = datetime.now() # Consider timezone if necessary
            time_remaining = end_time - now
            
            if time_remaining.total_seconds() <= 0:
                # Training is complete
                embed.description = "✅ Your training is complete! Use `/complete` to claim your results."
                embed.color = discord.Color.green()
            else:
                # Training is in progress
                # Use the helper function for formatting
                time_str = self._format_timedelta(time_remaining)
                embed.description = f"⏳ Training in progress... {time_str} remaining"
                
            # Add progress bar
            total_duration_seconds = session.duration_hours * 3600
            elapsed_seconds = (now - session.start_time).total_seconds()
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
                 self.logger.error(f"Problematic session data: {session.to_dict()}")
            except Exception as serialize_e:
                 self.logger.error(f"Could not serialize problematic session data: {serialize_e}")
            return None # Return None if any error occurs during embed creation

    def get_training_history(self, user_id: str, limit: int = 10) -> Optional[Dict]:
        """
        Get a user's training history with detailed statistics.
        """
        if user_id not in self.history:
            return None
        
        history = self.history[user_id][-limit:]
        
        # Calculate detailed statistics
        stats = {
            'total_sessions': len(self.history[user_id]),
            'total_points': sum(entry['points_gained'] for entry in self.history[user_id]),
            'total_cost': sum(entry['cost'] for entry in self.history[user_id]),
            'intense_sessions': sum(1 for entry in self.history[user_id] if entry['intensity'] == TrainingIntensity.INTENSE),
            'extreme_sessions': sum(1 for entry in self.history[user_id] if entry['intensity'] == TrainingIntensity.EXTREME),
            'max_duration': max(entry['duration_hours'] for entry in self.history[user_id]),
            'max_points': max(entry['points_gained'] for entry in self.history[user_id]),
            'unique_attributes': len(set(entry['attribute'] for entry in self.history[user_id])),
            'attribute_points': {},
            'total_hours': sum(entry['duration_hours'] for entry in self.history[user_id]),
            'average_points_per_hour': sum(entry['points_gained'] for entry in self.history[user_id]) / 
                                       sum(entry['duration_hours'] for entry in self.history[user_id]) if self.history[user_id] else 0
        }
        
        # Calculate points per attribute
        for entry in self.history[user_id]:
            if entry['attribute'] not in stats['attribute_points']:
                stats['attribute_points'][entry['attribute']] = 0
            stats['attribute_points'][entry['attribute']] += entry['points_gained']
        
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
