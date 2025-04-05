"""
Manages active battle simulations between players and AI opponents.
"""

import logging
import uuid
import random
import asyncio
import time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import Enum, auto

# Import dependencies from other core modules and utils
from .character_manager import CharacterManager
from ..utils.ollama_client import OllamaClient, OllamaError
from .battle_system import BattleSystem
from .character import Character

logger = logging.getLogger(__name__)

@dataclass
class BattleParticipant:
    """Represents a participant (player or AI) in a battle."""
    character_id: str  # Name/ID used to fetch data from CharacterManager
    character_data: Dict[str, Any] = field(repr=False) # Full data loaded from JSON
    current_hp: int
    max_hp: int
    current_chakra: int # Added current chakra
    max_chakra: int # Added max chakra
    status_effects: list[str] = field(default_factory=list)
    # Add other relevant stats like energy, buffs, debuffs as needed

@dataclass
class BattleState:
    """Holds the state of an ongoing battle instance."""
    # Non-default fields first
    interaction_context: Any # Store discord interaction or relevant context (e.g., channel id)
    player: BattleParticipant
    opponent: BattleParticipant # Could be AI or another player
    
    # Fields with default values
    battle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turn_number: int = 1
    is_ai_turn: bool = False
    last_action_description: str = "Battle started!"
    message_id: Optional[int] = None # Store message ID for potential updates

class BattleError(Enum):
    """Enumeration of possible battle-related errors."""
    PLAYER_NOT_FOUND = auto()
    OPPONENT_NOT_FOUND = auto()
    BATTLE_IN_PROGRESS = auto()
    INVALID_OPPONENT = auto()
    BATTLE_NOT_FOUND = auto()
    INVALID_ACTION = auto()
    SYSTEM_ERROR = auto()

class BattleManagerError(Exception):
    """Custom exception for Battle Manager errors."""
    pass

