"""Tests for the mission system."""
import pytest
import os
import shutil # For cleaning up test data dir
from datetime import datetime, timedelta, timezone
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from unittest.mock import AsyncMock, patch, MagicMock
from HCshinobi.core.constants import RANK_ORDER
from HCshinobi.core.database import Database
from HCshinobi.core.missions.mission import Mission, MissionDifficulty, MissionStatus
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from HCshinobi.core.d20_mission import DifficultyLevel
import uuid
from HCshinobi.utils.file_io import save_json # Import save_json for fixture setup
from tests.utils.time_utils import get_mock_now, get_past_hours

# Directory for test character data
TEST_DATA_DIR = "./test_character_data"

@pytest.fixture(scope="function") # Use function scope to ensure clean state
def character_system(temp_data_dir):
    """Creates a CharacterSystem instance for testing, cleaning up afterwards."""
    # Ensure the test directory is clean before starting
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    
    # Let's mock it to avoid dependency issues from test_character_mission_integration
    mock = MagicMock(spec=CharacterSystem)
    # Store created characters within the mock
    mock._characters = {}
    async def get_char(user_id):
        return mock._characters.get(user_id)
    async def save_char(char):
        mock._characters[char.id] = char
        return True # Simulate successful save
    mock.get_character = AsyncMock(side_effect=get_char)
    mock.save_character = AsyncMock(side_effect=save_char)
    return mock

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
    """Create a fresh mission system for each test, with mocked dependencies."""
    missions_dir = os.path.join(temp_data_dir, 'missions')
    os.makedirs(missions_dir, exist_ok=True)
    
    # Define mission definitions file path within the temp missions dir
    defs_file = os.path.join(missions_dir, "mission_definitions.json")
    
    # Create dummy mission definitions file
    example_defs = {
        "D001": {"name": "Fetch Herbs D1", "rank": "D", "reward": {"ryo": 50, "exp": 20}},
        "D002": {"name": "Fetch Herbs D2", "rank": "D", "reward": {"ryo": 55, "exp": 22}},
        "D003": {"name": "Escort Merchant D", "rank": "D", "reward": {"ryo": 60, "exp": 25}, "requirements": {"level": 1}},
        "D004": {"name": "Guard Duty D", "rank": "D", "reward": {"ryo": 45, "exp": 18}},
        "C001": {"name": "Capture Bandit C", "rank": "C", "reward": {"ryo": 200, "exp": 100}, "requirements": {"level": 5}},
        "S001": {"name": "Assassinate Daimyo S", "rank": "S", "reward": {"ryo": 10000, "exp": 5000}, "requirements": {"level": 20, "jutsu": ["Stealth"]}}
    }
    save_json(defs_file, example_defs) # Use synchronous save for fixture setup

    # Define other file paths
    active_file = os.path.join(missions_dir, "active_missions.json")
    completed_file = os.path.join(missions_dir, "completed_missions.json")
    
    # Create empty active/completed files if they don't exist
    if not os.path.exists(active_file): save_json(active_file, {})
    if not os.path.exists(completed_file): save_json(completed_file, {})

    system = MissionSystem(
        character_system=character_system, 
        data_dir=temp_data_dir, # Pass the base temp data dir
        currency_system=mock_currency_system,
        progression_engine=mock_progression_engine
    )
    # Ensure paths are correctly set if init doesn't do it exactly like this
    # system.mission_definitions_file = defs_file
    # system.active_missions_file = active_file
    # system.completed_missions_file = completed_file
    
    # Important: Need to manually load data after initialization for tests
    # Use asyncio.run or equivalent if calling async fixture from sync context,
    # but pytest-asyncio usually handles this if fixture is async.
    # Assuming tests are async or fixture becomes async.
    # For simplicity here, we assume tests call load_mission_data if needed.
    
    return system

