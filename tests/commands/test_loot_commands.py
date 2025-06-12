"""Test loot commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord import app_commands

@pytest.fixture
def mock_interaction():
    """Create a mock interaction for testing app commands."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 123456789
    interaction.user.name = "TestUser"
    interaction.user.display_name = "Test User"
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 987654321
    
    # Set up response methods
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    
    return interaction

@pytest.fixture
def mock_character_system():
    """Create a mock character system."""
    system = AsyncMock()
    system.get_character = AsyncMock(return_value=MagicMock(name="Test Character"))
    return system

@pytest.fixture
def mock_loot_system():
    """Create a mock loot system."""
    system = AsyncMock()
    system.get_character_loot = AsyncMock(return_value=[
        {"name": "Test Item", "value": 100, "quantity": 1}
    ])
    system.get_character_loot_history = AsyncMock(return_value=[
        {"timestamp": "2024-01-01", "item_name": "Test Item", "value": 100, "quantity": 1}
    ])
    system.sell_item = AsyncMock(return_value={
        "success": True,
        "item_name": "Test Item",
        "value": 100
    })
    return system

@pytest.fixture
def loot_commands_cog(mock_bot, mock_character_system, mock_loot_system):
    """Create a LootCommands cog with mocked dependencies."""
    from HCshinobi.bot.cogs.loot_commands import LootCommands
    cog = LootCommands(mock_bot)
    cog.character_system = mock_character_system
    cog.loot_system = mock_loot_system
    return cog

@pytest.mark.asyncio
async def test_loot_command(loot_commands_cog, mock_interaction):
    """Test the loot command."""
    # Get the command from the cog
    command = loot_commands_cog.loot
    assert command is not None, "Loot command not found"
    
    # Call the command
    await command.callback(loot_commands_cog, mock_interaction)
    
    # Verify response
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_loot_history_command(loot_commands_cog, mock_interaction):
    """Test the loot_history command."""
    # Get the command from the cog
    command = loot_commands_cog.loot_history
    assert command is not None, "Loot history command not found"
    
    # Call the command
    await command.callback(loot_commands_cog, mock_interaction)
    
    # Verify response
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_loot_sell_command(loot_commands_cog, mock_interaction):
    """Test the loot_sell command."""
    # Get the command from the cog
    command = loot_commands_cog.loot_sell
    assert command is not None, "Loot sell command not found"
    
    # Call the command
    await command.callback(loot_commands_cog, mock_interaction, item_id="test_item")
    
    # Verify response
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once()
    # TODO: Add specific assertions for loot_sell command output 