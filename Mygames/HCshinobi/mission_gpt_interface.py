import asyncio
import logging
from typing import Optional, Dict, List, Any, Union

# Import your existing MissionSystem, OpenAIClient, and your Character model.
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.character import Character
from HCshinobi.utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

class MissionGPTInterface:
    """
    Interface combining the MissionSystem and OpenAIClient.
    Decides if user input is a mission command or a general GPT question, then routes accordingly.
    """

    def __init__(self, mission_system: MissionSystem, openai_client: OpenAIClient):
        """
        Initialize the interface with mission system and OpenAI client.
        
        Args:
            mission_system: The initialized MissionSystem
            openai_client: The initialized OpenAIClient
        """
        self.mission_system = mission_system
        self.openai_client = openai_client
        self.model = "gpt-4o-mini"  # Default to 4o-mini as requested

    async def handle_user_input(self, user_id: Union[int, str], message: str) -> str:
        """
        Main entry point. Given user_id and a text command/message:
          - If it's recognized as a mission command, route to the mission system.
          - Otherwise, pass it to GPT and return that response.
          
        Args:
            user_id: User ID (string or int)
            message: User's message/command
            
        Returns:
            A string with the relevant response to send back to the user.
        """
        # Normalize the message and user_id
        text = message.strip().lower()
        user_id_str = str(user_id)

        # Check for mission keywords to route to the mission system
        if text.startswith("accept mission"):
            # e.g. "accept mission tutorial_fetch"
            parts = text.split()
            if len(parts) >= 3:
                mission_id = parts[2]  # Extract mission ID
            else:
                return "Please specify which mission to accept, e.g. `accept mission tutorial_fetch`."

            # Get the character
            character = await self.get_character(user_id)
            if not character:
                return "Could not find or create your character. Contact an admin."

            # Attempt to assign the mission
            success, msg = await self.mission_system.assign_mission(character, mission_id)
            return msg

        elif text == "complete mission":
            # The user wants to complete their active mission
            character = await self.get_character(user_id)
            if not character:
                return "Could not find your character data."

            result = await self.mission_system.complete_mission(character)
            if not result:
                return "You don't have an active mission or an error occurred."
            if "error" in result:
                return result["error"]

            # Build a user-friendly completion message
            mission_name = result.get("mission_name", "Unknown")
            reward_text = ", ".join(result.get("rewards_granted", [])) if result.get("rewards_granted") else "No rewards"
            progression_text = "\n".join(result.get("progression_notes", [])) if result.get("progression_notes") else ""
            response_lines = [
                f"Mission **{mission_name}** completed!",
                f"You received: **{reward_text}**",
            ]
            if progression_text:
                response_lines.append(progression_text)
            return "\n".join(response_lines)

        elif text == "my mission":
            # Check what the user's current active mission is
            active = self.mission_system.get_active_mission(user_id)
            if not active:
                return "You don't have an active mission. Try `accept mission <id>`."
            return (f"Your current mission is **{active.get('name')}**: {active.get('description')} "
                    f"(Rank {active.get('rank')}).")
        
        elif text == "roll":
            # Process a d20 challenge roll for the current mission
            result = self.mission_system.process_d20_challenge(user_id)
            if not result.get("success", False):
                return result.get("message", "Error processing your roll.")
            
            # Format a nice response with roll results
            roll_value = result.get("roll", 0)
            difficulty = result.get("difficulty", 0)
            success = roll_value >= difficulty
            
            response_lines = [
                f"**You rolled: {roll_value}** (Difficulty: {difficulty})",
                f"**{'SUCCESS' if success else 'FAILURE'}!**",
                result.get("description", "")
            ]
            
            # If the mission was completed, add that info
            if "mission_completion" in result:
                completion = result["mission_completion"]
                response_lines.append(f"\n**Mission {completion.get('mission_name', 'Unknown')} completed!**")
                response_lines.append(f"Rewards: {', '.join(completion.get('rewards_granted', ['None']))}")
            
            return "\n".join(response_lines)

        elif text == "available missions":
            # List missions the user can accept
            character = await self.get_character(user_id)
            if not character:
                return "Could not find your character data."
            available = self.mission_system.get_available_missions(character)
            if not available:
                return "No missions are available or you already have one active."
            response_lines = ["Available Missions:"]
            for m in available:
                response_lines.append(f"- **{m['id']}** ({m['rank']} Rank): {m.get('name')} - {m.get('description')}")
            return "\n".join(response_lines)

        else:
            # If we get here, treat the input as a GPT question
            logger.info(f"Routing to GPT (model: {self.model}): {message}")
            
            # Pass the request to the OpenAI client with our specified model
            system_prompt = "You are a helpful ninja assistant in the world of Naruto."
            
            if self.openai_client.using_api:
                # Using process_prompt directly with the model parameter
                gpt_response = await self.openai_client.process_prompt(
                    prompt=message,
                    model=self.model,  # Use the model we've set (4o-mini by default)
                )
            else:
                # For browser automation, construct a URL that specifies the model if possible
                model_url = None
                if "chat.openai.com" in self.openai_client.target_gpt_url:
                    base_url = self.openai_client.target_gpt_url.split("?")[0]
                    model_url = f"{base_url}?model={self.model}"
                
                gpt_response = await self.openai_client.process_prompt(
                    prompt=message,
                    model_url=model_url
                )
                
            return gpt_response or "Sorry, I couldn't generate a response."

    async def get_character(self, user_id: Union[int, str]) -> Optional[Character]:
        """
        Retrieve or create the Character for a given user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Character object or None if it couldn't be retrieved/created
        """
        user_id_str = str(user_id)
        
        # Try to get existing character
        character = self.mission_system.character_system.get_character(user_id_str)
        
        # If no character exists, try to create one
        if character is None:
            try:
                character = await self.mission_system.character_system.create_character(user_id_str)
                logger.info(f"Created new character for user {user_id_str}")
            except Exception as e:
                logger.error(f"Failed to create character for user {user_id_str}: {e}")
                return None
                
        return character

    def set_model(self, model: str) -> None:
        """
        Change the model used for GPT responses.
        
        Args:
            model: The model identifier (e.g., "gpt-4o-mini", "gpt-4o", etc.)
        """
        self.model = model
        logger.info(f"Model changed to: {model}")