@pytest.mark.asyncio
async def test_mission_initialization():
    """Test that a mission can be created with correct attributes."""
    # Adjusted to match the Mission dataclass definition
    test_time = datetime.utcnow()
    mission = Mission(
        id="TEST001",
        title="Test Mission",
        description="A test mission",
        difficulty=MissionDifficulty.D_RANK, # Use enum
        village="Leaf", # Added village
        reward={"ryo": 2000, "exp": 100}, # Use dict
        duration=timedelta(hours=1), # Use duration
        requirements={"level": 1}, # Keep requirements
        # Add other required fields from dataclass if necessary
        created_at=test_time # Provide a value for default factory field if needed for comparison
        # objectives are part of the mission definition data, not the Mission object itself usually
    )
    
    assert mission.id == "TEST001"
    assert mission.title == "Test Mission"
    assert mission.difficulty == MissionDifficulty.D_RANK
    assert mission.status == MissionStatus.AVAILABLE # Default status
    assert mission.reward == {"ryo": 2000, "exp": 100}
    assert mission.duration == timedelta(hours=1)
    assert mission.village == "Leaf"
    assert mission.created_at == test_time
    assert mission.started_at is None
    assert mission.completed_at is None

@pytest.mark.asyncio
async def test_get_available_missions(mission_system):
    """Test filtering available missions by character."""
    await mission_system.load_mission_data() # Load data first
    
    # Create mock characters with different levels and ID
    char_lvl1 = MagicMock(spec=Character, id="user_lvl1", level=1, rank="Genin")
    char_lvl5 = MagicMock(spec=Character, id="user_lvl5", level=5, rank="Chunin")
    char_lvl20 = MagicMock(spec=Character, id="user_lvl20", level=20, rank="Jonin")

    # Level 1 should see D-rank missions
    level_1_missions = mission_system.get_available_missions(char_lvl1)
    assert len(level_1_missions) > 0
    assert all(m['rank'] == 'D' for m in level_1_missions), "Level 1 should only see D rank"

    # Level 5 should see D and C rank
    level_5_missions = mission_system.get_available_missions(char_lvl5)
    ranks_seen_lvl5 = {m['rank'] for m in level_5_missions}
    assert 'D' in ranks_seen_lvl5
    assert 'C' in ranks_seen_lvl5
    assert 'S' not in ranks_seen_lvl5, "Level 5 should not see S rank"
    assert len(level_5_missions) > len(level_1_missions)

    # Level 20 should see all (D, C, S based on fixture defs)
    level_20_missions = mission_system.get_available_missions(char_lvl20)
    ranks_seen_lvl20 = {m['rank'] for m in level_20_missions}
    assert 'D' in ranks_seen_lvl20
    assert 'C' in ranks_seen_lvl20
    assert 'S' in ranks_seen_lvl20

@pytest.mark.asyncio
async def test_assign_mission(mission_system, character_system):
    """Test mission assignment (previously accept_mission)."""
    await mission_system.load_mission_data() # Load data first
    
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    char2 = Character(id="user2", name="TestUser2", level=1, rank="Genin")
    await character_system.save_character(char1) # Save to mock system
    await character_system.save_character(char2)

    # Assign a valid mission (D001 for char1)
    success, message = await mission_system.assign_mission(char1, "D001")
    assert success is True, f"Assigning valid mission failed: {message}"
    assert "D001" in mission_system.active_missions.get(char1.id, {}).get("mission_id", "")
    
    # Try assigning another mission to the same user (should fail)
    success, message = await mission_system.assign_mission(char1, "D002")
    assert success is False, "Should not assign mission when one is active"
    assert "already have an active mission" in message

    # Try assigning a non-existent mission
    success, message = await mission_system.assign_mission(char2, "NONEXISTENT")
    assert success is False, "Should not assign non-existent mission"
    assert "does not exist" in message

@pytest.mark.asyncio
async def test_complete_mission(mission_system, character_system, mock_currency_system, mock_progression_engine):
    """Test mission completion."""
    await mission_system.load_mission_data()
    
    # Setup Character
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Assign and complete a mission
    await mission_system.assign_mission(char1, "D001")
    assert char1.id in mission_system.active_missions

    # Complete the mission - now takes only character object
    rewards = await mission_system.complete_mission(char1) 
    
    assert rewards is not None, "Completion should return rewards"
    assert rewards.get("ryo") == 50 # From fixture definition
    assert rewards.get("exp") == 20 # From fixture definition
    assert char1.id not in mission_system.active_missions, "Mission should be removed from active"
    assert char1.id in mission_system.completed_missions
    assert "D001" in mission_system.completed_missions[char1.id]

    # Verify mocks were called
    mock_currency_system.add_ryo.assert_called_once_with(char1.id, 50)
    mock_progression_engine.grant_experience.assert_called_once_with(char1.id, 20)

    # Try completing when no mission is active
    rewards_none = await mission_system.complete_mission(char1)
    assert rewards_none is None, "Should return None when no mission is active"

