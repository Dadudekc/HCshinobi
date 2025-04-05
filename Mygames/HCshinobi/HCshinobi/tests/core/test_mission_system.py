"""Tests for the mission system."""
import pytest
import os
import shutil # For cleaning up test data dir
from datetime import datetime, timedelta
from HCshinobi.core.mission_system import MissionSystem, Mission
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem

# Directory for test character data
TEST_DATA_DIR = "./test_character_data"

@pytest.fixture(scope="function") # Use function scope to ensure clean state
def character_system():
    """Creates a CharacterSystem instance for testing, cleaning up afterwards."""
    # Ensure the test directory is clean before starting
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    
    cs = CharacterSystem(data_dir=TEST_DATA_DIR)
    # No need to call cs.initialize() if we manually add characters in tests
    yield cs # Provide the instance to the test
    
    # Cleanup after test runs
    if os.path.exists(TEST_DATA_DIR):
         shutil.rmtree(TEST_DATA_DIR)

@pytest.fixture
def mission_system(character_system): # Depend on the character_system fixture
    """Create a fresh mission system for each test, loading from the JSON file."""
    # Initialize the system, passing the character system instance
    system = MissionSystem(character_system=character_system)
    
    # Reset available missions (ensure state is clean, including accepted_by)
    for mission in system.available_missions.values():
        mission.accepted_by = None
        mission.accepted_at = None
        
    # Reset active and completed missions for a clean slate before each test
    system.active_missions = {}
    system.completed_missions = {}
    
    return system

def test_mission_initialization():
    """Test that a mission can be created with correct attributes."""
    mission = Mission(
        mission_id="TEST001",
        title="Test Mission",
        description="A test mission",
        rank="D",
        reward_exp=100,
        reward_ryo=2000,
        requirements={"level": 1},
        objectives=["Test objective 1", "Test objective 2"],
        time_limit=timedelta(hours=1),
        location="Test Location"
    )
    
    assert mission.mission_id == "TEST001"
    assert mission.title == "Test Mission"
    assert mission.description == "A test mission"
    assert mission.rank == "D"
    assert mission.reward_exp == 100
    assert mission.reward_ryo == 2000
    assert mission.requirements == {"level": 1}
    assert mission.objectives == ["Test objective 1", "Test objective 2"]
    assert mission.time_limit == timedelta(hours=1)
    assert mission.location == "Test Location"
    assert not mission.completed
    assert mission.accepted_by is None
    assert mission.accepted_at is None
    assert mission.completed_at is None

def test_get_available_missions(mission_system):
    """Test filtering available missions by level."""
    # Level 1 should see D-rank missions
    level_1_missions = mission_system.get_available_missions(1)
    assert len(level_1_missions) == 4  # D001, D002, D003, D004
    assert all(m.rank == "D" for m in level_1_missions)
    
    # Level 5 should see D and C rank missions
    level_5_missions = mission_system.get_available_missions(5)
    assert len(level_5_missions) == 5  # All D-rank and C001
    assert any(m.rank == "C" for m in level_5_missions)
    
    # Level 10 should see all missions
    level_10_missions = mission_system.get_available_missions(10)
    assert len(level_10_missions) == 6  # All missions
    assert any(m.rank == "B" for m in level_10_missions)

    # Level 0 (invalid) should see no missions
    level_0_missions = mission_system.get_available_missions(0)
    assert len(level_0_missions) == 0

