import pytest
import os
import shutil
from unittest.mock import MagicMock, AsyncMock

from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from HCshinobi.utils.file_io import save_json

# --- Fixtures ---

TEST_DATA_DIR = "./test_progression_data"

@pytest.fixture(scope="function")
def temp_data_dir():
    """Creates a temporary data directory for testing, cleaning up afterwards."""
    if os.path.exists(TEST_DATA_DIR):
        shutil.rmtree(TEST_DATA_DIR)
    os.makedirs(os.path.join(TEST_DATA_DIR, 'characters'), exist_ok=True)
    os.makedirs(os.path.join(TEST_DATA_DIR, 'progression'), exist_ok=True)
    yield TEST_DATA_DIR
    # Clean up after test
    # shutil.rmtree(TEST_DATA_DIR)

@pytest.fixture(scope="function")
def character_system_mock(temp_data_dir):
    """Provides a mocked CharacterSystem."""
    mock = MagicMock(spec=CharacterSystem)
    mock.character_data_dir = os.path.join(temp_data_dir, 'characters')
    mock._characters = {}
    async def get_char(user_id):
        return mock._characters.get(user_id)
    async def save_char(char):
        mock._characters[char.id] = char
        # In a real test, we might actually save/load here
        return True
    mock.get_character = AsyncMock(side_effect=get_char)
    mock.save_character = AsyncMock(side_effect=save_char)
    return mock

@pytest.fixture(scope="function")
def progression_engine(character_system_mock, temp_data_dir):
    """Creates a ProgressionEngine instance with pre-populated data."""
    prog_dir = os.path.join(temp_data_dir, 'progression')
    
    # Create dummy level curve
    level_curve = { str(i+1): (i+1)*100 for i in range(10) } # Simple curve 1=100, 2=200, etc.
    save_json(os.path.join(prog_dir, 'level_curve.json'), level_curve)
    
    # Create dummy ranks
    ranks = {
        "Genin": {"exp_required": 500, "next_rank": "Chunin"},
        "Chunin": {"exp_required": 1500, "next_rank": "Jonin"},
        "Jonin": {}
    }
    save_json(os.path.join(prog_dir, 'ranks.json'), ranks)
    
    # Empty achievements/titles for these tests
    save_json(os.path.join(prog_dir, 'achievements.json'), {})
    save_json(os.path.join(prog_dir, 'titles.json'), {})

    engine = ShinobiProgressionEngine(character_system_mock, temp_data_dir)
    # Manually load data for the test instance
    engine._load_progression_data()
    engine.rank_order = engine._generate_rank_order(engine.ranks_data)
    # Override stat points per level for predictable testing if needed
    # engine.STAT_POINTS_PER_LEVEL = 1 
    return engine

# --- Test Cases ---

@pytest.mark.asyncio
async def test_grant_exp_no_level_up(progression_engine, character_system_mock):
    """Test granting EXP that does not result in a level up."""
    char = Character(id="user1", name="Test", level=1, exp=0, rank="Genin", stat_points=0)
    await character_system_mock.save_character(char)
    
    result = await progression_engine.grant_exp(char.id, 50, "test", character=char)
    
    assert result["exp_gained"] == 50
    assert result["level_up"] is False
    assert result["rank_up"] is False
    assert char.level == 1
    assert char.exp == 50
    assert char.stat_points == 0
    assert "Gained 50 EXP" in result["messages"][0]
    character_system_mock.save_character.assert_not_called() # Save only on level/rank up