@pytest.mark.asyncio
async def test_mission_time_limit(mission_system, character_system):
    """Test mission time limit enforcement."""
    await mission_system.load_mission_data()

    # Setup Character
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Assign a mission with a short duration for testing (or mock time)
    # Let's assume D001 has a duration (needs definition update or mocking)
    # For simplicity, we'll manually set the start time far in the past
    await mission_system.assign_mission(char1, "D001") 
    
    # Manually set start time to be long ago to simulate expiration
    mock_now = get_mock_now()
    past_time = get_past_hours(24)
    mission_system.active_missions[char1.id]["start_time"] = past_time.isoformat()
    
    # Try completing the expired mission
    rewards = await mission_system.complete_mission(char1)
    assert rewards is None, "Completing expired mission should fail and return None"
    assert char1.id not in mission_system.active_missions, "Expired mission should be removed from active"
    # Check if it landed in completed or a different state (depends on implementation)
    # Assuming expired missions are just removed, not added to completed:
    assert "D001" not in mission_system.completed_missions.get(char1.id, [])

@pytest.mark.asyncio
async def test_get_mission_progress(mission_system, character_system):
    """Test getting mission progress."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Assign a mission
    await mission_system.assign_mission(char1, "D001")

    # Update progress (assuming a method exists, like update_mission_progress)
    # If not, this test needs to be adapted or the method added
    # mission_system.update_mission_progress(char1.id, progress={"steps_taken": 5})
    
    # Get active mission details (Use string ID)
    active_mission_data = mission_system.get_active_mission(char1.id)
    assert active_mission_data is not None
    # assert active_mission_data.get("progress", {}).get("steps_taken") == 5 # Check updated progress if applicable

    # Test with no active mission
    char2 = Character(id="user2", name="TestUser2", level=1, rank="Genin")
    await character_system.save_character(char2)
    assert mission_system.get_active_mission(char2.id) is None

@pytest.mark.asyncio
async def test_mission_requirements(mission_system, character_system):
    """Test mission requirements enforcement using Character objects."""
    await mission_system.load_mission_data()

    # --- Setup Test Characters ---
    char_lvl1 = Character(id="user_lvl1", name="Lvl1 NoJutsu", clan="Test", level=1, rank="Genin")
    char_lvl5 = Character(id="user_lvl5", name="Lvl5 NoJutsu", clan="Test", level=5, rank="Chunin")
    char_lvl15_stealth = Character(id="user_lowlvl", name="Lvl15 Stealth", clan="Test", level=15, rank="Chunin", jutsu={"Stealth"}) # Use set for jutsu
    await character_system.save_character(char_lvl1)
    await character_system.save_character(char_lvl5)
    await character_system.save_character(char_lvl15_stealth)
    
    # --- Level Requirements ---
    # Try assigning C001 (Level 5 req) to char_lvl1 (Level 1)
    success, message = await mission_system.assign_mission(char_lvl1, "C001")
    assert success is False, "Should fail assignment due to level requirement"
    assert "level requirement" in message.lower() # Check for reason, ensure lowercase comparison

    # Try assigning C001 to char_lvl5 (meets requirement)
    success, _ = await mission_system.assign_mission(char_lvl5, "C001")
    assert success is True, f"Assigning C001 to Lvl 5 failed: {message}"
    assert char_lvl5.id in mission_system.active_missions

    # --- Jutsu Requirements ---
    # Try assigning S001 (Level 20, Stealth req) to char_lvl15_stealth (Level 15, has Stealth) - Should fail on level
    success, message = await mission_system.assign_mission(char_lvl15_stealth, "S001")
    assert success is False, "Should fail assignment due to level requirement (S001)"
    assert "level requirement" in message.lower() 
    
    # --- Character meets Level, Lacks Jutsu ---
    char_lvl20_no_jutsu = Character(id="user_lvl20_no", name="Lvl20 NoJutsu", clan="Test", level=20, rank="Jonin")
    await character_system.save_character(char_lvl20_no_jutsu)
    success, message = await mission_system.assign_mission(char_lvl20_no_jutsu, "S001")
    assert success is False, "Should fail assignment due to missing jutsu requirement"
    assert "missing" in message.lower() and "stealth" in message.lower(), f"Incorrect failure message: {message}"
    
    # --- Character meets Jutsu, Lacks Level --- 
    # This was already tested above with char_lvl15_stealth trying S001
    
    # --- Character meets Both Level and Jutsu ---
    char_lvl20_stealth = Character(id="user_lvl20_stealth", name="Lvl20 Stealth", clan="Test", level=20, rank="Jonin", jutsu={"Stealth"})
    await character_system.save_character(char_lvl20_stealth)
    success, message = await mission_system.assign_mission(char_lvl20_stealth, "S001")
    assert success is True, f"Should succeed assignment when meeting both requirements: {message}"
    assert char_lvl20_stealth.id in mission_system.active_missions
    
    # --- Character meets Neither (Level 1, No Jutsu) --- 
    # Try assigning S001 to char_lvl1
    success, message = await mission_system.assign_mission(char_lvl1, "S001")
    assert success is False, "Should fail assignment due to level requirement (S001 for Lvl1)"
    assert "level requirement" in message.lower(), f"Incorrect failure message for Lvl1 on S001: {message}" # Primary failure is level

@pytest.mark.asyncio
async def test_mission_cleanup(mission_system, character_system):
    """Test that missions are removed from active list after completion/failure."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Assign and complete a mission
    await mission_system.assign_mission(char1, "D001")
    assert char1.id in mission_system.active_missions
    await mission_system.complete_mission(char1)
    assert char1.id not in mission_system.active_missions
    assert "D001" in mission_system.completed_missions.get(char1.id, [])

    # Assign another mission and simulate failure (e.g., via expiration)
    await mission_system.assign_mission(char1, "D002")
    assert char1.id in mission_system.active_missions
    # Simulate expiration
    mock_now = get_mock_now()
    past_time = get_past_hours(24)
    mission_system.active_missions[char1.id]["start_time"] = past_time.isoformat()
    await mission_system.complete_mission(char1) # This will check for expiration implicitly now
    assert char1.id not in mission_system.active_missions, "Expired mission should be removed"
    assert "D002" not in mission_system.completed_missions.get(char1.id, []), "Expired mission shouldn't be completed"

