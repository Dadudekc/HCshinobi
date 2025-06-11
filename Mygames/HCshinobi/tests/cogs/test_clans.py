import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum
import discord

# Adjust path as needed
from HCshinobi.bot.cogs.clans import ClanCommands, RarityTier, get_rarity_color

pytestmark = pytest.mark.asyncio

# If importing real RarityTier/get_rarity_color is problematic, keep mocks:
# class RarityTier(Enum): ...
# def get_rarity_color(rarity_str: str): ...

# --- Fixtures --- 
@pytest.fixture
def mock_bot_clans():
    """Fixture for a mock bot with clan-related services correctly mocked."""
    bot = MagicMock(spec=["services"])
    bot.services = MagicMock()
    bot.services.character_system = AsyncMock()
    # get_player_clan is SYNC according to cog code
    bot.services.clan_assignment_engine = MagicMock() # Changed to MagicMock
    bot.services.clan_assignment_engine.get_player_clan = MagicMock() # Mock the method
    # Mock the service object itself
    bot.services.clan_data = AsyncMock()
    # Mock async methods on the service
    bot.services.clan_data.get_clan_by_name = AsyncMock() # This is awaited
    bot.services.clan_data.get_all_clans = AsyncMock() # This is awaited
    bot.services.clan_data.add_clan = AsyncMock()      # This is awaited
    bot.services.token_system = AsyncMock()
    bot.services.npc_manager = AsyncMock()
    bot.services.personality_modifiers = AsyncMock()
    return bot

@pytest.fixture
def clans_cog(mock_bot_clans):
    """Fixture to create an instance of the ClanCommands cog."""
    # Pass the mock bot to the cog constructor
    cog = ClanCommands(bot=mock_bot_clans)
    # Allow mocks for functions within the cog's module if needed
    # E.g., patch get_rarity_color directly if it causes issues
    return cog

