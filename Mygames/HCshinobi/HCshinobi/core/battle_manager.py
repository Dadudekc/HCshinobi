"""
Manages active battle simulations between players and AI opponents.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

# Import dependencies from other core modules and utils
from .character_manager import CharacterManager
from ..utils.ollama_client import OllamaClient, OllamaError

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

class BattleManagerError(Exception):
    """Custom exception for Battle Manager errors."""
    pass

class BattleManager:
    """Handles the creation, state management, and progression of battles."""

    def __init__(self, character_manager: CharacterManager, ollama_client: OllamaClient):
        """
        Initializes the BattleManager.

        Args:
            character_manager: Instance of CharacterManager to load character data.
            ollama_client: Instance of OllamaClient to interact with the AI model.
        """
        self.character_manager = character_manager
        self.ollama_client = ollama_client
        self.active_battles: Dict[str, BattleState] = {} # Keyed by battle_id
        logger.info("BattleManager initialized.")

    def _create_participant(self, character_id: str) -> Optional[BattleParticipant]:
        """Loads character data and creates a BattleParticipant."""
        char_data = self.character_manager.get_character(character_id)
        if not char_data:
            logger.error(f"Failed to create participant: Character '{character_id}' not found.")
            return None

        # --- Read HP & Chakra from base_stats --- 
        # Default to 100 if base_stats or values are missing
        stats = char_data.get('base_stats', {})
        max_hp = stats.get('hp', 100) 
        current_hp = max_hp
        max_chakra = stats.get('chakra_pool', 100) # Read chakra pool
        current_chakra = max_chakra # Initialize current chakra
        # --- End HP & Chakra Reading --- 

        return BattleParticipant(
            character_id=character_id,
            character_data=char_data,
            current_hp=current_hp,
            max_hp=max_hp,
            current_chakra=current_chakra, # Pass chakra values
            max_chakra=max_chakra
        )

    async def start_battle(
        self,
        interaction_context: Any,
        player_character_id: str,
        opponent_character_id: str
    ) -> BattleState:
        """
        Starts a new battle instance.

        Args:
            interaction_context: Discord interaction or context where the battle was initiated.
            player_character_id: The ID/name of the player's character.
            opponent_character_id: The ID/name of the opponent's character (e.g., "Solomon").

        Returns:
            The initial BattleState object.

        Raises:
            BattleManagerError: If characters cannot be loaded.
        """
        logger.info(f"Attempting to start battle: Player '{player_character_id}' vs Opponent '{opponent_character_id}'")
        
        player = self._create_participant(player_character_id)
        opponent = self._create_participant(opponent_character_id)

        if not player or not opponent:
            raise BattleManagerError("Failed to start battle: Could not load character data for one or both participants.")

        battle = BattleState(
            interaction_context=interaction_context,
            player=player,
            opponent=opponent
        )
        
        self.active_battles[battle.battle_id] = battle
        logger.info(f"Battle {battle.battle_id} started successfully.")
        return battle

    def get_battle_state(self, battle_id: str) -> Optional[BattleState]:
        """Retrieves the current state of an active battle."""
        return self.active_battles.get(battle_id)

    async def process_player_action(self, battle_id: str, action: str, details: Optional[Dict] = None) -> BattleState:
        """
        Processes an action taken by the player.
        (Placeholder - actual game logic to be implemented here)
        This might involve updating HP, applying effects, etc.
        After processing, it should trigger the AI's turn.

        Args:
            battle_id: The ID of the battle.
            action: The action performed by the player (e.g., 'attack', 'defend', 'use_skill').
            details: Additional details about the action (e.g., skill name, target).

        Returns:
            The updated BattleState after the player's action and potentially the AI's response.
            
        Raises:
            BattleManagerError: If the battle ID is invalid or action processing fails.
        """
        battle = self.get_battle_state(battle_id)
        if not battle:
            raise BattleManagerError(f"Invalid battle ID: {battle_id}")
        if battle.is_ai_turn:
             raise BattleManagerError("Cannot process player action: It's currently the AI's turn.")

        logger.info(f"[Battle {battle_id}] Processing player action: {action} {details or ''}")

        # --- Placeholder Action Logic ---
        # TODO: Implement actual logic based on 'action' and 'details'
        # Example: Reduce opponent HP on 'attack'
        if action == 'attack':
            damage = 10 # Placeholder
            battle.opponent.current_hp -= damage
            battle.last_action_description = f"{battle.player.character_id} attacked {battle.opponent.character_id} for {damage} damage!"
            logger.debug(f"[Battle {battle_id}] Opponent HP reduced to {battle.opponent.current_hp}")
        elif action == 'pass':
             battle.last_action_description = f"{battle.player.character_id} passed their turn."
        else:
             battle.last_action_description = f"{battle.player.character_id} performed action: {action}. (Logic TBD)"
        # --- End Placeholder --- 
        
        # Check for battle end condition (e.g., opponent defeated - though maybe not for Solomon)
        if battle.opponent.current_hp <= 0:
             # Handle opponent defeat (might differ for winless scenario)
             logger.info(f"[Battle {battle_id}] Opponent defeated.")
             # return self.end_battle(battle_id, f"{battle.player.character_id} won!") # Example end

        # It's now the AI's turn
        battle.is_ai_turn = True
        battle.turn_number += 1 # Increment turn after player AND AI go, or just after player? Decide later.

        # Trigger AI turn processing
        try:
            return await self._process_ai_turn(battle_id)
        except Exception as e:
            logger.error(f"[Battle {battle_id}] Error during subsequent AI turn processing: {e}", exc_info=True)
            # Decide how to handle: raise, return current state, etc.
            # For now, return state after player action but before AI potentially failed
            return battle 

    async def _process_ai_turn(self, battle_id: str) -> BattleState:
        """
        Generates and processes the AI opponent's action using Ollama.
        Includes improved prompt engineering and basic action handling.

        Args:
            battle_id: The ID of the battle.

        Returns:
            The updated BattleState after the AI's action.
            
        Raises:
            BattleManagerError: If the battle ID is invalid or AI processing fails.
        """
        battle = self.get_battle_state(battle_id)
        if not battle:
            raise BattleManagerError(f"Invalid battle ID: {battle_id}")
        if not battle.is_ai_turn:
            raise BattleManagerError("Cannot process AI turn: It's not the AI's turn.")

        ai_char = battle.opponent
        player_char = battle.player
        logger.info(f"[Battle {battle_id}] Processing AI ({ai_char.character_id}) turn ({battle.turn_number})...")

        # --- 1. Prepare Data for Prompt --- 
        ai_data = ai_char.character_data
        combat_behavior = ai_data.get('combat_behavior', {})
        personality = ai_data.get('personality_philosophy', {})
        signature_techniques = ai_data.get('signature_techniques', [])

        # --- Placeholder Chakra Costs --- 
        # TODO: Define these properly, maybe in technique data itself
        TECHNIQUE_COSTS = {
            "Amaterasu": 150, 
            "Kamui Phase": 100, 
            "Eclipse Fang Severance": 200,
            "Attack": 0,
            "Defend": 0,
            "Pass": 0
        }
        # --- End Placeholder Costs --- 

        # --- Determine Available Actions --- 
        available_actions = []
        # Basic Taijutsu/Actions
        available_actions.append({"name": "Attack", "cost": TECHNIQUE_COSTS["Attack"]})
        available_actions.append({"name": "Defend", "cost": TECHNIQUE_COSTS["Defend"]})
        # Signature Techniques (check basic chakra cost)
        for tech in signature_techniques:
             tech_name = tech.get('name')
             cost = TECHNIQUE_COSTS.get(tech_name, 9999) # Default high cost if not defined
             if tech_name and ai_char.current_chakra >= cost:
                  available_actions.append({"name": tech_name, "cost": cost})
             # Simple check for specific key abilities mentioned previously
             elif "Amaterasu" in tech_name and ai_char.current_chakra >= TECHNIQUE_COSTS["Amaterasu"]:
                 available_actions.append({"name": "Amaterasu", "cost": TECHNIQUE_COSTS["Amaterasu"]})
             elif "Kamui" in tech_name and ai_char.current_chakra >= TECHNIQUE_COSTS["Kamui Phase"]:
                 available_actions.append({"name": "Kamui Phase", "cost": TECHNIQUE_COSTS["Kamui Phase"]})

        # Always allow passing
        available_actions.append({"name": "Pass", "cost": TECHNIQUE_COSTS["Pass"]})
        
        action_list_str = ", ".join([f"{a['name']} (Cost: {a['cost']})" for a in available_actions])
        # --- End Available Actions --- 

        # --- 2. Construct Prompt --- 
        system_prompt_lines = [
            f"You are {ai_char.character_id}, {ai_data.get('titles', ['a formidable shinobi'])[0]}.",
            "Your core traits: " + ", ".join(ai_data.get('core_traits', [])),
            f"Your personality: Reserved ({personality.get('reserved_demeanor', '')}), Controlled Escalation ({personality.get('controlled_escalation', '')}), Disciplined ({personality.get('willpower_discipline', '')}).",
            f"Your combat directives: Precision over flash ({combat_behavior.get('directives',{}).get('precision_over_flash')}), Gradual escalation ({combat_behavior.get('directives',{}).get('gradual_escalation')}), Calculated resource use ({combat_behavior.get('directives',{}).get('calculated_resource_use')}).",
            f"Your goal is to test your opponent, {player_char.character_id}, efficiently and methodically, not necessarily to defeat them instantly. Escalate your power only as needed."
        ]
        system_prompt = " ".join(system_prompt_lines)

        battle_state_summary = (
            f"**Current Situation (Turn {battle.turn_number})**\n"
            f"- Your Status: HP {ai_char.current_hp}/{ai_char.max_hp}, Chakra {ai_char.current_chakra}/{ai_char.max_chakra}, Effects: {ai_char.status_effects or 'None'}\n"
            f"- Opponent ({player_char.character_id}) Status: HP {player_char.current_hp}/{player_char.max_hp}, Chakra {player_char.current_chakra}/{player_char.max_chakra}, Effects: {player_char.status_effects or 'None'}\n"
            f"- Last Action Taken: {battle.last_action_description}\n"
            f"**Your Available Actions:**\n[{action_list_str}]\n"
            f"**Task:** Based on your personality, directives, and the current battle state, choose the most logical and tactical action from the list above. Consider chakra cost and your goal of testing the opponent. **Output ONLY the exact name of the chosen action.**"
        )
        prompt = battle_state_summary
        logger.debug(f"[Battle {battle_id}] Sending prompt to Ollama:\nSystem: {system_prompt}\nPrompt: {prompt}")
        # --- End Prompt Construction --- 

        # --- 3. Call Ollama --- 
        ai_action_text = "Pass" # Default fallback
        try:
            # Reduce temperature slightly for more predictable choices
            ollama_response = await self.ollama_client.generate(
                prompt=prompt,
                system_message=system_prompt,
                options={"temperature": 0.6} 
            )
            response_content = ollama_response.get('response', '').strip()
            # Basic validation: Check if response is one of the available action names
            chosen_action = next((a for a in available_actions if a['name'].lower() == response_content.lower()), None)
            if chosen_action:
                ai_action_text = chosen_action['name'] # Use the exact name with correct casing
                logger.info(f"[Battle {battle_id}] Received AI action from Ollama: '{ai_action_text}'")
            else:
                logger.warning(f"[Battle {battle_id}] Ollama response '{response_content}' not in available actions. Falling back to Pass.")
                ai_action_text = "Pass"
                battle.last_action_description = f"AI ({ai_char.character_id}) considered its options and passed." 

        except OllamaError as e:
            logger.error(f"[Battle {battle_id}] Ollama API error during AI turn: {e}")
            battle.last_action_description = f"AI ({ai_char.character_id}) encountered an error and passed." 
        except Exception as e:
             logger.error(f"[Battle {battle_id}] Unexpected error during AI turn Ollama call: {e}", exc_info=True)
             battle.last_action_description = f"AI ({ai_char.character_id}) encountered an unexpected error and passed."
        # --- End Ollama Call --- 

        # --- 4. Parse and Apply AI Action --- 
        # TODO: Refine damage calculations, implement chakra costs accurately, handle more skills
        action_cost = TECHNIQUE_COSTS.get(ai_action_text, 0)
        
        # Check if AI can afford the action (should be guaranteed by available action list, but double-check)
        if ai_char.current_chakra < action_cost:
             logger.warning(f"[Battle {battle_id}] AI cannot afford {ai_action_text} (Cost: {action_cost}, Current: {ai_char.current_chakra}). Forcing Pass.")
             ai_action_text = "Pass"
             action_cost = 0
             battle.last_action_description = f"AI ({ai_char.character_id}) lacked the chakra for their intended action and passed."

        # Deduct cost first
        ai_char.current_chakra -= action_cost
        logger.debug(f"[Battle {battle_id}] AI Chakra updated: {ai_char.current_chakra}/{ai_char.max_chakra} (-{action_cost})")

        # Apply action effects
        if ai_action_text.lower() == "attack":
            damage = 30 # Placeholder - TODO: Calculate based on stats
            player_char.current_hp -= damage
            battle.last_action_description = f"AI ({ai_char.character_id}) attacked {player_char.character_id} with precise strikes for {damage} damage!"
            logger.debug(f"[Battle {battle_id}] Player HP reduced to {player_char.current_hp}")
        elif ai_action_text.lower() == "amaterasu":
            damage = 50 # Placeholder
            player_char.current_hp -= damage
            # Add burning status? TODO: Implement status effect system
            # if "Burning" not in player_char.status_effects:
            #      player_char.status_effects.append("Burning")
            battle.last_action_description = f"AI ({ai_char.character_id}) unleashed Amaterasu upon {player_char.character_id} for {damage} damage! The black flames burn fiercely."
            logger.debug(f"[Battle {battle_id}] Player HP reduced to {player_char.current_hp}")
        elif ai_action_text.lower() == "kamui phase":
            # Apply phasing status to AI
            if "Phasing" not in ai_char.status_effects:
                 ai_char.status_effects.append("Phasing") # TODO: Add duration/removal logic
            battle.last_action_description = f"AI ({ai_char.character_id}) used Kamui, becoming temporarily intangible."
            logger.debug(f"[Battle {battle_id}] AI status effects: {ai_char.status_effects}")
        elif ai_action_text.lower() == "defend":
             # TODO: Implement defense logic (e.g., temp damage reduction status)
             battle.last_action_description = f"AI ({ai_char.character_id}) took a defensive stance."
        elif ai_action_text.lower() == "pass":
            # Description was likely set during fallback, but set default if needed
            if not battle.last_action_description.endswith("passed."):
                battle.last_action_description = f"AI ({ai_char.character_id}) observed and passed its turn."
        else:
            # Handle other skills or fallback if parsing somehow failed earlier
            battle.last_action_description = f"AI ({ai_char.character_id}) performed: {ai_action_text}. (Effect Logic TBD)"
            logger.warning(f"[Battle {battle_id}] Unhandled AI action: {ai_action_text}")
        # --- End Action Application ---

        # --- 5. Post-Turn Checks & Cleanup --- 
        # Example: Remove phasing after one turn?
        if "Phasing" in ai_char.status_effects:
             # TODO: Implement proper duration/trigger for removal
             # ai_char.status_effects.remove("Phasing") 
             pass # For now, let it persist until proper logic added

        # Check for battle end condition (e.g., player defeated)
        if player_char.current_hp <= 0:
             logger.info(f"[Battle {battle_id}] Player defeated.")
             # Handle player defeat (e.g., end battle, maybe different message for Solomon)
             return self.end_battle(battle_id, f"{player_char.character_id} was overwhelmed by {ai_char.character_id}!") # Example end
        
        # It's now the player's turn again
        battle.is_ai_turn = False

        logger.debug(f"[Battle {battle_id}] AI turn complete. Player HP: {player_char.current_hp}, AI HP: {ai_char.current_hp}, AI Chakra: {ai_char.current_chakra}")
        return battle

    def end_battle(self, battle_id: str, reason: str = "Battle ended.") -> Optional[BattleState]:
        """
        Removes an active battle from the manager.

        Args:
            battle_id: The ID of the battle to end.
            reason: A description of why the battle ended.

        Returns:
            The final battle state object if found, otherwise None.
        """
        logger.info(f"Ending battle {battle_id}. Reason: {reason}")
        final_state = self.active_battles.pop(battle_id, None)
        if final_state:
             final_state.last_action_description = reason
        else:
             logger.warning(f"Attempted to end non-existent battle ID: {battle_id}")
        return final_state 