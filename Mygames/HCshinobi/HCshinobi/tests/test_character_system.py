"""Tests for async character system."""
import pytest
import pytest_asyncio
import os
import json
import aiofiles
from unittest.mock import MagicMock, AsyncMock # Import mocks
from datetime import datetime # Import datetime
import copy # For deep copying test data

from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_data import ClanData # Import dependency
from HCshinobi.core.progression_engine import ShinobiProgressionEngine # Import dependency
from HCshinobi.core.constants import CHARACTERS_SUBDIR, DATA_DIR # Import constants

# --- Mocks --- #
@pytest.fixture
def mock_clan_data():
    mock = MagicMock() 
    # Mock the get_clan_by_name method used by CharacterSystem
    mock.get_clan_by_name = MagicMock(return_value = {
        "name": "MockClan", # This name might differ from input clan name
        "stat_bonuses": {"strength": 2, "ninjutsu": 1},
        "affinity": "Fire"
    })
    # Keep get_all_clans if used elsewhere, adjust if needed
    mock.get_all_clans = MagicMock(return_value = {"MockClan": mock.get_clan_by_name.return_value})
    return mock

@pytest.fixture
def mock_progression_engine():
    mock = MagicMock(spec=ShinobiProgressionEngine)
    mock.check_achievement = AsyncMock() # Mock async methods
    mock.check_jutsu_achievements = AsyncMock()
    mock.check_stat_achievements = AsyncMock()
    return mock

# --- Test Fixture --- #
@pytest.fixture
def character_system_instance(tmp_path, mock_clan_data, mock_progression_engine):
    """Create a character system instance pointing to a temporary directory with mocks."""
    test_data_dir = tmp_path / DATA_DIR
    test_char_dir = test_data_dir / CHARACTERS_SUBDIR
    test_char_dir.mkdir(parents=True, exist_ok=True)
    
    system = CharacterSystem(
        data_dir=str(test_data_dir),
        clan_data_service=mock_clan_data,
        progression_engine=mock_progression_engine
    )
    system.progression_engine = mock_progression_engine 
    return system

@pytest.fixture
def test_character_data():
    """Return data for a test character matching the Character class."""
    # Return the same data as before, it matches the current Character class
    return {
        "id": "test_user_1",
        "name": "Test Character One",
        "clan": "Test Clan",
        "level": 5,
        "exp": 150,
        "specialization": None,
        "rank": "Genin",
        "hp": 150,
        "chakra": 120,
        "stamina": 110,
        "strength": 15,
        "speed": 13,
        "defense": 12,
        "willpower": 10,
        "chakra_control": 16,
        "intelligence": 14,
        "perception": 11,
        "stat_points": 3,
        "ninjutsu": 20,
        "taijutsu": 18,
        "genjutsu": 5,
        "accuracy": 55,
        "evasion": 60,
        "crit_chance": 0.1,
        "crit_damage": 1.75,
        "elemental_affinity": "Wind",
        "jutsu": ["fireball", "clone"],
        "equipment": {"weapon": "katana", "armor": "flak_jacket"},
        "inventory": {"kunai": 10, "shuriken": 20, "healing_balm": 2},
        "is_active": True,
        "status_effects": ["focused"],
        "active_effects": {"strength_boost": {"amount": 5, "duration": 3}},
        "status_conditions": {"poison": {"damage": 2, "duration": 5}},
        "buffs": {"speed_buff": {"value": 10, "turns": 2}},
        "debuffs": {"defense_debuff": {"value": -5, "turns": 1}},
        "wins": 2,
        "losses": 1,
        "draws": 0,
        "wins_against_rank": {"Genin": 1, "Chunin": 1},
        "achievements": {"first_win", "level_5"},
        "titles": ["Rookie"],
        "equipped_title": "Rookie",
        "completed_missions": {"mission_1", "mission_3"},
        "clan_rank": "Member",
        "clan_exp": 150,
        "clan_achievements": {"clan_join"},
        "clan_skills": {"clan_taijutsu": 2},
        "clan_jutsu_mastery": {},
        "clan_contribution_points": 50,
        "clan_role": "Member",
        "clan_joined_at": None,
        "max_hp": 150,
        "max_chakra": 120,
        "max_stamina": 110,
        "jutsu_mastery": {"fireball": {"level": 2, "gauge": 50}},
        "last_daily_claim": None,
        "active_mission_id": None,
    }

# === Test Core Lifecycle ===