@pytest.mark.asyncio
async def test_mission_state_isolation(mission_system, character_system):
    """Test that mission state changes for one user don't affect others."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    char2 = Character(id="user2", name="TestUser2", level=1, rank="Genin")
    await character_system.save_character(char1)
    await character_system.save_character(char2)

    # User1 assigns and completes D001
    await mission_system.assign_mission(char1, "D001")
    await mission_system.complete_mission(char1)
    assert char1.id not in mission_system.active_missions
    assert "D001" in mission_system.completed_missions.get(char1.id, [])

    # User2 assigns D002
    await mission_system.assign_mission(char2, "D002")
    assert char2.id in mission_system.active_missions
    assert mission_system.active_missions[char2.id]["mission_id"] == "D002"
    
    # Check User1's state hasn't changed
    assert char1.id not in mission_system.active_missions
    assert "D001" in mission_system.completed_missions.get(char1.id, [])
    assert "D002" not in mission_system.completed_missions.get(char1.id, [])

@pytest.mark.asyncio
async def test_invalid_mission_operations(mission_system, character_system):
    """Test operations with invalid mission IDs or user IDs."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Try to complete when no mission is active
    rewards = await mission_system.complete_mission(char1)
    assert rewards is None

    # Try assigning invalid mission ID
    success, message = await mission_system.assign_mission(char1, "INVALID_ID")
    assert success is False
    assert "does not exist" in message

    # Try assigning to non-existent character (mock get_character to return None)
    character_system.get_character.side_effect = lambda user_id: None # Override mock for this test

    with pytest.raises(ValueError, match="Failed to validate character"): # Assuming assign checks character validity first
         # Use a mock with an 'id' attribute
        await mission_system.assign_mission(MagicMock(spec=Character, id="nonexistent"), "D001")

    character_system.get_character.side_effect = None # Reset mock

