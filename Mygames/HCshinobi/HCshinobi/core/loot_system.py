"""
System for generating random loot drops in chat.
"""

import random
import time
from typing import Dict, Optional, Tuple
import logging
from datetime import datetime, timedelta

from .character import Character
from .character_system import CharacterSystem
from .currency_system import CurrencySystem

# Setup logger
logger = logging.getLogger(__name__)

class LootSystem:
    """Handles random loot drops in the chat."""
    
    # Rarity definitions with weights and multipliers
    RARITIES = {
        "Common": {"weight": 60, "multiplier": 1.0, "color": 0x969696},  # Gray
        "Uncommon": {"weight": 25, "multiplier": 1.5, "color": 0x1E88E5},  # Blue
        "Rare": {"weight": 10, "multiplier": 2.0, "color": 0x9C27B0},  # Purple
        "Epic": {"weight": 4, "multiplier": 3.0, "color": 0xFF9800},  # Orange
        "Legendary": {"weight": 1, "multiplier": 5.0, "color": 0xFFD700}  # Gold
    }
    
    # Base rewards by rank
    RANK_REWARDS = {
        "Academy Student": {"base": 50, "cooldown": 10800},  # 3 hours
        "Genin": {"base": 100, "cooldown": 7200},  # 2 hours
        "Chunin": {"base": 200, "cooldown": 3600},  # 1 hour
        "Jonin": {"base": 400, "cooldown": 1800},  # 30 minutes
        "ANBU": {"base": 600, "cooldown": 900},  # 15 minutes
        "Kage": {"base": 1000, "cooldown": 600}  # 10 minutes
    }
    
    def __init__(self, character_system: CharacterSystem, currency_system: CurrencySystem):
        """Initialize the LootSystem."""
        self.character_system = character_system
        self.currency_system = currency_system
        self.last_drop_time = {}  # Store last drop time by player ID
        self.logger = logging.getLogger(__name__)
        
    def can_drop_loot(self, player_id: str) -> Tuple[bool, Optional[str]]:
        """Check if a player can receive a loot drop.
        
        Args:
            player_id: The player's ID
            
        Returns:
            Tuple of (can_drop, message)
        """
        # Get player's character
        character = self.character_system.get_character(player_id)
        if not character:
            return False, "❌ You need a character to receive loot drops! Use /create to create one."
            
        # Check cooldown
        last_drop = self.last_drop_time.get(player_id)
        if last_drop:
            rank_info = self.RANK_REWARDS.get(character.rank, self.RANK_REWARDS["Genin"])
            cooldown = rank_info["cooldown"]
            time_left = (last_drop + timedelta(seconds=cooldown)) - datetime.now()
            
            if time_left.total_seconds() > 0:
                minutes = int(time_left.total_seconds() // 60)
                seconds = int(time_left.total_seconds() % 60)
                return False, f"⏰ You must wait {minutes}m {seconds}s before your next loot drop!"
                
        return True, None
        
    def generate_loot_drop(self, player_id: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Generate a loot drop for a player.
        
        Args:
            player_id: The player's ID
            
        Returns:
            Tuple of (success, loot_data, message)
        """
        # Check if player can receive loot
        can_drop, message = self.can_drop_loot(player_id)
        if not can_drop:
            return False, None, message
            
        # Get player's character
        character = self.character_system.get_character(player_id)
        if not character:
            return False, None, "❌ Character not found!"
            
        # Get rank info
        rank_info = self.RANK_REWARDS.get(character.rank, self.RANK_REWARDS["Genin"])
        base_reward = rank_info["base"]
        
        # Determine rarity
        total_weight = sum(rarity["weight"] for rarity in self.RARITIES.values())
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        selected_rarity = None
        for rarity, info in self.RARITIES.items():
            current_weight += info["weight"]
            if roll <= current_weight:
                selected_rarity = rarity
                break
                
        if not selected_rarity:
            selected_rarity = "Common"
            
        # Calculate final reward
        multiplier = self.RARITIES[selected_rarity]["multiplier"]
        final_reward = int(base_reward * multiplier)
        
        # Add some randomness (±10%)
        variation = random.uniform(-0.1, 0.1)
        final_reward = int(final_reward * (1 + variation))
        
        # Award the Ryō using add_balance_and_save with fallback
        if hasattr(self.currency_system, 'add_balance_and_save'):
            self.currency_system.add_balance_and_save(player_id, final_reward)
        else:
            # Fall back to old method or alternative method
            try:
                if hasattr(self.currency_system, 'add_ryo'):
                    self.currency_system.add_ryo(player_id, final_reward)
                else:
                    self.currency_system.add_to_balance(player_id, final_reward)
                
                # Save currency data manually if needed
                if hasattr(self.currency_system, 'save_currency_data'):
                    self.currency_system.save_currency_data()
            except Exception as e:
                logger.error(f"Error adding currency reward to player {player_id}: {e}")
        
        # Update last drop time
        self.last_drop_time[player_id] = datetime.now()
        
        # Create loot data
        loot_data = {
            "rarity": selected_rarity,
            "amount": final_reward,
            "color": self.RARITIES[selected_rarity]["color"],
            "rank": character.rank,
            "base_reward": base_reward,
            "multiplier": multiplier
        }
        
        return True, loot_data, None
        
    def get_next_drop_time(self, player_id: str) -> Optional[str]:
        """Get time until next possible loot drop.
        
        Args:
            player_id: The player's ID
            
        Returns:
            Time until next drop or None if no cooldown
        """
        last_drop = self.last_drop_time.get(player_id)
        if not last_drop:
            return None
            
        character = self.character_system.get_character(player_id)
        if not character:
            return None
            
        rank_info = self.RANK_REWARDS.get(character.rank, self.RANK_REWARDS["Genin"])
        cooldown = rank_info["cooldown"]
        
        time_left = (last_drop + timedelta(seconds=cooldown)) - datetime.now()
        if time_left.total_seconds() <= 0:
            return None
            
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)
        return f"{minutes}m {seconds}s" 