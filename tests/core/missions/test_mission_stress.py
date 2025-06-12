"""
Stress tests and race condition tests for the mission system.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import discord
from datetime import datetime, timedelta
from typing import List
import json
import uuid
from discord.ext import commands

from HCshinobi.core.missions.mission import Mission, MissionStatus, MissionDifficulty
from HCshinobi.core.missions.discord_interface import MissionInterface
from HCshinobi.core.missions.generator import MissionGenerator
from HCshinobi.core.character_system import CharacterSystem

@pytest.fixture
def mock_bot():
    """Create a mock Discord bot with mocked services."""
    bot = MagicMock(spec=commands.Bot) # Use spec=commands.Bot for stricter mocking
    bot.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 123456789
    # Add mock services needed by MissionInterface or its methods
    bot.services = MagicMock()
    
    # Create mocks for services
    mock_character_system = AsyncMock(spec=CharacterSystem)
    mock_currency_system = AsyncMock()
    mock_progression_engine = AsyncMock()
    
    # Attach progression and currency systems AS ATTRIBUTES of character_system
    mock_character_system.progression_engine = mock_progression_engine
    mock_character_system.currency_system = mock_currency_system # Assuming currency is also accessed via character_system
    
    # Assign the configured character_system mock to bot.services
    bot.services.character_system = mock_character_system
    # Assign progression/currency also to bot.services just in case they are accessed directly elsewhere
    bot.services.currency_system = mock_currency_system 
    bot.services.progression_engine = mock_progression_engine
    # Add other services if needed
    return bot

@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = Mock(spec=discord.User)
    user.id = 987654321
    user.send = AsyncMock()
    return user

@pytest.fixture
def mock_interaction(mock_user):
    """Create a mock Discord interaction."""
    interaction = Mock(spec=discord.Interaction)
    interaction.user = mock_user
    interaction.response = Mock()
    interaction.response.defer = AsyncMock()
    interaction.followup = Mock()
    interaction.followup.send = AsyncMock()
    return interaction

@pytest.fixture
def mock_ollama_response():
    """Create a mock Ollama API response."""
    mission_id_counter = 0
    
    def create_response():
        nonlocal mission_id_counter
        mission_id_counter += 1
        return {
            "response": json.dumps({
                "title": f"Test Mission {mission_id_counter}",
                "description": "A test mission description",
                "requirements": {
                    "min_level": 5,
                    "team_size": 1,
                    "special_requirements": ["test_requirement"]
                },
                "reward": {
                    "ryo": 1000,
                    "exp": 500,
                    "items": ["test_item"]
                },
                "duration_hours": 1
            })
        }
    return create_response

class MockResponse:
    """Mock aiohttp response."""
    def __init__(self, mock_ollama_response):
        self.status = 200
        self._mock_ollama_response = mock_ollama_response

    async def json(self):
        """Return mock response data."""
        return self._mock_ollama_response()

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

class MockAioHttpSession:
    """Mock aiohttp client session."""
    def __init__(self, mock_ollama_response):
        self._mock_ollama_response = mock_ollama_response

    def post(self, *args, **kwargs):
        """Mock post request."""
        return MockResponse(self._mock_ollama_response)

    async def close(self):
        """Mock close session."""
        pass

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        pass

@pytest.fixture
def mock_aiohttp_session(mock_ollama_response):
    """Create a mock aiohttp session."""
    return MockAioHttpSession(mock_ollama_response)

@pytest.fixture
def mission_interface(mock_bot):
    """Create a mission interface instance."""
    interface = MissionInterface(mock_bot)
    
    # Attach only the services the interface might expect directly on self
    # Based on the error, character_system seems to be the primary one.
    interface.character_system = mock_bot.services.character_system
    # Keep progression/currency if they might be accessed directly on interface, 
    # otherwise remove them if they are ONLY accessed via interface.character_system.* 
    interface.currency_system = mock_bot.services.currency_system # Keep for now
    interface.progression_engine = mock_bot.services.progression_engine # Keep for now

    # Re-attach callback methods correctly
    if hasattr(interface, 'mission_command') and hasattr(interface.mission_command, 'callback'):
        interface.mission_command = interface.mission_command.callback.__get__(interface, MissionInterface)
    if hasattr(interface, 'missions_command') and hasattr(interface.missions_command, 'callback'):
        interface.missions_command = interface.missions_command.callback.__get__(interface, MissionInterface)
    if hasattr(interface, 'complete_mission_command') and hasattr(interface.complete_mission_command, 'callback'):
        interface.complete_mission_command = interface.complete_mission_command.callback.__get__(interface, MissionInterface)
    return interface

@pytest.mark.asyncio
async def test_rapid_mission_requests(mission_interface, mock_interaction, mock_aiohttp_session):
    """Test rapid mission requests from the same user."""
    with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
        # Create multiple mission requests simultaneously
        requests = 10
        tasks = []
        
        for _ in range(requests):
            tasks.append(
                mission_interface.mission_command(mock_interaction, difficulty="D", village="Leaf")
            )
        
        # Run all requests concurrently
        await asyncio.gather(*tasks)
        
        # Verify that only one mission was assigned per cooldown period
        active_missions = len([
            m for m in mission_interface.active_missions.get("Leaf", [])
            if m.status == MissionStatus.AVAILABLE
        ])
        # The cooldown is 2 seconds, so we expect at most 1 mission per 2 seconds
        # Since we're running all requests concurrently, we should only get 1 mission
        assert active_missions == 1

@pytest.mark.asyncio
async def test_mission_completion_spam(mission_interface, mock_interaction):
    """Test rapid mission completion attempts."""
    # Create a test mission
    mission = Mission(
        id="test_mission",
        title="Test Mission",
        description="Test Description",
        difficulty=MissionDifficulty.D_RANK,
        village="Leaf",
        reward={"ryo": 100, "exp": 100},
        duration=timedelta(hours=1)
    )
    
    # Add mission to player's missions
    mission_interface.player_missions[mock_interaction.user.id] = mission
    mission.start()
    
    # Try to complete the mission multiple times simultaneously
    completion_attempts = 10
    tasks = []
    
    for _ in range(completion_attempts):
        tasks.append(
            mission_interface.complete_mission_command(mock_interaction, mission_id="test_mission")
        )
    
    # Run all completion attempts concurrently
    await asyncio.gather(*tasks)
    
    # Verify mission was only completed once
    assert mission.status == MissionStatus.COMPLETED
    assert mission.completed_at is not None
    assert mock_interaction.followup.send.call_count == completion_attempts

@pytest.mark.asyncio
async def test_mission_generator_stress(mock_interaction, mock_aiohttp_session):
    """Test mission generator under heavy load."""
    with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
        async with MissionGenerator() as generator:
            # Override the session with our mock
            generator.session = mock_aiohttp_session
            
            # Generate multiple missions concurrently
            difficulties = [
                MissionDifficulty.D_RANK,
                MissionDifficulty.C_RANK,
                MissionDifficulty.B_RANK
            ]
            count_per_difficulty = 5
            
            missions = await generator.generate_mission_batch(
                "Leaf",
                difficulties,
                count_per_difficulty
            )
            
            # Verify all missions were generated correctly
            assert len(missions) == len(difficulties) * count_per_difficulty
            
            # Verify each mission has unique ID
            mission_ids = [mission.id for mission in missions]
            assert len(mission_ids) == len(set(mission_ids))

@pytest.mark.asyncio
async def test_concurrent_village_missions(mission_interface, mock_interaction, mock_aiohttp_session):
    """Test handling missions from multiple villages concurrently."""
    with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
        villages = ["Leaf", "Sand", "Mist", "Cloud", "Stone"]
        tasks = []
        
        for village in villages:
            tasks.append(
                mission_interface.mission_command(mock_interaction, difficulty="D", village=village)
            )
        
        # Run all village requests concurrently
        await asyncio.gather(*tasks)
        
        # Verify missions were created for each village within rate limit
        total_missions = sum(
            len(missions) for missions in mission_interface.active_missions.values()
        )
        assert total_missions <= len(villages)

@pytest.mark.asyncio
async def test_mission_status_race_conditions(mission_interface, mock_interaction):
    """Test race conditions in mission status changes."""
    mission = Mission(
        id="test_mission",
        title="Test Mission",
        description="Test Description",
        difficulty=MissionDifficulty.D_RANK,
        village="Leaf",
        reward={"ryo": 100, "exp": 100},
        duration=timedelta(hours=1)
    )
    
    mission_interface.player_missions[mock_interaction.user.id] = mission
    
    # Try different status changes concurrently
    async def status_changes():
        try:
            if not mission.status == MissionStatus.COMPLETED:
                mission.start()
                mission.complete()
        except ValueError:
            pass
    
    tasks = [status_changes() for _ in range(10)]
    await asyncio.gather(*tasks)
    
    # Verify mission ended up in a valid state
    assert mission.status in [MissionStatus.AVAILABLE, MissionStatus.IN_PROGRESS, MissionStatus.COMPLETED]

@pytest.mark.asyncio
async def test_expired_mission_cleanup(mission_interface, mock_interaction):
    """Test handling of expired missions during rapid requests."""
    # Create expired mission
    expired_mission = Mission(
        id="expired_mission",
        title="Expired Mission",
        description="Test Description",
        difficulty=MissionDifficulty.D_RANK,
        village="Leaf",
        reward={"ryo": 100, "exp": 100},
        duration=timedelta(seconds=0)
    )
    
    expired_mission.start()
    mission_interface.player_missions[mock_interaction.user.id] = expired_mission
    
    # Try to interact with expired mission multiple times
    tasks = []
    for _ in range(5):
        tasks.extend([
            mission_interface.missions_command(interaction=mock_interaction),
            mission_interface.complete_mission_command(mock_interaction, mission_id="expired_mission")
        ])
    
    await asyncio.gather(*tasks)
    
    # Verify expired mission was handled correctly
    assert expired_mission.status == MissionStatus.EXPIRED 