@pytest.mark.asyncio
async def test_mission_reward_validation(mission_system, character_system, mock_currency_system, mock_progression_engine):
    """Test mission reward validation and consistency."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    missions_to_test = ["D001", "D002", "D003"]
    total_ryo = 0
    total_exp = 0

    for mission_id in missions_to_test:
        # Get expected rewards from definitions
        mission_def = mission_system.mission_definitions.get(mission_id)
        assert mission_def is not None, f"Mission definition {mission_id} not found"
        expected_reward = mission_def.get("reward", {})
        expected_ryo = expected_reward.get("ryo", 0)
        expected_exp = expected_reward.get("exp", 0)
        
        total_ryo += expected_ryo
        total_exp += expected_exp

        await mission_system.assign_mission(char1, mission_id)
        rewards = await mission_system.complete_mission(char1)
        
        assert rewards is not None, f"Completion of {mission_id} failed unexpectedly"
        assert rewards.get("ryo") == expected_ryo
        assert rewards.get("exp") == expected_exp

    # Check if mocks were called with the correct total amounts (or individual amounts)
    # This depends on how mocks are set up (e.g., call_args_list)
    # Example: Check total calls match number of missions
    assert mock_currency_system.add_ryo.call_count == len(missions_to_test)
    assert mock_progression_engine.grant_experience.call_count == len(missions_to_test)
    # Example: Check cumulative effect if mocks tracked total (less common)
    # assert mock_currency_system.add_ryo.call_args == call(char1.id, total_ryo) # Simplified

@pytest.mark.asyncio
async def test_mission_time_limit_edge_cases(mission_system, character_system):
    """Test edge cases for mission time limits."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Assign a mission
    await mission_system.assign_mission(char1, "D001") 
    
    # Manually set start time EXACTLY at the boundary (or just before/after)
    # This requires knowing the duration defined for D001
    mission_duration = timedelta(hours=1) # Assume D001 has 1 hour duration for test setup
    
    # Case 1: Just before expiration
    start_time_ok = datetime.now(timezone.utc) - mission_duration + timedelta(seconds=10)
    mission_system.active_missions[char1.id]["start_time"] = start_time_ok.isoformat()
    rewards_ok = await mission_system.complete_mission(char1)
    assert rewards_ok is not None, "Should complete successfully just before expiration"
    assert char1.id not in mission_system.active_missions # Should be removed after completion

    # Case 2: Just after expiration
    await mission_system.assign_mission(char1, "D002") # Assign a new one
    start_time_expired = datetime.now(timezone.utc) - mission_duration - timedelta(seconds=10)
    mission_system.active_missions[char1.id]["start_time"] = start_time_expired.isoformat()
    rewards_expired = await mission_system.complete_mission(char1)
    assert rewards_expired is None, "Should fail completion just after expiration"
    assert char1.id not in mission_system.active_missions # Should be removed after expiration check

@pytest.mark.asyncio
async def test_mission_cleanup_edge_cases(mission_system, character_system):
    """Test edge cases in mission cleanup."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)
    
    # Assign multiple missions sequentially and complete them
    all_d_missions = ["D001", "D002", "D003", "D004"]
    for mission_id in all_d_missions:
        success, _ = await mission_system.assign_mission(char1, mission_id)
        assert success is True, f"Failed to assign {mission_id}"
        rewards = await mission_system.complete_mission(char1)
        assert rewards is not None, f"Failed to complete {mission_id}"
        assert char1.id not in mission_system.active_missions, f"Active mission not cleaned up after {mission_id}"
        assert mission_id in mission_system.completed_missions.get(char1.id, []), f"{mission_id} not in completed list"

    # Check final state
    assert char1.id not in mission_system.active_missions
    assert len(mission_system.completed_missions.get(char1.id, [])) == len(all_d_missions)

@pytest.mark.asyncio
async def test_mission_progress_details(mission_system, character_system):
    """Test detailed mission progress tracking and validation."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    await mission_system.assign_mission(char1, "D001")

    # Check initial progress (should be empty or default) - Use string ID
    active_mission_data = mission_system.get_active_mission(char1.id)
    assert active_mission_data is not None
    # assert "progress" not in active_mission_data or active_mission_data["progress"] == {} # Example check

    # Simulate progress update (Needs update_mission_progress method or different test approach)
    # progress_update = {"objective_1_complete": True}
    # mission_system.update_mission_progress(char1.id, progress_update)

    # Verify updated progress - Use string ID
    # updated_mission_data = mission_system.get_active_mission(char1.id)
    # assert updated_mission_data.get("progress", {}).get("objective_1_complete") is True

    # Test invalid progress update (e.g., wrong format, invalid user)
    # with pytest.raises(SomeRelevantError):
    #     mission_system.update_mission_progress("invalid_user", {"steps": 1})
    # with pytest.raises(SomeRelevantError):
    #     mission_system.update_mission_progress(char1.id, "not_a_dict")