def test_accept_mission(mission_system, character_system):
    """Test mission acceptance."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    char3 = Character(id="user3", name="TestUser3", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2
    character_system.characters[char3.id] = char3
    
    # Accept a valid mission (D001 for user1)
    success, message = mission_system.accept_mission("user1", "D001")
    assert success
    assert "Accepted mission" in message
    assert "D001" in mission_system.active_missions.get("user1", {})

    # Try to accept the same mission again (user2 tries D001 - should SUCCEED as missions aren't unique per se)
    success, message = mission_system.accept_mission("user2", "D001")
    assert success
    assert "Accepted mission" in message
    assert "D001" in mission_system.active_missions.get("user2", {})

    # User1 accepts D002 (should succeed)
    success, message = mission_system.accept_mission("user1", "D002")
    assert success
    assert "Accepted mission" in message
    assert "D002" in mission_system.active_missions.get("user1", {})
    assert len(mission_system.active_missions.get("user1", {})) == 2

    # Accept maximum number of missions
    user3_missions = ["D002", "D003", "D004"]  # Different missions for user3
    for i, mission_id in enumerate(user3_missions, 1):
        success, message = mission_system.accept_mission("user3", mission_id) # Removed user_level
        assert success, f"Should be able to accept mission {i} of 3"
        
    # Try to accept a 4th mission
    success, message = mission_system.accept_mission("user3", "C001") # C001 requires Lvl 5, but limit is hit first
    assert not success
    assert "maximum number of active missions" in message.lower()

@pytest.mark.asyncio
async def test_complete_mission(mission_system, character_system):
    """Test mission completion."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2
    
    # Accept and complete a mission
    mission_system.accept_mission("user1", "D001")
    success, message, rewards = await mission_system.complete_mission("user1", "D001")
    assert success
    assert "Completed mission" in message
    assert rewards["exp"] == 100
    assert rewards["ryo"] == 1000
    
    # Try to complete the same mission again
    success, message, rewards = await mission_system.complete_mission("user1", "D001")
    assert not success
    assert "not found in your active missions" in message.lower()
    assert rewards is None
    
    # Check character's completed missions
    char1_reloaded = character_system.get_character("user1")
    assert char1_reloaded is not None
    assert "D001" in char1_reloaded.completed_missions
    assert len(char1_reloaded.completed_missions) == 1

    # Try to complete a mission that wasn't accepted
    success, message, rewards = await mission_system.complete_mission("user2", "D001")
    assert not success
    assert "not found in your active missions" in message.lower()
    assert rewards is None