@pytest.mark.asyncio
async def test_create_character_success(character_system_instance, mock_clan_data):
    """Test successfully creating a new character, including clan bonuses."""
    system = character_system_instance
    system.save_character = AsyncMock(return_value=True)
    mock_clan_data_service = system.clan_data_service 
    user_id = "new_user_123"
    name = "New Shinobi"
    input_clan_name = "MockClanInput" 
    
    mock_clan_details = {
        "name": "MockClanInternal", 
        "stat_bonuses": {"strength": 2, "ninjutsu": 1}, 
        "affinity": "Fire" # Affinity comes from here
    }
    mock_clan_data_service.get_clan_by_name.return_value = mock_clan_details
    expected_strength = 10 + mock_clan_details["stat_bonuses"]["strength"]
    expected_ninjutsu = 0 + mock_clan_details["stat_bonuses"]["ninjutsu"]
    # The code uses _determine_affinity which also calls get_clan_by_name
    # expected_affinity = mock_clan_details["affinity"] # _determine_affinity logic might differ

    # Action - create_character does not accept arbitrary kwargs like level
    character = await system.create_character(user_id, name, input_clan_name) 
    
    # Assertions
    assert character is not None
    assert character.clan == mock_clan_details["name"] 
    assert character.level == 1 # Should default to 1
    
    # Check the mock was called correctly (3 times total)
    assert mock_clan_data_service.get_clan_by_name.call_count == 3
    assert mock_clan_data_service.get_clan_by_name.call_args_list[0].args == (input_clan_name,)
    assert mock_clan_data_service.get_clan_by_name.call_args_list[1].args == (mock_clan_details["name"],) 
    assert mock_clan_data_service.get_clan_by_name.call_args_list[2].args == (mock_clan_details["name"],) 
    
    # Check final stats reflect bonuses
    assert character.strength == expected_strength
    assert character.ninjutsu == expected_ninjutsu
    assert character.speed == 10 
    # Check elemental_affinity was set (based on _determine_affinity call)
    # Assuming _determine_affinity returns the affinity from clan_details for this mock
    assert character.elemental_affinity == mock_clan_details["affinity"]

    # Verify save was called
    system.save_character.assert_called_once_with(character)

@pytest.mark.asyncio
async def test_create_character_clan_not_found(character_system_instance, mock_clan_data):
    """Test creating a character when the specified clan doesn't exist."""
    system = character_system_instance
    system.save_character = AsyncMock(return_value=True)
    mock_clan_data_service = system.clan_data_service 
    mock_clan_data_service.get_clan_by_name.return_value = None
    
    user_id = "user_no_clan"
    name = "Clanless Wonder"
    input_clan_name = "NonExistentClan"
    
    character = await system.create_character(user_id, name, input_clan_name)
    
    # Assert the clan wasn't found, and the character uses defaults
    assert character is not None
    assert character.clan is None
    assert character.strength == 10 # Default base strength
    assert character.elemental_affinity is None

    # Clan not found means _get_clan_stat_bonuses and _determine_affinity short-circuit
    mock_clan_data_service.get_clan_by_name.assert_called_once_with("NonExistentClan")
    assert mock_clan_data_service.get_clan_by_name.call_count == 1 

    # Verify save_character was called
    system.save_character.assert_called_once_with(character)

