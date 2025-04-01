"""Tests for the currency system."""
import pytest
import os
import json
from datetime import datetime
from HCshinobi.core.currency_system import CurrencySystem

@pytest.fixture
def currency_system(setup_test_environment):
    """Create currency system instance."""
    data_file = setup_test_environment / "currency" / "currency.json"
    system = CurrencySystem(str(data_file))
    system.save_currency_data()  # Initialize empty data
    return system

def test_initialization(currency_system):
    """Test currency system initialization."""
    assert currency_system is not None
    assert hasattr(currency_system, 'currency_data')
    assert isinstance(currency_system.currency_data, dict)

def test_load_currency_data(currency_system):
    """Test loading currency data."""
    # Create test data
    test_data = {"player1": 1000, "player2": 2000}
    os.makedirs(os.path.dirname(currency_system.data_file), exist_ok=True)
    with open(currency_system.data_file, 'w') as f:
        json.dump(test_data, f)
    
    # Load data
    currency_system.load_currency_data()
    assert currency_system.currency_data == test_data

def test_save_currency_data(currency_system):
    """Test saving currency data."""
    # Set test data
    test_data = {"player1": 1000, "player2": 2000}
    currency_system.currency_data = test_data
    
    # Save data
    currency_system.save_currency_data()
    
    # Verify saved data
    with open(currency_system.data_file, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == test_data

def test_get_player_balance(currency_system):
    """Test getting player balance."""
    player_id = "test_player"
    assert currency_system.get_player_balance(player_id) == 0

def test_set_player_balance(currency_system):
    """Test setting player balance."""
    player_id = "test_player"
    currency_system.set_player_balance(player_id, 1000)
    assert currency_system.get_player_balance(player_id) == 1000

def test_add_to_balance(currency_system):
    """Test adding to player balance."""
    player_id = "test_player"
    currency_system.set_player_balance(player_id, 1000)
    new_balance = currency_system.add_to_balance(player_id, 500)
    assert new_balance == 1500
    assert currency_system.get_player_balance(player_id) == 1500

def test_deduct_from_balance(currency_system):
    """Test deducting from player balance."""
    player_id = "test_player"
    currency_system.set_player_balance(player_id, 1000)
    success = currency_system.deduct_from_balance(player_id, 500)
    assert success
    assert currency_system.get_player_balance(player_id) == 500

def test_has_sufficient_funds(currency_system):
    """Test checking for sufficient funds."""
    # Set initial balance
    currency_system.set_player_balance("player1", 1000)
    
    # Test sufficient funds
    assert currency_system.has_sufficient_funds("player1", 500) is True
    
    # Test insufficient funds
    assert currency_system.has_sufficient_funds("player1", 1500) is False
    
    # Test non-existing player
    assert currency_system.has_sufficient_funds("player2", 1000) is False

def test_transfer_funds(currency_system):
    """Test transferring funds between players."""
    player1 = "test_player1"
    player2 = "test_player2"
    currency_system.set_player_balance(player1, 1000)
    currency_system.set_player_balance(player2, 500)
    
    success = currency_system.transfer_funds(player1, player2, 700)
    assert success
    assert currency_system.get_player_balance(player1) == 300
    assert currency_system.get_player_balance(player2) == 1200 