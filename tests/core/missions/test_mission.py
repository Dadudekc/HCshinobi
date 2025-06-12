"""
Tests for the mission system.
"""
import pytest
from datetime import datetime, timedelta
from HCshinobi.core.missions.mission import Mission, MissionStatus, MissionDifficulty

@pytest.fixture
def sample_mission():
    """Create a sample mission for testing."""
    return Mission(
        id="test_mission_1",
        title="Test Mission",
        description="A test mission description",
        difficulty=MissionDifficulty.D_RANK,
        village="Leaf",
        reward={"ryo": 1000, "exp": 500, "items": ["test_item"]},
        duration=timedelta(hours=1),
        requirements={
            "min_level": 5,
            "team_size": 1,
            "special_requirements": ["test_requirement"]
        }
    )

def test_mission_creation(sample_mission):
    """Test mission creation and properties."""
    assert sample_mission.id == "test_mission_1"
    assert sample_mission.title == "Test Mission"
    assert sample_mission.difficulty == MissionDifficulty.D_RANK
    assert sample_mission.village == "Leaf"
    assert sample_mission.status == MissionStatus.AVAILABLE
    assert sample_mission.reward["ryo"] == 1000
    assert sample_mission.reward["exp"] == 500
    assert sample_mission.reward["items"] == ["test_item"]
    assert sample_mission.duration == timedelta(hours=1)
    assert sample_mission.requirements["min_level"] == 5
    assert sample_mission.requirements["team_size"] == 1
    assert sample_mission.requirements["special_requirements"] == ["test_requirement"]

def test_mission_serialization(sample_mission):
    """Test mission serialization to and from dictionary."""
    mission_dict = sample_mission.to_dict()
    new_mission = Mission.from_dict(mission_dict)
    
    assert new_mission.id == sample_mission.id
    assert new_mission.title == sample_mission.title
    assert new_mission.difficulty == sample_mission.difficulty
    assert new_mission.village == sample_mission.village
    assert new_mission.status == sample_mission.status
    assert new_mission.reward == sample_mission.reward
    assert new_mission.duration == sample_mission.duration
    assert new_mission.requirements == sample_mission.requirements

def test_mission_lifecycle(sample_mission):
    """Test mission status changes."""
    # Test starting mission
    sample_mission.start()
    assert sample_mission.status == MissionStatus.IN_PROGRESS
    assert sample_mission.started_at is not None
    
    # Test completing mission
    sample_mission.complete()
    assert sample_mission.status == MissionStatus.COMPLETED
    assert sample_mission.completed_at is not None

def test_mission_expiration(sample_mission):
    """Test mission expiration check."""
    sample_mission.start()
    assert not sample_mission.check_expired()
    
    # Set duration to 0 to force expiration
    sample_mission.duration = timedelta(seconds=0)
    assert sample_mission.check_expired()

def test_mission_progress(sample_mission):
    """Test mission progress updates."""
    sample_mission.start()
    
    # Update progress
    sample_mission.update_progress("test_key", 10)
    assert sample_mission.progress["test_key"] == 10
    
    # Try updating non-active mission
    sample_mission.complete()
    with pytest.raises(ValueError):
        sample_mission.update_progress("test_key", 20)

def test_mission_validation(sample_mission):
    """Test mission validation rules."""
    # Test invalid status changes
    with pytest.raises(ValueError):
        sample_mission.complete()  # Can't complete before starting
    
    sample_mission.start()
    sample_mission.complete()
    
    with pytest.raises(ValueError):
        sample_mission.start()  # Can't start completed mission
    
    with pytest.raises(ValueError):
        sample_mission.fail()  # Can't fail completed mission 