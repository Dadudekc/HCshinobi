"""
Tests for battle effects module.
"""
import pytest
from datetime import datetime, timezone
from HCshinobi.core.battle.types import StatusEffect, BattleLogCallback
from HCshinobi.core.battle.effects import (
    add_status_effect,
    apply_status_effects,
    tick_status_durations,
    can_player_act
)
from HCshinobi.core.battle.state import BattleState, BattleParticipant
from HCshinobi.core.character import Character

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

@pytest.fixture
def battle_log_callback():
    """Create a mock battle log callback."""
    def callback(battle: BattleState, message: str) -> None:
        battle.battle_log.append(message)
    return callback

def test_status_effect_creation():
    """Test creating a StatusEffect instance."""
    effect = StatusEffect(
        name="Poison",
        duration=3,
        potency=0.1,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    
    assert effect.name == "Poison"
    assert effect.duration == 3
    assert effect.potency == 0.1
    assert effect.effect_type == "start_turn"
    assert effect.description == "Takes damage at start of turn"
    assert isinstance(effect.applied_at, datetime)

def test_status_effect_serialization():
    """Test StatusEffect serialization and deserialization."""
    effect = StatusEffect(
        name="Poison",
        duration=3,
        potency=0.1,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    
    # Convert to dict and back
    effect_dict = effect.to_dict()
    reconstructed = StatusEffect.from_dict(effect_dict)
    
    assert reconstructed.name == effect.name
    assert reconstructed.duration == effect.duration
    assert reconstructed.potency == effect.potency
    assert reconstructed.effect_type == effect.effect_type
    assert reconstructed.description == effect.description
    assert isinstance(reconstructed.applied_at, datetime)

def test_add_status_effect(battle_state, battle_log_callback):
    """Test adding a status effect to a character."""
    effect = StatusEffect(
        name="Poison",
        duration=3,
        potency=0.1,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    
    # Add effect to attacker participant
    add_status_effect(battle_state, battle_state.attacker.id, effect, battle_log_callback)
    
    assert len(battle_state.attacker.effects) == 1
    assert battle_state.attacker.effects[0]["name"] == "Poison"
    assert battle_state.attacker.effects[0]["duration"] == 3
    assert len(battle_state.battle_log) == 1
    assert "was affected by Poison" in battle_state.battle_log[0]

def test_add_status_effect_refresh(battle_state, battle_log_callback):
    """Test refreshing an existing status effect."""
    # Add initial effect to attacker participant
    effect1 = StatusEffect(
        name="Poison",
        duration=2,
        potency=0.1,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    add_status_effect(battle_state, battle_state.attacker.id, effect1, battle_log_callback)
    
    # Add stronger effect to attacker participant
    effect2 = StatusEffect(
        name="Poison",
        duration=3,
        potency=0.2,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    add_status_effect(battle_state, battle_state.attacker.id, effect2, battle_log_callback)
    
    assert len(battle_state.attacker.effects) == 1
    assert battle_state.attacker.effects[0]["duration"] == 3
    assert battle_state.attacker.effects[0]["potency"] == 0.2
    assert len(battle_state.battle_log) == 2
    assert "was refreshed" in battle_state.battle_log[1]

def test_apply_status_effects(battle_state, battle_log_callback):
    """Test applying status effects at start of turn."""
    # Add poison effect to attacker
    effect = StatusEffect(
        name="Poison",
        duration=3,
        potency=0.1,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    battle_state.attacker.effects.append(effect.to_dict())
    
    # Apply effects
    apply_status_effects(battle_state, "start_turn", battle_log_callback)
    
    assert battle_state.attacker.current_hp == 90  # 100 - (100 * 0.1)
    assert len(battle_state.battle_log) == 1
    assert "took 10 poison damage" in battle_state.battle_log[0]

def test_apply_regeneration_effect(battle_state, battle_log_callback):
    """Test applying regeneration effect."""
    # Add regeneration effect to attacker
    effect = StatusEffect(
        name="Regeneration",
        duration=3,
        potency=0.1,
        effect_type="start_turn",
        description="Heals at start of turn"
    )
    battle_state.attacker.effects.append(effect.to_dict())
    battle_state.attacker.current_hp = 80  # Set HP below max
    
    # Apply effects
    apply_status_effects(battle_state, "start_turn", battle_log_callback)
    
    assert battle_state.attacker.current_hp == 90  # 80 + (100 * 0.1)
    assert len(battle_state.battle_log) == 1
    assert "regenerated 10 HP" in battle_state.battle_log[0]

def test_tick_status_durations(battle_state, battle_log_callback):
    """Test ticking down status effect durations."""
    # Add poison effect to attacker participant's effects list
    effect = StatusEffect(
        name="Poison",
        duration=3,
        potency=0.1,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    battle_state.attacker.effects.append(effect.to_dict())
    
    # Tick durations
    tick_status_durations(battle_state, battle_log_callback)
    
    assert battle_state.attacker.effects[0]["duration"] == 2
    assert len(battle_state.battle_log) == 0  # No messages for non-expired effects

def test_tick_status_durations_expiration(battle_state, battle_log_callback):
    """Test status effect expiration."""
    # Add poison effect with 1 turn duration to attacker participant's effects list
    effect = StatusEffect(
        name="Poison",
        duration=1,
        potency=0.1,
        effect_type="start_turn",
        description="Takes damage at start of turn"
    )
    battle_state.attacker.effects.append(effect.to_dict())
    
    # Tick durations
    tick_status_durations(battle_state, battle_log_callback)
    
    assert len(battle_state.attacker.effects) == 0
    assert len(battle_state.battle_log) == 1
    assert "wore off" in battle_state.battle_log[0]

def test_can_player_act(battle_state, battle_log_callback):
    """Test checking if a player can act when stunned."""
    # Add stun effect to attacker participant's effects list
    effect = StatusEffect(
        name="Stun",
        duration=1,
        potency=1.0,
        effect_type="action_check", # Assuming this is the type checked by can_player_act
        description="Cannot act this turn"
    )
    battle_state.attacker.effects.append(effect.to_dict())
    
    # Check if attacker can act
    assert not can_player_act(battle_state, battle_state.attacker.id, battle_log_callback)
    assert len(battle_state.battle_log) == 1
    assert "is stunned" in battle_state.battle_log[0]
    
    # Check defender can still act (ensure effects are participant-specific)
    # Make sure defender has no effects
    battle_state.defender.effects = []
    # Reset log maybe?
    battle_state.battle_log.clear()
    assert can_player_act(battle_state, battle_state.defender.id, battle_log_callback)
    assert len(battle_state.battle_log) == 0 # No log message expected for defender

# Potential test for can_player_act when not stunned
def test_can_player_act_not_stunned(battle_state, battle_log_callback):
    """Test checking if a player can act when not affected by action-preventing effects."""
    # Ensure attacker has no effects
    battle_state.attacker.effects = []
    battle_state.battle_log.clear()
    assert can_player_act(battle_state, battle_state.attacker.id, battle_log_callback)
    assert len(battle_state.battle_log) == 0 # No log message expected 