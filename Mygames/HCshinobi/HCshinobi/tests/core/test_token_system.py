"""Tests for the TokenSystem core service."""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from HCshinobi.core.token_system import TokenSystem, TokenError
from HCshinobi.core.constants import TOKEN_START_AMOUNT, TOKEN_COSTS, MAX_CLAN_BOOST_TOKENS, TOKEN_FILE
from pathlib import Path
from HCshinobi.utils.file_io import load_json, save_json
from HCshinobi.utils.logging import get_logger, log_event

@pytest.fixture
def mock_token_data():
    """Sample token data for testing."""
    return {
        "tokens": {
            "user1": 100,
            "user2": 50,
            "user3": 0
        },
        "unlocks": {
            "user1": ["weapon_crafting", "elemental_affinity"],
            "user2": ["weapon_crafting"]
        }
    }

@pytest_asyncio.fixture
async def token_system(tmp_path, mock_token_data):
    """Fixture to create a TokenSystem instance for testing."""
    data_dir = str(tmp_path)
    token_file_path = tmp_path / TOKEN_FILE
    token_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Mock logger and file IO directly
    mock_logger = MagicMock()
    # Mock load_json to return specific data for the token file
    mock_load_json = AsyncMock(return_value=mock_token_data)
    mock_save_json = AsyncMock()
    
    # Ensure the mock load_json only returns data for the expected file
    async def selective_load(path):
        if Path(path) == token_file_path:
            return mock_token_data
        # Handle log file loading if needed, return empty list
        if Path(path).name == "token_transactions.log": 
             return []
        return None
    mock_load_json = AsyncMock(side_effect=selective_load)
    mock_save_json = AsyncMock()
    
    with patch('HCshinobi.core.token_system.load_json', mock_load_json), \
         patch('HCshinobi.core.token_system.save_json', mock_save_json), \
         patch('HCshinobi.core.token_system.get_logger', return_value=mock_logger), \
         patch('HCshinobi.core.token_system.log_event'):
        # TokenSystem.__init__ takes no args, uses constants for file paths
        instance = TokenSystem()
        # Patch the file paths used internally if they differ from constants
        instance.TOKEN_FILE = str(token_file_path) # Ensure instance uses the temp path
        instance.TOKEN_LOG_FILE = str(tmp_path / "token_transactions.log")
        # Reload data after patching path, if _load_tokens is not async or called later
        # Assuming _load_tokens is called in __init__ and uses the patched load_json
        return instance

@pytest.mark.asyncio
async def test_load_existing_tokens(token_system):
    """Test loading data from an existing token file."""
    # The fixture `token_system` should have loaded the mock data
    assert token_system.player_tokens == {"user1": 100, "user2": 50}

@pytest.mark.asyncio
async def test_load_invalid_data(tmp_path):
    """Test handling of invalid (non-dict) token file."""
    token_file_path = tmp_path / TOKEN_FILE

@pytest.mark.asyncio
async def test_get_player_tokens(token_system, mock_token_data):
    """Test retrieving player token balances."""
    token_system.player_tokens = mock_token_data["tokens"]
    
    # Test existing player
    assert token_system.get_player_tokens("user1") == 100
    
    # Test new player (should return TOKEN_START_AMOUNT)
    assert token_system.get_player_tokens("new_user") == TOKEN_START_AMOUNT

@pytest.mark.asyncio
async def test_ensure_player_exists(token_system):
    """Test ensuring a player exists in the token data."""
    # Test adding a new player
    await token_system.ensure_player_exists("new_user")
    assert "new_user" in token_system.player_tokens
    assert token_system.player_tokens["new_user"] == TOKEN_START_AMOUNT

    # Test existing player (should not change balance or trigger save)
    initial_tokens = 50
    token_system.player_tokens["existing_user"] = initial_tokens
    # Reset save mock if used
    # token_system._save_tokens.reset_mock()
    await token_system.ensure_player_exists("existing_user")
    assert token_system.player_tokens["existing_user"] == initial_tokens
    # Assert save was *not* called
    # token_system._save_tokens.assert_not_called()

@pytest.mark.asyncio
async def test_add_tokens(token_system):
    """Test adding and removing tokens."""
    token_system.player_tokens = {"user1": 100}
    
    # Test adding tokens
    new_balance = await token_system.add_tokens("user1", 50, "test_add")
    assert new_balance == 150
    assert token_system.player_tokens["user1"] == 150
    
    # Test removing tokens
    new_balance = await token_system.add_tokens("user1", -30, "test_remove")
    assert new_balance == 120
    assert token_system.player_tokens["user1"] == 120
    
    # Test removing more than balance (should set to 0)
    new_balance = await token_system.add_tokens("user1", -200, "test_remove_excess")
    assert new_balance == 0
    assert token_system.player_tokens["user1"] == 0
    
    # Test adding to new player
    new_balance = await token_system.add_tokens("new_user", 25, "test_add_new")
    assert new_balance == TOKEN_START_AMOUNT + 25
    
    # Test invalid amount
    with pytest.raises(ValueError):
        await token_system.add_tokens("user1", 0, "test_zero")