@pytest.mark.asyncio
async def test_create_character_already_exists(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test trying to create a character that already exists."""
    system = character_system_instance
    system.save_character = AsyncMock(return_value=True)
    mock_clan_data_service = system.clan_data_service 
    user_id = "existing_user"
    name = "Existing Shinobi"
    clan1 = "Sand"
    clan2 = "Mist"
    
    # --- Create Character 1 ---
    mock_clan_data_service.get_clan_by_name.return_value = {"name": clan1, "stat_bonuses": {}, "affinity": None}
    char1 = await system.create_character(user_id, name, clan1)
    assert char1 is not None
    # Check calls for first creation
    assert mock_clan_data_service.get_clan_by_name.call_count == 3
    assert system.save_character.call_count == 1
    # Reset mocks
    mock_clan_data_service.get_clan_by_name.reset_mock()
    system.save_character.reset_mock()

    # --- Try to Create Again (should return None immediately) ---
    # No need to mock save_character or get_clan_by_name again, as it should fail early
    char2 = await system.create_character(user_id, "Different Name", clan2)
    assert char2 is None 
    
    # Verify mocks were NOT called for the second attempt
    mock_clan_data_service.get_clan_by_name.assert_not_called()
    system.save_character.assert_not_called()
    
    # Verify original character is still in memory and unchanged
    in_memory_char = await system.get_character(user_id) 
    assert in_memory_char == char1 
    assert in_memory_char.name == name 

@pytest.mark.asyncio
async def test_save_and_load_character(character_system_instance, test_character_data, mock_clan_data, mock_progression_engine):
    """Test saving a character and then loading it back."""
    system = character_system_instance
    # Assume save works correctly due to serialization fix / separate tests
    original_character = Character(**test_character_data)
    user_id = original_character.id
    
    # Save character
    save_success = await system.save_character(original_character)
    assert save_success, "Character saving failed unexpectedly"
    
    # Clear in-memory cache to force loading from file
    system.characters.clear()
    assert user_id not in system.characters 
    
    # Load characters
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 1
    
    # Verify it's in memory now
    assert user_id in system.characters
    loaded_char = await system.get_character(user_id) 
    assert loaded_char is not None
    
    # Compare key attributes individually instead of full dict
    assert loaded_char.id == original_character.id
    assert loaded_char.name == original_character.name
    assert loaded_char.level == original_character.level
    assert loaded_char.strength == original_character.strength
    assert loaded_char.inventory == original_character.inventory
    assert loaded_char.jutsu == original_character.jutsu
    assert loaded_char.achievements == original_character.achievements # Sets should compare correctly
    # Optionally check a datetime field if one was set and saved
    # assert loaded_char.clan_joined_at == original_character.clan_joined_at

@pytest.mark.asyncio
async def test_get_character_by_name(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test retrieving a character by name."""
    system = character_system_instance
    system.save_character = AsyncMock(return_value=True)
    mock_clan_data_service = system.clan_data_service
    
    # --- Create Character 1 ---
    clan1 = "Leaf"
    mock_clan_data_service.get_clan_by_name.return_value = {"name": clan1, "stat_bonuses": {}, "affinity": None}
    char1 = await system.create_character("user1", "Naruto Uzumaki", clan1)
    assert mock_clan_data_service.get_clan_by_name.call_count == 3
    assert system.save_character.call_count == 1
    mock_clan_data_service.get_clan_by_name.reset_mock()
    system.save_character.reset_mock()
    
    # --- Create Character 2 ---
    clan2 = "Leaf" 
    mock_clan_data_service.get_clan_by_name.return_value = {"name": clan2, "stat_bonuses": {"speed": 1}, "affinity": "Lightning"}
    char2 = await system.create_character("user2", "Sasuke Uchiha", clan2)
    assert mock_clan_data_service.get_clan_by_name.call_count == 3
    assert system.save_character.call_count == 1
    
    assert char1 is not None and char2 is not None
    
    # --- Test Get By Name --- Remove await
    found_char = system.get_character_by_name("naruto uzumaki") 
    assert found_char is not None
    assert found_char.id == "user1"
    
    found_char_exact = system.get_character_by_name("Sasuke Uchiha") 
    assert found_char_exact is not None
    assert found_char_exact.id == "user2"
    
    not_found = system.get_character_by_name("Sakura Haruno") 
    assert not_found is None

@pytest.mark.asyncio
async def test_get_all_characters(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test getting all loaded characters."""
    system = character_system_instance
    system.save_character = AsyncMock(return_value=True)
    mock_clan_data_service = system.clan_data_service
    # Remove await
    assert not system.get_all_characters(), "Initial character list should be empty" 
    
    # --- Create Character 1 ---
    clan1 = "Test Clan A"
    mock_clan_data_service.get_clan_by_name.return_value = {"name": clan1, "stat_bonuses": {}, "affinity": None}
    char1 = await system.create_character("user1", "Character 1", clan1)
    assert mock_clan_data_service.get_clan_by_name.call_count == 3
    assert system.save_character.call_count == 1
    mock_clan_data_service.get_clan_by_name.reset_mock()
    system.save_character.reset_mock()

    # --- Create Character 2 ---
    clan2 = "Test Clan B"
    mock_clan_data_service.get_clan_by_name.return_value = {"name": clan2, "stat_bonuses": {}, "affinity": None}
    char2 = await system.create_character("user2", "Character 2", clan2)
    assert mock_clan_data_service.get_clan_by_name.call_count == 3
    assert system.save_character.call_count == 1
    
    # --- Test Get All --- Remove await
    all_chars = system.get_all_characters() 
    assert len(all_chars) == 2
    assert {c.id for c in all_chars} == {"user1", "user2"}

# === Test Edge Cases & Error Handling ===

@pytest.mark.asyncio
async def test_load_from_empty_directory(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test loading from an empty directory."""
    system = character_system_instance
    system.characters.clear() # Ensure cache is clear
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 0
    assert not system.characters

@pytest.mark.asyncio
async def test_load_from_nonexistent_directory(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test loading from a directory that doesn't exist (fixture handles creation)."""
    system = character_system_instance 
    system.characters.clear() 
    
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 0
    assert not system.characters
    assert os.path.isdir(system.character_data_dir) 

@pytest.mark.asyncio
async def test_load_with_malformed_json(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test loading when a file contains invalid JSON."""
    system = character_system_instance
    user_id_good = "good_user"
    user_id_bad = "bad_user"
    filepath_good = os.path.join(system.character_data_dir, f"{user_id_good}.json") 
    filepath_bad = os.path.join(system.character_data_dir, f"{user_id_bad}.json")
    
    # Create a valid character file (needs enough fields for Character.from_dict)
    good_char_data = {"id": user_id_good, "name": "Good", "clan": "Test", "level": 1}
    async with aiofiles.open(filepath_good, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(good_char_data))
        
    # Create a file with invalid JSON
    async with aiofiles.open(filepath_bad, mode='w', encoding='utf-8') as f:
        await f.write("this is not json{")
        
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 1
    assert loaded_list[0].id == user_id_good
    assert user_id_good in system.characters
    assert user_id_bad not in system.characters

@pytest.mark.asyncio
async def test_load_with_missing_id_field(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test loading a JSON file that is valid JSON but missing the 'id' field."""
    system = character_system_instance
    user_id_bad_filename = "missing_id_user" 
    filepath_bad = os.path.join(system.character_data_dir, f"{user_id_bad_filename}.json")
    
    # Create a file missing the 'id' key (add other required fields)
    bad_data = {"name": "No ID", "clan": "Test", "level": 1}
    async with aiofiles.open(filepath_bad, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(bad_data))
        
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 1 
    assert user_id_bad_filename in system.characters
    assert system.characters[user_id_bad_filename].id == user_id_bad_filename
    assert system.characters[user_id_bad_filename].name == "No ID"

@pytest.mark.asyncio
async def test_load_with_mismatched_id(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test loading a file where filename ID doesn't match internal 'id' field."""
    system = character_system_instance
    filename_id = "file_id_123"
    internal_id = "internal_id_ABC"
    filepath = os.path.join(system.character_data_dir, f"{filename_id}.json")
    
    # Create a file with mismatched id (add other required fields)
    bad_data = {"id": internal_id, "name": "Mismatch ID", "clan": "Test", "level": 1}
    async with aiofiles.open(filepath, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(bad_data))
        
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 1 
    assert filename_id in system.characters
    assert system.characters[filename_id].id == filename_id
    assert system.characters[filename_id].name == "Mismatch ID"

@pytest.mark.asyncio
async def test_get_nonexistent_character(character_system_instance, mock_clan_data, mock_progression_engine):
    """Test getting a character that hasn't been loaded or created."""
    system = character_system_instance
    system.characters.clear()
    await system.load_characters()
    assert await system.get_character("nonexistent_user") is None

@pytest.mark.asyncio
async def test_attribute_integrity_save_load(character_system_instance, test_character_data, mock_clan_data, mock_progression_engine):
    """Verify complex attributes are preserved during save/load."""
    system = character_system_instance
    
    # Create character using the test fixture data
    original_character = Character(**test_character_data)

    # Save character (rely on actual save & serialization fix)
    save_success = await system.save_character(original_character)
    assert save_success, "Saving failed, cannot test load integrity"

    # Clear cache and reload from file
    system.characters.clear()
    loaded_list = await system.load_characters() 
    assert len(loaded_list) > 0, "Failed to load any character from file"

    loaded_character = await system.get_character(original_character.id) 
    assert loaded_character is not None

    # Compare key attributes, especially complex ones
    assert loaded_character.inventory == original_character.inventory
    assert loaded_character.jutsu == original_character.jutsu
    # Sets might be loaded as lists due to JSON, compare as sets
    assert set(loaded_character.achievements) == original_character.achievements 
    assert set(loaded_character.completed_missions) == original_character.completed_missions
    assert loaded_character.equipment == original_character.equipment
    assert loaded_character.active_effects == original_character.active_effects
    assert loaded_character.jutsu_mastery == original_character.jutsu_mastery

@pytest.mark.asyncio
async def test_get_character_loads_from_file(character_system_instance, test_character_data, mocker, mock_clan_data, mock_progression_engine):
    """Test that get_character loads from file if not in memory."""
    system = character_system_instance
    user_id = test_character_data["id"]
    filepath = os.path.join(system.character_data_dir, f"{user_id}.json")

    # Ensure character is NOT in memory but EXISTS on disk
    system.characters.clear()
    # Prepare data for JSON dump (convert sets to lists)
    data_to_dump = copy.deepcopy(test_character_data)
    for key, value in data_to_dump.items():
        if isinstance(value, set):
            data_to_dump[key] = sorted(list(value))
            
    async with aiofiles.open(filepath, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(data_to_dump))
    
    # Mock os.path.exists used within _load_character
    mock_exists = mocker.patch("aiofiles.os.path.exists", return_value=True)
    # Mock aiofiles.open used within _load_character
    mock_open = mocker.patch("aiofiles.open")
    mock_file_handle = AsyncMock()
    # Use the json-serializable data for the mock read
    mock_file_handle.read = AsyncMock(return_value=json.dumps(data_to_dump)) 
    mock_open.return_value.__aenter__.return_value = mock_file_handle
    
    spy_load = mocker.spy(system, "_load_character")

    # Action
    loaded_char = await system.get_character(user_id)

    # Assertions
    spy_load.assert_called_once_with(user_id)
    mock_exists.assert_called_once_with(filepath)
    mock_open.assert_called_once_with(filepath, mode='r', encoding='utf-8')
    assert loaded_char is not None
    assert loaded_char.id == user_id
    assert loaded_char.name == test_character_data["name"]
    assert user_id in system.characters

@pytest.mark.asyncio
async def test_get_character_returns_none_if_not_found(character_system_instance, mocker, mock_clan_data, mock_progression_engine):
    """Test get_character returns None if not in memory and not on disk."""
    system = character_system_instance
    user_id = "non_existent_user"
    filepath = os.path.join(system.character_data_dir, f"{user_id}.json")

    system.characters.clear()
    mock_exists = mocker.patch("aiofiles.os.path.exists", return_value=False)
    spy_load = mocker.spy(system, "_load_character")

    loaded_char = await system.get_character(user_id)

    spy_load.assert_called_once_with(user_id)
    mock_exists.assert_called_once_with(filepath)
    assert loaded_char is None
    assert user_id not in system.characters

@pytest.mark.asyncio
async def test_save_character_serializes_datetime(character_system_instance, mocker, mock_clan_data, mock_progression_engine):
    """Test that save_character correctly serializes datetime objects."""
    system = character_system_instance
    user_id = "datetime_user"
    now = datetime.utcnow()
    # Use an actual field: clan_joined_at
    character = Character(id=user_id, name="DateTime Test", clan_joined_at=now)
    
    # Mock the save_json utility which _serialize_character_data is part of
    mock_save_json = mocker.patch("HCshinobi.core.character_system.save_json", return_value=True)
    
    success = await system.save_character(character)
    
    assert success
    mock_save_json.assert_called_once() 
    args, kwargs = mock_save_json.call_args
    saved_data = args[1] # Data passed to save_json
    assert "clan_joined_at" in saved_data
    # Check if the datetime was converted to ISO format string
    assert saved_data["clan_joined_at"] == now.isoformat()

@pytest.mark.asyncio
async def test_save_character_serializes_set(character_system_instance, mocker, mock_clan_data, mock_progression_engine):
    """Test that save_character correctly serializes set objects to lists."""
    system = character_system_instance
    user_id = "set_user"
    # Use an actual field: achievements
    test_set = {"ach1", "ach2"}
    character = Character(id=user_id, name="Set Test", achievements=test_set)
    
    mock_save_json = mocker.patch("HCshinobi.core.character_system.save_json", return_value=True)
    
    success = await system.save_character(character)
    
    assert success
    mock_save_json.assert_called_once()
    args, kwargs = mock_save_json.call_args
    saved_data = args[1]
    assert "achievements" in saved_data
    # Check if the set was converted to a sorted list
    assert isinstance(saved_data["achievements"], list)
    assert saved_data["achievements"] == sorted(list(test_set))

# --- Placeholder for log_event --- #
def log_event(event_type, agent_id, data):
    print(f"[TEST_LOG] Event: {event_type}, Agent: {agent_id}, Data: {data}")

# Add more tests here for:
# - Jutsu Management (add_jutsu, increase_jutsu_mastery, migrate_jutsu_data)
# - update_character_stat
# - shutdown
# - delete_character

