"""Integration tests for character and mission system interactions."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
import os
import tempfile
import shutil
import logging # Import logging
import json
from unittest.mock import AsyncMock, MagicMock

from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.character import Character
from HCshinobi.core.missions.mission import Mission, MissionDifficulty, MissionStatus
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from HCshinobi.utils.file_io import save_json
from tests.utils.time_utils import get_mock_now, get_past_hours

# Get a logger instance for the test module
logger = logging.getLogger(__name__)

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest_asyncio.fixture
async def character_system(temp_data_dir):
    """Create a character system with test data and proper setup."""
    system = CharacterSystem(temp_data_dir) 
    # We need to load characters *before* creating new ones in tests
    # await system.load_characters()
    # Pre-create some test characters - moved creation to within tests where needed
    # await system.create_character("user_lvl_1", "Lvl1", "TestClan", level=1) 
    # await system.create_character("user_lvl_10", "Lvl10", "TestClan", level=10)
    return system

@pytest.fixture
def mock_currency_system():
    """Provides a mock CurrencySystem."""
    mock = MagicMock(spec=CurrencySystem)
    mock.get_balance = AsyncMock(return_value=10000)
    mock.add_ryo = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_progression_engine():
    """Provides a mock ShinobiProgressionEngine."""
    mock = MagicMock(spec=ShinobiProgressionEngine)
    mock.grant_experience = AsyncMock(return_value=True)
    mock.check_achievement = AsyncMock(return_value=False)
    return mock

@pytest.fixture
def mission_system(character_system, temp_data_dir, mock_currency_system, mock_progression_engine):
    """Create a fresh mission system for integration tests."""
    missions_dir = os.path.join(temp_data_dir, 'missions')
    os.makedirs(missions_dir, exist_ok=True)
    
    defs_file = os.path.join(missions_dir, "mission_definitions.json")
    example_defs = {
        "D001": {"name": "Fetch Herbs D1", "rank": "D", "reward": {"ryo": 50, "exp": 20}, "requirements": {"level": 1}},
        "D002": {"name": "Deliver Scroll D2", "rank": "D", "reward": {"ryo": 60, "exp": 25}, "requirements": {"level": 1}},
        "C001": {"name": "Capture Bandit C", "rank": "C", "reward": {"ryo": 200, "exp": 100}, "requirements": {"level": 5}}
        # Add more as needed for integration tests
    }
    save_json(defs_file, example_defs)
    
    active_file = os.path.join(missions_dir, "active_missions.json")
    completed_file = os.path.join(missions_dir, "completed_missions.json")
    if not os.path.exists(active_file): save_json(active_file, {})
    if not os.path.exists(completed_file): save_json(completed_file, {})

    system = MissionSystem(
        character_system=character_system,
        data_dir=temp_data_dir,
        currency_system=mock_currency_system,
        progression_engine=mock_progression_engine
    )
    # Consider loading data here if needed before tests run
    # await system.load_mission_data() # Might require fixture to be async
    return system

@pytest.fixture
def setup_missions(tmp_path):
    """Set up test missions in a temporary directory."""
    missions_dir = tmp_path / "data" / "missions"
    missions_dir.mkdir(parents=True, exist_ok=True)
    missions_file = missions_dir / "missions.json"

    test_missions = [
        {
            "mission_id": "d_rank_1",
            "title": "D-Rank Mission 1",
            "description": "A simple D-rank mission for testing",
            "rank": "D",
            "reward_exp": 150,
            "reward_ryo": 100,
            "requirements": {
                "level": 1
            },
            "objectives": ["Complete the mission"],
            "time_limit_hours": 24,
            "location": "Village"
        },
        {
            "mission_id": "d_rank_2",
            "title": "D-Rank Mission 2",
            "description": "Another D-rank mission for testing",
            "rank": "D",
            "reward_exp": 150,
            "reward_ryo": 150,
            "requirements": {
                "level": 1
            },
            "objectives": ["Complete the mission"],
            "time_limit_hours": 24,
            "location": "Village"
        },
        {
            "mission_id": "d_rank_3",
            "title": "D-Rank Mission 3",
            "description": "One more D-rank mission",
            "rank": "D",
            "reward_exp": 50,
            "reward_ryo": 50,
            "requirements": {
                "level": 1
            },
            "objectives": ["Complete this mission too"],
            "time_limit_hours": 24,
            "location": "Training Grounds"
        },
        {
            "mission_id": "c_rank_1",
            "title": "C-Rank Mission 1",
            "description": "A C-rank mission for testing",
            "rank": "C",
            "reward_exp": 200,
            "reward_ryo": 300,
            "requirements": {
                "level": 3
            },
            "objectives": ["Complete the mission"],
            "time_limit_hours": 24,
            "location": "Village"
        }
    ]

    with open(missions_file, 'w') as f:
        json.dump(test_missions, f)

    return str(missions_file)

@pytest.mark.asyncio
async def test_character_mission_level_requirements(character_system, mission_system):
    """Test level requirements for missions using integrated systems."""
    await mission_system.load_mission_data() # Load mission defs

    # Create characters with different levels
    char_lvl1 = await character_system.create_character("user_lvl_1", "Lvl1", "TestClan", level=1, rank="Genin")
    char_lvl5 = await character_system.create_character("user_lvl_5", "Lvl5", "TestClan", level=5, rank="Chunin")
    assert char_lvl1 is not None
    assert char_lvl5 is not None

    # Level 1 tries C-rank (level 5 required)
    success, msg = await mission_system.assign_mission(char_lvl1, "C001")
    assert success is False
    assert "level requirement" in msg.lower()

    # Level 5 tries C-rank
    success, msg = await mission_system.assign_mission(char_lvl5, "C001")
    assert success is True, f"Assigning mission failed: {msg}"

@pytest.mark.asyncio
async def test_character_mission_rewards(character_system, mission_system, mock_currency_system):
    """Test mission rewards affect character stats via mocked systems."""
    await mission_system.load_mission_data()
    
    # Create character
    character = await character_system.create_character("user1", "Reward Tester", "Leaf", rank="Genin")
    assert character is not None
    initial_exp = character.exp
    # Get initial balance from mock system
    initial_ryo = await mock_currency_system.get_balance(character.id) 

    # Assign and complete mission D001 (Reward: ryo=50, exp=20)
    success, msg = await mission_system.assign_mission(character, "D001")
    assert success is True, f"Assign mission failed: {msg}"
    
    rewards = await mission_system.complete_mission(character)
    assert rewards is not None
    assert rewards.get("ryo") == 50
    assert rewards.get("exp") == 20

    # Reload character to get updated exp (assuming progression engine updated it)
    # Note: Character object itself might not be updated in place unless ProgressionEngine returns it
    # It's safer to refetch or rely on progression engine mock verification
    # updated_character = await character_system.get_character(character.id)
    # assert updated_character.exp == initial_exp + 20
    # Verify progression engine was called instead:
    mission_system.progression_engine.grant_experience.assert_called_with(character.id, 20)

    # Verify currency system was called
    mock_currency_system.add_ryo.assert_called_with(character.id, 50)
    # Optional: Check final balance if needed (depends on mock setup)
    # final_ryo = await mock_currency_system.get_balance(character.id)
    # assert final_ryo == initial_ryo + 50 # This assumes add_ryo modified the value get_balance returns

@pytest.mark.asyncio
async def test_character_mission_limits(character_system, mission_system):
    """Test character-specific mission limits (assuming 1 active mission limit)."""
    await mission_system.load_mission_data()
    
    # Create two characters
    char1 = await character_system.create_character("user1", "Mission Master", "Leaf", rank="Genin")
    char2 = await character_system.create_character("user2", "Mission Helper", "Sand", rank="Genin")
    assert char1 is not None and char2 is not None

    # Assign one mission to char1
    eligible_missions_char1 = mission_system.get_available_missions(char1)
    assert len(eligible_missions_char1) > 0, "No eligible missions found for char1"
    first_mission_id = eligible_missions_char1[0]["id"] 
    
    success, msg = await mission_system.assign_mission(char1, first_mission_id)
    assert success is True, f"Failed to assign first mission: {msg}"

    # Try to assign a second mission to char1 (should fail due to active limit)
    if len(eligible_missions_char1) > 1:
        second_mission_id = eligible_missions_char1[1]["id"]
        success, msg = await mission_system.assign_mission(char1, second_mission_id)
        assert success is False, "Should not assign second mission to char1"
        assert "already have an active mission" in msg
    else:
        # Cannot test limit if only one mission is eligible
        pass

    # Assign a mission to char2 (should succeed)
    eligible_missions_char2 = mission_system.get_available_missions(char2)
    assert len(eligible_missions_char2) > 0, "No eligible missions found for char2"
    char2_mission_id = eligible_missions_char2[0]["id"]
    success, msg = await mission_system.assign_mission(char2, char2_mission_id)
    assert success is True, f"Failed to assign mission to char2: {msg}"
    assert char2.id in mission_system.active_missions

@pytest.mark.asyncio
async def test_character_mission_persistence(character_system, mission_system, temp_data_dir):
    """Test mission state persists across reloads."""
    await mission_system.load_mission_data()
    
    # Create character and assign mission
    char1 = await character_system.create_character("user_persist", "State Tester", "Leaf", rank="Genin")
    assert char1 is not None
    
    success, msg = await mission_system.assign_mission(char1, "D001")
    assert success, f"Assign mission failed: {msg}"
    assert char1.id in mission_system.active_missions
    
    # Simulate reload by creating a new MissionSystem instance using the same data dir
    new_mission_system = MissionSystem(
        character_system=character_system, # Use same (mocked or real) character system
        data_dir=temp_data_dir,
        currency_system=mission_system.currency_system, # Reuse mock
        progression_engine=mission_system.progression_engine # Reuse mock
    )
    await new_mission_system.load_mission_data() # Load from files
    
    # Verify the mission is still active for the user in the new instance
    assert char1.id in new_mission_system.active_missions, "Active mission state not persisted"
    assert new_mission_system.active_missions[char1.id]["mission_id"] == "D001"
    
    # Complete mission in new system
    reloaded_char = await character_system.get_character(char1.id) # Refetch might be needed
    assert reloaded_char is not None
    rewards = await new_mission_system.complete_mission(reloaded_char)
    assert rewards is not None
    assert char1.id not in new_mission_system.active_missions
    assert char1.id in new_mission_system.completed_missions
    assert "D001" in new_mission_system.completed_missions[char1.id]

@pytest.mark.asyncio
async def test_character_mission_completion_tracking(character_system, mission_system):
    """Test tracking completed missions per character."""
    await mission_system.load_mission_data() # Load missions

    # Create character
    character = await character_system.create_character("user1", "Completion Tracker", "Leaf", rank="Genin")
    assert character is not None

    # Assign and complete D001
    success, msg = await mission_system.assign_mission(character, "D001")
    assert success is True, f"Failed to assign D001: {msg}"
    await mission_system.complete_mission(character)

    # Verify D001 is marked completed for the user (Needs method in MissionSystem)
    completed_count = mission_system.get_completed_mission_count(character.id, "D001")
    assert completed_count == 1, "D001 should be marked as completed once"

    # Assign and complete D001 again
    success, msg = await mission_system.assign_mission(character, "D001")
    assert success is True, f"Failed to re-assign D001: {msg}"
    await mission_system.complete_mission(character)
    completed_count = mission_system.get_completed_mission_count(character.id, "D001")
    assert completed_count == 2, "D001 should be marked as completed twice"

    # Assign and complete D002
    success, msg = await mission_system.assign_mission(character, "D002")
    assert success is True, f"Failed to assign D002: {msg}"
    await mission_system.complete_mission(character)
    completed_count_d002 = mission_system.get_completed_mission_count(character.id, "D002")
    assert completed_count_d002 == 1, "D002 should be marked as completed once"

    # Verify total completed missions (Needs method in MissionSystem or CharacterSystem)
    # total_completed = mission_system.get_total_completed_missions(character.id)
    # assert total_completed == 3 # Or check character stats if stored there

    # Test completion check for a mission not completed
    completed_count_c001 = mission_system.get_completed_mission_count(character.id, "C001")
    assert completed_count_c001 == 0, "C001 should not be marked as completed"

@pytest.mark.asyncio
async def test_character_mission_level_progression(character_system, mission_system, mock_progression_engine):
    """Test character level progression mock calls through missions."""
    await mission_system.load_mission_data()

    # Create character
    char1 = await character_system.create_character("user_prog", "Level Up", "Leaf", rank="Genin")
    assert char1 is not None
    initial_level = char1.level
    initial_exp = char1.exp
    
    # Define mission with enough EXP to level up (or use mock)
    mission_id = "D001" # Reward: exp=20
    exp_reward = 20
    
    # Assign and complete
    success, msg = await mission_system.assign_mission(char1, mission_id)
    assert success, f"Assign failed: {msg}"
    rewards = await mission_system.complete_mission(char1)
    assert rewards is not None
    assert rewards.get("exp") == exp_reward
    
    # Verify progression engine was called
    mock_progression_engine.grant_experience.assert_called_with(char1.id, exp_reward)
    
    # To truly test level up, the ProgressionEngine mock or the real engine
    # would need to handle level-up logic based on EXP thresholds.
    # For now, we just verify the grant_experience call.

@pytest.mark.skip(reason="State recovery logic needs review/implementation")
@pytest.mark.asyncio
async def test_character_mission_state_recovery(character_system, mission_system):
    # ... (Test skipped) ...
    pass

@pytest.mark.asyncio
async def test_character_mission_failure_handling(character_system, mission_system):
    """Test how character and mission systems handle failures (e.g., expiration)."""
    await mission_system.load_mission_data()
    
    character = await character_system.create_character("user_fail", "Failure Tester", "Leaf", rank="Genin")
    assert character is not None
    initial_exp = character.exp

    # Assign a mission
    success, msg = await mission_system.assign_mission(character, "D001")
    assert success, f"Assign failed: {msg}"
    assert character.id in mission_system.active_missions

    # Simulate expiration
    mock_now = get_mock_now()
    past_time = get_past_hours(24)
    mission_system.active_missions[character.id]["start_time"] = past_time.isoformat()

    # Attempt completion - should fail, return None, and clear active mission
    rewards = await mission_system.complete_mission(character)
    assert rewards is None, "Expired mission should return None"
    assert character.id not in mission_system.active_missions, "Expired mission should be cleared"
    assert "D001" not in mission_system.completed_missions.get(character.id, []), "Expired mission shouldn't be marked completed"

    # Verify character EXP didn't change (mock was not called)
    mission_system.progression_engine.grant_experience.assert_not_called()
    mission_system.currency_system.add_ryo.assert_not_called()
    # refetched_char = await character_system.get_character(character.id)
    # assert refetched_char.exp == initial_exp # Assuming EXP wasn't granted 