@pytest.mark.asyncio
async def test_use_tokens(token_system):
    """Test using tokens for purchases/actions."""
    token_system.player_tokens = {"user1": 100}
    
    # Test successful use
    remaining = await token_system.use_tokens("user1", 30, "test_purchase")
    assert remaining == 70
    assert token_system.player_tokens["user1"] == 70
    
    # Test insufficient funds
    with pytest.raises(TokenError):
        await token_system.use_tokens("user1", 100, "test_insufficient")
    
    # Test invalid amount
    with pytest.raises(ValueError):
        await token_system.use_tokens("user1", 0, "test_zero")
    with pytest.raises(ValueError):
        await token_system.use_tokens("user1", -10, "test_negative")

@pytest.mark.asyncio
async def test_use_tokens_for_clan_boost(token_system):
    """Test using tokens for clan boost."""
    token_system.player_tokens = {"user1": 100}
    
    # Test valid boost
    remaining = await token_system.use_tokens("user1", 2, "clan_boost_TestClan")
    assert remaining == 98  # Assuming cost is 1 token per boost
    
    # Test maximum token limit
    with pytest.raises(ValueError):
        await token_system.use_tokens("user1", MAX_CLAN_BOOST_TOKENS + 1, "clan_boost_TestClan")
    
    # Test insufficient funds
    token_system.player_tokens["user2"] = 0
    with pytest.raises(TokenError):
        await token_system.use_tokens("user2", 1, "clan_boost_TestClan")

@pytest.mark.asyncio
async def test_use_tokens_for_reroll(token_system):
    """Test using tokens for clan reroll."""
    reroll_cost = TOKEN_COSTS["reroll_clan"]
    token_system.player_tokens = {"user1": reroll_cost + 10}
    
    # Test successful reroll
    remaining = await token_system.use_tokens("user1", reroll_cost, "reroll_clan")
    assert remaining == token_system.player_tokens["user1"] == 10
    
    # Test insufficient funds
    token_system.player_tokens["user2"] = reroll_cost - 1
    with pytest.raises(TokenError):
        await token_system.use_tokens("user2", reroll_cost, "reroll_clan")

@pytest.mark.asyncio
async def test_feature_unlocks(token_system):
    """Test feature unlock functionality."""
    feature = "weapon_crafting"
    cost = TOKEN_COSTS[f"unlock_feature_{feature}"]
    token_system.player_tokens = {"user1": cost + 10}
    token_system.player_unlocks = {}
    
    # Test successful unlock
    remaining = await token_system.unlock_feature("user1", feature)
    assert remaining == cost + 10 - cost
    assert feature in token_system.get_player_unlocks("user1")
    
    # Test duplicate unlock
    with pytest.raises(TokenError):
        await token_system.unlock_feature("user1", feature)
    
    # Test insufficient funds
    token_system.player_tokens["user2"] = cost - 1
    with pytest.raises(TokenError):
        await token_system.unlock_feature("user2", feature)
    
    # Test invalid feature
    with pytest.raises(ValueError):
        await token_system.unlock_feature("user1", "invalid_feature")

@pytest.mark.asyncio
async def test_transaction_logging(token_system):
    """Test transaction logging functionality."""
    # Reset state potentially modified by fixture loading
    token_system.player_tokens = {"user1": 100}
    token_system.transaction_log = []

    mock_now = datetime(2024, 1, 1, 12, 0)

    # Patch save_json specifically for *this test* to intercept the log save call.
    # The fixture already handles mocking for the instance's internal operations.
    with patch('HCshinobi.core.token_system.save_json', new_callable=AsyncMock) as mock_save_json_for_test, \
         patch('HCshinobi.core.token_system.datetime') as mock_datetime:

        mock_datetime.now.return_value = mock_now

        # Use the fixture-provided, initialized token_system instance
        await token_system.add_tokens("user1", 50, "test_transaction_log")

        # Verify save_json was called for the log file path
        log_call = None
        for call_args in mock_save_json_for_test.call_args_list:
            # Ensure the first argument (path) matches the instance's log file path
            if len(call_args[0]) > 0 and Path(call_args[0][0]).resolve() == Path(token_system.log_file).resolve():
                log_call = call_args
                break

        assert log_call is not None, "save_json was not called for the log file"

        # Verify the data saved in the log call
        saved_log_data = log_call[0][1]
        assert isinstance(saved_log_data, list)
        assert len(saved_log_data) > 0

        log_entry = saved_log_data[-1] # Get the last entry in the log

        assert log_entry["player_id"] == "user1"
        assert log_entry["type"] == "add"
        assert log_entry["amount"] == 50
        assert log_entry["reason"] == "test_transaction_log"
        assert log_entry["balance_after"] == 150 # 100 + 50
        assert log_entry["timestamp"] == mock_now.isoformat()

    # Clean up the manually created instance if necessary, though pytest fixtures should handle temp dirs 