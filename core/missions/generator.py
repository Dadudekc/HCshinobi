"""
Mission generator using Ollama for dynamic mission creation.
"""
import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from datetime import timedelta

from .mission import Mission, MissionDifficulty

logger = logging.getLogger(__name__)

class MissionGenerator:
    """Generates dynamic missions using Ollama."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._mission_counter = 0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def generate_mission(self, village: str, difficulty: MissionDifficulty) -> Mission:
        """
        Generate a dynamic mission using Ollama.
        
        Args:
            village: The village the mission is for
            difficulty: The difficulty level of the mission
            
        Returns:
            A dynamically generated Mission object
        """
        if not self.session:
            raise RuntimeError("MissionGenerator must be used as an async context manager")

        # Prepare the prompt for Ollama
        prompt = f"""Generate a unique ninja mission for the {village} village with {difficulty.value}-rank difficulty.
        The mission should be creative and engaging, with clear objectives and rewards.
        Format the response as a JSON object with the following structure:
        {{
            "title": "Mission title",
            "description": "Detailed mission description",
            "requirements": {{
                "min_level": number,
                "team_size": number,
                "special_requirements": ["list", "of", "requirements"]
            }},
            "reward": {{
                "ryo": number,
                "exp": number,
                "items": ["list", "of", "items"]
            }},
            "duration_hours": number
        }}"""

        try:
            async with self.session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama2",
                    "prompt": prompt,
                    "stream": False
                }
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Ollama API returned status {response.status}")
                
                result = await response.json()
                mission_data = json.loads(result["response"])

                # Create mission object from generated data
                self._mission_counter += 1
                return Mission(
                    id=f"mission_{self._mission_counter}",
                    title=mission_data["title"],
                    description=mission_data["description"],
                    difficulty=difficulty,
                    village=village,
                    reward=mission_data["reward"],
                    duration=timedelta(hours=mission_data["duration_hours"]),
                    requirements=mission_data["requirements"]
                )

        except Exception as e:
            logger.error(f"Error generating mission: {e}")
            raise

    async def generate_mission_batch(
        self,
        village: str,
        difficulties: list[MissionDifficulty],
        count: int = 1
    ) -> list[Mission]:
        """
        Generate multiple missions in parallel.
        
        Args:
            village: The village the missions are for
            difficulties: List of difficulty levels to generate
            count: Number of missions to generate per difficulty
            
        Returns:
            List of generated Mission objects
        """
        tasks = []
        for difficulty in difficulties:
            for _ in range(count):
                tasks.append(self.generate_mission(village, difficulty))
        
        return await asyncio.gather(*tasks) 