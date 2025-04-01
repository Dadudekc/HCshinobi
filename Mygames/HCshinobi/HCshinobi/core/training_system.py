"""Training system for the HCshinobi Discord bot."""
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import logging
import json
import os

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
    LIGHT = "light"  # 1.0x cost, 1.0x gain
    MODERATE = "moderate"  # 1.5x cost, 1.5x gain
    INTENSE = "intense"  # 2.0x cost, 2.0x gain
    EXTREME = "extreme"  # 3.0x cost, 2.5x gain

    @staticmethod
    def get_multipliers(intensity: str) -> Tuple[float, float]:
        """Get cost and gain multipliers for intensity level.
        
        Light: 1.0x cost, 1.0x gain (base training)
        Moderate: 1.5x cost, 1.8x gain (efficient training)
        Intense: 2.5x cost, 2.5x gain (challenging training)
        Extreme: 4.0x cost, 3.0x gain (risky training)
        """
        multipliers = {
            TrainingIntensity.LIGHT: (1.0, 1.0),    # Base training
            TrainingIntensity.MODERATE: (1.5, 1.8),  # More efficient
            TrainingIntensity.INTENSE: (2.5, 2.5),   # High risk, high reward
            TrainingIntensity.EXTREME: (4.0, 3.0)    # Maximum risk, maximum reward
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

class TrainingSystem:
    """Manages character training sessions."""
    
    def __init__(self, data_dir: str, character_system, currency_system):
        """Initialize the training system.
        
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
        self.history_file = os.path.join(data_dir, "training_history.json")
        self.achievements_file = os.path.join(data_dir, "training_achievements.json")
        self.cooldowns: Dict[str, datetime] = {}
        self.cooldown_hours = 1  # 1 hour cooldown between sessions
        self.achievements = self._initialize_achievements()
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
        """Load training data from file.
        
        Returns:
            dict: Training data
        """
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
        """Check and award achievements based on training statistics.
        
        Args:
            user_id: Discord user ID
            stats: Training statistics dictionary
            
        Returns:
            List of (achievement_name, description, reward) for newly earned achievements
        """
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = []
        
        earned_achievements = []
        for achievement in self.achievements:
            if achievement.name not in self.user_achievements[user_id]:
                # Check achievement conditions
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
            self.currency_system.add_ryo(user_id, reward)
        
        self.save_achievements()
        return earned_achievements
    
    def load_sessions(self):
        """Load active training sessions from file."""
        try:
            if os.path.exists(self.training_file):
                with open(self.training_file, 'r') as f:
                    data = json.load(f)
                    for user_id, session_data in data.items():
                        self.active_sessions[user_id] = TrainingSession(
                            user_id=session_data['user_id'],
                            attribute=session_data['attribute'],
                            duration_hours=session_data['duration_hours'],
                            cost_per_hour=session_data['cost_per_hour'],
                            intensity=session_data['intensity']
                        )
                        # Restore datetime objects
                        self.active_sessions[user_id].start_time = datetime.fromisoformat(session_data['start_time'])
                        self.active_sessions[user_id].end_time = datetime.fromisoformat(session_data['end_time'])
                        self.active_sessions[user_id].completed = session_data['completed']
        except Exception as e:
            logger.error(f"Error loading training sessions: {e}")
            self.active_sessions = {}
    
    def save_sessions(self):
        """Save active training sessions to file."""
        try:
            data = {}
            for user_id, session in self.active_sessions.items():
                data[user_id] = {
                    'user_id': session.user_id,
                    'attribute': session.attribute,
                    'duration_hours': session.duration_hours,
                    'cost_per_hour': session.cost_per_hour,
                    'intensity': session.intensity,
                    'start_time': session.start_time.isoformat(),
                    'end_time': session.end_time.isoformat(),
                    'completed': session.completed
                }
            with open(self.training_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving training sessions: {e}")
    
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
    
    def get_training_cost(self, attribute: str, intensity: str) -> int:
        """Get the cost per hour to train a specific attribute.
        
        Args:
            attribute: The attribute to train
            intensity: Training intensity level
            
        Returns:
            Cost in Ryō per hour
        """
        # Base costs for different attributes
        costs = {
            'ninjutsu': 200,
            'taijutsu': 150,
            'genjutsu': 200,
            'intelligence': 100,
            'strength': 100,
            'speed': 100,
            'stamina': 100,
            'chakra_control': 150,
            'perception': 100,
            'willpower': 100
        }
        base_cost = costs.get(attribute, 100)
        cost_multiplier, _ = TrainingIntensity.get_multipliers(intensity)
        return int(base_cost * cost_multiplier)
    
    def is_on_cooldown(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Check if a user is on training cooldown.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (is_on_cooldown, remaining_time)
        """
        if user_id not in self.cooldowns:
            return False, None
            
        cooldown_end = self.cooldowns[user_id]
        if datetime.now() >= cooldown_end:
            del self.cooldowns[user_id]
            return False, None
            
        remaining = cooldown_end - datetime.now()
        hours = remaining.total_seconds() / 3600
        return True, f"{hours:.1f} hours"
    
    def start_training(self, player_id: str, training_type: str) -> bool:
        """Start a training session.
        
        Args:
            player_id: The ID of the player
            training_type: Type of training (taijutsu, ninjutsu, genjutsu)
            
        Returns:
            bool: True if training started successfully
        """
        # Check if player is already training
        if player_id in self.training_data:
            return False
        
        # Get character
        character = self.character_system.get_character(player_id)
        if not character:
            return False
        
        # Check if player has enough Ryō
        training_cost = self._get_training_cost(training_type)
        if not self.currency_system.check_balance(player_id, training_cost):
            return False
        
        # Deduct training cost
        self.currency_system.deduct_balance(player_id, training_cost)
        
        # Start training session
        self.training_data[player_id] = {
            "type": training_type,
            "start_time": datetime.now().isoformat(),
            "duration": 3600  # 1 hour training session
        }
        
        self._save_training_data()
        return True
    
    def end_training(self, player_id: str) -> dict:
        """End a training session.
        
        Args:
            player_id: The ID of the player
            
        Returns:
            dict: Training results
        """
        if player_id not in self.training_data:
            return None
        
        training_session = self.training_data[player_id]
        start_time = datetime.fromisoformat(training_session["start_time"])
        duration = training_session["duration"]
        
        # Calculate training results
        results = self._calculate_training_results(player_id, training_session["type"], duration)
        
        # Apply results to character
        self._apply_training_results(player_id, results)
        
        # Clean up training session
        del self.training_data[player_id]
        self._save_training_data()
        
        return results
    
    def _get_training_cost(self, training_type: str) -> int:
        """Get the cost for a training type.
        
        Args:
            training_type: Type of training
            
        Returns:
            int: Cost in Ryō
        """
        costs = {
            "taijutsu": 100,
            "ninjutsu": 150,
            "genjutsu": 200
        }
        return costs.get(training_type, 100)
    
    def _calculate_training_results(self, player_id: str, training_type: str, duration: int) -> dict:
        """Calculate training results.
        
        Args:
            player_id: The ID of the player
            training_type: Type of training
            duration: Training duration in seconds
            
        Returns:
            dict: Training results
        """
        character = self.character_system.get_character(player_id)
        if not character:
            return None
        
        # Base stat increase
        base_increase = duration / 3600  # 1 point per hour
        
        # Calculate stat increases based on training type
        results = {
            "taijutsu": {"strength": base_increase * 2, "speed": base_increase},
            "ninjutsu": {"chakra": base_increase * 2, "intelligence": base_increase},
            "genjutsu": {"intelligence": base_increase * 2, "chakra": base_increase}
        }
        
        return results.get(training_type, {})
    
    def _apply_training_results(self, player_id: str, results: dict):
        """Apply training results to character.
        
        Args:
            player_id: The ID of the player
            results: Training results to apply
        """
        character = self.character_system.get_character(player_id)
        if not character:
            return
        
        # Apply stat increases
        for stat, increase in results.items():
            if stat in character["stats"]:
                character["stats"][stat] += increase
        
        # Save updated character
        self.character_system.save_character(player_id, character)
    
    def get_training_status(self, player_id: str) -> dict:
        """Get the current training status of a player.
        
        Args:
            player_id: The ID of the player
            
        Returns:
            dict: Training status
        """
        if player_id not in self.training_data:
            return None
        
        training_session = self.training_data[player_id]
        start_time = datetime.fromisoformat(training_session["start_time"])
        duration = training_session["duration"]
        
        # Calculate remaining time
        end_time = start_time + timedelta(seconds=duration)
        remaining = (end_time - datetime.now()).total_seconds()
        
        return {
            "type": training_session["type"],
            "remaining_time": max(0, remaining),
            "start_time": start_time.isoformat()
        }
    
    def get_training_history(self, user_id: str, limit: int = 10) -> Optional[Dict]:
        """Get a user's training history with detailed statistics.
        
        Args:
            user_id: Discord user ID
            limit: Maximum number of history entries to return
            
        Returns:
            Training history dictionary if found, None otherwise
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
        
        stats['max_attribute_points'] = max(stats['attribute_points'].values()) if stats['attribute_points'] else 0
        
        # Check for new achievements
        earned_achievements = self.check_achievements(user_id, stats)
        
        return {
            'entries': history,
            'stats': stats,
            'earned_achievements': earned_achievements,
            'achievements': self.user_achievements.get(user_id, [])
        } 