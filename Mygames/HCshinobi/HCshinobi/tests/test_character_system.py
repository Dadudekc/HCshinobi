"""Tests for async character system."""
import pytest
import pytest_asyncio # Use pytest_asyncio for async fixtures
import os
import json
import aiofiles

from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem

# Keep fixture synchronous - it just sets up the object and temp dir
@pytest.fixture
def character_system_instance(tmp_path):
    """Create a character system instance pointing to a temporary directory."""
    data_dir = tmp_path / "characters"
    data_dir.mkdir()
    return CharacterSystem(str(data_dir)) # Pass the string path

@pytest.fixture
def test_character_data():
    """Return data for a test character."""
    # Use a dict for data to be saved/loaded, easier to manage
    return {
        "id": "test_user_1",
        "name": "Test Character One",
        "clan": "Test Clan",
        "level": 5,
        "exp": 150,
        "ryo": 5000,
        "hp": 150,
        "chakra": 120,
        "stamina": 110,
        "strength": 15,
        "defense": 12,
        "speed": 13,
        "ninjutsu": 20,
        "taijutsu": 18,
        "genjutsu": 5,
        "willpower": 10,
        "chakra_control": 16,
        "intelligence": 14,
        "perception": 11,
        "max_hp": 150,
        "max_chakra": 120,
        "max_stamina": 110,
        "inventory": ["kunai", "shuriken", "healing_balm"],
        "jutsu": ["fireball", "clone"],
        "equipment": {"weapon": "katana", "armor": "flak_jacket"},
        "is_active": True,
        "status_effects": [],
        "active_effects": [],
        "status_conditions": [],
        "buffs": {},
        "debuffs": {},
        "wins": 2,
        "losses": 1,
        "draws": 0,
        "completed_missions": []
    }

# === Test Core Lifecycle ===

@pytest.mark.asyncio
async def test_create_character_success(character_system_instance):
    """Test successfully creating a new character."""
    system = character_system_instance
    user_id = "new_user_123"
    name = "New Shinobi"
    clan = "Leaf"
    
    # Check doesn't exist initially
    assert not system.character_exists(user_id)
    assert system.get_character(user_id) is None
    
    character = await system.create_character(user_id, name, clan, level=2) # Add a kwarg
    
    assert character is not None
    assert character.id == user_id
    assert character.name == name
    assert character.clan == clan
    assert character.level == 2 # Check kwarg was applied
    
    # Check exists in memory now
    assert system.character_exists(user_id)
    assert system.get_character(user_id) == character
    
    # Verify file was created
    filepath = os.path.join(system.data_dir, f"{user_id}.json")
    assert os.path.exists(filepath)
    async with aiofiles.open(filepath, mode='r', encoding='utf-8') as f:
        content = await f.read()
        data = json.loads(content)
        assert data['id'] == user_id
        assert data['name'] == name
        assert data['level'] == 2

@pytest.mark.asyncio
async def test_create_character_already_exists(character_system_instance):
    """Test trying to create a character that already exists."""
    system = character_system_instance
    user_id = "existing_user"
    name = "Existing Shinobi"
    clan = "Sand"
    
    # Create first time
    char1 = await system.create_character(user_id, name, clan)
    assert char1 is not None
    assert system.character_exists(user_id)
    
    # Try to create again
    char2 = await system.create_character(user_id, "Different Name", "Different Clan")
    assert char2 is None # Should fail and return None
    
    # Verify original character is still in memory
    assert system.get_character(user_id) == char1
    assert system.get_character(user_id).name == name # Name should not have changed

@pytest.mark.asyncio
async def test_save_and_load_character(character_system_instance, test_character_data):
    """Test saving a character and then loading it back."""
    system = character_system_instance
    character = Character(**test_character_data)
    user_id = character.id
    
    # Save character
    save_success = await system.save_character(character)
    assert save_success
    
    # Clear in-memory cache to force loading from file
    system.characters.clear()
    assert not system.character_exists(user_id)
    
    # Load all characters (should load the one we saved)
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 1
    
    # Verify it's in memory now
    assert system.character_exists(user_id)
    loaded_char = system.get_character(user_id)
    
    assert loaded_char is not None
    # Compare loaded character to original data
    # Using asdict helps compare complex nested structures like lists/dicts
    from dataclasses import asdict
    assert asdict(loaded_char) == test_character_data

@pytest.mark.asyncio
async def test_get_character_by_name(character_system_instance):
    """Test retrieving a character by name."""
    system = character_system_instance
    char1 = await system.create_character("user1", "Naruto Uzumaki", "Leaf")
    char2 = await system.create_character("user2", "Sasuke Uchiha", "Leaf")
    
    assert char1 is not None and char2 is not None
    
    # Case-insensitive check
    found_char = system.get_character_by_name("naruto uzumaki")
    assert found_char is not None
    assert found_char.id == "user1"
    
    found_char_exact = system.get_character_by_name("Sasuke Uchiha")
    assert found_char_exact is not None
    assert found_char_exact.id == "user2"
    
    not_found = system.get_character_by_name("Sakura Haruno")
    assert not_found is None

