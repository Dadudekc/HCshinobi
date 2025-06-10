"""Agent for handling dynamic Ollama-based mission generation."""
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from .base_agent import BaseAgent, Message
from .utils import with_error_handling, with_performance_tracking, create_message
from ..mission_system import MissionSystem
from ..utils.ollama_client import OllamaClient
from .mission_templates import (
    calculate_mission_rewards,
    get_clan_requirements,
    get_mission_template,
    validate_mission_data,
    validate_adaptation_data,
    calculate_adapted_difficulty,
    MISSION_CHAINS
)

logger = logging.getLogger(__name__)

class MissionGenerationAgent(BaseAgent):
    """Agent responsible for generating and managing dynamic missions using Ollama."""
    
    VALID_DIFFICULTIES = ["easy", "medium", "hard"]
    REQUIRED_PERFORMANCE_FIELDS = [
        "completion_time", 
        "objectives_completed", 
        "total_objectives", 
        "damage_taken"
    ]
    
    def __init__(
        self,
        agent_id: str,
        mission_system: MissionSystem,
        ollama_model: str = "ninja:latest",
        ollama_host: str = "http://localhost:11434"
    ):
        """Initialize the mission generation agent."""
        super().__init__(agent_id)
        self.mission_system = mission_system
        self.ollama_client = OllamaClient(
            model=ollama_model,
            host=ollama_host
        )
        
    async def _on_start(self) -> None:
        """Set up message handlers on startup."""
        self.register_message_handler("generate_mission", self.handle_generate_mission)
        self.register_message_handler("adapt_mission", self.handle_adapt_mission)
        self.register_message_handler("check_requirements", self.handle_check_requirements)
        self.register_message_handler("get_mission_chain", self.handle_get_mission_chain)
        self.register_message_handler("progress_mission_chain", self.handle_progress_mission_chain)
        
    async def _send_error_response(
        self,
        error: Exception,
        message: Message,
        message_type: str
    ) -> None:
        """Send standardized error response."""
        logger.error(f"Error in {message_type}: {error}")
        await self.send_message(create_message(
            sender=self.agent_id,
            receiver=message.sender,
            message_type=message_type,
            content={
                "success": False,
                "error": str(error)
            },
            correlation_id=message.id
        ))

    def _validate_message_content(self, content: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that message content has all required fields."""
        missing_fields = [field for field in required_fields if field not in content]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    async def _validate_character(self, character_id: str) -> Dict[str, Any]:
        """Validate and retrieve character data."""
        try:
            character = await self.mission_system.get_character(character_id)
            if not character:
                raise ValueError(f"Character not found: {character_id}")
            return character
        except Exception as e:
            raise ValueError(f"Failed to validate character: {e}")

    async def _validate_mission(self, mission_id: str) -> Dict[str, Any]:
        """Validate and retrieve mission data."""
        try:
            mission = await self.mission_system.get_mission(mission_id)
            if not mission:
                raise ValueError(f"Mission not found: {mission_id}")
            return mission
        except Exception as e:
            raise ValueError(f"Failed to validate mission: {e}")

    async def _validate_chain(self, chain_id: str) -> Dict[str, Any]:
        """Validate and retrieve chain data."""
        if chain_id not in MISSION_CHAINS:
            raise ValueError(f"Invalid chain ID: {chain_id}")
        return MISSION_CHAINS[chain_id]

    @with_error_handling()
    @with_performance_tracking("check_requirements")
    async def handle_check_requirements(self, message: Message) -> None:
        """Check if a character has the required items for a mission."""
        try:
            content = message.content
            self._validate_message_content(content, ["character_id", "mission_id"])
            
            character_id = content["character_id"]
            mission_id = content["mission_id"]
            
            # Get character and mission data
            character = await self._validate_character(character_id)
            mission = await self._validate_mission(mission_id)
            
            # Check inventory against requirements
            required_items = mission["requirements"]["required_items"]
            missing_items = [item for item in required_items if item not in character["inventory"]]
            
            await self.send_message(create_message(
                sender=self.agent_id,
                receiver=message.sender,
                message_type="requirements_checked",
                content={
                    "success": True,
                    "character_id": character_id,
                    "mission_id": mission_id,
                    "has_requirements": len(missing_items) == 0,
                    "missing_items": missing_items
                },
                correlation_id=message.id
            ))
            
        except Exception as e:
            await self._send_error_response(e, message, "requirements_checked")

    @with_error_handling()
    @with_performance_tracking("generate_mission")
    async def handle_generate_mission(self, message: Message) -> None:
        """Handle mission generation requests."""
        try:
            content = message.content
            self._validate_message_content(content, ["character_id"])
            
            difficulty = content.get("difficulty", "medium")
            if difficulty not in self.VALID_DIFFICULTIES:
                raise ValueError(f"Invalid difficulty: {difficulty}. Must be one of {self.VALID_DIFFICULTIES}")
            
            character = await self._validate_character(content["character_id"])
            
            # Construct prompt for Ollama
            prompt = self._build_mission_prompt(
                character=character,
                difficulty=difficulty,
                theme=content.get("theme"),
                constraints=content.get("constraints", {})
            )
            
            # Generate and parse mission
            response = await self.ollama_client.generate(prompt)
            mission_data = await self._parse_mission_response(response)
            
            # Register the mission
            mission_id = await self.mission_system.register_dynamic_mission(mission_data)
            
            await self.send_message(create_message(
                sender=self.agent_id,
                receiver=message.sender,
                message_type="mission_generated",
                content={
                    "success": True,
                    "mission_id": mission_id,
                    "mission_data": mission_data
                },
                correlation_id=message.id
            ))
            
        except Exception as e:
            await self._send_error_response(e, message, "mission_generated")

    @with_error_handling()
    @with_performance_tracking("adapt_mission")
    async def handle_adapt_mission(self, message: Message) -> None:
        """Handle requests to adapt mission difficulty based on player performance."""
        try:
            content = message.content
            self._validate_message_content(content, ["mission_id", "performance_data"])
            
            mission_id = content["mission_id"]
            performance_data = content["performance_data"]
            
            # Validate performance data structure
            self._validate_message_content(performance_data, self.REQUIRED_PERFORMANCE_FIELDS)
            
            # Get current mission data
            mission = await self._validate_mission(mission_id)
            
            # Generate adaptation prompt
            prompt = self._build_adaptation_prompt(
                mission=mission,
                performance_data=performance_data
            )
            
            # Get and apply adaptations
            response = await self.ollama_client.generate(prompt)
            adaptations = await self._parse_adaptation_response(response)
            
            # Apply adaptations
            updated_mission = await self.mission_system.update_mission(
                mission_id,
                adaptations
            )
            
            await self.send_message(create_message(
                sender=self.agent_id,
                receiver=message.sender,
                message_type="mission_adapted",
                content={
                    "success": True,
                    "mission_id": mission_id,
                    "adaptations": adaptations,
                    "updated_mission": updated_mission
                },
                correlation_id=message.id
            ))
            
        except Exception as e:
            await self._send_error_response(e, message, "mission_adapted")
        
    @with_error_handling()
    @with_performance_tracking("get_mission_chain")
    async def handle_get_mission_chain(self, message: Message) -> None:
        """Handle requests to get available mission chains for a character."""
        try:
            content = message.content
            self._validate_message_content(content, ["character_id"])
            
            character = await self._validate_character(content["character_id"])
            
            # Find available chains based on rank and level
            available_chains = []
            for chain_id, chain in MISSION_CHAINS.items():
                if (
                    character["rank"] == chain["required_rank"] and
                    character["level"] >= chain.get("required_level", 0)
                ):
                    # Get progress in this chain
                    progress = await self.mission_system.get_chain_progress(
                        character["id"],
                        chain_id
                    )
                    
                    available_chains.append({
                        "chain_id": chain_id,
                        "name": chain["name"],
                        "description": chain["description"],
                        "progress": progress,
                        "next_mission": self._get_next_chain_mission(chain, progress)
                    })
                    
            await self.send_message(create_message(
                sender=self.agent_id,
                receiver=message.sender,
                message_type="mission_chains",
                content={
                    "success": True,
                    "character_id": character["id"],
                    "available_chains": available_chains
                },
                correlation_id=message.id
            ))
            
        except Exception as e:
            await self._send_error_response(e, message, "mission_chains")
            
    @with_error_handling()
    @with_performance_tracking("progress_mission_chain")
    async def handle_progress_mission_chain(self, message: Message) -> None:
        """Handle requests to progress in a mission chain."""
        try:
            content = message.content
            self._validate_message_content(content, ["character_id", "chain_id", "mission_id"])
            
            character = await self._validate_character(content["character_id"])
            chain = await self._validate_chain(content["chain_id"])
            
            # Get chain progress
            progress = await self.mission_system.get_chain_progress(
                character["id"],
                content["chain_id"]
            )
            
            # Verify mission is next in chain
            next_mission = self._get_next_chain_mission(chain, progress)
            if not next_mission or next_mission["id"] != content["mission_id"]:
                raise ValueError("Invalid mission for current chain progress")
            
            # Update progress and grant rewards
            await self.mission_system.update_chain_progress(
                character["id"],
                content["chain_id"],
                content["mission_id"]
            )
            
            # Grant unlocked items
            for item in next_mission["unlocks"]:
                await self.mission_system.grant_item(character["id"], item)
                
            # Check if chain is complete
            is_complete = len(progress) + 1 == len(chain["missions"])
            
            await self.send_message(create_message(
                sender=self.agent_id,
                receiver=message.sender,
                message_type="chain_progress_updated",
                content={
                    "success": True,
                    "character_id": character["id"],
                    "chain_id": content["chain_id"],
                    "mission_completed": content["mission_id"],
                    "unlocked_items": next_mission["unlocks"],
                    "is_chain_complete": is_complete,
                    "next_mission": self._get_next_chain_mission(chain, progress + [content["mission_id"]]) if not is_complete else None
                },
                correlation_id=message.id
            ))
            
        except Exception as e:
            await self._send_error_response(e, message, "chain_progress_updated")
        
    def _get_next_chain_mission(
        self,
        chain: Dict[str, Any],
        completed_missions: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get the next mission in a chain based on progress."""
        for mission in chain["missions"]:
            if mission["id"] not in completed_missions:
                return mission
        return None
        
    def _get_clan_requirements(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """Get clan-specific requirements and rewards."""
        clan = character.get("clan")
        return get_clan_requirements(clan) if clan else {}
        
    def _build_mission_prompt(
        self,
        character: Dict[str, Any],
        difficulty: str,
        theme: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for mission generation."""
        # Get template and requirements
        mission_type = theme if theme else "training"  # Default to training
        template = get_mission_template(difficulty, mission_type)
        clan_requirements = self._get_clan_requirements(character)
        
        # Calculate rewards
        rewards = calculate_mission_rewards(
            difficulty=difficulty,
            mission_type=mission_type,
            clan=character.get("clan")
        )
        
        # Build prompt parts
        prompt_parts = [
            "Generate a Naruto-themed ninja mission with the following specifications:",
            f"\nCharacter Level: {character['level']}",
            f"Character Clan: {character.get('clan', 'None')}",
            f"Character Inventory: {', '.join(character.get('inventory', []))}",
            f"Difficulty: {difficulty}",
            f"Mission Type: {mission_type}"
        ]
        
        # Add clan-specific requirements if any
        if clan_requirements:
            prompt_parts.extend([
                "\nClan-Specific Requirements:",
                f"Required Items: {', '.join(clan_requirements.get('special_items', []))}",
                "Bonus Rewards Available: " + 
                ", ".join(f"{item} ({chance*100}%)" for item, chance in clan_requirements.get('bonus_rewards', {}).items())
            ])
            
        # Add base template requirements
        prompt_parts.extend([
            f"\nBase Required Items: {', '.join(template['required_items'])}",
            f"Recommended Items: {', '.join(template['recommended_items'])}",
            f"\nBase Rewards:",
            f"XP: {rewards['base_xp']}",
            f"Ryo: {rewards['base_ryo']}",
            "\nPossible Item Rewards: " +
            ", ".join(f"{rarity} ({chance*100}%)" for rarity, chance in rewards['item_chances'].items())
        ])
        
        if constraints:
            prompt_parts.append("\nConstraints:")
            for key, value in constraints.items():
                prompt_parts.append(f"- {key}: {value}")
                
        # Add mission format template
        prompt_parts.extend([
            "\nProvide the mission in the following JSON format:",
            self._get_mission_format_template()
        ])
        
        return "\n".join(prompt_parts)
        
    def _get_mission_format_template(self) -> str:
        """Get the standardized mission format template."""
        return """{
            "id": "unique_mission_id",
            "name": "Mission Name",
            "description": "Detailed mission description",
            "objectives": [
                {
                    "description": "Objective description",
                    "required_items": ["item1"],
                    "completion_criteria": "How to complete this objective"
                }
            ],
            "requirements": {
                "min_level": N,
                "required_items": ["item1"],
                "recommended_items": ["item1"],
                "recommended_jutsu": ["jutsu1"]
            },
            "rewards": {
                "xp": N,
                "ryo": N,
                "items": ["item1"],
                "bonus_conditions": [
                    {
                        "condition": "Complete without using any food pills",
                        "bonus_reward": {"ryo": N, "items": ["special_item"]}
                    }
                ]
            },
            "challenges": [
                {
                    "type": "combat/skill/stealth",
                    "difficulty": N,
                    "description": "Challenge description",
                    "required_items": ["item1"],
                    "failure_consequences": "What happens if this challenge is failed"
                }
            ],
            "failure_conditions": [
                {
                    "condition": "Missing required items",
                    "consequence": "Mission cannot be started"
                }
            ]
        }"""
        
    @with_error_handling()
    async def _parse_mission_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate the mission data from Ollama response."""
        try:
            mission_data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama: {e}\nResponse: {response[:500]}")
            raise ValueError(f"Invalid JSON response from mission generation AI: {e}")
            
        # Validate mission data
        errors = validate_mission_data(mission_data)
        if errors:
            error_msg = "\n".join(errors)
            logger.error(f"Invalid mission data: {error_msg}")
            raise ValueError(error_msg)
                
        return mission_data
            
    def _build_adaptation_prompt(
        self,
        mission: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> str:
        """Build prompt for mission adaptation."""
        # Calculate adapted difficulty
        adaptation_result = calculate_adapted_difficulty(
            mission["difficulty"],
            performance_data
        )
        
        # Use json.dumps for proper formatting in the prompt
        mission_json = json.dumps(mission, indent=2)
        perf_json = json.dumps(performance_data, indent=2)
        
        return f"""
        Analyze the following mission and player performance data to suggest adaptations:
        
        Mission:
        {mission_json}
        
        Performance Data:
        {perf_json}
        
        Performance Analysis:
        - Performance Score: {adaptation_result['performance_score']:.2f}
        - Suggested Difficulty Adjustment: {adaptation_result['difficulty_adjustment']:.2f}
        - New Difficulty Level: {adaptation_result['new_difficulty']:.1f}
        
        Suggest adaptations in JSON format:
        {{
            "difficulty_adjustment": float,  # {adaptation_result['difficulty_adjustment']:.2f} recommended
            "reward_adjustment": float,      # Adjust based on difficulty change
            "additional_challenges": [
                {{
                    "type": "combat/skill/stealth",
                    "difficulty": N,
                    "description": "Challenge description",
                    "required_items": ["item1"]
                }}
            ],
            "removed_challenges": ["challenge_id1"],
            "modified_objectives": [
                {{
                    "objective_id": "obj1",
                    "new_required_items": ["item1"],
                    "difficulty_adjustment": float
                }}
            ],
            "item_requirement_changes": {{
                "added_required_items": ["item1"],
                "removed_required_items": ["item2"],
                "added_recommended_items": ["item3"],
                "removed_recommended_items": ["item4"]
            }}
        }}
        """
        
    @with_error_handling()
    async def _parse_adaptation_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate adaptation suggestions from Ollama response."""
        try:
            adaptation_data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON adaptation response from Ollama: {e}\nResponse: {response[:500]}")
            raise ValueError(f"Invalid JSON response from mission adaptation AI: {e}")
        
        # Validate adaptation data
        errors = validate_adaptation_data(adaptation_data)
        if errors:
            error_msg = "\n".join(errors)
            logger.error(f"Invalid adaptation data: {error_msg}")
            raise ValueError(error_msg)
        
        return adaptation_data 