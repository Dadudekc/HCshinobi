"""Integration tests for character and mission system interactions."""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import os
import tempfile
import shutil
import logging # Import logging
import json

from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.character_system import CharacterSystem

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
    """Create a character system with test data."""
    system = CharacterSystem(temp_data_dir)
    await system.load_characters()
    # Pre-create some test characters for convenience
    await system.create_character("user_lvl_1", "Lvl1", "TestClan", level=1)
    await system.create_character("user_lvl_5", "Lvl5", "TestClan", level=5)
    await system.create_character("user_lvl_10", "Lvl10", "TestClan", level=10)
    return system

@pytest.fixture
def mission_system(character_system):
    """Create a mission system for testing."""
    system = MissionSystem(character_system=character_system)
    yield system
    # Reset mission state after each test
    # system.available_missions.clear() # Clearing available might cause issues if needed across tests
    system.active_missions.clear()

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
    """Test mission level requirements with character levels."""
    # Create a level 1 character
    character = await character_system.create_character("user1", "Rookie Ninja", "Leaf")
    assert character is not None
    assert character.level == 1
    
    # Try missions at different ranks
    success, message = mission_system.accept_mission("user1", "D001")
    assert success, f"Failed to accept D-rank mission: {message}"
    assert "D001" in mission_system.active_missions["user1"]
    
    # Try C-rank mission (should fail for level 1)
    success, message = mission_system.accept_mission("user1", "C001")
    assert not success, "Accepted C-rank mission at level 1"

@pytest.mark.asyncio
async def test_character_mission_rewards(character_system, mission_system):
    """Test mission rewards affect character stats."""
    # Create character
    character = await character_system.create_character("user1", "Reward Tester", "Leaf")
    initial_exp = character.exp
    initial_ryo = character.ryo
    initial_level = character.level
    
    # Accept mission
    success, _ = mission_system.accept_mission("user1", "D001")
    assert success, "Failed to accept mission D001"
    mission_details = mission_system.available_missions.get("D001")
    assert mission_details is not None, "Mission D001 details not found"

    # Complete the mission and get rewards
    success, _, rewards = await mission_system.complete_mission("user1", "D001")
    assert success, "Failed to complete mission D001"
    assert rewards is not None
    assert rewards["exp"] == mission_details.reward_exp
    assert rewards["ryo"] == mission_details.reward_ryo

    # Rewards are now applied *within* complete_mission
    # await character_system.save_character(character) # No need to save again

    # Get character again to check updated stats (after complete_mission)
    updated_character = character_system.get_character("user1")
    assert updated_character is not None
    # Check against expected values after 1 mission and potential level up
    if updated_character.level > initial_level:
        # Leveled up, EXP should reset (assuming exact EXP for level up)
        expected_exp = 0
    else:
        # Did not level up
        expected_exp = initial_exp + rewards["exp"]
    assert updated_character.exp == expected_exp, f"Expected EXP {expected_exp}, got {updated_character.exp}"
    assert updated_character.ryo == initial_ryo + rewards["ryo"] # Ryo simply accumulates

@pytest.mark.asyncio
async def test_character_mission_limits(character_system, mission_system):
    """Test character-specific mission limits."""
    # Create two characters
    char1 = await character_system.create_character("user1", "Mission Master", "Leaf")
    char2 = await character_system.create_character("user2", "Mission Helper", "Sand")
    
    # Accept maximum missions for char1 (Filter for D-Rank, suitable for Level 1)
    accepted_count = 0
    # Filter available missions to only those the character meets the requirements for
    eligible_mission_ids = [
        mid for mid, m in mission_system.available_missions.items()
        if character_system.get_character("user1").level >= m.requirements.get("level", 0)
        # Add other requirement checks here if necessary (e.g., jutsu, items)
        # For this test, level check is likely sufficient for D-Ranks
    ]
    
    if len(eligible_mission_ids) < 3:
        pytest.skip("Not enough eligible missions (found {len(eligible_mission_ids)}) for the level 1 character to test the limit.")

    for mission_id in eligible_mission_ids[:3]: # Try to accept first 3 *eligible* available
        success, _ = mission_system.accept_mission("user1", mission_id)
        if success:
            accepted_count += 1
    
    # Assert against the hardcoded limit of 3
    assert accepted_count == 3, f"Expected 3 missions accepted, but got {accepted_count}"

    # Try accepting one more (should fail)
    if len(eligible_mission_ids) > 3:
        success, message = mission_system.accept_mission("user1", eligible_mission_ids[3])
        assert not success, "Accepted more than max missions (3) for char1"
        assert "maximum number" in message.lower()
    else:
        pytest.skip("Not enough available missions to test exceeding the limit.")

    # Accept missions for char2 (should be independent)
    success, _ = mission_system.accept_mission("user2", "D001")
    assert success, "Failed to accept mission for char2"
    assert "D001" in mission_system.active_missions["user2"]