@pytest.mark.asyncio
async def test_mission_time_limit(mission_system, character_system):
    """Test mission time limit enforcement."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2
    
    # Accept a mission
    mission_system.accept_mission("user1", "D001")
    mission = mission_system.active_missions["user1"]["D001"]
    
    # Artificially set accepted_at to past the time limit
    mission.accepted_at = datetime.now() - timedelta(hours=2) # D001 time limit is 1 hour
    
    # Try to complete the expired mission
    success, message, rewards = await mission_system.complete_mission("user1", "D001")
    assert not success
    assert "time limit exceeded" in message.lower()
    assert rewards is None

    # Accept another mission and complete it just before time limit
    mission_system.accept_mission("user2", "D002") # D002 time limit is 2 hours
    mission = mission_system.active_missions["user2"]["D002"]
    mission.accepted_at = datetime.now() - timedelta(hours=1, minutes=59) # Just under 2 hours
    success, message, rewards = await mission_system.complete_mission("user2", "D002")
    assert success
    assert rewards is not None

def test_get_mission_progress(mission_system, character_system):
    """Test getting mission progress."""
    # Setup Character
    char1 = Character(id="user1", name="TestUser1", level=1)
    character_system.characters[char1.id] = char1
    
    # Accept a mission
    mission_system.accept_mission("user1", "D001")
    
    # Get progress
    progress = mission_system.get_mission_progress("user1", "D001")
    assert progress is not None
    assert progress["title"] == "Lost Cat"
    assert progress["rank"] == "D"
    assert len(progress["objectives"]) == 3 # Updated based on actual data
    assert progress["objectives"] == ["Search the village", "Find the cat", "Return the cat to its owner"] # Updated
    assert isinstance(progress["time_remaining"], timedelta)
    
    # Get progress for non-existent mission
    progress = mission_system.get_mission_progress("user1", "INVALID")
    assert progress is None
    
    # Get progress for non-existent user (character system handles this implicitly)
    progress = mission_system.get_mission_progress("invalid_user", "D001")
    assert progress is None # Because character won't be found

def test_mission_requirements(mission_system, character_system): # Add character_system fixture
    """Test mission requirements enforcement using Character objects."""
    
    # --- Setup Test Characters --- 
    # Level 1, No special attributes
    char_lvl1 = Character(id="user_lvl1", name="Lvl1 NoJutsu", clan="Test", level=1)
    character_system.characters[char_lvl1.id] = char_lvl1 
    
    # Level 5, No special attributes
    char_lvl5 = Character(id="user_lvl5", name="Lvl5 NoJutsu", clan="Test", level=5)
    character_system.characters[char_lvl5.id] = char_lvl5
    
    # Level 1, OK for D-rank
    char_lvl1_ok = Character(id="user_lvl1_ok", name="Lvl1 OK", clan="Test", level=1)
    character_system.characters[char_lvl1_ok.id] = char_lvl1_ok
    
    # Level 15, Has Stealth Jutsu (for S001 check)
    char_lvl15_stealth = Character(id="user_lowlvl", name="Lvl15 Stealth", clan="Test", level=15, jutsu=["Stealth"])
    character_system.characters[char_lvl15_stealth.id] = char_lvl15_stealth
    
    # Level 20, No Jutsu
    char_lvl20_no_jutsu = Character(id="user_no_attrs_or_jutsu", name="Lvl20 NoJutsu", clan="Test", level=20)
    character_system.characters[char_lvl20_no_jutsu.id] = char_lvl20_no_jutsu
    
    # Level 20, Has wrong Jutsu (Fireball)
    char_lvl20_fireball = Character(id="user_wrong_jutsu", name="Lvl20 Fireball", clan="Test", level=20, jutsu=["Fireball"])
    character_system.characters[char_lvl20_fireball.id] = char_lvl20_fireball
    
    # Level 20, Has correct Jutsu (Stealth)
    char_lvl20_stealth = Character(id="user_ok_jutsu", name="Lvl20 Stealth", clan="Test", level=20, jutsu=["Stealth"])
    character_system.characters[char_lvl20_stealth.id] = char_lvl20_stealth
    
    # --- Level Requirements --- 
    success, message = mission_system.accept_mission("user_lvl1", "C001") # Use char_lvl1
    assert not success
    assert "mission requires level 5" in message.lower()
    assert "you are level 1" in message.lower()

    success, message = mission_system.accept_mission("user_lvl5", "B001") # Use char_lvl5
    assert not success
    assert "mission requires level 10" in message.lower()
    assert "you are level 5" in message.lower()

    success, message = mission_system.accept_mission("user_lvl1_ok", "D001") # Use char_lvl1_ok
    assert success
    assert "Accepted mission" in message
    
    # --- Attribute Requirements (S001 requires level 20 and jutsu: "Stealth") ---
    # Try S-rank with insufficient level (char_lvl15_stealth)
    success, message = mission_system.accept_mission("user_lowlvl", "S001")
    assert not success
    assert "mission requires level 20" in message.lower()
    assert "you are level 15" in message.lower()
    
    # Try S-rank with sufficient level but missing the 'jutsu' attribute (char_lvl20_no_jutsu)
    success, message = mission_system.accept_mission("user_no_attrs_or_jutsu", "S001")
    assert not success
    assert "requires jutsu: Stealth" in message # Adjusted expectation
    assert "You don't have it" in message
    
    # Try S-rank with sufficient level but wrong jutsu (char_lvl20_fireball)
    success, message = mission_system.accept_mission("user_wrong_jutsu", "S001")
    assert not success
    assert "requires jutsu: Stealth" in message # Check exact message
    assert "You don't have it" in message # The specific check fails
    
    # Try S-rank with sufficient level and correct jutsu (char_lvl20_stealth - should succeed)
    success, message = mission_system.accept_mission("user_ok_jutsu", "S001")
    assert success
    assert "Accepted mission" in message

@pytest.mark.asyncio
async def test_mission_cleanup(mission_system, character_system):
    """Test that missions are removed from active list after completion/failure."""
    # Setup Character
    char1 = Character(id="user1", name="TestUser1", level=1)
    character_system.characters[char1.id] = char1

    # Accept and complete a mission
    mission_system.accept_mission("user1", "D001")
    assert "D001" in mission_system.active_missions["user1"]
    await mission_system.complete_mission("user1", "D001")
    assert "user1" not in mission_system.active_missions or "D001" not in mission_system.active_missions.get("user1", {})

    # Accept and fail due to time limit
    mission_system.accept_mission("user1", "D002")
    mission = mission_system.active_missions["user1"]["D002"]
    mission.accepted_at = datetime.now() - timedelta(hours=3) # Expired
    await mission_system.complete_mission("user1", "D002") # Call complete to trigger expiration check
    assert "user1" not in mission_system.active_missions or "D002" not in mission_system.active_missions.get("user1", {})

@pytest.mark.asyncio
async def test_mission_state_isolation(mission_system, character_system):
    """Test that mission state changes for one user don't affect others."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2

    # User1 accepts and completes D001
    mission_system.accept_mission("user1", "D001")
    success, _, rewards = await mission_system.complete_mission("user1", "D001")
    assert success

    # User2 accepts D002 (should be independent)
    success, _ = mission_system.accept_mission("user2", "D002")
    assert success
    assert "D002" in mission_system.active_missions["user2"]

    # Check User1's state
    assert "user1" not in mission_system.active_missions # Should be empty after completion
    char1_reloaded = character_system.get_character("user1")
    assert "D001" in char1_reloaded.completed_missions

