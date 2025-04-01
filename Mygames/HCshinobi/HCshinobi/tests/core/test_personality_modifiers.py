"""Tests for the PersonalityModifiers core service."""
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from HCshinobi.core.personality_modifiers import PersonalityModifiers
from HCshinobi.core.constants import MODIFIERS_FILE
from pathlib import Path
import json
# Correct import path for utils
from HCshinobi.utils.file_io import load_json, save_json
from HCshinobi.utils.logging import get_logger

@pytest.fixture
def mock_modifier_data():
    """Sample personality modifiers data for testing."""
    return {
        "Intelligent": {"Nara": 1.5, "Uchiha": 1.2},
        "Aggressive": {"Kaguya": 1.7, "Uchiha": 1.3}
    }

@pytest_asyncio.fixture
async def personality_modifiers_instance(tmp_path, mock_modifier_data):
    """Create a PersonalityModifiers instance with mocked dependencies and initialized."""
    modifiers_file_path = tmp_path / MODIFIERS_FILE
    modifiers_file_path.parent.mkdir(exist_ok=True)

    mock_logger = MagicMock()
    mock_save_json = AsyncMock()

    # Selective load based on path
    async def selective_load(path):
        normalized_path = Path(path).resolve()
        normalized_target = modifiers_file_path.resolve()
        if normalized_path == normalized_target:
            return mock_modifier_data
        return None # Default for other paths

    with patch('HCshinobi.core.personality_modifiers.load_json', selective_load), \
         patch('HCshinobi.core.personality_modifiers.save_json', mock_save_json), \
         patch('HCshinobi.core.personality_modifiers.get_logger', return_value=mock_logger):
        instance = PersonalityModifiers(modifiers_file_path=str(modifiers_file_path))
        await instance.initialize()
        yield (instance, mock_save_json)

# --- Tests ---
@pytest.mark.asyncio
async def test_initialization(personality_modifiers_instance):
    """Test initialization and loading."""
    instance, _ = personality_modifiers_instance # Unpack
    assert len(instance.personality_modifiers) == 2
    assert "Aggressive" in instance.personality_modifiers

@pytest.mark.asyncio
async def test_load_existing_modifiers(personality_modifiers_instance, mock_modifier_data):
    """Test loading pre-existing modifier data."""
    instance, _ = personality_modifiers_instance # Unpack
    assert instance.personality_modifiers == mock_modifier_data

@pytest.mark.asyncio
async def test_load_invalid_data(tmp_path):
    """Test loading invalid data (not a dict)."""
    modifiers_file_path = tmp_path / MODIFIERS_FILE
    modifiers_file_path.parent.mkdir(exist_ok=True)
    with open(modifiers_file_path, 'w') as f:
        json.dump(["invalid"], f) # Write list instead of dict

    mock_logger = MagicMock()
    mock_save_json = AsyncMock()
    # Mock load_json to return None for this test
    mock_load_json_invalid = AsyncMock(return_value=None)

    with patch('HCshinobi.core.personality_modifiers.load_json', mock_load_json_invalid), \
         patch('HCshinobi.core.personality_modifiers.save_json', mock_save_json), \
         patch('HCshinobi.core.personality_modifiers.get_logger', return_value=mock_logger):
        instance = PersonalityModifiers(modifiers_file_path=str(modifiers_file_path))
        await instance.initialize()
        assert len(instance.personality_modifiers) > 0 # Default should load
        # When load_json returns None, it logs INFO then creates defaults
        mock_logger.info.assert_called() # Assertion remains info
        mock_save_json.assert_called()

@pytest.mark.asyncio
async def test_get_clan_modifiers(personality_modifiers_instance):
    """Test retrieving modifiers for a specific personality."""
    instance, _ = personality_modifiers_instance # Unpack
    mods = instance.get_clan_modifiers("Intelligent") # Synchronous
    assert mods == {"Nara": 1.5, "Uchiha": 1.2}
    
    mods_none = instance.get_clan_modifiers("NonExistent") # Synchronous
    assert mods_none == {}
    
    mods_empty = instance.get_clan_modifiers("") # Synchronous
    assert mods_empty == {}

