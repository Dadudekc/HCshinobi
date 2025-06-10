"""Tests for clan commands extension."""
import pytest
import discord
from discord.ext import commands
from discord import app_commands, Color
from unittest.mock import MagicMock, AsyncMock, patch
import pytest_asyncio

# Assuming these imports are correct based on project structure
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.character import Character
from HCshinobi.core.clan import Clan
from HCshinobi.extensions.clan_commands import ClanCommands
from HCshinobi.bot.bot import HCBot

# Fixtures
@pytest.fixture
def mock_bot():
    """Create mock bot instance with necessary services."""
    bot = AsyncMock(spec=commands.Bot)
    bot.services = MagicMock()
    bot.services.character_system = AsyncMock(spec=CharacterSystem)
    bot.services.clan_system = AsyncMock(spec=ClanSystem)
    bot.logger = MagicMock()
    return bot

@pytest.fixture
def mock_interaction():
    """Create a mock interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = "123456789"
    interaction.user.name = "TestUser"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.followup.send = AsyncMock()
    interaction.response.defer = AsyncMock()
    return interaction

@pytest.fixture
def mock_character():
    """Create a mock character."""
    return Character(
        id="123456789",
        name="Test Character",
        clan="Test Clan", # Initially in a clan for some tests
        level=5,
        exp=100,
        hp=100,
        chakra=100,
        stamina=100,
        strength=10,
        defense=10,
        speed=10,
        ninjutsu=10,
        willpower=10,
        max_hp=100,
        max_chakra=100,
        max_stamina=100,
        inventory=[],
        is_active=True,
        status_effects=[],
        wins=0,
        losses=0,
        draws=0
    )

@pytest_asyncio.fixture
async def mock_clan():
    # Provides a Clan instance consistent with the updated Clan.__init__
    return Clan(
        name="Test Clan",
        description="A clan for testing",
        rarity="rare",
        leader_id="leader123", # Added leader_id
        members=["123456789"],
        level=2 # Added level
        # Add other fields if needed by tests
    )

@pytest.fixture
def cog(mock_bot):
    """Create ClanCommands cog instance."""
    # Initialize with the mocked systems from bot.services
    return ClanCommands(
        mock_bot,
        mock_bot.services.clan_system,
        mock_bot.services.character_system
    )

# Tests
@pytest.mark.asyncio
async def test_clan_command_no_character(cog, mock_interaction):
    """Test /clan command when user has no character."""
    cog.character_system.get_character.return_value = None
    await cog.clan.callback(cog, mock_interaction)
    cog.character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    mock_interaction.response.send_message.assert_called_once_with("You need to create a character first!")

@pytest.mark.asyncio
async def test_clan_command_not_in_clan(cog, mock_interaction, mock_character):
    """Test /clan command when character is not in a clan."""
    mock_character.clan = None
    cog.character_system.get_character.return_value = mock_character
    await cog.clan.callback(cog, mock_interaction)
    cog.character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    mock_interaction.response.send_message.assert_called_once_with("You are not in a clan. Use /clan create or /clan join to join one!")

@pytest.mark.asyncio
async def test_clan_command_clan_not_found(cog, mock_interaction, mock_character):
    """Test /clan command when the character's clan doesn't exist in the system."""
    mock_character.clan = "Missing Clan"
    cog.character_system.get_character.return_value = mock_character
    cog.clan_system.get_clan.return_value = None
    await cog.clan.callback(cog, mock_interaction)
    cog.character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    cog.clan_system.get_clan.assert_called_once_with("Missing Clan")
    mock_interaction.response.send_message.assert_called_once_with("Your clan could not be found.")

@pytest.mark.asyncio
async def test_clan_command_success(cog, mock_interaction, mock_character, mock_clan):
    """Test successful /clan command execution."""
    mock_character.clan = mock_clan.name
    cog.character_system.get_character.return_value = mock_character
    cog.clan_system.get_clan.return_value = mock_clan # This mock_clan now includes leader_id

    await cog.clan.callback(cog, mock_interaction)

    cog.character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    cog.clan_system.get_clan.assert_called_once_with(mock_clan.name)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert embed.title == f"Clan: {mock_clan.name}"
    assert mock_clan.description in embed.description
    # Add more embed content checks if necessary

@pytest.mark.asyncio
async def test_clan_command_exception(cog, mock_interaction, mock_character):
    """Test /clan command general exception handling."""
    # Mock get_character to raise an error *before* clan logic runs
    test_exc = Exception("Database error")
    cog.character_system.get_character.side_effect = test_exc

    # Patch the module-level logger where the error is actually logged
    mock_logger = MagicMock()
    with patch('HCshinobi.extensions.clan_commands.logger', mock_logger):
        await cog.clan.callback(cog, mock_interaction)

    cog.character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    mock_interaction.response.send_message.assert_called_once_with(
        "An error occurred while retrieving clan information."
    )
    # Check that the *original* exception was logged using the patched logger
    mock_logger.error.assert_called_once()
    # Optional: check the log message content
    log_args, _ = mock_logger.error.call_args
    assert "Database error" in log_args[0]

# --- clan_create tests ---
@pytest.mark.asyncio
async def test_create_clan_no_character(cog, mock_interaction):
    """Test /clan_create when user has no character."""
    cog.character_system.get_character.return_value = None
    await cog.create_clan.callback(cog, mock_interaction, "New Clan", "Desc")
    mock_interaction.response.send_message.assert_called_once_with("You need to create a character first!")

@pytest.mark.asyncio
async def test_create_clan_already_in_clan(cog, mock_interaction, mock_character):
    """Test /clan_create when user is already in a clan."""
    mock_character.clan = "Existing Clan"
    cog.character_system.get_character.return_value = mock_character
    await cog.create_clan.callback(cog, mock_interaction, "New Clan", "Desc")
    mock_interaction.response.send_message.assert_called_once_with("You are already in a clan!")

@pytest.mark.asyncio
async def test_create_clan_failed(cog, mock_interaction, mock_character):
    """Test /clan_create when clan system fails to create."""
    mock_character.clan = None
    cog.character_system.get_character.return_value = mock_character
    cog.clan_system.create_clan.return_value = None # Simulate failure (e.g., name taken)
    await cog.create_clan.callback(cog, mock_interaction, "Taken Name", "Desc")
    cog.clan_system.create_clan.assert_called_once_with("Taken Name", str(mock_interaction.user.id), "Desc")
    mock_interaction.response.send_message.assert_called_once_with("Failed to create clan. The name may be taken.")

@pytest.mark.asyncio
async def test_create_clan_success(cog, mock_interaction, mock_character):
    """Test successful /clan_create."""
    clan_name = "New Clan"
    description = "A new clan"
    mock_character.clan = None
    cog.character_system.get_character.return_value = mock_character
    # Assume create_clan returns the created Clan object
    # Mock the ClanSystem.create_clan method
    created_clan_instance = Clan(
        name=clan_name,
        description=description,
        rarity="common", # Assuming default or based on cost/logic
        leader_id=str(mock_interaction.user.id),
        members=[str(mock_interaction.user.id)],
        level=1
    )
    cog.clan_system.create_clan.return_value = created_clan_instance
    # Ensure the mock character_system has the update_character method
    cog.character_system.update_character = AsyncMock(return_value=True)
    # cog.character_system.update_character.return_value = True # Assume update succeeds

    await cog.create_clan.callback(cog, mock_interaction, clan_name, description)

    cog.character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    # Verify create_clan call arguments (using positional args as called in the cog)
    cog.clan_system.create_clan.assert_called_once_with(
        clan_name,
        str(mock_interaction.user.id),
        description
    )
    # Verify character update call
    cog.character_system.update_character.assert_called_once_with(
        str(mock_interaction.user.id), {"clan": clan_name}
    )
    # Verify success response (checks embed)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert embed.title == "Clan Created"
    assert clan_name in embed.description
    # assert mock_interaction.response.send_message.assert_called_once_with(
    #     f"Clan '{clan_name}' created successfully!", ephemeral=True
    # )

# --- clan_join tests ---
@pytest.mark.asyncio
async def test_join_clan_no_character(cog, mock_interaction):
    """Test /clan_join when user has no character."""
    cog.character_system.get_character.return_value = None
    await cog.join_clan.callback(cog, mock_interaction, "Target Clan")
    mock_interaction.response.send_message.assert_called_once_with("You need to create a character first!")

@pytest.mark.asyncio
async def test_join_clan_already_in_clan(cog, mock_interaction, mock_character):
    """Test /clan_join when user is already in a clan."""
    mock_character.clan = "Existing Clan"
    cog.character_system.get_character.return_value = mock_character
    await cog.join_clan.callback(cog, mock_interaction, "Target Clan")
    mock_interaction.response.send_message.assert_called_once_with("You are already in a clan!")

@pytest.mark.asyncio
async def test_join_clan_not_found(cog, mock_interaction, mock_character):
    """Test /clan_join when target clan doesn't exist."""
    mock_character.clan = None
    cog.character_system.get_character.return_value = mock_character
    cog.clan_system.get_clan.return_value = None
    await cog.join_clan.callback(cog, mock_interaction, "NonExistent Clan")
    cog.clan_system.get_clan.assert_called_once_with("NonExistent Clan")
    mock_interaction.response.send_message.assert_called_once_with("Clan 'NonExistent Clan' not found.")