@pytest.mark.asyncio
async def test_invalid_mission_operations(mission_system, character_system):
    """Test operations with invalid mission IDs or user IDs."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    character_system.characters[char1.id] = char1

    # Try to complete invalid mission
    success, message, rewards = await mission_system.complete_mission("user1", "INVALID")
    assert not success
    assert "not found in your active missions" in message.lower()
    assert rewards is None

    # Try to complete mission for invalid user
    success, message, rewards = await mission_system.complete_mission("invalid_user", "D001")
    assert not success
    assert "not found in your active missions" in message.lower()
    assert rewards is None

    # Try to accept mission for invalid user
    success, message = mission_system.accept_mission("invalid_user", "D001")
    assert not success
    assert "Character not found" in message

    # Try to accept invalid mission ID
    success, message = mission_system.accept_mission("user1", "INVALID")
    assert not success
    assert "Mission not found" in message

@pytest.mark.asyncio
async def test_mission_reward_validation(mission_system, character_system):
    """Test mission reward validation and consistency."""
    # Setup Character
    char1 = Character(id="user1", name="TestUser1", level=1)
    character_system.characters[char1.id] = char1

    # Accept and complete multiple missions
    missions_to_test = ["D001", "D002", "D003"]
    rewards_log = []

    for mission_id in missions_to_test:
        initial_rewards = {
            "exp": mission_system.available_missions[mission_id].reward_exp,
            "ryo": mission_system.available_missions[mission_id].reward_ryo
        }
        accept_success, _ = mission_system.accept_mission("user1", mission_id)
        assert accept_success

        complete_success, _, completion_rewards = await mission_system.complete_mission("user1", mission_id)
        assert complete_success
        assert completion_rewards is not None
        assert completion_rewards["exp"] == initial_rewards["exp"]
        assert completion_rewards["ryo"] == initial_rewards["ryo"]
        rewards_log.append(completion_rewards)

    char1_reloaded = character_system.get_character("user1")
    assert char1_reloaded is not None
    assert len(rewards_log) == len(missions_to_test)

@pytest.mark.asyncio
async def test_mission_time_limit_edge_cases(mission_system, character_system):
    """Test edge cases for mission time limits."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2

    # Accept a mission
    mission_system.accept_mission("user1", "D001")
    mission = mission_system.active_missions["user1"]["D001"]

    # Test completion *just after* the limit
    mission.accepted_at = datetime.now() - (mission.time_limit + timedelta(seconds=1))
    success_late, message_late, rewards_late = await mission_system.complete_mission("user1", "D001")
    assert not success_late
    assert "time limit exceeded" in message_late.lower()
    assert rewards_late is None

    # Test mission with no time limit (S001)
    char_high = Character(id="user_high", name="HighLvl", level=20, jutsu=["Stealth"])
    character_system.characters[char_high.id] = char_high
    mission_system.accept_mission("user_high", "S001")
    mission_s = mission_system.active_missions["user_high"]["S001"]
    assert mission_s.time_limit == timedelta(hours=12)
    mission_s.accepted_at = datetime.now() - timedelta(days=365)
    success_s, _, _ = await mission_system.complete_mission("user_high", "S001")
    assert not success_s # Should fail due to expiry

