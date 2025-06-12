import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

# Adjust path as needed
from HCshinobi.bot.cogs.missions import MissionCommands

pytestmark = pytest.mark.asyncio

# --- Fixtures --- 
@pytest.fixture
def mock_bot():
    """Fixture to create a mock bot with required services."""
    bot = MagicMock()
    
    # Set up mission system
    mission_system = MagicMock()
    mission_system.get_available_missions = AsyncMock()
    mission_system.accept_mission = AsyncMock()
    mission_system.complete_mission = AsyncMock()
    mission_system.get_active_mission = AsyncMock()
    bot.mission_system = mission_system
    
    # Set up character system
    character_system = MagicMock()
    character_system.get_character = AsyncMock()
    bot.character_system = character_system
    
    # Set up logger
    bot.logger = MagicMock()
    
    return bot

@pytest.fixture
def missions_cog(mock_bot):
    """Fixture to create an instance of the MissionCommands cog."""
    return MissionCommands(bot=mock_bot)

@pytest.fixture
def mock_interaction_missions():
    """Fixture for a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = "5555555555"
    interaction.user.display_name = "MissionTester"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.followup.send = AsyncMock()
    return interaction

# --- Tests --- 
class TestMissionCommands:

    async def test_mission_board_success(self, missions_cog, mock_interaction_missions, mock_bot):
        """Test /mission_board successfully displays available missions."""
        # Arrange
        player_id = mock_interaction_missions.user.id
        mock_character = MagicMock() # Assume character exists
        mock_bot.character_system.get_character.return_value = mock_character
        
        mock_missions = [
            {"mission_id": "M001", "title": "Deliver Scrolls", "rank": "D", "description": "Take these scrolls...", "reward_exp": 50, "reward_ryo": 10},
            {"mission_id": "M002", "title": "Guard Duty", "rank": "C", "description": "Stand post...", "reward_exp": 150, "reward_ryo": 30}
        ]
        mock_bot.mission_system.get_available_missions.return_value = mock_missions

        # Act
        # Call the callback directly, passing the cog instance (self)
        await missions_cog.mission_board.callback(missions_cog, mock_interaction_missions)

        # Assert
        mock_bot.character_system.get_character.assert_awaited_once_with(player_id)
        # Check await count explicitly if assert_awaited_once fails
        assert mock_bot.character_system.get_character.await_count == 1
        mock_bot.mission_system.get_available_missions.assert_awaited_once_with(player_id)
        assert mock_bot.mission_system.get_available_missions.await_count == 1
        mock_interaction_missions.response.send_message.assert_called_once()
        # Use the correct fixture name
        args, kwargs = mock_interaction_missions.response.send_message.call_args 
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == "🗒️ Mission Board"
        assert len(sent_embed.fields) == len(mock_missions)
        assert "Deliver Scrolls" in sent_embed.fields[0].name

    async def test_mission_board_no_character(self, missions_cog, mock_interaction_missions, mock_bot):
        """Test /mission_board when user has no character."""
        # Arrange
        player_id = mock_interaction_missions.user.id
        mock_bot.character_system.get_character.return_value = None # No character

        # Act
        await missions_cog.mission_board.callback(missions_cog, mock_interaction_missions)

        # Assert
        mock_bot.character_system.get_character.assert_awaited_once_with(player_id)
        # Check await count explicitly
        assert mock_bot.character_system.get_character.await_count == 1
        mock_bot.mission_system.get_available_missions.assert_not_awaited()
        mock_interaction_missions.response.send_message.assert_called_once_with(
            "You don't have a character. Use `/create` to create one.",
            ephemeral=True
        )

    async def test_mission_accept_success(self, missions_cog, mock_interaction_missions, mock_bot):
        """Test /mission_accept successfully accepts a mission."""
        # Arrange
        player_id = mock_interaction_missions.user.id
        mission_number_to_accept = 1 # User interacts with the number
        expected_mission_id = "M001" # The ID corresponding to number 1
        mock_character = MagicMock()
        mock_bot.character_system.get_character.return_value = mock_character

        # Mock available missions so the cog can find the mission_id
        mock_available = [
            {"mission_id": expected_mission_id, "title": "Test Mission"} # Add other fields if needed by cog
        ]
        mock_bot.mission_system.get_available_missions.return_value = mock_available

        # Mock mission system response for assigning the mission
        mock_accept_response = (True, f"Mission '{expected_mission_id}' accepted!") # Use ID in message
        # Ensure assign_mission is the method being mocked, and it's async
        mock_bot.mission_system.assign_mission = AsyncMock(return_value=mock_accept_response)

        # Act: Call the callback directly, passing the cog instance (self)
        await missions_cog.mission_accept.callback(missions_cog, mock_interaction_missions, mission_number=mission_number_to_accept)

        # Assert
        mock_bot.character_system.get_character.assert_awaited_once_with(player_id)
        # Cog calls get_available_missions first
        mock_bot.mission_system.get_available_missions.assert_awaited_once_with(player_id)
        # Check that assign_mission was called with the correct mission_id
        mock_bot.mission_system.assign_mission.assert_awaited_once_with(player_id, expected_mission_id)
        mock_interaction_missions.response.send_message.assert_awaited_once()
        args, kwargs = mock_interaction_missions.response.send_message.call_args
        # Check response message (plain text, not embed according to cog code)
        assert kwargs.get('embed') is None
        assert isinstance(args[0], str)
        assert f"Mission '{expected_mission_id}' accepted!" in args[0]
        # assert sent_embed.title == "Mission Accepted" # Remove embed checks

    # TODO: Add test for mission_accept when mission not found / already active / requirements not met
    # TODO: Add tests for other mission commands (progress, complete, abandon etc.) 