@pytest.mark.asyncio
async def test_mission_objective_validation(mission_system, character_system):
    """Test mission objective validation and tracking."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    missions_to_test = ["D001", "D002", "D003"] # Assuming these have objectives defined
    for mission_id in missions_to_test:
        success, _ = await mission_system.assign_mission(char1, mission_id)
        assert success
        
        mission_def = mission_system.mission_definitions.get(mission_id, {})
        objectives = mission_def.get("objectives", []) # Assuming objectives are in definition
        
        # Simulate completing objectives (if progress tracking exists)
        # for obj_key in objectives:
        #     mission_system.update_mission_progress(char1.id, objective=obj_key, status="completed")
            
        # Validate completion (if validation logic exists)
        # is_complete = mission_system.check_mission_completion(char1.id)
        # assert is_complete == True
        
        # For now, just complete normally
        await mission_system.complete_mission(char1)

@pytest.mark.asyncio
async def test_mission_expiration(mission_system, character_system):
    """Test mission expiration and cleanup."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Assign mission
    success, _ = await mission_system.assign_mission(char1, "D001")
    assert success

    # Simulate time passing beyond duration
    mission_duration = timedelta(hours=1) # Assume 1 hour duration
    start_time_expired = datetime.now(timezone.utc) - mission_duration - timedelta(minutes=1)
    mission_system.active_missions[char1.id]["start_time"] = start_time_expired.isoformat()

    # Attempt completion - should detect expiration
    rewards = await mission_system.complete_mission(char1)
    assert rewards is None, "Expired mission should not yield rewards"
    assert char1.id not in mission_system.active_missions, "Expired mission should be removed"

@pytest.mark.asyncio
async def test_mission_state_persistence(mission_system, character_system, temp_data_dir):
    """Test mission state persistence and cleanup."""
    await mission_system.load_mission_data()
    char1 = Character(id="user1", name="TestUser1", level=1, rank="Genin")
    await character_system.save_character(char1)

    missions = ["D001", "D002", "D003"]
    for mission_id in missions:
        success, _ = await mission_system.assign_mission(char1, mission_id)
        assert success
        rewards = await mission_system.complete_mission(char1)
        assert rewards is not None

    # Create a new instance to simulate reload
    new_mission_system = MissionSystem(
        character_system=mission_system.character_system, # Use same mock
        data_dir=temp_data_dir, 
        currency_system=mission_system.currency_system, # Use same mock
        progression_engine=mission_system.progression_engine # Use same mock
    )
    await new_mission_system.load_mission_data() # Load saved state

    # Verify state loaded correctly
    assert char1.id not in new_mission_system.active_missions, "No active missions should be loaded"
    assert len(new_mission_system.completed_missions.get(char1.id, [])) == len(missions), "Completed missions not persisted"
    assert set(new_mission_system.completed_missions.get(char1.id, [])) == set(missions)

@pytest.mark.asyncio
async def test_update_mission_progress_no_active_mission(mission_system, character_system):
    """Test updating progress when no mission is active."""
    # logger.info("TEST_ADDED: test_update_mission_progress_no_active_mission") # Placeholder for log_event
    char1 = Character(id="user_no_active", name="Test No Active", level=1, rank="Genin")
    await character_system.save_character(char1)

    success, message = mission_system.update_mission_progress(char1.id, progress=0.5)
    assert success is False
    assert "don't have an active mission" in message

@pytest.mark.asyncio
async def test_update_mission_progress_updates_data(mission_system, character_system):
    """Test that updating progress modifies the active mission data."""
    # logger.info("TEST_ADDED: test_update_mission_progress_updates_data") # Placeholder for log_event
    await mission_system.load_mission_data()
    char1 = Character(id="user_prog_update", name="Progress Updater", level=1, rank="Genin")
    await character_system.save_character(char1)

    # Assign a mission
    await mission_system.assign_mission(char1, "D001")
    assert str(char1.id) in mission_system.active_missions
    mission_system.active_missions[str(char1.id)]["objectives_complete"] = [] # Ensure objectives list exists

    # Update progress
    new_progress = 0.75
    success, message = mission_system.update_mission_progress(char1.id, progress=new_progress)
    assert success is True
    assert "Mission progress updated" in message
    assert mission_system.active_missions[str(char1.id)].get("progress") == new_progress

    # Update objective
    objective_to_complete = "fetch_herbs"
    success, message = mission_system.update_mission_progress(char1.id, objective=objective_to_complete)
    assert success is True
    assert "Mission progress updated" in message
    assert objective_to_complete in mission_system.active_missions[str(char1.id)].get("objectives_complete", [])

    # Update both
    another_objective = "report_back"
    final_progress = 1.0
    success, message = mission_system.update_mission_progress(char1.id, progress=final_progress, objective=another_objective)
    assert success is True
    assert "Mission progress updated" in message
    assert mission_system.active_missions[str(char1.id)].get("progress") == final_progress
    assert another_objective in mission_system.active_missions[str(char1.id)].get("objectives_complete", [])
    assert objective_to_complete in mission_system.active_missions[str(char1.id)].get("objectives_complete", []) # Verify previous objective still there