@pytest.mark.asyncio
async def test_get_all_characters(character_system_instance):
    """Test getting all loaded characters."""
    system = character_system_instance
    assert not system.get_all_characters() # Should be empty initially
    
    char1 = await system.create_character("user1", "Character 1", "Test Clan")
    char2 = await system.create_character("user2", "Character 2", "Test Clan")
    
    all_chars = system.get_all_characters()
    assert len(all_chars) == 2
    assert {c.id for c in all_chars} == {"user1", "user2"}

# === Test Edge Cases & Error Handling ===

@pytest.mark.asyncio
async def test_load_from_empty_directory(character_system_instance):
    """Test loading from an empty directory."""
    system = character_system_instance
    # Directory is created empty by the fixture
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 0
    assert not system.characters # Internal cache should be empty

@pytest.mark.asyncio
async def test_load_from_nonexistent_directory(tmp_path):
    """Test loading from a directory that doesn't exist."""
    non_existent_dir = tmp_path / "nonexistent_chars"
    system = CharacterSystem(str(non_existent_dir))
    
    # Should attempt to create the directory and return empty
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 0
    assert not system.characters
    assert os.path.isdir(non_existent_dir) # Check that it created the dir

@pytest.mark.asyncio
async def test_load_with_malformed_json(character_system_instance):
    """Test loading when a file contains invalid JSON."""
    system = character_system_instance
    user_id_good = "good_user"
    user_id_bad = "bad_user"
    filepath_good = os.path.join(system.data_dir, f"{user_id_good}.json")
    filepath_bad = os.path.join(system.data_dir, f"{user_id_bad}.json")
    
    # Create a valid character file
    good_char_data = {"id": user_id_good, "name": "Good", "clan": "Test"}
    async with aiofiles.open(filepath_good, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(good_char_data))
        
    # Create a file with invalid JSON
    async with aiofiles.open(filepath_bad, mode='w', encoding='utf-8') as f:
        await f.write("this is not json{")
        
    # Load characters - should load the good one and skip the bad one
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 1
    assert loaded_list[0].id == user_id_good
    assert user_id_good in system.characters
    assert user_id_bad not in system.characters

@pytest.mark.asyncio
async def test_load_with_missing_id_field(character_system_instance):
    """Test loading a JSON file that is valid JSON but missing the 'id' field."""
    system = character_system_instance
    user_id_bad = "missing_id_user"
    filepath_bad = os.path.join(system.data_dir, f"{user_id_bad}.json")
    
    # Create a file missing the 'id' key
    bad_data = {"name": "No ID", "clan": "Test"}
    async with aiofiles.open(filepath_bad, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(bad_data))
        
    # Load characters - should skip the bad file
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 0
    assert not system.characters

@pytest.mark.asyncio
async def test_load_with_mismatched_id(character_system_instance):
    """Test loading a file where filename ID doesn't match internal 'id' field."""
    system = character_system_instance
    filename_id = "file_id_123"
    internal_id = "internal_id_ABC"
    filepath = os.path.join(system.data_dir, f"{filename_id}.json")
    
    # Create a file with mismatched id
    bad_data = {"id": internal_id, "name": "Mismatch", "clan": "Test"}
    async with aiofiles.open(filepath, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(bad_data))
        
    # Load characters - should skip the mismatched file
    loaded_list = await system.load_characters()
    assert len(loaded_list) == 0
    assert not system.characters

@pytest.mark.asyncio
async def test_get_nonexistent_character(character_system_instance):
    """Test getting a character that hasn't been loaded or created."""
    system = character_system_instance
    # Ensure cache is empty
    await system.load_characters() 
    assert system.get_character("nonexistent_user") is None

@pytest.mark.asyncio
async def test_attribute_integrity_save_load(character_system_instance, test_character_data):
    """Verify complex attributes (lists, dicts) are preserved during save/load."""
    system = character_system_instance
    original_character = Character(**test_character_data)
    
    # Save
    await system.save_character(original_character)
    
    # Clear cache and reload
    system.characters.clear()
    await system.load_characters()
    
    loaded_character = system.get_character(original_character.id)
    assert loaded_character is not None
    
    # Detailed checks for complex types
    assert loaded_character.inventory == test_character_data['inventory']
    assert loaded_character.jutsu == test_character_data['jutsu']
    assert loaded_character.equipment == test_character_data['equipment']
    assert loaded_character.status_effects == test_character_data['status_effects'] # Empty lists
    assert loaded_character.buffs == test_character_data['buffs'] # Empty dicts
    
    # Check a few simple attributes too
    assert loaded_character.level == test_character_data['level']
    assert loaded_character.name == test_character_data['name'] 