@pytest.fixture
def mock_interaction_clans():
    """Fixture for a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = "9876543210"
    interaction.user.display_name = "ClanTester"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.followup.send = AsyncMock()
    # Mock guild permissions if needed for admin checks
    interaction.user.guild_permissions = MagicMock(spec=discord.Permissions)
    interaction.user.guild_permissions.administrator = False # Default to not admin
    return interaction

# --- Tests --- 
class TestClanCommands:

    @patch("HCshinobi.bot.cogs.clans.get_rarity_color")
    async def test_my_clan_has_clan(self, mock_get_color, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /my_clan successfully displays the user's assigned clan info."""
        # Arrange
        user_id = mock_interaction_clans.user.id
        clan_name = "Uchiha"
        mock_clan_details = {
            'name': clan_name,
            'description': 'Sharingan users',
            'rarity': RarityTier.LEGENDARY.value,
            'members': [user_id, "111", "222"]
        }
        # Mock the assignment engine to return the clan name
        mock_bot_clans.services.clan_assignment_engine.get_player_clan = MagicMock(return_value=clan_name)
        # Mock clan_data to return details for that clan name
        mock_bot_clans.services.clan_data.get_clan_by_name = AsyncMock(return_value=mock_clan_details)
        mock_get_color.return_value = discord.Color.red()

        # Act
        await clans_cog.my_clan.callback(clans_cog, mock_interaction_clans)

        # Assert
        mock_bot_clans.services.clan_assignment_engine.get_player_clan.assert_called_once_with(user_id)
        mock_bot_clans.services.clan_data.get_clan_by_name.assert_awaited_once_with(clan_name)
        mock_interaction_clans.response.send_message.assert_awaited_once()
        _, kwargs = mock_interaction_clans.response.send_message.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == "Your Clan Assignment"
        assert f"You belong to the **{clan_name}** clan." in sent_embed.description
        assert any(field.name == "Rarity" and field.value == RarityTier.LEGENDARY.value for field in sent_embed.fields)
        assert sent_embed.color == discord.Color.red()
        assert kwargs.get('ephemeral') is True # /my_clan is ephemeral
        
    async def test_my_clan_no_clan(self, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /my_clan when the user has no clan assigned."""
        # Arrange
        user_id = mock_interaction_clans.user.id
        # Mock assignment engine to return None
        mock_bot_clans.services.clan_assignment_engine.get_player_clan = MagicMock(return_value=None)
        # Mock clan_data just in case (shouldn't be called)
        mock_bot_clans.services.clan_data.get_clan_by_name = AsyncMock(return_value=None)
        
        # Act
        await clans_cog.my_clan.callback(clans_cog, mock_interaction_clans)
        
        # Assert
        mock_bot_clans.services.clan_assignment_engine.get_player_clan.assert_called_once_with(user_id)
        # Ensure get_clan_by_name was NOT called
        mock_bot_clans.services.clan_data.get_clan_by_name.assert_not_awaited()
        mock_interaction_clans.response.send_message.assert_awaited_once_with(
            "You have not been assigned a clan yet. Use `/roll_clan` to get started!",
            ephemeral=True
        )

    @patch("HCshinobi.bot.cogs.clans.get_rarity_color")
    async def test_clan_list_success(self, mock_get_color, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /clan_list successfully lists clans by rarity."""
        # Arrange
        mock_clans = [
            {'name': 'Uchiha', 'rarity': RarityTier.LEGENDARY.value, 'members': []},
            {'name': 'Senju', 'rarity': RarityTier.LEGENDARY.value, 'members': []},
            {'name': 'Hyuga', 'rarity': RarityTier.RARE.value, 'members': []},
            {'name': 'Nara', 'rarity': RarityTier.UNCOMMON.value, 'members': []},
            {'name': 'Akimichi', 'rarity': RarityTier.UNCOMMON.value, 'members': []},
            {'name': 'Yamanaka', 'rarity': RarityTier.UNCOMMON.value, 'members': []},
        ]
        mock_bot_clans.services.clan_data.get_all_clans = AsyncMock(return_value=mock_clans)

        # Act
        await clans_cog.clan_list.callback(clans_cog, mock_interaction_clans)

        # Assert
        mock_bot_clans.services.clan_data.get_all_clans.assert_awaited_once()
        mock_interaction_clans.response.send_message.assert_awaited_once()
        _, kwargs = mock_interaction_clans.response.send_message.call_args
        sent_embed = kwargs.get('embed')

        assert sent_embed is not None
        assert sent_embed.title == "Available Clans"
        assert len(sent_embed.fields) == 3 # Legendary, Rare, Uncommon

        # Check Legendary field
        legendary_field = discord.utils.get(sent_embed.fields, name=f"🏅 {RarityTier.LEGENDARY.value}")
        assert legendary_field is not None
        assert legendary_field.value == "- Senju\n- Uchiha" # Check sorting
        assert legendary_field.inline is False

        # Check Rare field
        rare_field = discord.utils.get(sent_embed.fields, name=f"🏅 {RarityTier.RARE.value}")
        assert rare_field is not None
        assert rare_field.value == "- Hyuga"
        assert rare_field.inline is False
        
        # Check Uncommon field
        uncommon_field = discord.utils.get(sent_embed.fields, name=f"🏅 {RarityTier.UNCOMMON.value}")
        assert uncommon_field is not None
        assert uncommon_field.value == "- Akimichi\n- Nara\n- Yamanaka" # Check sorting
        assert uncommon_field.inline is False
        
        # Check Common and Epic are NOT present
        common_field = discord.utils.get(sent_embed.fields, name=f"🏅 {RarityTier.COMMON.value}")
        assert common_field is None
        epic_field = discord.utils.get(sent_embed.fields, name=f"🏅 {RarityTier.EPIC.value}")
        assert epic_field is None
        
        # Ensure message is not ephemeral by default
        assert kwargs.get('ephemeral') is not True
        
    async def test_clan_list_no_clans(self, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /clan_list when no clans are loaded."""
        # Arrange
        mock_bot_clans.services.clan_data.get_all_clans = AsyncMock(return_value=[]) # Return empty list

        # Act
        await clans_cog.clan_list.callback(clans_cog, mock_interaction_clans)

        # Assert
        mock_bot_clans.services.clan_data.get_all_clans.assert_awaited_once()
        mock_interaction_clans.response.send_message.assert_awaited_once()
        args, kwargs = mock_interaction_clans.response.send_message.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert "No clans have been loaded" in sent_embed.description
        assert len(sent_embed.fields) == 0
        # Check if ephemeral=True is expected here based on cog logic
        # Looking at the cog, it sends ephemeral=True when no clans are loaded.
        assert kwargs.get('ephemeral') is True 

    @patch("HCshinobi.bot.cogs.clans.get_rarity_color")
    async def test_clan_info_success(self, mock_get_color, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /clan_info successfully retrieves clan details."""
        # Arrange
        mock_get_color.return_value = discord.Color.green()
        clan_name = "Aburame"
        mock_clan_details = {
            "name": clan_name,
            "description": "Insect users",
            "rarity": RarityTier.RARE.value,
            "members": ["1", "2"]
        }
        mock_bot_clans.services.clan_data.get_clan_by_name.return_value = mock_clan_details

        # Act
        await clans_cog.clan_info.callback(clans_cog, mock_interaction_clans, clan_name=clan_name)

        # Assert
        mock_bot_clans.services.clan_data.get_clan_by_name.assert_awaited_once_with(clan_name)
        mock_interaction_clans.response.send_message.assert_awaited_once()
        _, kwargs = mock_interaction_clans.response.send_message.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == f"{clan_name} Clan"
        assert sent_embed.description == "Insect users"
        assert any(field.name == "Rarity" and field.value == RarityTier.RARE.value for field in sent_embed.fields)
        assert any(field.name == "Members" and field.value == "2" for field in sent_embed.fields)
        assert sent_embed.color == discord.Color.green()
        assert kwargs.get('ephemeral') is not True

    @patch("HCshinobi.bot.cogs.clans.get_rarity_color")
    async def test_clan_info_not_found(self, mock_get_color, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /clan_info when the clan name is not found but suggestions exist."""
        # Arrange
        mock_get_color.return_value = discord.Color.red() # Not used if text is sent
        clan_name = "NonExistentClan"
        mock_bot_clans.services.clan_data.get_clan_by_name.return_value = None
        # Mock get_all_clans to return names that will be found by the basic suggestion logic
        suggestions_data = [{"name": "NonExistentClanImposter"}, {"name": "AnotherClan"}]
        mock_bot_clans.services.clan_data.get_all_clans.return_value = suggestions_data
        # Define the expected suggestions based on the cog's logic
        expected_suggestions = ["NonExistentClanImposter"]

        # Act
        await clans_cog.clan_info.callback(clans_cog, mock_interaction_clans, clan_name=clan_name)

        # Assert
        mock_bot_clans.services.clan_data.get_clan_by_name.assert_awaited_once_with(clan_name)
        # Assert get_all_clans was awaited (since get_clan_by_name returned None)
        mock_bot_clans.services.clan_data.get_all_clans.assert_awaited_once()
        mock_interaction_clans.response.send_message.assert_awaited_once()

        # Construct the exact expected message based on the expected_suggestions, matching cog output
        expected_suggestions_text = "\n".join(expected_suggestions) # No dash needed
        expected_response_msg = (f"Clan '{clan_name}' not found. " # Adjusted punctuation/spacing slightly if needed
                                 f"Did you mean one of these?\n{expected_suggestions_text}")

        # Assert the exact message was sent
        mock_interaction_clans.response.send_message.assert_awaited_once_with(
            expected_response_msg,
            ephemeral=True
        )
        # Keep the embed check for clarity, though covered by the above assert
        _, kwargs = mock_interaction_clans.response.send_message.call_args
        assert kwargs.get('embed') is None

    @patch("HCshinobi.bot.cogs.clans.get_rarity_color", return_value=discord.Color.default())
    async def test_create_clan_success(self, mock_get_color, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /create_clan successfully adds a clan (admin only)."""
        # Arrange
        # Ensure user has admin perms *within this test*
        mock_interaction_clans.user.guild_permissions.administrator = True
        clan_name = "TestClan"
        clan_desc = "A clan for testing"
        # Ensure a valid rarity value from the Enum is passed
        clan_rarity_value = RarityTier.COMMON.value
        mock_bot_clans.services.clan_data.add_clan.return_value = True

        # Act
        await clans_cog.create_clan.callback(clans_cog, mock_interaction_clans, name=clan_name, description=clan_desc, rarity=clan_rarity_value)

        # Assert
        mock_bot_clans.services.clan_data.add_clan.assert_awaited_once()
        call_args, _ = mock_bot_clans.services.clan_data.add_clan.call_args
        added_clan_dict = call_args[0]
        assert added_clan_dict.get("name") == clan_name
        assert added_clan_dict.get("description") == clan_desc
        assert added_clan_dict.get("rarity") == clan_rarity_value
        assert added_clan_dict.get("members") == []
        
        # Check response
        mock_interaction_clans.response.send_message.assert_awaited_once()
        args, kwargs = mock_interaction_clans.response.send_message.call_args
        assert f"Successfully created clan {clan_name}" in args[0]
        assert kwargs.get('ephemeral') == True

    async def test_create_clan_no_permission(self, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /create_clan fails if user is not admin."""
        # Arrange
        # Mock user permissions to NOT be administrator
        mock_interaction_clans.user.guild_permissions = MagicMock(spec=discord.Permissions)
        mock_interaction_clans.user.guild_permissions.administrator = False
        
        # Act
        await clans_cog.create_clan.callback(clans_cog, mock_interaction_clans, name="Test", description="Desc", rarity=RarityTier.COMMON.value)
        
        # Assert
        mock_interaction_clans.response.send_message.assert_called_once_with(
            "You need administrator permissions to create clans.",
            ephemeral=True
        )
        mock_bot_clans.services.clan_data.add_clan.assert_not_called() # Ensure not called

    # --- /join_clan tests --- 

    async def test_join_clan_success(self, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test successfully joining a clan."""
        # Arrange
        user_id = mock_interaction_clans.user.id
        clan_name = "Nara"
        mock_clan_details = {
            'name': clan_name,
            'description': 'Shadow users',
            'rarity': RarityTier.UNCOMMON.value,
            'members': ["111111"] # Existing members, not the user
        }
        mock_bot_clans.services.clan_data.get_clan_by_name.return_value = mock_clan_details
        mock_bot_clans.services.clan_data.update_clan = AsyncMock() # Mock the update method

        # Act
        await clans_cog.join_clan.callback(clans_cog, mock_interaction_clans, clan_name=clan_name)

        # Assert
        mock_bot_clans.services.clan_data.get_clan_by_name.assert_awaited_once_with(clan_name)
        # Check that update_clan was called with the user added
        mock_bot_clans.services.clan_data.update_clan.assert_awaited_once()
        call_args, _ = mock_bot_clans.services.clan_data.update_clan.call_args
        updated_clan_dict = call_args[0]
        assert user_id in updated_clan_dict['members']
        assert "111111" in updated_clan_dict['members'] # Ensure original members remain
        assert updated_clan_dict['name'] == clan_name # Ensure other data is preserved
        
        # Check response
        mock_interaction_clans.response.send_message.assert_awaited_once_with(
            f"Successfully joined clan {clan_name}",
            ephemeral=True
        )

    async def test_join_clan_not_found(self, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test trying to join a clan that does not exist."""
        # Arrange
        user_id = mock_interaction_clans.user.id
        clan_name = "MissingClan"
        mock_bot_clans.services.clan_data.get_clan_by_name.return_value = None # Clan not found
        mock_bot_clans.services.clan_data.update_clan = AsyncMock()

        # Act
        await clans_cog.join_clan.callback(clans_cog, mock_interaction_clans, clan_name=clan_name)

        # Assert
        mock_bot_clans.services.clan_data.get_clan_by_name.assert_awaited_once_with(clan_name)
        # Ensure update_clan was NOT called
        mock_bot_clans.services.clan_data.update_clan.assert_not_awaited()
        # Check response
        mock_interaction_clans.response.send_message.assert_awaited_once_with(
            f"Clan '{clan_name}' not found. Use `/clan_list` to see available clans.",
            ephemeral=True
        )

    async def test_join_clan_already_member(self, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test trying to join a clan the user is already in."""
        # Arrange
        user_id = mock_interaction_clans.user.id
        clan_name = "Nara"
        # Mock clan data including the user's ID in the members list
        mock_clan_details = {
            'name': clan_name,
            'description': 'Shadow users',
            'rarity': RarityTier.UNCOMMON.value,
            'members': ["111111", user_id] # User is already a member
        }
        mock_bot_clans.services.clan_data.get_clan_by_name.return_value = mock_clan_details
        mock_bot_clans.services.clan_data.update_clan = AsyncMock()

        # Act
        await clans_cog.join_clan.callback(clans_cog, mock_interaction_clans, clan_name=clan_name)

        # Assert
        mock_bot_clans.services.clan_data.get_clan_by_name.assert_awaited_once_with(clan_name)
        # Ensure update_clan was NOT called
        mock_bot_clans.services.clan_data.update_clan.assert_not_awaited()
        # Check response
        mock_interaction_clans.response.send_message.assert_awaited_once_with(
            "You are already a member of this clan.",
            ephemeral=True
        )

    # --- /clan tests --- 

    @patch("HCshinobi.bot.cogs.clans.get_rarity_color")
    async def test_clan_success(self, mock_get_color, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /clan successfully displays the user's clan info."""
        # Arrange
        user_id = mock_interaction_clans.user.id
        clan_name = "Hyuga"
        mock_clan_details = {
            'name': clan_name,
            'description': 'All-seeing eyes',
            'rarity': RarityTier.RARE.value,
            'members': [user_id, "111", "222"]
        }
        mock_bot_clans.services.clan_data.get_clan_by_member = AsyncMock(return_value=mock_clan_details)
        mock_get_color.return_value = discord.Color.purple() # Example color
        
        # Act
        await clans_cog.clan.callback(clans_cog, mock_interaction_clans)
        
        # Assert
        mock_bot_clans.services.clan_data.get_clan_by_member.assert_awaited_once_with(user_id)
        mock_interaction_clans.response.send_message.assert_awaited_once()
        _, kwargs = mock_interaction_clans.response.send_message.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == f"{clan_name} Clan"
        assert sent_embed.description == 'All-seeing eyes'
        assert any(field.name == "Rarity" and field.value == RarityTier.RARE.name.title() for field in sent_embed.fields)
        assert any(field.name == "Members" and field.value == str(len(mock_clan_details['members'])) for field in sent_embed.fields)
        assert sent_embed.color == discord.Color.purple()
        # Ensure message is not ephemeral by default for info commands
        assert kwargs.get('ephemeral') is not True 
        
    async def test_clan_no_clan(self, clans_cog, mock_interaction_clans, mock_bot_clans):
        """Test /clan when the user is not in a clan."""
        # Arrange
        user_id = mock_interaction_clans.user.id
        # Mock get_clan_by_member to return None
        mock_bot_clans.services.clan_data.get_clan_by_member = AsyncMock(return_value=None)

        # Act
        await clans_cog.clan.callback(clans_cog, mock_interaction_clans)

        # Assert
        mock_bot_clans.services.clan_data.get_clan_by_member.assert_awaited_once_with(user_id)
        mock_interaction_clans.response.send_message.assert_awaited_once_with(
            "You are not currently in a clan. Use `/clan_list` to see available clans.",
            ephemeral=True
        ) 