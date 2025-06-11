"""
NPC prompt generator module for the Naruto MMO Discord game.
Generates AI-based NPC prompts for background stories, quests, combat, and dialogue.
"""
import os
import json
import random
from typing import Dict, List, Optional, Any

# Configuration for different AI providers
AI_PROVIDERS = {
    "openai": {
        "models": ["gpt-4", "gpt-4o", "gpt-3.5-turbo"],
        "default_model": "gpt-4o",
        "max_tokens": 1024,
        "temperature": 0.7
    },
    "local": {
        "models": ["llama-3-8b", "mistral-7b", "mixtral-8x7b"],
        "default_model": "llama-3-8b",
        "max_tokens": 512,
        "temperature": 0.8
    }
}

class NPCPromptGenerator:
    """
    Generates prompts for AI models to create NPC-related content.
    Supports different AI providers: OpenAI API or local models.
    """
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Initialize the NPC prompt generator.
        
        Args:
            provider: AI provider to use ("openai" or "local")
            model: Specific model to use (optional, defaults to provider's default model)
        """
        if provider not in AI_PROVIDERS:
            raise ValueError(f"Unsupported AI provider: {provider}. Must be one of {list(AI_PROVIDERS.keys())}")
            
        self.provider = provider
        self.config = AI_PROVIDERS[provider]
        self.model = model or self.config["default_model"]
        
        if self.model not in self.config["models"]:
            raise ValueError(f"Unsupported model: {self.model} for provider {provider}. Must be one of {self.config['models']}")
    
    def format_prompt_data(self, npc_data: Dict[str, Any], prompt_type: str) -> Dict[str, Any]:
        """
        Format NPC data into a structured prompt for AI generation.
        
        Args:
            npc_data: Dictionary containing NPC information
            prompt_type: Type of prompt to generate ("background", "quest", "combat", "dialogue")
            
        Returns:
            Dict[str, Any]: Formatted prompt data
        """
        valid_prompt_types = ["background", "quest", "combat", "dialogue"]
        if prompt_type not in valid_prompt_types:
            raise ValueError(f"Unsupported prompt type: {prompt_type}. Must be one of {valid_prompt_types}")
        
        # Base prompt structure
        prompt = {
            "messages": [
                {"role": "system", "content": self._get_system_prompt(prompt_type)}
            ],
            "model": self.model,
            "temperature": self.config["temperature"],
            "max_tokens": self.config["max_tokens"]
        }
        
        # Add NPC data as user message
        npc_context = self._format_npc_context(npc_data, prompt_type)
        prompt["messages"].append({"role": "user", "content": npc_context})
        
        return prompt
    
    def _get_system_prompt(self, prompt_type: str) -> str:
        """
        Get the system prompt for the specified prompt type.
        
        Args:
            prompt_type: Type of prompt to generate
            
        Returns:
            str: System prompt
        """
        system_prompts = {
            "background": "You are an expert NPC creator for a Naruto-themed MMO game. Generate a detailed background story for an NPC who was once a player character. Include their personality traits, relationships, motivations, and how they died. Keep the tone consistent with the Naruto universe.",
            
            "quest": "You are a quest designer for a Naruto-themed MMO game. Create an engaging quest given by an NPC who was once a player character. Include quest name, description, objectives, difficulty level, and rewards. Make the quest thematically appropriate for the NPC's clan and backstory.",
            
            "combat": "You are a combat designer for a Naruto-themed MMO game. Design a combat encounter with an NPC who was once a player character. Describe their fighting style, special abilities, and tactics based on their clan. Include a description of the location and possible rewards.",
            
            "dialogue": "You are a dialogue writer for a Naruto-themed MMO game. Write a dialogue interaction with an NPC who was once a player character. Make their speech patterns and content reflect their clan, personality, and backstory. The dialogue should reveal something about their character or history."
        }
        
        return system_prompts.get(prompt_type, "Generate content for a Naruto-themed MMO game.")
    
    def _format_npc_context(self, npc_data: Dict[str, Any], prompt_type: str) -> str:
        """
        Format NPC data into a context string for the AI prompt.
        
        Args:
            npc_data: Dictionary containing NPC information
            prompt_type: Type of prompt to generate
            
        Returns:
            str: Formatted context string
        """
        # Extract required fields with defaults
        name = npc_data.get("name", "Unknown Shinobi")
        clan = npc_data.get("clan", "Unknown Clan")
        clan_lore = npc_data.get("clan_lore", "A mysterious clan with unknown abilities.")
        personality = npc_data.get("personality", "Mysterious")
        death_story = npc_data.get("death_story", "Died in battle under unknown circumstances.")
        level = npc_data.get("level", 1)
        abilities = npc_data.get("abilities", [])
        location = npc_data.get("location", "Village")
        
        # Format abilities list
        abilities_text = "None known"
        if abilities:
            abilities_text = "\n- " + "\n- ".join(abilities)
        
        # Construct the context based on prompt type
        if prompt_type == "background":
            return f"""Create a background story for the following NPC:

Name: {name}
Clan: {clan}
Clan Lore: {clan_lore}
Personality: {personality}
Level: {level}
Known Abilities: {abilities_text}
Current Location: {location}
Death: {death_story}

Write a detailed background story in 2-3 paragraphs that explains who this character was, their motivations, and how they died. Your response should be from an omniscient narrator perspective."""

        elif prompt_type == "quest":
            return f"""Create a quest given by the following NPC:

Name: {name}
Clan: {clan}
Clan Lore: {clan_lore}
Personality: {personality}
Level: {level}
Known Abilities: {abilities_text}
Current Location: {location}
Background: {death_story}

Design a quest that this NPC would give to players. Include:
1. Quest Name
2. Quest Description (what the NPC tells the player)
3. Quest Objectives (3-5 steps)
4. Difficulty Level
5. Rewards

Make sure the quest relates to the NPC's clan abilities or backstory."""

        elif prompt_type == "combat":
            return f"""Create a combat encounter with the following NPC:

Name: {name}
Clan: {clan}
Clan Lore: {clan_lore}
Personality: {personality}
Level: {level}
Known Abilities: {abilities_text}
Current Location: {location}
Background: {death_story}

Design a combat encounter against this NPC. Include:
1. Battle Introduction (how the encounter starts)
2. Combat Style and Tactics
3. Special Moves and Abilities
4. Location Description
5. Difficulty Level
6. Rewards for Defeating"""

        elif prompt_type == "dialogue":
            return f"""Create a dialogue with the following NPC:

Name: {name}
Clan: {clan}
Clan Lore: {clan_lore}
Personality: {personality}
Level: {level}
Known Abilities: {abilities_text}
Current Location: {location}
Background: {death_story}

Write a dialogue interaction between this NPC and a player character. Make the NPC's speech patterns and content reflect their clan, personality, and backstory. Include at least 3-5 exchanges that reveal something about the NPC's character or history."""

        else:
            return f"Generate content for NPC named {name} from the {clan} clan. They are described as {personality} and {death_story}"
    
    def generate_prompt(self, npc_data: Dict[str, Any], prompt_type: str) -> Dict[str, Any]:
        """
        Generate a complete prompt ready to be sent to an AI model.
        
        Args:
            npc_data: Dictionary containing NPC information
            prompt_type: Type of prompt to generate
            
        Returns:
            Dict[str, Any]: Complete prompt data
            
        Note: This is a stub implementation. In a production environment, this would
        connect to the OpenAI API or local models to generate the actual content.
        """
        # Format the prompt data
        prompt = self.format_prompt_data(npc_data, prompt_type)
        
        # Add metadata for tracking and reference
        prompt["metadata"] = {
            "npc_id": npc_data.get("npc_id", "unknown"),
            "npc_name": npc_data.get("name", "Unknown"),
            "prompt_type": prompt_type,
            "provider": self.provider,
            "model": self.model
        }
        
        return prompt
    
    def mock_ai_response(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock AI response for testing without an actual AI provider.
        
        Args:
            prompt: Complete prompt data
            
        Returns:
            Dict[str, Any]: Mock AI response
        """
        prompt_type = prompt["metadata"]["prompt_type"]
        npc_name = prompt["metadata"]["npc_name"]
        
        # Generate mock responses based on prompt type
        mock_responses = {
            "background": [
                f"{npc_name} was born into a modest family within the clan, showing exceptional talent from an early age. Their unique ability to master techniques quickly caught the attention of village elders, leading to specialized training. Unfortunately, their promising career was cut short during a high-risk mission, where they sacrificed themselves to save their teammates.",
                
                f"Raised in the outskirts of their clan's territory, {npc_name} grew up with a strong sense of independence. They were known for their unorthodox approach to traditional clan techniques, often combining them with skills learned from outsiders. Their death came unexpectedly during what should have been a routine patrol, ambushed by enemy ninjas seeking to steal clan secrets."
            ],
            
            "quest": [
                f"Quest: Unfinished Business\nDescription: {npc_name} appears before you, their spirit unable to rest until their final mission is completed. They ask you to retrieve a special scroll hidden in enemy territory.\nObjectives:\n1. Infiltrate the enemy camp\n2. Locate the hidden chamber\n3. Retrieve the scroll\n4. Return without being detected\nDifficulty: Challenging\nRewards: Rare jutsu scroll, 500 experience points",
                
                f"Quest: Legacy of Honor\nDescription: {npc_name} requests your help to clear their name from a false accusation that haunts their legacy.\nObjectives:\n1. Gather evidence from three witnesses\n2. Infiltrate the records hall\n3. Replace the falsified documents\n4. Report to the clan elder\nDifficulty: Moderate\nRewards: Unique weapon, 300 experience points"
            ],
            
            "combat": [
                f"Battle Introduction: As you enter the misty clearing, {npc_name} materializes from the shadows, their eyes reflecting a challenge. 'Let's see if you're worthy of carrying on what I started.'\n\nCombat Style: {npc_name} utilizes quick, precise strikes, focusing on wearing down opponents with rapid combinations rather than single powerful attacks. They excel at mid-range combat, using clan-specific jutsu to control the battlefield.\n\nSpecial Moves:\n- Shadow Step: Teleports behind the opponent for a surprise attack\n- Elemental Barrage: Launches multiple elemental projectiles\n- Forbidden Technique: Ultimate move that sacrifices health for massive damage\n\nLocation: A foggy forest clearing with ancient stone monuments that {npc_name} can use for tactical advantages.\n\nDifficulty: Hard\n\nRewards: Unique chakra enhancement item, clan-specific technique scroll",
                
                f"Battle Introduction: {npc_name} stands atop the waterfall, arms crossed. 'I've been watching your progress. Now, show me how much you've grown.'\n\nCombat Style: Prioritizes defensive techniques and counterattacks, forcing the player to make the first move. Utilizes the environment strategically, especially the flowing water and slippery rocks.\n\nSpecial Moves:\n- Reflective Barrier: Returns a portion of damage back to the attacker\n- Water Prison: Temporarily immobilizes the player\n- Ancestral Power: Channels the power of fallen clan members for enhanced abilities\n\nLocation: A sacred waterfall with multiple elevations and hazardous terrain.\n\nDifficulty: Medium\n\nRewards: Water-based jutsu scroll, legendary crafting material"
            ],
            
            "dialogue": [
                f"Player: 'Are you {npc_name}? I've heard stories about you.'\n\n{npc_name}: 'Stories, hm? The living always reduce us to stories. What matters is what you do with the time you have left.'\n\nPlayer: 'I'm trying to master the technique your clan is known for.'\n\n{npc_name}: 'It took me years to perfect that technique, and even then, it wasn't enough in the end. The secret isn't in your hands or your chakra—it's in understanding what you're willing to sacrifice.'\n\nPlayer: 'What happened on your final mission?'\n\n{npc_name}: *expression darkens* 'Some questions are better left unanswered. But know this: loyalty to your comrades will always be more important than completing the mission. That's a lesson I learned too late.'",
                
                f"Player: 'I didn't expect to find you here.'\n\n{npc_name}: 'Few do. This place holds memories... both the kind worth keeping and those I wish to forget.'\n\nPlayer: 'The village elders speak highly of your talents.'\n\n{npc_name}: *laughs softly* 'The elders remember what they wish to remember. My greatest talent was seeing through the deceptions we tell ourselves.'\n\nPlayer: 'Can you teach me something that isn't in the scrolls?'\n\n{npc_name}: 'The most valuable lesson? Power without purpose becomes its own enemy. I mastered every technique in our clan's arsenal, yet failed at the one thing that mattered most—protecting those I cared about. Remember that when you're chasing power.'"
            ]
        }
        
        # Select a random mock response
        responses = mock_responses.get(prompt_type, ["No mock response available for this prompt type."])
        response_text = random.choice(responses)
        
        return {
            "id": f"mock-response-{random.randint(1000, 9999)}",
            "model": prompt["model"],
            "created": int(os.times().elapsed),
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(str(prompt)) // 4,
                "completion_tokens": len(response_text) // 4,
                "total_tokens": (len(str(prompt)) + len(response_text)) // 4
            },
            "metadata": prompt["metadata"]
        }


# Example usage function
def generate_npc_content(npc_data: Dict[str, Any], prompt_type: str = "background", provider: str = "openai") -> str:
    """
    Generate content for an NPC using the prompt generator.
    
    Args:
        npc_data: Dictionary containing NPC information
        prompt_type: Type of prompt to generate
        provider: AI provider to use
        
    Returns:
        str: Generated content
        
    Note: This is a stub implementation that returns mock responses.
    In a production environment, this would call the actual AI API.
    """
    generator = NPCPromptGenerator(provider=provider)
    prompt = generator.generate_prompt(npc_data, prompt_type)
    
    # In a real implementation, you would call the AI API here
    # response = call_ai_api(prompt)
    
    # For now, use the mock response
    mock_response = generator.mock_ai_response(prompt)
    
    # Extract the generated content
    content = mock_response["choices"][0]["message"]["content"]
    
    return content 