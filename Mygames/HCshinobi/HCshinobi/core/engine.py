"""
Engine module for the HCshinobi project.
Handles core game mechanics and systems integration.
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .character_system import CharacterSystem
from .clan_data import ClanData
from .battle_system import BattleSystem
from .currency_system import CurrencySystem
from .training_system import TrainingSystem

logger = logging.getLogger(__name__)

class Engine:
    """
    Core game engine that manages all systems and their interactions.
    Handles game state, system coordination, and game mechanics.
    """
    
    def __init__(self, data_dir: str = "data"):
        """Initialize the game engine.
        
        Args:
            data_dir: Directory to store game data
        """
        self.data_dir = data_dir
        self.character_system = CharacterSystem(data_dir)
        self.clan_data = ClanData()
        self.battle_system = BattleSystem()
        self.currency_system = CurrencySystem(data_dir)
        self.training_system = TrainingSystem(data_dir, self.currency_system)
        
        # Game state tracking
        self.active_battles: Dict[str, Dict[str, Any]] = {}
        self.training_sessions: Dict[str, Dict[str, Any]] = {}
        self.last_daily_reset: Optional[datetime] = None
        
        logger.info("Game engine initialized successfully")

    def check_daily_reset(self) -> None:
        """Check if daily reset is needed and perform it if necessary."""
        current_time = datetime.now()
        
        # If no last reset time or it's a new day
        if (not self.last_daily_reset or 
            current_time.date() > self.last_daily_reset.date()):
            self._perform_daily_reset()
            self.last_daily_reset = current_time

    def _perform_daily_reset(self) -> None:
        """Perform daily reset of game systems."""
        logger.info("Performing daily reset...")
        
        # Reset training sessions
        self.training_sessions.clear()
        
        # Reset active battles
        self.active_battles.clear()
        
        # Reset daily quests and rewards
        self.currency_system.reset_daily_rewards()
        
        logger.info("Daily reset completed")

    def start_battle(self, attacker_id: str, defender_id: str) -> Optional[str]:
        """Start a battle between two characters.
        
        Args:
            attacker_id: Discord ID of the attacking player
            defender_id: Discord ID of the defending player
            
        Returns:
            Battle ID if successful, None otherwise
        """
        # Get characters
        attacker = self.character_system.get_character(attacker_id)
        defender = self.character_system.get_character(defender_id)
        
        if not attacker or not defender:
            return None
            
        # Start battle
        battle_id = self.battle_system.start_battle(attacker, defender)
        if battle_id:
            self.active_battles[battle_id] = {
                'attacker_id': attacker_id,
                'defender_id': defender_id,
                'start_time': datetime.now()
            }
            return battle_id
        return None

    def end_battle(self, battle_id: str) -> Optional[Dict[str, Any]]:
        """End a battle and process rewards.
        
        Args:
            battle_id: ID of the battle to end
            
        Returns:
            Battle results if successful, None otherwise
        """
        if battle_id not in self.active_battles:
            return None
            
        battle_data = self.active_battles[battle_id]
        results = self.battle_system.end_battle(battle_id)
        
        if results:
            # Process rewards
            winner_id = battle_data['attacker_id'] if results['winner'] == 'attacker' else battle_data['defender_id']
            loser_id = battle_data['defender_id'] if results['winner'] == 'attacker' else battle_data['attacker_id']
            
            # Award experience and currency
            self.currency_system.award_battle_rewards(winner_id, results['exp_gained'])
            
            # Update character stats
            winner = self.character_system.get_character(winner_id)
            if winner:
                winner.gain_exp(results['exp_gained'])
                self.character_system.update_character(winner_id, winner)
        
        del self.active_battles[battle_id]
        return results

    def start_training(self, user_id: str, attribute: str) -> bool:
        """Start a training session.
        
        Args:
            user_id: Discord ID of the user
            attribute: Attribute to train
            
        Returns:
            True if successful, False otherwise
        """
        character = self.character_system.get_character(user_id)
        if not character:
            return False
            
        if self.training_system.start_training(user_id, attribute):
            self.training_sessions[user_id] = {
                'attribute': attribute,
                'start_time': datetime.now()
            }
            return True
        return False

    def complete_training(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Complete a training session and process results.
        
        Args:
            user_id: Discord ID of the user
            
        Returns:
            Training results if successful, None otherwise
        """
        if user_id not in self.training_sessions:
            return None
            
        session = self.training_sessions[user_id]
        results = self.training_system.complete_training(user_id)
        
        if results:
            # Update character stats
            character = self.character_system.get_character(user_id)
            if character:
                if results['success']:
                    # Apply attribute increase
                    setattr(character, session['attribute'], 
                           getattr(character, session['attribute']) + results['increase'])
                    # Award experience
                    character.gain_exp(results['exp_gained'])
                    self.character_system.update_character(user_id, character)
                
                # Process chakra cost
                self.currency_system.deduct_chakra(user_id, results['chakra_cost'])
        
        del self.training_sessions[user_id]
        return results

    def get_battle_status(self, battle_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a battle.
        
        Args:
            battle_id: ID of the battle
            
        Returns:
            Battle status if found, None otherwise
        """
        return self.battle_system.get_battle_status(battle_id)

    def get_training_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a training session.
        
        Args:
            user_id: Discord ID of the user
            
        Returns:
            Training status if found, None otherwise
        """
        if user_id not in self.training_sessions:
            return None
        return self.training_system.get_training_status(user_id)

    def use_jutsu(self, battle_id: str, user_id: str, jutsu: str) -> Optional[Dict[str, Any]]:
        """Use a jutsu in battle.
        
        Args:
            battle_id: ID of the battle
            user_id: Discord ID of the user
            jutsu: Name of the jutsu to use
            
        Returns:
            Jutsu results if successful, None otherwise
        """
        if battle_id not in self.active_battles:
            return None
            
        battle_data = self.active_battles[battle_id]
        if user_id not in [battle_data['attacker_id'], battle_data['defender_id']]:
            return None
            
        character = self.character_system.get_character(user_id)
        if not character or jutsu not in character.jutsu:
            return None
            
        return self.battle_system.use_jutsu(battle_id, user_id, jutsu) 