async def main():
    """
    Example startup sequence.
    """
    # Initialize your character system, currency system, progression engine, etc.
    # For demonstration purposes, we'd set these up
    
    # Example (replace with your actual objects):
    from HCshinobi.core.character_system import CharacterSystem
    from HCshinobi.core.currency_system import CurrencySystem
    from HCshinobi.core.progression_engine import ShinobiProgressionEngine
    
    character_system = CharacterSystem("data/characters", "data/character_types")
    currency_system = CurrencySystem("data/currency.json")
    progression_engine = ShinobiProgressionEngine(character_system)
    
    # Create the MissionSystem
    data_dir = "data"
    mission_system = MissionSystem(
        character_system=character_system,
        data_dir=data_dir,
        currency_system=currency_system,
        progression_engine=progression_engine
    )
    # Load missions
    await mission_system.ready_hook()
    
    # Create the OpenAIClient
    # For API key approach:
    # openai_client = OpenAIClient(api_key="your_api_key_here")
    
    # For browser automation approach:
    openai_client = OpenAIClient(
        profile_dir="path/to/chrome/profile",
        cookie_dir="path/to/cookies",
        target_gpt_url="https://chat.openai.com/?model=gpt-4o-mini",
        headless=False
    )
    
    # Boot the client
    openai_client.boot()
    
    # Create our unified interface
    mission_gpt = MissionGPTInterface(mission_system, openai_client)
    
    # Example usage
    user_id = 12345678
    
    # a) Check available missions
    response = await mission_gpt.handle_user_input(user_id, "available missions")
    print(response)
    
    # b) Accept a mission
    response = await mission_gpt.handle_user_input(user_id, "accept mission tutorial_fetch")
    print(response)
    
    # c) Ask GPT a question
    response = await mission_gpt.handle_user_input(user_id, "What's the best way to become a strong ninja?")
    print(response)
    
    # d) Roll for a d20 challenge
    response = await mission_gpt.handle_user_input(user_id, "roll")
    print(response)
    
    # e) Complete the mission
    response = await mission_gpt.handle_user_input(user_id, "complete mission")
    print(response)
    
    # Shutdown
    await openai_client.shutdown()


# Run the async main function if executed directly
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    asyncio.run(main()) 