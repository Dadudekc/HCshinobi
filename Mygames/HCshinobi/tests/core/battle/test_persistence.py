"""
Tests for battle persistence module.
"""
import pytest
from pytest import mark
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, List

from HCshinobi.core.battle.persistence import BattlePersistence
from HCshinobi.core.battle.state import BattleState, BattleParticipant
from HCshinobi.core.character import Character

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def persistence(temp_data_dir):
    """Create a BattlePersistence instance with a temporary directory."""
    return BattlePersistence(temp_data_dir)

@pytest.fixture
def sample_character():
    """Create a sample character for testing."""
    return Character(
        id="test_char",
        name="Test Character",
        hp=100,
        max_hp=100,
        chakra=50,
        max_chakra=50,
        strength=10,
        defense=5,
        speed=8,
        ninjutsu=7,
        genjutsu=6,
        taijutsu=9
    )

@pytest.fixture
def attacker(sample_character):
    """Create a sample attacker participant."""
    return BattleParticipant.from_character(sample_character)

@pytest.fixture
def defender():
    """Create a sample defender participant."""
    defender_char = Character(
        id="opponent",
        name="Opponent",
        hp=100,
        max_hp=100,
        chakra=50,
        max_chakra=50,
        strength=10,
        defense=5,
        speed=8,
        ninjutsu=7,
        genjutsu=6,
        taijutsu=9
    )
    return BattleParticipant.from_character(defender_char)

@pytest.fixture
def battle_state(attacker, defender):
    """Create a sample battle state for testing."""
    return BattleState(
        attacker=attacker,
        defender=defender,
        current_turn_player_id=attacker.id
    )

@pytest.mark.asyncio
async def test_save_and_load_active_battles(persistence, battle_state):
    """Test saving and loading active battles."""
    # Add a battle
    battle_id = battle_state.id
    await persistence.add_active_battle(battle_id, battle_state)

    # Load battles
    loaded_battles = await persistence.load_active_battles()

    assert len(loaded_battles) == 1
    assert battle_id in loaded_battles
    loaded_battle = loaded_battles[battle_id]
    assert loaded_battle.attacker.id == battle_state.attacker.id
    assert loaded_battle.defender.id == battle_state.defender.id
    assert loaded_battle.attacker.current_hp == battle_state.attacker.current_hp

@pytest.mark.asyncio
async def test_save_and_load_battle_history(persistence, battle_state):
    """Test saving and loading battle history."""
    battle_id = battle_state.id
    log_entry = "Test battle log entry"
    battle_state.battle_log.append(log_entry)
    battle_state.winner_id = battle_state.attacker.id
    battle_state.is_active = False

    # Add battle to history (assuming it stores the log)
    await persistence.add_battle_to_history(battle_id, battle_state)

    # Load history
    loaded_history_map = await persistence.load_battle_history()
    assert len(loaded_history_map) == 1
    assert battle_id in loaded_history_map

    # Assuming history stores a list of log entries (strings)
    loaded_log_list = loaded_history_map[battle_id]
    assert isinstance(loaded_log_list, list)
    assert len(loaded_log_list) == 1
    # Assert based on the error: check the first item is the string
    assert isinstance(loaded_log_list[0], str)
    assert loaded_log_list[0] == log_entry

@pytest.mark.asyncio
async def test_remove_active_battle(persistence, battle_state):
    """Test removing an active battle."""
    battle_id = battle_state.id
    
    # Add and then remove a battle
    await persistence.add_active_battle(battle_id, battle_state)
    await persistence.remove_active_battle(battle_id)

    assert battle_id not in persistence.active_battles
    await persistence.save_active_battles()
    loaded_battles = await persistence.load_active_battles()
    assert len(loaded_battles) == 0

@pytest.mark.asyncio
async def test_add_battle_to_history_multiple_entries(persistence, battle_state):
    """Test adding multiple history entries (assuming logs are appended)."""
    battle_id = battle_state.id
    log_entry_1 = "First entry"
    log_entry_2 = "Second entry"

    # First entry
    battle_state.battle_log = [log_entry_1]
    battle_state.winner_id = battle_state.attacker.id
    battle_state.is_active = False
    await persistence.add_battle_to_history(battle_id, battle_state)

    # Second entry (create new state just to get a different log)
    battle_state_2 = BattleState(
        attacker=battle_state.attacker,
        defender=battle_state.defender,
        current_turn_player_id=battle_state.defender.id,
        battle_log=[log_entry_2] # Only change the log for this test
    )
    battle_state_2.is_active = False
    await persistence.add_battle_to_history(battle_id, battle_state_2)

    loaded_history_map = await persistence.load_battle_history()
    assert battle_id in loaded_history_map
    loaded_log_list = loaded_history_map[battle_id]
    # Corrected Assertion: Expect 2 log entries if only logs are stored and appended
    assert len(loaded_log_list) == 2
    assert loaded_log_list[0] == log_entry_1
    assert loaded_log_list[1] == log_entry_2

@pytest.mark.asyncio
async def test_persistence_with_empty_data(persistence):
    """Test persistence behavior with empty/missing data."""
    # Test loading non-existent battles
    loaded_battles = await persistence.load_active_battles()
    assert len(loaded_battles) == 0

    # Test loading non-existent history
    loaded_history = await persistence.load_battle_history()
    assert len(loaded_history) == 0

@pytest.mark.asyncio
async def test_persistence_data_consistency(persistence, battle_state):
    """Test data consistency across save/load operations."""
    battle_id = battle_state.id
    
    # Modify battle state
    battle_state.turn_number = 5
    battle_state.attacker.current_hp = 75
    battle_state.defender.current_hp = 60
    battle_state.battle_log.append("Test log entry")
    
    # Save battle
    await persistence.add_active_battle(battle_id, battle_state)
    await persistence.save_active_battles()
    
    # Load and verify all properties
    loaded_battles = await persistence.load_active_battles()
    assert battle_id in loaded_battles
    loaded_battle = loaded_battles[battle_id]
    
    assert loaded_battle.turn_number == 5
    assert loaded_battle.attacker.current_hp == 75
    assert loaded_battle.defender.current_hp == 60
    assert len(loaded_battle.battle_log) == 1
    assert "Test log entry" in loaded_battle.battle_log