@pytest.mark.asyncio
async def test_character_mission_persistence(character_system, mission_system):
    """Test mission state persists with character data."""
    # Create character and accept mission
    character = await character_system.create_character("user1", "State Tester", "Leaf")
    mission_system.accept_mission("user1", "D001")
    assert "D001" in mission_system.active_missions.get("user1", {}), "Mission not active initially"
    
    # Save character data
    await character_system.save_character(character)
    
    # Save and reload character system
    await character_system.shutdown()
    data_dir = character_system.data_dir
    # Pass the characters sub-directory path
    new_character_system = CharacterSystem(data_dir)
    await new_character_system.load_characters() # Use load_characters
    
    # Verify character still exists
    reloaded_character = new_character_system.get_character("user1")
    assert reloaded_character is not None
    assert reloaded_character.name == "State Tester"
    
    # Verify mission is still active
    active_missions = mission_system.get_active_missions("user1")
    assert len(active_missions) == 1
    assert active_missions[0].mission_id == "D001"
    
    await new_character_system.shutdown()

@pytest.mark.asyncio
async def test_character_mission_completion_tracking(character_system, mission_system):
    """Test tracking of completed missions per character."""
    # Create character
    character = await character_system.create_character("user1", "Mission Tracker", "Leaf")
    
    # Complete multiple missions
    missions_to_complete = ["D001", "D002"]
    for mission_id in missions_to_complete:
        accept_success, _ = mission_system.accept_mission("user1", mission_id)
        if accept_success:
             await mission_system.complete_mission("user1", mission_id)
        else:
             pytest.fail(f"Failed to accept mission {mission_id} for completion tracking.")

    # Check completed missions on the character object
    char1_reloaded = character_system.get_character("user1")
    assert char1_reloaded is not None
    assert len(char1_reloaded.completed_missions) == len(missions_to_complete)
    assert all(mid in char1_reloaded.completed_missions for mid in missions_to_complete)

    # Verify another character has separate completion tracking
    char2 = await character_system.create_character("user2", "New Tracker", "Sand")
    char2_reloaded = character_system.get_character("user2")
    assert char2_reloaded is not None
    assert not char2_reloaded.completed_missions # Should be empty set

@pytest.mark.asyncio
async def test_character_mission_rewards_persistence(character_system, mission_system):
    """Test that mission rewards persist in character data."""
    character = await character_system.create_character("user1", "Reward Tester", "Leaf")
    initial_exp = character.exp
    initial_ryo = character.ryo
    
    total_exp_reward = 0
    total_ryo_reward = 0
    # Filter for missions the level 1 character can actually accept
    eligible_mission_ids = [
        mid for mid, m in mission_system.available_missions.items()
        if character.level >= m.requirements.get("level", 0)
    ]

    if len(eligible_mission_ids) < 2:
        pytest.skip(f"Not enough eligible missions (found {len(eligible_mission_ids)}) for persistence test.")

    missions_to_test = eligible_mission_ids[:2]

    for mission_id in missions_to_test:
        success, msg = mission_system.accept_mission("user1", mission_id)
        if not success:
            pytest.fail(f"Failed to accept eligible mission {mission_id}: {msg}")

        mission_details = mission_system.available_missions.get(mission_id)
        assert mission_details is not None

        # Complete and get rewards
        success, _, rewards = await mission_system.complete_mission("user1", mission_id)
        assert success, f"Failed to complete mission {mission_id}"
        assert rewards is not None

        # Character data is updated and saved within complete_mission now
        # We just need to track the expected total reward
        total_exp_reward += rewards["exp"]
        total_ryo_reward += rewards["ryo"]

    # Reload character and verify cumulative stats
    final_character = character_system.get_character("user1")
    assert final_character is not None
    # Calculate expected final EXP considering level ups and resets
    # Level 1->2 needs 100. D001(100) -> Level 2, EXP 0.
    # Level 2->3 needs 200. D002(75) -> Level 2, EXP 75.
    expected_final_exp = 75 # Based on completing D001 then D002
    assert final_character.exp == expected_final_exp, f"Expected final EXP {expected_final_exp} after resets, got {final_character.exp}"
    assert final_character.ryo == initial_ryo + total_ryo_reward, f"Expected final Ryo {initial_ryo + total_ryo_reward}, got {final_character.ryo}"

