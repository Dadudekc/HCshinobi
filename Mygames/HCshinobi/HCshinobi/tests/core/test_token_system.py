"""Tests for the TokenSystem core service."""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock, Mock
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

@pytest.fixture
def token_system(tmp_path, mock_token_data):
    """Fixture to create a TokenSystem instance for testing."""
    token_file_path = tmp_path / TOKEN_FILE
    log_file_path = tmp_path / "token_transactions.log"
    token_file_path.parent.mkdir(parents=True, exist_ok=True)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    mock_logger = MagicMock()
    mock_save_json = MagicMock()
    
    # Ensure the mock load_json only returns data for the expected file paths
    def selective_load(path):
        resolved_path = Path(path).resolve()
        if resolved_path == token_file_path.resolve():
            print(f"DEBUG: Mock load_json returning mock_token_data for {path}")
            return mock_token_data
        if resolved_path == log_file_path.resolve(): 
             print(f"DEBUG: Mock load_json returning [] for {path}")
             return []
        print(f"DEBUG: Mock load_json called with unexpected path: {path}")
        return None
    mock_load_json = MagicMock(side_effect=selective_load)
    
    # Patch load/save/logger/log_event *before* initializing TokenSystem
    with patch('HCshinobi.core.token_system.load_json', mock_load_json), \
         patch('HCshinobi.core.token_system.save_json', mock_save_json), \
         patch('HCshinobi.core.token_system.get_logger', return_value=mock_logger), \
         patch('HCshinobi.core.token_system.log_event'):
        # Initialize the instance with the correct paths
        instance = TokenSystem(token_file=str(token_file_path), log_file=str(log_file_path))
        # Explicitly call initialize() so it uses the mocked load_json
        instance.initialize() 
        yield instance # Use yield if fixture needs cleanup later

@pytest.mark.asyncio
async def test_load_existing_tokens(token_system):
    """Test loading data from an existing token file."""
    # The fixture should now correctly load data via instance.initialize()
    assert token_system.player_tokens == {"user1": 100, "user2": 50, "user3": 0}
    assert token_system.player_unlocks == {"user1": ["weapon_crafting", "elemental_affinity"], "user2": ["weapon_crafting"]}

@pytest.mark.asyncio
async def test_load_invalid_data(tmp_path):
    """Test handling of invalid (non-dict) token file."""
    token_file_path = tmp_path / TOKEN_FILE
    log_file_path = tmp_path / "token_transactions.log"
    token_file_path.parent.mkdir(parents=True, exist_ok=True)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_file_path, 'w') as f:
        f.write("invalid data") # Write non-JSON data
        
    mock_logger = MagicMock()
    mock_load_json_invalid = MagicMock(return_value=None) # Simulate load failure
    mock_save_json = MagicMock()

    # Patch load/save/logger
    with patch('HCshinobi.core.token_system.load_json', mock_load_json_invalid), \
         patch('HCshinobi.core.token_system.save_json', mock_save_json), \
         patch('HCshinobi.core.token_system.logger', mock_logger), \
         patch('HCshinobi.core.token_system.log_event'): 
        # Initialize with the invalid file path
        instance = TokenSystem(token_file=str(token_file_path), log_file=str(log_file_path))
        # initialize() is called explicitly in __init__ for TokenSystem, so it runs here
        instance.initialize()
        assert instance.player_tokens == {}
        assert instance.player_unlocks == {}
        # Check that a warning or error was logged
        assert mock_logger.warning.called or mock_logger.error.called

@pytest.mark.asyncio
async def test_get_player_tokens(token_system, mock_token_data):
    """Test retrieving player token balances."""
    # Fixture should have loaded the data correctly
    assert token_system.get_player_tokens("user1") == 100
    assert token_system.get_player_tokens("user3") == 0
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
    cost_per_token = TOKEN_COSTS.get("clan_boost", 1)
    valid_boost_amount = 2
    valid_cost = cost_per_token * valid_boost_amount
    
    # Test valid boost by calling the correct method
    remaining = await token_system.use_tokens_for_clan_boost("user1", "TestClan", valid_boost_amount)
    assert remaining == 100 - valid_cost 
    
    # Test maximum token limit violation by calling the correct method
    with pytest.raises(ValueError):
        await token_system.use_tokens_for_clan_boost("user1", "TestClan", MAX_CLAN_BOOST_TOKENS + 1)
    
    # Test insufficient funds
    token_system.player_tokens["user2"] = valid_cost - 1 # Set insufficient funds
    with pytest.raises(TokenError):
        await token_system.use_tokens_for_clan_boost("user2", "TestClan", valid_boost_amount)

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

    # Patch save_json with a regular Mock, as it's synchronous
    with patch('HCshinobi.core.token_system.save_json', new_callable=Mock) as mock_save_json_for_test, \
         patch('HCshinobi.core.token_system.datetime') as mock_datetime:

        mock_datetime.now.return_value = mock_now

        # Use the fixture-provided, initialized token_system instance
        await token_system.add_tokens("user1", 50, "test_transaction_log")

        # Verify save_json was called (not awaited)
        log_call = None
        save_calls = 0 # Count calls relevant to log/token files
        for call_args in mock_save_json_for_test.call_args_list:
            # First arg is path, second is data
            if len(call_args[0]) > 0:
                call_path = Path(call_args[0][0]).resolve()
                # Check if it saved the token file or the log file
                if call_path == Path(token_system.token_file).resolve():
                    save_calls += 1
                elif call_path == Path(token_system.log_file).resolve():
                    save_calls += 1
                    log_call = call_args # Store the log call specifically

        assert save_calls >= 1, "save_json was not called for token or log file"
        assert log_call is not None, "save_json was not called specifically for the log file"

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