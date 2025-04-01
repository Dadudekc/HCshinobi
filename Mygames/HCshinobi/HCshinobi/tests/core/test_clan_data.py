"""Tests for the ClanData core service."""
import pytest
from unittest.mock import patch, AsyncMock
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.constants import RarityTier, CLAN_FILE
from HCshinobi.utils.file_io import load_json, save_json
from HCshinobi.utils.logging import get_logger
from unittest.mock import MagicMock
import json
from pathlib import Path
import pytest_asyncio

@pytest.fixture
def mock_logger():
    return MagicMock()

@pytest.fixture
def mock_clan_data_content():
    # Add more fields to match default structure better
    return [
        {
            "name": "TestClan1",
            "rarity": "Common",
            "base_weight": 10.0,
            "lore": "Original lore for TestClan1",
            "suggested_personalities": [],
            "strength_bonus": 1,
            "defense_bonus": 1,
            "speed_bonus": 1,
            "starting_jutsu": []
        },
        {
            "name": "TestClan2",
            "rarity": "Uncommon",
            "base_weight": 5.0,
            "lore": "Original lore for TestClan2",
            "suggested_personalities": [],
            "strength_bonus": 2,
            "defense_bonus": 2,
            "speed_bonus": 2,
            "starting_jutsu": []
        }
    ]

@pytest_asyncio.fixture
async def clan_data_instance(tmp_path, mock_clan_data_content):
    """Create a ClanData instance with mocked dependencies, ensuring it's initialized."""
    data_dir = str(tmp_path)
    clan_file_path = tmp_path / "clans" / CLAN_FILE
    clan_file_path.parent.mkdir(exist_ok=True)
    
    # Mock logger and file IO directly
    mock_logger = MagicMock()
    mock_save_json = AsyncMock()

    # Selective load based on path
    async def selective_load(path):
        normalized_path = Path(path).resolve()
        normalized_target = clan_file_path.resolve()
        if normalized_path == normalized_target:
             return mock_clan_data_content
        return None # Default behavior for other paths

    # Patch dependencies
    with patch('HCshinobi.core.clan_data.load_json', selective_load), \
         patch('HCshinobi.core.clan_data.save_json', mock_save_json), \
         patch('HCshinobi.core.clan_data.get_logger', return_value=mock_logger):
        # Initialize ClanData with the temp data directory
        instance = ClanData(data_dir=str(tmp_path))
        # Await the initialization which loads data
        await instance.initialize()
        # Return instance and the mock for save assertions
        yield (instance, mock_save_json) # Use yield if cleanup is needed later

# --- Tests ---
@pytest.mark.asyncio
async def test_initialization(clan_data_instance):
    """Test initialization and loading."""
    instance, _ = clan_data_instance # Unpack
    assert len(instance.clans) == 2
    assert instance.clans[0]['name'] == "TestClan1"

@pytest.mark.asyncio
async def test_load_existing_clans(clan_data_instance, mock_clan_data_content):
    """Test loading pre-existing clan data."""
    instance, _ = clan_data_instance # Unpack
    # The fixture already loads the data via initialize()
    assert instance.clans == mock_clan_data_content

@pytest.mark.asyncio
async def test_load_invalid_data(tmp_path):
    """Test loading invalid data (not a list)."""
    data_dir = str(tmp_path)
    clan_file_path = tmp_path / "clans" / CLAN_FILE
    clan_file_path.parent.mkdir(exist_ok=True)
    # Write invalid data (a dictionary instead of a list)
    with open(clan_file_path, 'w') as f:
        json.dump({"invalid": "data"}, f)
        
    mock_logger = MagicMock()
    mock_save_json = AsyncMock()
    # Mock load_json for this test to return None, simulating load failure
    mock_load_json_invalid = AsyncMock(return_value=None)

    with patch('HCshinobi.core.clan_data.load_json', mock_load_json_invalid), \
         patch('HCshinobi.core.clan_data.save_json', mock_save_json), \
         patch('HCshinobi.core.clan_data.get_logger', return_value=mock_logger):
        instance = ClanData(data_dir=data_dir)
        await instance.initialize()
        assert len(instance.clans) > 0 # Default clans should be created
        # When load_json returns None, it logs an ERROR then creates defaults
        mock_logger.error.assert_called() # Corrected assertion
        mock_save_json.assert_called()

@pytest.mark.asyncio
async def test_get_all_clans(clan_data_instance, mock_clan_data_content):
    """Test retrieving all clans."""
    instance, _ = clan_data_instance # Unpack
    clans = instance.get_all_clans() # This method is synchronous
    assert clans == mock_clan_data_content