@pytest.mark.asyncio
async def test_join_clan_failed(cog, mock_interaction, mock_character, mock_clan):
    """Test /clan_join when adding member fails."""
    mock_character.clan = None
    cog.character_system.get_character.return_value = mock_character
    cog.clan_system.get_clan.return_value = mock_clan
    cog.clan_system.add_member.return_value = False # Simulate failure
    await cog.join_clan.callback(cog, mock_interaction, mock_clan.name)
    cog.clan_system.add_member.assert_called_once_with(mock_clan.name, str(mock_interaction.user.id))
    mock_interaction.response.send_message.assert_called_once_with("Failed to join clan.")

@pytest.mark.asyncio
async def test_join_clan_success(cog, mock_interaction, mock_character, mock_clan):
    """Test successful /clan_join."""
    mock_character.clan = None
    cog.character_system.get_character.return_value = mock_character
    # Ensure update_character is mocked as async
    cog.character_system.update_character = AsyncMock(return_value=True)
    cog.clan_system.get_clan.return_value = mock_clan
    cog.clan_system.add_member.return_value = True
    await cog.join_clan.callback(cog, mock_interaction, mock_clan.name)
    cog.clan_system.add_member.assert_called_once_with(mock_clan.name, str(mock_interaction.user.id))
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert embed.title == "Clan Joined"
    assert embed.description == f"Successfully joined clan: {mock_clan.name}"
    assert embed.color == cog._get_rarity_color(mock_clan.rarity)