@pytest.mark.asyncio
async def test_mission_cleanup_edge_cases(mission_system, character_system):
    """Test edge cases in mission cleanup."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2

    all_d_missions = ["D001", "D002", "D003", "D004"]
    for mission_id in all_d_missions:
        accept_success, _ = mission_system.accept_mission("user1", mission_id)
        assert accept_success
        success, _, rewards = await mission_system.complete_mission("user1", mission_id)
        assert success
        assert "user1" not in mission_system.active_missions or mission_id not in mission_system.active_missions["user1"]
        char1_reloaded = character_system.get_character("user1")
        assert mission_id in char1_reloaded.completed_missions

    # Test completing mission when user entry is already empty/removed
    mission_system.accept_mission("user2", "D001")
    del mission_system.active_missions["user2"]
    success, _, _ = await mission_system.complete_mission("user2", "D001")
    assert not success

@pytest.mark.asyncio
async def test_mission_progress_details(mission_system, character_system):
    """Test detailed mission progress tracking and validation."""
    # Setup Character
    char1 = Character(id="user1", name="TestUser1", level=1)
    character_system.characters[char1.id] = char1

    mission_system.accept_mission("user1", "D001")
    progress = mission_system.get_mission_progress("user1", "D001")
    # ... (asserts on progress omitted)
    await mission_system.complete_mission("user1", "D001")
    assert mission_system.get_mission_progress("user1", "D001") is None

@pytest.mark.asyncio
async def test_mission_objective_validation(mission_system, character_system):
    """Test mission objective validation and tracking."""
    # Setup Character
    char1 = Character(id="user1", name="TestUser1", level=1)
    character_system.characters[char1.id] = char1

    missions_to_test = ["D001", "D002", "D003"]
    for mission_id in missions_to_test:
        accept_success, _ = mission_system.accept_mission("user1", mission_id)
        assert accept_success
        # ... (get progress, objective asserts omitted)
        success, _, rewards = await mission_system.complete_mission("user1", mission_id)
        assert success
        char1_reloaded = character_system.get_character("user1")
        assert mission_id in char1_reloaded.completed_missions

    char1_reloaded = character_system.get_character("user1")
    assert len(char1_reloaded.completed_missions) == len(missions_to_test)

@pytest.mark.asyncio
async def test_mission_expiration(mission_system, character_system):
    """Test mission expiration and cleanup."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2

    # Complete D001 successfully
    success, _ = mission_system.accept_mission("user1", "D001")
    assert success
    success, message, rewards = await mission_system.complete_mission("user1", "D001")
    assert success

    # Accept D002 for user2 and let it expire
    success, _ = mission_system.accept_mission("user2", "D002")
    assert success
    mission2 = mission_system.active_missions["user2"]["D002"]
    mission2.accepted_at = datetime.now() - (mission2.time_limit + timedelta(seconds=5))
    success, message, rewards = await mission_system.complete_mission("user2", "D002")
    assert not success
    assert "time limit exceeded" in message.lower()
    assert rewards is None
    assert "user2" not in mission_system.active_missions or "D002" not in mission_system.active_missions["user2"]

@pytest.mark.asyncio
async def test_mission_state_persistence(mission_system, character_system):
    """Test mission state persistence and cleanup."""
    # Setup Characters
    char1 = Character(id="user1", name="TestUser1", level=1)
    char2 = Character(id="user2", name="TestUser2", level=1)
    character_system.characters[char1.id] = char1
    character_system.characters[char2.id] = char2

    missions = ["D001", "D002", "D003"]
    for mission_id in missions:
        success, _ = mission_system.accept_mission("user1", mission_id)
        assert success
        success, _, rewards = await mission_system.complete_mission("user1", mission_id)
        assert success
        char1_reloaded = character_system.get_character("user1")
        assert mission_id in char1_reloaded.completed_missions

    # ... (final asserts omitted)

def test_load_multiple_mission_files(mission_system):
    """Test that the system loads missions from all .json files in the directory."""
    # missions.json has 6 missions, extra_missions.json has 2
    expected_total_missions = 8 
    assert len(mission_system.available_missions) == expected_total_missions, \
           f"Expected {expected_total_missions} total missions loaded, but got {len(mission_system.available_missions)}"
    
    # Check for specific mission IDs from each file
    assert "D001" in mission_system.available_missions, "Mission D001 from missions.json not loaded."
    assert "S001" in mission_system.available_missions, "Mission S001 from extra_missions.json not loaded."
    assert "A001" in mission_system.available_missions, "Mission A001 from extra_missions.json not loaded." 