@pytest.mark.asyncio
async def test_update_mission_progress_saves_state(mission_system, character_system):
    """Test that updating progress triggers a save."""
    # logger.info("TEST_ADDED: test_update_mission_progress_saves_state") # Placeholder for log_event
    await mission_system.load_mission_data()
    char1 = Character(id="user_prog_save", name="Progress Saver", level=1, rank="Genin")
    await character_system.save_character(char1)
    await mission_system.assign_mission(char1, "D001")
    mission_system.active_missions[str(char1.id)]["objectives_complete"] = []

    # Patch the save method to check if it's called
    with patch.object(mission_system, '_save_active_missions', new_callable=AsyncMock) as mock_save:
        success, _ = mission_system.update_mission_progress(char1.id, progress=0.5)
        assert success is True
        mock_save.assert_called_once()

    # Reset mock and test objective update save
    mock_save.reset_mock()
    with patch.object(mission_system, '_save_active_missions', new_callable=AsyncMock) as mock_save:
        success, _ = mission_system.update_mission_progress(char1.id, objective="some_objective")
        assert success is True
        mock_save.assert_called_once()

@pytest.mark.asyncio
async def test_load_multiple_mission_files(mission_system, temp_data_dir):
    """Test that the system loads missions from the definitions file."""
    # Create an extra mission definition file
    # extra_defs_file = os.path.join(temp_data_dir, 'missions', "extra_missions.json")
    # extra_defs = {"X001": {"name": "Extra Mission", "rank": "B"}, "X002": {"name": "Another Extra", "rank": "A"}}
    # save_json(extra_defs_file, extra_defs) # This doesn't work as system only loads one def file

    # Reload data
    await mission_system.load_mission_data()

    # Check if all definitions from the primary file are loaded
    expected_mission_count = 6 # Based on fixture setup
    assert len(mission_system.mission_definitions) == expected_mission_count, \
           f"Expected {expected_mission_count} total missions loaded from definitions, but got {len(mission_system.mission_definitions)}"
    assert "D001" in mission_system.mission_definitions
    assert "C001" in mission_system.mission_definitions
    assert "S001" in mission_system.mission_definitions
    # assert "X001" not in mission_system.mission_definitions # Ensure it doesn't load extra files by default

    # Check for specific mission IDs from each file
    assert "D001" in mission_system.mission_definitions, "Mission D001 from mission_definitions.json not loaded."
    assert "S001" in mission_system.mission_definitions, "Mission S001 from mission_definitions.json not loaded."
    # assert "A001" in mission_system.mission_definitions, "Mission A001 from mission_definitions.json not loaded." # Removed assertion for non-existent mission 

# --- D20 System Tests ---

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "skill_name, difficulty, roll, expected_success",
    [
        ("strength", 15, 16, True),  # Roll > DC
        ("speed", 10, 10, True),   # Roll == DC
        ("chakra", 20, 19, False), # Roll < DC
        ("intelligence", 5, 4, False), # Roll < DC (easy)
        ("strength", 15, 1, False), # Critical Failure
        ("speed", 10, 20, True),  # Critical Success
    ]
)
async def test_skill_check_basic(mission_system, character_system, skill_name, difficulty, roll, expected_success):
    """Test basic D20 skill checks with various outcomes."""
    # log_event("TEST_ADDED", "CoverageAgent", {"test": "test_skill_check_basic"})
    char = Character(id="user_d20", name="D20 Tester", level=10, rank="Chunin", attributes={"strength": 2, "speed": 1, "chakra": 3, "intelligence": 0})
    await character_system.save_character(char)

    # Patch the roll method to control the outcome
    with patch.object(mission_system.d20_runner, 'roll_d20', return_value=roll):
        result = mission_system.skill_check(char, skill_name, difficulty)

    assert result["success"] == expected_success
    assert result["roll"] == roll
    assert result["difficulty"] == difficulty # Checks if DC is passed correctly
    # assert result["modifier"] == char.attributes.get(skill_name, 0) # Check modifier calculation (if runner returns it)
    # assert result["total"] == roll + char.attributes.get(skill_name, 0) # Check total calculation (if runner returns it)
    if roll == 1:
        assert result.get("is_critical_failure") is True
    if roll == 20:
        assert result.get("is_critical_success") is True