# --- clan_leave tests ---
@pytest.mark.asyncio
async def test_leave_clan_no_character(cog, mock_interaction):
    """Test /clan_leave when user has no character."""
    cog.character_system.get_character.return_value = None
    await cog.leave_clan.callback(cog, mock_interaction)
    mock_interaction.response.send_message.assert_called_once_with("You need to create a character first!")

@pytest.mark.asyncio
async def test_leave_clan_not_in_clan(cog, mock_interaction, mock_character):
    """Test /clan_leave when user is not in a clan."""
    mock_character.clan = None
    cog.character_system.get_character.return_value = mock_character
    await cog.leave_clan.callback(cog, mock_interaction)
    mock_interaction.response.send_message.assert_called_once_with("You are not in a clan!")

@pytest.mark.asyncio
async def test_leave_clan_failed(cog, mock_interaction, mock_character):
    """Test /clan_leave when removing member fails."""
    mock_character.clan = "Test Clan"
    cog.character_system.get_character.return_value = mock_character
    cog.clan_system.remove_member.return_value = False # Simulate failure
    await cog.leave_clan.callback(cog, mock_interaction)
    cog.clan_system.remove_member.assert_called_once_with(mock_character.clan, str(mock_interaction.user.id))
    mock_interaction.response.send_message.assert_called_once_with("Failed to leave clan.")

@pytest.mark.asyncio
async def test_leave_clan_success(cog, mock_interaction, mock_character):
    """Test successful /clan_leave."""
    mock_character.clan = "Test Clan"
    cog.character_system.get_character.return_value = mock_character
    # Ensure update_character is mocked as async
    cog.character_system.update_character = AsyncMock(return_value=True)
    cog.clan_system.remove_member.return_value = True
    await cog.leave_clan.callback(cog, mock_interaction)
    cog.clan_system.remove_member.assert_called_once_with(mock_character.clan, str(mock_interaction.user.id))
    mock_interaction.response.send_message.assert_called_once_with("Successfully left your clan.")

# --- clan_list tests ---
@pytest.mark.asyncio
async def test_clan_list_no_clans(cog, mock_interaction):
    """Test /clan_list when no clans exist."""
    cog.clan_system.get_all_clans.return_value = []
    await cog.clan_list.callback(cog, mock_interaction)
    cog.clan_system.get_all_clans.assert_called_once()
    mock_interaction.response.send_message.assert_called_once_with("No clans found.")