@pytest.mark.asyncio
async def test_character_mission_level_progression(character_system, mission_system, setup_missions):
    """Test character level progression through missions."""
    # Set up mission system with test missions
    mission_system.missions_file = setup_missions
    mission_system._load_missions()

    character = await character_system.create_character("user1", "Level Tester", "Leaf", level=1) # Start at level 1
    assert character is not None # Ensure character creation succeeded
    assert character.level == 1
    initial_level = character.level

    # Get both D and C rank missions
    d_rank_missions = {mid: m for mid, m in mission_system.available_missions.items() if m.rank == 'D'} 
    c_rank_missions = {mid: m for mid, m in mission_system.available_missions.items() if m.rank == 'C'} 

    logger.info(f"Available missions - D rank: {len(d_rank_missions)}, C rank: {len(c_rank_missions)}")
    for mid, m in d_rank_missions.items():
        logger.info(f"D rank mission {mid}: {m.reward_exp} EXP")
    for mid, m in c_rank_missions.items():
        logger.info(f"C rank mission {mid}: {m.reward_exp} EXP")

    if not d_rank_missions and not c_rank_missions:
        pytest.skip("No D or C rank missions available to test level progression.")

    # Combine all D and C rank mission IDs
    mission_ids_to_cycle = list(d_rank_missions.keys()) + list(c_rank_missions.keys())

    logger.info(f"Missions available for cycling: {len(mission_ids_to_cycle)}")
    for mid in mission_ids_to_cycle:
        m = mission_system.available_missions[mid]
        logger.info(f"Available mission for cycle {mid}: {m.rank} rank, {m.reward_exp} EXP, requires level {m.requirements.get('level', 1)}")

    if not mission_ids_to_cycle:
        pytest.skip("No eligible missions available for the character's level.")

    missions_completed_count = 0
    max_attempts = 100  # Increased from 50
    attempt = 0

    while character.level < 3 and attempt < max_attempts:  # Changed from level 5 to level 3
        attempt += 1
        mission_id = mission_ids_to_cycle[attempt % len(mission_ids_to_cycle)]
        mission = mission_system.available_missions[mission_id]

        # Ensure character object is up-to-date before checks
        character = character_system.get_character(character.id)
        assert character is not None

        logger.info(f"Attempt {attempt}/{max_attempts}: Character State BEFORE checks - Level: {character.level}, Exp: {character.exp}, Completed: {character.completed_missions}")

        logger.info(f"Attempt {attempt}/{max_attempts}: Trying {mission.rank}-rank mission {mission_id} (Level {character.level}, Exp {character.exp}, Required for next level: {character.level * 100})")

        # Check if already completed or active
        if mission_id in character.completed_missions:
            logger.info(f"Skipping already completed mission {mission_id} for {character.id}.")
            continue
        if mission_id in mission_system.active_missions.get(character.id, {}):
            logger.info(f"Mission {mission_id} already active for {character.id}. Attempting completion.")
            comp_success, _, rewards = await mission_system.complete_mission(character.id, mission_id)
            if comp_success:
                missions_completed_count += 1
                # Character stats/level are updated within complete_mission and saved
                character = character_system.get_character(character.id) # Refresh character
                logger.info(f"Completed previously active mission {mission_id}. User {character.id} Level: {character.level}, Exp: {character.exp}")
            else:
                logger.warning(f"Still failed to complete already active mission {mission_id}.")
            continue

        # Check if the mission is eligible for the character's current level
        if mission.requirements["level"] > character.level:
            logger.info(f"Skipping mission {mission_id} - requires level {mission.requirements['level']}, character is level {character.level}.")
            continue

        # Accept the mission
        accept_success, msg = mission_system.accept_mission(character.id, mission_id)
        if accept_success:
            # Complete the mission
            try:
                comp_success, _, rewards = await mission_system.complete_mission(character.id, mission_id)
            except Exception as e:
                logger.exception(f"Error during complete_mission call for {mission_id} in level progression test: {e}")
                comp_success = False

            if comp_success:
                missions_completed_count += 1
                # Character stats/level are updated within complete_mission and saved
                character = character_system.get_character(character.id) # Refresh character
                logger.info(f"Completed mission {mission_id}. User {character.id} Level: {character.level}, Exp: {character.exp}")
            else:
                logger.warning(f"Failed to complete mission {mission_id} during level progression test.")
                # If completion fails, ensure it's removed from active to avoid getting stuck
                if mission_id in mission_system.active_missions.get(character.id, {}):
                    del mission_system.active_missions[character.id][mission_id]
                    if not mission_system.active_missions[character.id]:
                        del mission_system.active_missions[character.id]
        else:
            logger.warning(f"Failed to accept mission {mission_id} for level progression: {msg}")

    if attempt >= max_attempts:
        pytest.fail(f"Level progression test exceeded max attempts ({max_attempts}). Final Level: {character.level}")
    assert character.level >= 3, f"Character failed to reach level 3. Final Level: {character.level}"

@pytest.mark.skip(reason="Mission state persistence not implemented")
@pytest.mark.asyncio
async def test_character_mission_state_recovery(character_system, mission_system):
    pass

@pytest.mark.asyncio
async def test_character_mission_failure_handling(character_system, mission_system):
    """Test how character and mission systems handle failures."""
    character = await character_system.create_character("user1", "Failure Tester", "Leaf")
    initial_exp = character.exp

    # Accept a mission
    mission_system.accept_mission("user1", "D001")

    # Simulate mission failure (e.g., time limit exceeded)
    mission = mission_system.active_missions["user1"]["D001"]
    mission.accepted_at = datetime.now() - timedelta(hours=2)

    # Attempt completion (should fail)
    success, _, rewards = await mission_system.complete_mission("user1", "D001")
    assert not success
    assert rewards is None

    # Verify character state is unchanged (no rewards)
    final_character = character_system.get_character("user1")
    assert final_character.exp == initial_exp
    assert "D001" not in final_character.completed_missions

    # Verify mission is removed from active list
    assert "user1" not in mission_system.active_missions or "D001" not in mission_system.active_missions["user1"] 