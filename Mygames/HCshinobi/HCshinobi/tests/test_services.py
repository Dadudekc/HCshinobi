"""Test suite for service container."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from HCshinobi.bot.services import ServiceContainer
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.character_manager import CharacterManager
from HCshinobi.core.token_system import TokenSystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.personality_modifiers import PersonalityModifiers

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return Mock(
        data_dir="test_data",
        ollama_base_url="http://localhost:11434",
        ollama_model="mistral",
        openai_api_key="test_key",
        openai_target_url="http://localhost:8000",
        openai_headless=True
    )

@pytest.mark.asyncio
async def test_service_container_initialization(mock_config):
    """Test service container initialization."""
    services = ServiceContainer(mock_config)
    
    # Before initialization, services should raise RuntimeError
    with pytest.raises(RuntimeError):
        _ = services.clan_data
        
    # After initialization, services should be available
    await services.initialize()
    assert services.clan_data is not None
    assert services.token_system is not None
    assert services.npc_manager is not None

@pytest.mark.asyncio
async def test_service_container_initialize(mock_config):
    """Test service container initialization."""
    services = ServiceContainer(mock_config)
    await services.initialize()

    # Check that the main system instances are created
    assert isinstance(services.clan_system, ClanSystem)
    assert isinstance(services.character_system, CharacterSystem)
    assert isinstance(services.battle_system, BattleSystem)
    assert isinstance(services.token_system, TokenSystem)
    assert isinstance(services.clan_data, ClanData) # Check underlying data manager
    assert isinstance(services.personality_modifiers, PersonalityModifiers)
    # AI clients might be None if keys are not mocked/provided
    # assert services.ollama_client is not None
    # assert services.openai_client is not None
    assert services.notification_dispatcher is not None

@pytest.mark.asyncio
async def test_service_container_shutdown(mock_config):
    """Test service container shutdown."""
    services = ServiceContainer(mock_config)
    await services.initialize()
    
    # Services should be available after initialization
    assert services.clan_data is not None
    
    # After shutdown, services should be cleaned up
    await services.shutdown()
    with pytest.raises(RuntimeError):
        _ = services.clan_data 