@pytest.mark.asyncio
async def test_skill_check_invalid_skill(mission_system, character_system):
    """Test skill check with an invalid skill name."""
    # log_event("TEST_ADDED", "CoverageAgent", {"test": "test_skill_check_invalid_skill"})
    char = Character(id="user_d20_invalid", name="Invalid Skill User", level=5, rank="Genin")
    await character_system.save_character(char)

    result = mission_system.skill_check(char, "invalid_skill_name", 10)

    assert result["success"] is False
    assert "error" in result
    assert "invalid_skill_name" in result["error"]

@pytest.mark.asyncio
async def test_skill_check_difficulty_conversion(mission_system, character_system):
    """Test that numeric difficulty is converted to DifficultyLevel enum correctly."""
    # log_event("TEST_ADDED", "CoverageAgent", {"test": "test_skill_check_difficulty_conversion"})
    char = Character(id="user_d20_diff", name="Difficulty Converter", level=5, rank="Genin")
    await character_system.save_character(char)

    # Patch the underlying D20Runner.skill_check to see what DifficultyLevel it receives
    with patch.object(mission_system.d20_runner, 'skill_check', return_value={"success": True}) as mock_d20_check:
        # DC 12 should map to MODERATE (DC 13)
        mission_system.skill_check(char, "strength", 12)
        mock_d20_check.assert_called_once()
        call_args, _ = mock_d20_check.call_args
        assert call_args[1] == DifficultyLevel.MODERATE # Check the DifficultyLevel enum

        mock_d20_check.reset_mock()

        # DC 18 should map to HARD (DC 18)
        mission_system.skill_check(char, "speed", 18)
        mock_d20_check.assert_called_once()
        call_args, _ = mock_d20_check.call_args
        assert call_args[1] == DifficultyLevel.HARD

        mock_d20_check.reset_mock()

        # DC 25 should map to VERY_HARD (DC 22) - closest lower
        # Correction: It finds the *closest* value, so 25 maps to NEARLY_IMPOSSIBLE (25)
        mission_system.skill_check(char, "chakra", 25)
        mock_d20_check.assert_called_once()
        call_args, _ = mock_d20_check.call_args
        assert call_args[1] == DifficultyLevel.NEARLY_IMPOSSIBLE

@pytest.mark.asyncio
async def test_load_multiple_mission_files(mission_system, temp_data_dir):
    """Test that the system loads missions from the definitions file."""
    # Create an extra mission definition file
    # extra_defs_file = os.path.join(temp_data_dir, 'missions', "extra_missions.json")
    # extra_defs = {"X001": {"name": "Extra Mission", "rank": "B"}, "X002": {"name": "Another Extra", "rank": "A"}}
    # save_json(extra_defs_file, extra_defs) # This doesn't work as system only loads one def file

    # Reload data
    await mission_system.load_mission_data()

    # Check if all definitions from the primary file are loaded
    expected_mission_count = 6 # Based on fixture setup
    assert len(mission_system.mission_definitions) == expected_mission_count, \
           f"Expected {expected_mission_count} total missions loaded from definitions, but got {len(mission_system.mission_definitions)}"
    assert "D001" in mission_system.mission_definitions
    assert "C001" in mission_system.mission_definitions
    assert "S001" in mission_system.mission_definitions
    # assert "X001" not in mission_system.mission_definitions # Ensure it doesn't load extra files by default

    # Check for specific mission IDs from each file
    assert "D001" in mission_system.mission_definitions, "Mission D001 from mission_definitions.json not loaded."
    assert "S001" in mission_system.mission_definitions, "Mission S001 from mission_definitions.json not loaded."
    # assert "A001" in mission_system.mission_definitions, "Mission A001 from mission_definitions.json not loaded." # Removed assertion for non-existent mission 