@pytest.mark.asyncio
async def test_clan_list_success(cog, mock_interaction, mock_clan):
    """Test successful /clan_list."""
    # Create a second clan instance with all required args
    clan_two = Clan(
        name="Clan Two",
        description="The second clan",
        rarity="common",
        leader_id="leader456",
        members=[]
    )
    clans = [mock_clan, clan_two]
    cog.clan_system.get_all_clans.return_value = clans

    await cog.clan_list.callback(cog, mock_interaction)

    cog.clan_system.get_all_clans.assert_called_once()
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert embed.title == "Available Clans"
    # Check if both clan names are in the embed field names
    field_names = [f.name for f in embed.fields]
    assert any(mock_clan.name in name for name in field_names)
    assert any(clan_two.name in name for name in field_names)

# --- _get_rarity_color test ---
def test_get_rarity_color(cog): # Pass the cog fixture
    """Test that rarity colors are correctly mapped."""
    assert cog._get_rarity_color('common') == Color.light_grey()
    assert cog._get_rarity_color('uncommon') == Color.green()
    assert cog._get_rarity_color('rare') == Color.blue()
    assert cog._get_rarity_color('epic') == Color.purple()
    assert cog._get_rarity_color('legendary') == Color.gold()
    assert cog._get_rarity_color('unknown') == Color.default()

# Note: Removed tests that were overly complex or tested outdated functionality
# Removed: test_clan_commands_missing_dependencies (hard to test service removal reliably)
# Removed: test_my_clan_command (used non-existent fixtures/attributes)
# Removed: test_setup_missing_attributes (similar to above)
# Removed: test_clan_info & test_clan_info_not_found (functionality merged into /clan)

async def test_clan_command_exceptions(self):
    """Test exception handling in clan commands."""
    # Test create command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.create_clan(self.interaction, "")  # Empty name
        
    with self.assertRaises(ValueError):
        await self.clan_cog.create_clan(self.interaction, "A" * 51)  # Name too long
        
    # Test join command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.join_clan(self.interaction, "")  # Empty clan name
        
    with self.assertRaises(ValueError):
        await self.clan_cog.join_clan(self.interaction, "NonexistentClan")  # Clan doesn't exist
        
    # Test leave command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.leave_clan(self.interaction)  # Not in a clan
        
    # Test list command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.list_clans(self.interaction, page=0)  # Invalid page number
        
    with self.assertRaises(ValueError):
        await self.clan_cog.list_clans(self.interaction, page_size=0)  # Invalid page size
        
    # Test clan info command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.clan_info(self.interaction, "")  # Empty clan name
        
    with self.assertRaises(ValueError):
        await self.clan_cog.clan_info(self.interaction, "NonexistentClan")  # Clan doesn't exist
        
    # Test clan leader command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.clan_leader(self.interaction, "")  # Empty clan name
        
    with self.assertRaises(ValueError):
        await self.clan_cog.clan_leader(self.interaction, "NonexistentClan")  # Clan doesn't exist
        
    # Test clan members command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.clan_members(self.interaction, "")  # Empty clan name
        
    with self.assertRaises(ValueError):
        await self.clan_cog.clan_members(self.interaction, "NonexistentClan")  # Clan doesn't exist
        
    # Test clan disband command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.disband_clan(self.interaction)  # Not in a clan
        
    with self.assertRaises(ValueError):
        await self.clan_cog.disband_clan(self.interaction)  # Not clan leader
        
    # Test clan kick command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.kick_member(self.interaction, None)  # No member specified
        
    with self.assertRaises(ValueError):
        await self.clan_cog.kick_member(self.interaction, "NonexistentUser")  # User doesn't exist
        
    with self.assertRaises(ValueError):
        await self.clan_cog.kick_member(self.interaction, "ValidUser")  # Not clan leader
        
    # Test clan promote command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.promote_member(self.interaction, None)  # No member specified
        
    with self.assertRaises(ValueError):
        await self.clan_cog.promote_member(self.interaction, "NonexistentUser")  # User doesn't exist
        
    with self.assertRaises(ValueError):
        await self.clan_cog.promote_member(self.interaction, "ValidUser")  # Not clan leader
        
    # Test clan demote command exceptions
    with self.assertRaises(ValueError):
        await self.clan_cog.demote_member(self.interaction, None)  # No member specified
        
    with self.assertRaises(ValueError):
        await self.clan_cog.demote_member(self.interaction, "NonexistentUser")  # User doesn't exist
        
    with self.assertRaises(ValueError):
        await self.clan_cog.demote_member(self.interaction, "ValidUser")  # Not clan leader 