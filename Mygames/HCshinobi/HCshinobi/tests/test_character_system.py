"""Tests for character system."""
import pytest
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem

@pytest.fixture
def character_system(tmp_path):
    """Create a character system for testing."""
    return CharacterSystem(str(tmp_path))

@pytest.fixture
def test_character():
    """Create a test character."""
    return Character(
        id="test_user",
        name="Test Character",
        clan="Test Clan",
        level=1,
        exp=0,
        hp=100,
        chakra=100,
        stamina=100,
        strength=10,
        defense=10,
        speed=10,
        ninjutsu=10,
        willpower=10,
        max_hp=100,
        max_chakra=100,
        max_stamina=100,
        inventory=[],
        is_active=True,
        status_effects=[],
        wins=0,
        losses=0,
        draws=0
    )

@pytest.mark.asyncio
async def test_character_lifecycle(character_system):
    """Test complete character lifecycle."""
    # Create character
    character = await character_system.create_character(
        user_id="test_user",
        name="Test Character",
        clan="Test Clan"
    )
    assert character is not None
    assert character.id == "test_user"
    assert character.name == "Test Character"
    assert character.clan == "Test Clan"
    
    # Get character
    loaded = await character_system.get_character("test_user")
    assert loaded is not None
    assert loaded.id == character.id
    assert loaded.name == character.name
    assert loaded.clan == character.clan
    
    # Check exists
    assert character_system.character_exists("test_user")
    assert not character_system.character_exists("nonexistent")
    
    # Get by name
    by_name = await character_system.get_character_by_name("Test Character")
    assert by_name is not None
    assert by_name.id == character.id
    
    # Get all characters
    all_chars = await character_system.get_all_characters()
    assert len(all_chars) == 1
    assert all_chars[0].id == character.id

@pytest.mark.asyncio
async def test_load_characters(character_system):
    """Test loading characters."""
    # Create character first
    character = await character_system.create_character(
        user_id="test_user",
        name="Test Character",
        clan="Test Clan"
    )
    assert character is not None
    
    # Load characters
    loaded = await character_system.load_characters()
    assert len(loaded) == 1
    assert loaded[0].id == character.id

@pytest.mark.asyncio
async def test_save_character(character_system, test_character):
    """Test saving a character."""
    # Save character
    success = await character_system.save_character(test_character)
    assert success
    
    # Verify saved
    loaded = await character_system.get_character(test_character.id)
    assert loaded is not None
    assert loaded.id == test_character.id
    assert loaded.name == test_character.name
    assert loaded.clan == test_character.clan

@pytest.mark.asyncio
async def test_character_exists(character_system):
    """Test checking if a character exists."""
    # Create character first
    character = await character_system.create_character(
        user_id="test_user",
        name="Test Character",
        clan="Test Clan"
    )
    assert character is not None
    
    # Check exists
    assert character_system.character_exists("test_user")
    assert not character_system.character_exists("nonexistent")

@pytest.mark.asyncio
async def test_get_all_characters(character_system):
    """Test getting all characters."""
    # Create multiple characters
    characters = [
        await character_system.create_character("user1", "Character 1", "Test Clan"),
        await character_system.create_character("user2", "Character 2", "Test Clan")
    ]
    
    # Get all characters
    all_chars = await character_system.get_all_characters()
    assert len(all_chars) == 2
    assert {c.id for c in all_chars} == {"user1", "user2"} 