"""
Tests for battle lifecycle module.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from HCshinobi.core.battle.lifecycle import BattleLifecycle
from HCshinobi.core.battle.persistence import BattlePersistence
from HCshinobi.core.battle.state import BattleState, BattleParticipant
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.progression_engine import ShinobiProgressionEngine

@pytest.fixture
def mock_character_system():
    """Create a mock character system."""
    return Mock(spec=CharacterSystem)

@pytest.fixture
def mock_persistence():
    """Create a mock persistence manager."""
    persistence = Mock(spec=BattlePersistence)
    persistence.add_battle_to_history = AsyncMock()
    persistence.remove_active_battle = AsyncMock()
    persistence.save_active_battles = AsyncMock()
    persistence.save_battle_history = AsyncMock()
    return persistence

@pytest.fixture
def mock_progression_engine():
    """Create a mock progression engine."""
    engine = Mock(spec=ShinobiProgressionEngine)
    engine.award_battle_experience = AsyncMock()
    return engine

@pytest.fixture
def lifecycle(mock_character_system, mock_persistence, mock_progression_engine):
    """Create a BattleLifecycle instance with mocked dependencies."""
    return BattleLifecycle(
        character_system=mock_character_system,
        persistence=mock_persistence,
        progression_engine=mock_progression_engine,
        battle_timeout=5  # Short timeout for testing
    )

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
        taijutsu=9,
        level=5
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
        taijutsu=9,
        level=5
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
async def test_handle_battle_end(lifecycle, battle_state):
    """Test handling battle end."""
    battle_id = battle_state.id
    battle_state.winner_id = battle_state.attacker.id
    
    await lifecycle.handle_battle_end(battle_state, battle_id)
    
    # Verify persistence calls
    lifecycle.persistence.add_battle_to_history.assert_called_once_with(battle_id, battle_state)
    lifecycle.persistence.remove_active_battle.assert_called_once_with(battle_id)

@pytest.mark.asyncio
async def test_handle_battle_end_with_exp_gain(lifecycle, battle_state):
    """Test handling battle end with experience gain."""
    battle_id = battle_state.id
    battle_state.winner_id = battle_state.attacker.id
    battle_state.turn_number = 3  # A few turns to affect exp gain
    
    await lifecycle.handle_battle_end(battle_state, battle_id)
    
    # Verify experience was awarded
    lifecycle.progression_engine.award_battle_experience.assert_called_once()
    call_args, _ = lifecycle.progression_engine.award_battle_experience.call_args
    winner_id_passed = call_args[0]
    exp_awarded = call_args[1]
    assert winner_id_passed == battle_state.winner_id
    assert exp_awarded > 0

def test_calculate_exp_gain(lifecycle, battle_state):
    """Test experience gain calculation."""
    battle_state.winner_id = battle_state.attacker.id
    
    # Test base case (same level)
    exp = lifecycle._calculate_exp_gain(battle_state)
    assert exp == 100  # Base experience

    # Test level difference bonus
    battle_state.defender.character.level = 7
    exp = lifecycle._calculate_exp_gain(battle_state)
    assert exp > 100

    # Test turn count penalty
    battle_state.turn_number = 10
    exp = lifecycle._calculate_exp_gain(battle_state)
    battle_state.defender.character.level = 5
    assert exp < 100

@pytest.mark.asyncio
async def test_cleanup_inactive_battles(lifecycle, battle_state):
    """Test cleaning up inactive battles."""
    battle_id = "test_battle"
    battle_state.last_action = datetime.now(timezone.utc) - timedelta(seconds=10)
    lifecycle.persistence.active_battles = {battle_id: battle_state}
    
    await lifecycle.cleanup_inactive_battles()
    
    # Verify battle was ended
    assert not battle_state.is_active
    assert battle_state.end_reason == "timeout"
    lifecycle.persistence.add_battle_to_history.assert_called_once_with(battle_id, battle_state)

@pytest.mark.asyncio
async def test_notify_players_battle_timeout(lifecycle):
    """Test player notification on battle timeout."""
    mock_bot = Mock()
    mock_bot.fetch_user = AsyncMock()
    mock_user = Mock()
    mock_user.send = AsyncMock()
    mock_bot.fetch_user.return_value = mock_user
    
    lifecycle.bot = mock_bot
    
    await lifecycle.notify_players_battle_timeout("attacker_id", "defender_id")
    
    # Verify both players were notified
    assert mock_bot.fetch_user.call_count == 2
    assert mock_user.send.call_count == 2
    assert "timed out" in mock_user.send.call_args[0][0]

@pytest.mark.asyncio
async def test_battle_timeout_check(lifecycle, battle_state):
    """Test battle timeout check task."""
    battle_id = "test_battle"
    battle_state.last_action = datetime.now(timezone.utc) - timedelta(seconds=10)
    lifecycle.persistence.active_battles = {battle_id: battle_state}

    # Run one iteration of the timeout check
    try:
        # Create a task for the timeout check
        task = asyncio.create_task(lifecycle._battle_timeout_check())
        await asyncio.sleep(0.1)  # Let it run briefly
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    except Exception as e:
        task.cancel()
        raise e

    # Verify inactive battles were cleaned up
    assert not battle_state.is_active
    assert battle_state.end_reason == "timeout"

@pytest.mark.asyncio
async def test_shutdown(lifecycle):
    """Test shutdown cleanup."""
    # Add some battle tasks
    mock_task = Mock()
    mock_task.cancel = Mock()
    lifecycle.battle_tasks["test_battle"] = mock_task
    
    await lifecycle.shutdown()
    
    # Verify tasks were cancelled and state was saved
    mock_task.cancel.assert_called_once()
    lifecycle.persistence.save_active_battles.assert_called_once()
    lifecycle.persistence.save_battle_history.assert_called_once() 