@pytest.mark.asyncio
async def test_get_clan_by_name(clan_data_instance, mock_clan_data_content):
    """Test retrieving a clan by name."""
    instance, _ = clan_data_instance # Unpack
    clan = instance.get_clan_by_name("TestClan1") # Synchronous
    assert clan == mock_clan_data_content[0]
    
    clan_none = instance.get_clan_by_name("NonExistent") # Synchronous
    assert clan_none is None

@pytest.mark.asyncio
async def test_get_clans_by_rarity(clan_data_instance):
    """Test retrieving clans by rarity."""
    instance, _ = clan_data_instance # Unpack
    common_clans = instance.get_clans_by_rarity(RarityTier.COMMON) # Synchronous
    assert len(common_clans) == 1
    assert common_clans[0]['name'] == "TestClan1"
    
    uncommon_clans = instance.get_clans_by_rarity(RarityTier.UNCOMMON) # Synchronous
    assert len(uncommon_clans) == 1
    assert uncommon_clans[0]['name'] == "TestClan2"
    
    rare_clans = instance.get_clans_by_rarity(RarityTier.RARE) # Synchronous
    assert len(rare_clans) == 0

@pytest.mark.asyncio
async def test_add_clan(clan_data_instance):
    """Test adding a new clan."""
    instance, mock_save_json = clan_data_instance # Unpack
    initial_count = len(instance.clans)
    mock_save_json.reset_mock() # Reset mock before action under test

    new_clan = {
        "name": "NewClan",
        "rarity": RarityTier.EPIC.value,
        "lore": "A new test clan",
        "base_weight": 7.5,
        # Adding required fields if ClanData validates them internally now
        "suggested_personalities": [],
        "strength_bonus": 1,
        "defense_bonus": 1,
        "speed_bonus": 1,
        "starting_jutsu": []
    }

    # Use the instance method which should handle saving via mocked save_json
    success = await instance.add_clan(new_clan)
    assert success
    assert len(instance.clans) == initial_count + 1
    assert instance.clans[-1]['name'] == "NewClan"
    # Assert save was called using the yielded mock
    mock_save_json.assert_called_once()

    # Test duplicate clan
    mock_save_json.reset_mock()
    success = await instance.add_clan(new_clan)
    assert not success
    mock_save_json.assert_not_called() # Save shouldn't be called for duplicates

    # Test invalid rarity (add_clan should validate)
    mock_save_json.reset_mock()
    invalid_clan = new_clan.copy()
    invalid_clan['name'] = "InvalidClan"
    invalid_clan['rarity'] = "InvalidRarity"
    success = await instance.add_clan(invalid_clan)
    assert not success
    mock_save_json.assert_not_called()

    # Test missing required field (add_clan should validate)
    # Assuming 'name' and 'rarity' are the minimal required fields for the add_clan check itself
    mock_save_json.reset_mock()
    incomplete_clan = {
        "name": "IncompleteClan",
        # Missing rarity
    }
    success = await instance.add_clan(incomplete_clan)
    assert not success
    mock_save_json.assert_not_called()

@pytest.mark.asyncio
async def test_update_clan(clan_data_instance):
    """Test updating an existing clan."""
    instance, mock_save_json = clan_data_instance # Unpack
    mock_save_json.reset_mock() # Reset before action

    # Test successful update
    update_data = {
        "lore": "Updated lore",
        "base_weight": 15.0
    }
    success = await instance.update_clan("TestClan1", update_data)
    assert success
    updated_clan = instance.get_clan_by_name("TestClan1")
    assert updated_clan['lore'] == "Updated lore"
    assert updated_clan['base_weight'] == 15.0
    mock_save_json.assert_called_once() # Check save occurred

    # Test non-existent clan
    mock_save_json.reset_mock()
    success = await instance.update_clan("NonExistentClan", update_data)
    assert not success
    mock_save_json.assert_not_called()

    # Test invalid rarity update (update_clan should validate)
    mock_save_json.reset_mock()
    invalid_update = {"rarity": "InvalidRarity"}
    success = await instance.update_clan("TestClan1", invalid_update)
    assert not success
    mock_save_json.assert_not_called()

    # Test empty name update (update_clan should validate)
    mock_save_json.reset_mock()
    invalid_update = {"name": ""}
    success = await instance.update_clan("TestClan1", invalid_update)
    assert not success
    mock_save_json.assert_not_called()

@pytest.mark.asyncio
async def test_get_clan_base_weights(clan_data_instance):
    """Test retrieving clan base weights."""
    instance, _ = clan_data_instance # Unpack
    weights = instance.get_clan_base_weights() # Synchronous
    assert isinstance(weights, dict)
    assert len(weights) == 2
    assert weights["TestClan1"] == 10.0
    assert weights["TestClan2"] == 5.0 