class BattleManager:
    """Handles the creation, state management, and progression of battles."""

    def __init__(self, character_manager: CharacterManager, ollama_client: Optional[OllamaClient], battle_system: BattleSystem):
        """
        Initializes the BattleManager.

        Args:
            character_manager: Instance of CharacterManager to load character data.
            ollama_client: Instance of OllamaClient to interact with the AI model.
            battle_system: Instance of BattleSystem to manage battle state.
        """
        self.character_manager = character_manager
        self.ollama_client = ollama_client
        self.battle_system = battle_system
        self.battle_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("BattleManager initialized.")

    async def get_battle_history(
        self,
        player_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get paginated and filtered battle history for a player.
        
        Args:
            player_id: The player's Discord ID
            page: Page number (1-based)
            page_size: Number of battles per page
            filters: Optional dictionary of filters (e.g., {"result": "victory", "enemy_type": "boss"})
            
        Returns:
            Dict containing:
            - battles: List of battle records for the current page
            - total_pages: Total number of pages
            - total_battles: Total number of battles matching filters
        """
        if player_id not in self.battle_history:
            return {"battles": [], "total_pages": 0, "total_battles": 0}
            
        # Apply filters if provided
        filtered_battles = self.battle_history[player_id]
        if filters:
            for key, value in filters.items():
                filtered_battles = [
                    battle for battle in filtered_battles
                    if battle.get(key) == value
                ]
                
        # Sort battles by timestamp (newest first)
        filtered_battles.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        # Calculate pagination
        total_battles = len(filtered_battles)
        total_pages = (total_battles + page_size - 1) // page_size
        page = max(1, min(page, total_pages))  # Ensure page is within bounds
        
        # Get battles for current page
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_battles = filtered_battles[start_idx:end_idx]
        
        return {
            "battles": page_battles,
            "total_pages": total_pages,
            "total_battles": total_battles,
            "current_page": page,
            "page_size": page_size
        }

    def _get_error_message(self, error: BattleError, **kwargs) -> Dict[str, Any]:
        """Get a user-friendly error message and code for the UI."""
        error_messages = {
            BattleError.PLAYER_NOT_FOUND: {
                "code": "PLAYER_NOT_FOUND",
                "message": "❌ Player not found in the game system."
            },
            BattleError.OPPONENT_NOT_FOUND: {
                "code": "OPPONENT_NOT_FOUND",
                "message": "❌ Opponent not found in the game system."
            },
            BattleError.BATTLE_IN_PROGRESS: {
                "code": "BATTLE_IN_PROGRESS",
                "message": "❌ You are already in a battle. Finish or flee from your current battle first."
            },
            BattleError.INVALID_OPPONENT: {
                "code": "INVALID_OPPONENT",
                "message": "❌ You cannot battle this opponent."
            },
            BattleError.BATTLE_NOT_FOUND: {
                "code": "BATTLE_NOT_FOUND",
                "message": "❌ Battle not found. It may have ended or been cancelled."
            },
            BattleError.INVALID_ACTION: {
                "code": "INVALID_ACTION",
                "message": "❌ Invalid action for the current battle state."
            },
            BattleError.SYSTEM_ERROR: {
                "code": "SYSTEM_ERROR",
                "message": "❌ An unexpected error occurred in the battle system."
            }
        }
        return error_messages.get(error, {
            "code": "UNKNOWN_ERROR",
            "message": "❌ An unknown error occurred."
        })

    async def start_battle(self, player_id: str, opponent_id: str) -> Dict[str, Any]:
        """Start a new battle between a player and an opponent (NPC or another player)."""
        try:
            # Check if player exists
            player_char = await self.character_manager.get_character(player_id)
            if not player_char:
                return self._get_error_message(BattleError.PLAYER_NOT_FOUND)
                
            # Check if opponent exists
            opponent_char = await self.character_manager.get_character(opponent_id)
            if not opponent_char:
                return self._get_error_message(BattleError.OPPONENT_NOT_FOUND)
                
            # Check if player is already in battle
            if player_id in self.battle_history:
                return self._get_error_message(BattleError.BATTLE_IN_PROGRESS)
                
            # Check if opponent is already in battle
            if opponent_id in self.battle_history:
                return self._get_error_message(BattleError.INVALID_OPPONENT)
                
            # Check level difference for PvP battles
            is_npc = hasattr(opponent_char, 'is_npc') and opponent_char.is_npc
            if not is_npc:
                level_diff = abs(player_char.level - opponent_char.level)
                if level_diff > 5:
                    return self._get_error_message(
                        BattleError.INVALID_OPPONENT,
                        message="❌ Level difference too high for PvP battle (max 5 levels)."
                    )
                    
            # Check for valid battle conditions
            if not self._validate_battle_conditions(player_char, opponent_char):
                return self._get_error_message(BattleError.INVALID_OPPONENT)
                
            # Start the battle
            battle_id = await self.battle_system.start_battle(player_id, opponent_id)
            if not battle_id:
                return self._get_error_message(BattleError.SYSTEM_ERROR)
                
            # Store battle data
            self.battle_history[player_id] = [{"battle_id": battle_id, "timestamp": time.time()}]
            
            return {
                "code": "SUCCESS",
                "message": "Battle started successfully!",
                "battle_id": battle_id,
                "battle_type": "pvp" if not is_npc else "pve",
                "level_diff": level_diff if not is_npc else 0
            }
        
        except Exception as e:
            logger.error(f"Error starting battle: {e}", exc_info=True)
            return self._get_error_message(BattleError.SYSTEM_ERROR)

    def _validate_battle_conditions(self, player: Character, opponent: Character) -> bool:
        """Validate battle conditions between player and opponent."""
        # Check if either participant is dead
        if player.hp <= 0 or opponent.hp <= 0:
            return False
            
        # Check if either participant is in a restricted state
        restricted_attr = 'restricted'
        if (hasattr(player, restricted_attr) and getattr(player, restricted_attr)) or \
           (hasattr(opponent, restricted_attr) and getattr(opponent, restricted_attr)):
            return False
            
        # Check for special battle restrictions
        special_battle_attr = 'in_special_battle'
        if (hasattr(player, special_battle_attr) and getattr(player, special_battle_attr)) or \
           (hasattr(opponent, special_battle_attr) and getattr(opponent, special_battle_attr)):
            return False
            
        # Check for clan war restrictions
        clan_war_attr = 'in_clan_war'
        if (hasattr(player, clan_war_attr) and getattr(player, clan_war_attr)) or \
           (hasattr(opponent, clan_war_attr) and getattr(opponent, clan_war_attr)):
            return False
            
        # Check for tournament restrictions
        tournament_attr = 'in_tournament'
        if (hasattr(player, tournament_attr) and getattr(player, tournament_attr)) or \
           (hasattr(opponent, tournament_attr) and getattr(opponent, tournament_attr)):
            return False
            
        return True

    def get_battle_state(self, battle_id: str) -> Optional[Any]: # Return type depends on BattleSystem.get_battle_state
        """Retrieve the current state of a battle from the BattleSystem."""
        return self.battle_system.get_battle_state(battle_id)

    async def process_player_action(self, player_id: str, action: Dict[str, Any], battle_id: Optional[str] = None) -> Optional[Any]:
        """Process a player's action in a specific battle."""
        logger.debug(f"Processing action for player {player_id}: {action}")

        # Find the battle if ID is not provided
        if not battle_id:
            battle_id = self.battle_system.get_battle_id_for_player(player_id)
            if not battle_id:
                logger.warning(f"Player {player_id} tried to act but is not in an active battle.")
                return self._get_error_message(BattleError.BATTLE_NOT_FOUND)

        # Delegate turn processing to BattleSystem
        try:
            # Use the battle_system method directly
            battle_state, message = await self.battle_system.process_action(
                battle_id,
                player_id,
                action['type'],
                **action
            )

            if not battle_state:
                return self._get_error_message(BattleError.BATTLE_NOT_FOUND, message=message)

            # Check if battle ended after player action
            if not battle_state.is_active:
                # Handle battle end cleanup if needed in manager (e.g., history)
                # self.end_battle(battle_id, message)
                return {"code": "BATTLE_ENDED", "message": message, "final_state": battle_state}
                
            # Determine if it's now AI's turn (if opponent is AI)
            # This logic might belong more in BattleSystem or need adjustment based on opponent type
            # opponent_is_ai = battle_state.opponent.get("is_ai", False) # Need a way to know if opponent is AI
            # if opponent_is_ai and battle_state.current_turn_player_id == battle_state.opponent.id:
            #     await self._process_ai_turn(battle_id)
            
            return {"code": "SUCCESS", "message": message, "battle_state": battle_state}

        except BattleManagerError as e:
            logger.warning(f"Battle action error: {e}")
            return self._get_error_message(BattleError.INVALID_ACTION, message=str(e))
        except Exception as e:
            logger.error(f"Error processing player action: {e}", exc_info=True)
            return self._get_error_message(BattleError.SYSTEM_ERROR)

    async def _process_ai_turn(self, battle_id: str):
        """Handle the AI's turn logic."""
        # --- MODIFIED: Fetch state from BattleSystem --- #
        battle_state = self.battle_system.get_battle_state(battle_id)
        if not battle_state or not battle_state.is_active:
            logger.warning(f"_process_ai_turn called for inactive/invalid battle {battle_id}")
            return None
        
        # Determine which participant is the AI (assuming opponent for now)
        if battle_state.current_turn_player_id == battle_state.attacker.id:
             logger.warning(f"_process_ai_turn called for battle {battle_id}, but it's not the opponent's turn.")
             return None # Or return current state? 
        ai_char = battle_state.defender # Assume AI is defender for this example
        player_char = battle_state.attacker
        ai_player_id = ai_char.id
        # --- END MODIFIED --- #

        logger.info(f"[Battle {battle_id}] Processing AI ({ai_player_id}) turn ({battle_state.turn_number})...")

        # --- 1. Prepare Data for Prompt (Refined Cost Check) --- 
        combat_behavior = getattr(ai_char, 'combat_behavior', {}) # Example access
        personality = getattr(ai_char, 'personality_philosophy', {}) # Example access
        signature_techniques = getattr(ai_char, 'jutsu', []) # Example access: Use learned jutsu list
        master_jutsu_data = self.battle_system.master_jutsu_data # Access via BattleSystem

        # --- Accurate Cost/Availability Check --- #
        available_actions = []
        # Basic Actions
        available_actions.append({"name": "Attack", "cost": 0, "type": "basic_attack"})
        # --- Defend Action - Leave commented until handled by BattleSystem --- #
        # available_actions.append({"name": "Defend", "cost": 0, "type": "defend"})
        # --- End Defend Action --- #
        available_actions.append({"name": "Pass", "cost": 0, "type": "pass"})

        # Signature Techniques
        for tech_name in signature_techniques:
             jutsu_info = master_jutsu_data.get(tech_name)
             if not jutsu_info:
                 logger.warning(f"[Battle {battle_id}] AI {ai_char.name} knows jutsu '{tech_name}' but it's not in master data. Skipping.")
                 continue
                 
             cost = jutsu_info.get('cost_amount', 0)
             cost_type = jutsu_info.get('cost_type', 'chakra') # Default to chakra
             current_resource = getattr(ai_char, cost_type, 0)

             if current_resource >= cost:
                  available_actions.append({"name": tech_name, "cost": cost, "type": "jutsu"})
             else:
                 logger.debug(f"[Battle {battle_id}] AI {ai_char.name} cannot afford {tech_name} (Needs {cost} {cost_type}, Has {current_resource}).")
        # --- END MODIFIED --- #
        
        action_list_str = ", ".join([f"{a['name']} (Cost: {a['cost']})" for a in available_actions])

        # --- 2. Construct Prompt (Using getattr for Character Attributes) --- 
        system_prompt_lines = [
            f"You are {ai_char.name}, a formidable shinobi.", # Use character name
            # --- MODIFIED: Use getattr for potential attributes --- #
            f"Your core traits: {getattr(ai_char, 'core_traits', ['Unknown'])}", 
            f"Your personality: {getattr(ai_char, 'personality_summary', 'Focused and calculating')}", 
            f"Your combat directives: {getattr(ai_char, 'combat_directives', 'Test opponent capabilities, conserve resources.')}", 
            # --- END MODIFIED --- #
            f"Your goal is to test your opponent, {player_char.name}, efficiently."
        ]
        system_prompt = " ".join(system_prompt_lines)

        battle_state_summary = (
            f"**Current Situation (Turn {battle_state.turn_number})**\n"
            f"- Your Status: HP {battle_state.defender_hp}/{ai_char.max_hp}, Chakra {ai_char.chakra}, Effects: {battle_state.defender_effects or 'None'}\n"	# Use state HP/Effects
            f"- Opponent ({player_char.name}) Status: HP {battle_state.attacker_hp}/{player_char.max_hp}, Chakra {player_char.chakra}, Effects: {battle_state.attacker_effects or 'None'}\n"	# Use state HP/Effects
            f"- Last Action Taken: {battle_state.battle_log[-1] if battle_state.battle_log else 'None'}\n"	# Use battle log
            f"**Your Available Actions:**\n[{action_list_str}]\n"
            f"**Task:** Based on your personality, directives, and the current battle state, choose the most logical action. Output ONLY the exact name."
        )
        prompt = battle_state_summary
        logger.debug(f"[Battle {battle_id}] Sending prompt to Ollama... Prompt length: {len(prompt)}")

        # --- 3. Call Ollama (Enhanced Logging) --- 
        ai_action_name = "Pass" # Default fallback
        chosen_action_details = next((a for a in available_actions if a['name'] == 'Pass'), None)
        try:
            if not self.ollama_client:
                raise OllamaError("Ollama client not available in BattleManager.")

            ollama_response = await self.ollama_client.generate(
                prompt=prompt,
                system_message=system_prompt,
                options={"temperature": 0.6} 
            )
            response_content = ollama_response.get('response', '').strip()
            
            matched_action = next((a for a in available_actions if a['name'].lower() == response_content.lower()), None)
            
            if matched_action:
                ai_action_name = matched_action['name']
                chosen_action_details = matched_action
                logger.info(f"[Battle {battle_id}] Received AI action from Ollama: '{ai_action_name}'")
            else:
                logger.warning(f"[Battle {battle_id}] Ollama response '{response_content}' invalid or not in available actions { [a['name'] for a in available_actions] }. Falling back to Pass.")
                ai_action_name = "Pass"
                chosen_action_details = next((a for a in available_actions if a['name'] == 'Pass'), None)

        except OllamaError as e:
            # --- MODIFIED: More specific logging --- #
            logger.error(f"[Battle {battle_id}] Ollama API error during AI turn generation: {e}. Falling back to Pass.")
            # --- END MODIFIED --- #
        except Exception as e:
             # --- MODIFIED: More specific logging --- #
             logger.error(f"[Battle {battle_id}] Unexpected error during Ollama call for AI turn: {e}. Falling back to Pass.", exc_info=True)
             # --- END MODIFIED --- #
        
        # --- 4. Format Action for BattleSystem --- #
        if not chosen_action_details:
             logger.error(f"[Battle {battle_id}] Could not determine AI action details, forcing Pass.")
             ai_action = {'type': 'pass'}
        else:
             ai_action = {'type': chosen_action_details['type']}
             if chosen_action_details['type'] == 'jutsu':
                  ai_action['jutsu_name'] = chosen_action_details['name']
        logger.debug(f"[Battle {battle_id}] Formatted AI action for BattleSystem: {ai_action}")
        # --- END MODIFIED --- #

        # --- 5. Delegate Action Processing to BattleSystem --- #
        try:
            result = await self.battle_system.process_turn(battle_id, ai_player_id, ai_action)
            logger.info(f"[Battle {battle_id}] AI turn processed by BattleSystem.")
            return result
        except Exception as e:
            logger.error(f"[Battle {battle_id}] Error calling BattleSystem.process_turn for AI action {ai_action}: {e}", exc_info=True)
            # If processing fails, maybe just return current state?
            return self.battle_system.get_battle_state(battle_id)
        # --- END MODIFIED --- #

    # Removed end_battle as BattleSystem should handle this
    # def end_battle(self, battle_id: str, reason: str = "Battle ended."):
    #     ... 