@pytest.mark.asyncio
async def test_get_all_personalities(personality_modifiers_instance):
    """Test retrieving all defined personality traits."""
    instance, _ = personality_modifiers_instance # Unpack
    personalities = instance.get_all_personalities() # Synchronous
    assert isinstance(personalities, list)
    assert len(personalities) == 2
    assert "Aggressive" in personalities
    assert "Intelligent" in personalities

@pytest.mark.asyncio
async def test_add_personality(personality_modifiers_instance):
    """Test adding a new personality trait."""
    instance, mock_save_json = personality_modifiers_instance # Unpack
    mock_save_json.reset_mock()
    initial_count = len(instance.get_all_personalities())

    new_personality = "Calm"
    new_modifiers = {"Aburame": 1.6, "Hyuga": 1.2}
    
    success = await instance.add_personality(new_personality, new_modifiers)
    assert success
    assert len(instance.get_all_personalities()) == initial_count + 1
    assert "Calm" in instance.get_all_personalities()
    assert instance.get_clan_modifiers("Calm") == new_modifiers
    mock_save_json.assert_called_once()

    # Test adding existing
    mock_save_json.reset_mock()
    success = await instance.add_personality("Aggressive", {"ClanX": 1.1})
    assert not success
    mock_save_json.assert_not_called()

    # Test adding invalid modifiers
    mock_save_json.reset_mock()
    success = await instance.add_personality("InvalidMods", {"ClanY": -0.5})
    assert not success
    mock_save_json.assert_not_called()

@pytest.mark.asyncio
async def test_update_personality(personality_modifiers_instance):
    """Test updating an existing personality trait."""
    instance, mock_save_json = personality_modifiers_instance # Unpack
    mock_save_json.reset_mock()

    updated_modifiers = {"Nara": 1.8, "Uchiha": 1.1, "NewClan": 1.0}
    
    success = await instance.update_personality("Intelligent", updated_modifiers)
    assert success
    assert instance.get_clan_modifiers("Intelligent") == updated_modifiers
    mock_save_json.assert_called_once()

    # Test updating non-existent
    mock_save_json.reset_mock()
    success = await instance.update_personality("NonExistent", {"ClanZ": 1.0})
    assert not success
    mock_save_json.assert_not_called()

    # Test updating with invalid modifiers
    mock_save_json.reset_mock()
    success = await instance.update_personality("Intelligent", {"ClanA": 0})
    assert not success
    mock_save_json.assert_not_called()

@pytest.mark.asyncio
async def test_remove_personality(personality_modifiers_instance):
    """Test removing a personality trait."""
    instance, mock_save_json = personality_modifiers_instance # Unpack
    mock_save_json.reset_mock()
    initial_count = len(instance.get_all_personalities())

    success = await instance.remove_personality("Aggressive")
    assert success
    assert len(instance.get_all_personalities()) == initial_count - 1
    assert "Aggressive" not in instance.get_all_personalities()
    mock_save_json.assert_called_once()

    # Test removing non-existent
    mock_save_json.reset_mock()
    success = await instance.remove_personality("NonExistent")
    assert not success
    mock_save_json.assert_not_called()

@pytest.mark.asyncio
async def test_get_suggested_personalities_for_clan(personality_modifiers_instance):
    """Test getting suggested personalities for a clan."""
    instance, _ = personality_modifiers_instance # Unpack
    # Using mock_modifier_data: {'Aggressive': {'Kaguya': 1.7, 'Uchiha': 1.3}, 'Intelligent': {'Nara': 1.5, 'Uchiha': 1.2}}
    suggestions_uchiha = instance.get_suggested_personalities_for_clan("Uchiha") # Synchronous

    assert "Intelligent" in suggestions_uchiha
    assert "Aggressive" in suggestions_uchiha
    assert len(suggestions_uchiha) == 2
    
    suggestions_nara = instance.get_suggested_personalities_for_clan("Nara") # Synchronous
    assert "Intelligent" in suggestions_nara
    assert len(suggestions_nara) == 1
    
    suggestions_none = instance.get_suggested_personalities_for_clan("NonExistentClan") # Synchronous
    assert len(suggestions_none) == 0 