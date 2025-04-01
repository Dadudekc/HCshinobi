"""Tests for the battle system."""
import pytest
from datetime import datetime, timedelta
from HCshinobi.core.battle_system import BattleSystem, BattleState
from HCshinobi.core.character import Character
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_character_system():
    """Create mock character system."""
    character_system = AsyncMock()
    character_system.get_character = AsyncMock()
    return character_system

@pytest.fixture
def battle_system(mock_character_system):
    """Create battle system instance."""
    system = BattleSystem(character_system=mock_character_system)
    system.active_battles = {}
    system.battle_history = {}
    return system

@pytest.fixture
def test_characters():
    """Create test characters for battle testing."""
    attacker = Character(
        id="player1",
        name="Test Attacker",
        clan="Uchiha",
        level=10,
        hp=100,
        chakra=100,
        strength=15,
        defense=10,
        speed=12,
        jutsu=["Fireball Jutsu"]
    )
    
    defender = Character(
        id="player2",
        name="Test Defender",
        clan="Hyuga",
        level=10,
        hp=100,
        chakra=100,
        strength=12,
        defense=15,
        speed=10,
        jutsu=["Gentle Fist"]
    )
    
    return attacker, defender

@pytest.mark.asyncio
async def test_initialization(battle_system):
    """Test battle system initialization."""
    assert battle_system is not None
    assert hasattr(battle_system, 'character_system')
    assert isinstance(battle_system.active_battles, dict)
    assert isinstance(battle_system.battle_history, dict)

@pytest.mark.asyncio
async def test_start_battle(battle_system, test_characters):
    """Test starting a battle."""
    attacker, defender = test_characters
    battle_system.character_system.get_character.side_effect = [attacker, defender]
    
    battle_state = await battle_system.start_battle(attacker.id, defender.id)
    assert isinstance(battle_state, BattleState)
    assert battle_state.attacker.id == attacker.id
    assert battle_state.defender.id == defender.id
    assert f"{attacker.id}_{defender.id}" in battle_system.active_battles

@pytest.mark.asyncio
async def test_battle_flow(battle_system, test_characters):
    """Test complete battle flow."""
    attacker, defender = test_characters
    initial_defender_hp = defender.hp # Store initial HP
    battle_system.character_system.get_character.side_effect = [attacker, defender, attacker, defender] # Need 4 calls now

    # Start battle
    battle_id = f"{attacker.id}_{defender.id}"
    battle_state = await battle_system.start_battle(attacker.id, defender.id)
    assert battle_state is not None
    assert battle_id in battle_system.active_battles

    # Calculate and apply enough damage to end the battle
    # We'll apply damage exactly equal to defender's initial HP
    damage_to_apply = initial_defender_hp

    applied = await battle_system.apply_damage(battle_id, damage_to_apply, 'defender')
    assert applied is True

    # Get the updated battle state and check HP
    updated_state = await battle_system.get_battle_status(battle_id)
    assert updated_state is not None
    # Defender HP should be 0 after applying damage equal to initial HP
    assert updated_state.defender_hp == 0

    # Check battle end - should now return True
    ended = battle_system.check_battle_end(battle_id) # check_battle_end is synchronous
    assert ended is True

    # Check that the battle is removed from active battles after end
    # This might happen in check_battle_end or end_battle, let's assume end_battle
    winner_id = await battle_system.end_battle(battle_id)
    # Assert the correct winner ID is returned
    assert winner_id == attacker.id 
    # Check the state in battle_history
    assert battle_id in battle_system.battle_history
    final_state = battle_system.battle_history[battle_id]
    assert final_state.defender_hp == 0
    assert final_state.winner == attacker.id
    assert final_state.is_active is False
    assert battle_id not in battle_system.active_battles # Should be removed

@pytest.mark.asyncio
async def test_battle_timeout(battle_system, test_characters):
    """Test battle timeout handling."""
    attacker, defender = test_characters
    # Ensure mocks are set for get_character within this test scope
    battle_system.character_system.get_character = AsyncMock(side_effect=lambda id: attacker if id == attacker.id else defender)

    battle_id = f"{attacker.id}_{defender.id}"
    battle_state = await battle_system.start_battle(attacker.id, defender.id)
    assert battle_id in battle_system.active_battles # Ensure battle was actually added
    assert battle_state is not None

    # Simulate battle timeout by adjusting last_action time
    battle_state.last_action = datetime.now() - timedelta(minutes=30)
    # Update the state in the active_battles dictionary
    battle_system.active_battles[battle_id] = battle_state 

    # Use check_battle_end to verify timeout
    ended_by_timeout = battle_system.check_battle_end(battle_id)
    assert ended_by_timeout is True
    
    # Verify the battle state was updated correctly (is_active=False, winner=None)
    final_state = battle_system.active_battles[battle_id]
    assert final_state.is_active is False
    assert final_state.winner is None 