@pytest.mark.asyncio
async def test_grant_exp_single_level_up(progression_engine, character_system_mock):
    """Test granting EXP that results in a single level up."""
    # Level curve: 1=100, 2=200
    char = Character(id="user2", name="Test", level=1, exp=80, rank="Genin", stat_points=0)
    await character_system_mock.save_character(char)
    
    result = await progression_engine.grant_exp(char.id, 30, "test", character=char)
    
    assert result["exp_gained"] == 30
    assert result["level_up"] is True
    assert result["new_level"] == 2
    assert result["stat_points_gained"] == ShinobiProgressionEngine.STAT_POINTS_PER_LEVEL
    assert result["rank_up"] is False
    assert char.level == 2
    assert char.exp == 110 # Cumulative EXP
    assert char.stat_points == ShinobiProgressionEngine.STAT_POINTS_PER_LEVEL
    assert "Level Up!" in result["messages"][1]
    character_system_mock.save_character.assert_called_once_with(char)

@pytest.mark.asyncio
async def test_grant_exp_multiple_level_ups(progression_engine, character_system_mock):
    """Test granting EXP that results in multiple level ups."""
    # Level curve: 1=100, 2=200, 3=300
    char = Character(id="user3", name="Test", level=1, exp=50, rank="Genin", stat_points=0)
    await character_system_mock.save_character(char)
    
    result = await progression_engine.grant_exp(char.id, 200, "test", character=char)
    expected_stat_points = 2 * ShinobiProgressionEngine.STAT_POINTS_PER_LEVEL
    
    assert result["exp_gained"] == 200
    assert result["level_up"] is True
    assert result["new_level"] == 3
    assert result["stat_points_gained"] == expected_stat_points
    assert result["rank_up"] is False
    assert char.level == 3
    assert char.exp == 250 # Cumulative EXP
    assert char.stat_points == expected_stat_points
    assert "Level Up!" in result["messages"][1] # Level 2 message
    assert "Level Up!" in result["messages"][2] # Level 3 message
    character_system_mock.save_character.assert_called_once_with(char)

@pytest.mark.asyncio
async def test_grant_exp_level_and_rank_up(progression_engine, character_system_mock):
    """Test granting EXP that results in both level and rank up."""
    # Level curve: 1=100, 2=200, 3=300, 4=400, 5=500
    # Rank curve: Genin -> Chunin at 500 EXP (relative to start of rank)
    char = Character(id="user4", name="Test", level=4, exp=350, rank="Genin", stat_points=9)
    await character_system_mock.save_character(char)
    
    # Grant enough EXP to reach level 5 (needs 500 total) and rank up (needs 500 relative)
    result = await progression_engine.grant_exp(char.id, 200, "test", character=char)
    expected_stat_points = 1 * ShinobiProgressionEngine.STAT_POINTS_PER_LEVEL
    
    assert result["exp_gained"] == 200
    assert result["level_up"] is True
    assert result["new_level"] == 5
    assert result["stat_points_gained"] == expected_stat_points
    assert result["rank_up"] is True
    assert result["new_rank"] == "Chunin"
    assert char.level == 5
    assert char.exp == 50 # 350 + 200 = 550 total. Rank up costs 500. 550-500 = 50. Level EXP remains cumulative.
    assert char.stat_points == 9 + expected_stat_points
    assert "Level Up!" in result["messages"][1]
    assert "Rank Up!" in result["messages"][2]
    character_system_mock.save_character.assert_called_once_with(char)

@pytest.mark.asyncio
async def test_grant_exp_max_level(progression_engine, character_system_mock):
    """Test granting EXP when character is at the max defined level."""
    # Level curve defined up to 10 (1000 EXP)
    char = Character(id="user5", name="Test", level=10, exp=1000, rank="Jonin", stat_points=30)
    await character_system_mock.save_character(char)

    result = await progression_engine.grant_exp(char.id, 50, "test", character=char)

    assert result["exp_gained"] == 50
    assert result["level_up"] is False
    assert char.level == 10
    assert char.exp == 1050
    assert char.stat_points == 30 # No more stat points
    assert len(result["messages"]) == 1 # Only EXP gain message
    character_system_mock.save_character.assert_not_called()

# Add more tests? e.g., edge cases, exact EXP thresholds 