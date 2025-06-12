import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Assuming your cog is here - adjust path as needed
from HCshinobi.bot.cogs.character_commands import CharacterCommands

# We might need to mock discord objects
import discord

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_bot():
    """Fixture to create a mock bot with required services."""
    bot = MagicMock()
    
    # Set up character system
    character_system = MagicMock()
    character_system.get_character = AsyncMock()
    character_system.create_character = AsyncMock()
    character_system.delete_character = AsyncMock()
    bot.character_system = character_system
    
    # Set up other required services
    bot.currency_system = MagicMock()
    bot.token_system = MagicMock()
    bot.mission_system = MagicMock()
    bot.logger = MagicMock()
    
    return bot

@pytest.fixture
def character_cog(mock_bot):
    """Fixture to create an instance of the CharacterCommands cog."""
    return CharacterCommands(bot=mock_bot)

@pytest.fixture
def mock_interaction():
    """Fixture to create a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = "1234567890"
    interaction.user.display_name = "TestUser"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    return interaction


class TestCharacterCommands:
    
    async def test_create_character_already_exists(self, character_cog, mock_interaction, mock_bot):
        """Test the /create command when the user already has a character."""
        # Arrange: Mock get_character to return an existing character
        mock_existing_character = MagicMock()
        mock_bot.character_system.get_character.return_value = mock_existing_character
        
        # Act: Call the command
        await character_cog.create.callback(character_cog, mock_interaction)
        
        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
        mock_bot.character_system.get_character.assert_awaited_once_with("1234567890")
        # Ensure create_character was NOT called
        mock_bot.character_system.create_character.assert_not_awaited()
        # Check that the correct followup message was sent and it's ephemeral
        mock_interaction.followup.send.assert_awaited_once_with(
            "You already have a Shinobi character! Use `/profile`.",
            ephemeral=True
        )

    async def test_profile_success(self, character_cog, mock_interaction, mock_bot):
        """Test the /profile command when the user has a character."""
        # Arrange: Mock services to return character data, clan, and currency
        mock_character = MagicMock()
        mock_character.id = mock_interaction.user.id
        mock_character.name = "TestUser"
        mock_character.level = 5
        mock_character.hp = 100
        mock_character.max_hp = 100
        mock_character.chakra = 50
        mock_character.max_chakra = 50
        mock_character.stamina = 50
        mock_character.max_stamina = 50
        # Add combat stats for the embed field
        mock_character.taijutsu = 15
        mock_character.ninjutsu = 10
        mock_character.genjutsu = 5
        # Add clan directly to the character object
        mock_character.clan = "Uzumaki"
        # Mock other attributes as needed for the embed
        mock_character.strength = 10
        mock_character.speed = 12
        mock_character.defense = 9
        mock_character.willpower = 11
        mock_character.chakra_control = 7
        mock_character.intelligence = 8
        mock_character.exp = 150
        mock_character.rank = "Genin"
        mock_character.completed_missions = set()
        mock_character.achievements = set()
        mock_character.titles = []
        mock_character.wins_against_rank = {}
        mock_character.clan_achievements = set()
        mock_character.clan_skills = {}
        mock_character.clan_jutsu_mastery = {}
        mock_character.jutsu_mastery = {}
        mock_character.inventory = {}
        mock_character.equipment = {}
        mock_character.status_effects = []
        mock_character.active_effects = {}
        mock_character.status_conditions = {}
        mock_character.buffs = {}
        mock_character.debuffs = {}

        mock_bot.character_system.get_character.return_value = mock_character
        # Remove mock for clan_assignment_engine as it's no longer used directly
        # mock_bot.services.clan_assignment_engine.get_player_clan.return_value = "Uzumaki"
        
        # Mock currency/token systems if they are added to the bot mock fixture
        # Ensure these mocks exist if the profile command uses them
        if not hasattr(mock_bot, 'currency_system'):
            mock_bot.currency_system = MagicMock()
        if not hasattr(mock_bot, 'token_system'):
            mock_bot.token_system = MagicMock()
        
        # Ensure the specific methods are AsyncMocks *before* setting return_value
        mock_bot.currency_system.get_player_balance = MagicMock()
        mock_bot.token_system.get_player_tokens = MagicMock()
        
        # Target the correct methods called in the profile command
        mock_bot.currency_system.get_player_balance.return_value = 1000
        mock_bot.token_system.get_player_tokens.return_value = 5 # Assuming this is the corresponding method

        # Act: Call the profile command
        await character_cog.profile.callback(character_cog, mock_interaction)

        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
        mock_bot.character_system.get_character.assert_awaited_once_with("1234567890")
        # Remove assertion for clan_assignment_engine
        # mock_bot.services.clan_assignment_engine.get_player_clan.assert_called_once_with("1234567890")
        # Only assert currency/token if they are actually called in the current profile implementation
        # Check character_commands.py to confirm if these are still used in profile
        # Assert sync calls to currency and token methods (no await expected)
        mock_bot.currency_system.get_player_balance.assert_called_once_with("1234567890")
        mock_bot.token_system.get_player_tokens.assert_called_once_with("1234567890")
        
        # Check that the embed was sent
        mock_interaction.followup.send.assert_awaited_once()
        args, kwargs = mock_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == "TestUser's Shinobi Profile"
        
        # Find the clan field and check its value
        clan_field = discord.utils.get(sent_embed.fields, name="⚜️ Clan")
        assert clan_field is not None, "\"⚜️ Clan\" field not found in profile embed.\""
        assert clan_field.value == "Uzumaki", f"Clan field value mismatch. Expected 'Uzumaki', got '{clan_field.value}'"
        
        # Find the combat stats field and check its value (example)
        combat_stats_field = discord.utils.get(sent_embed.fields, name="Combat Stats")
        assert combat_stats_field is not None, "\"Combat Stats\" field not found.\""
        # You might want more specific checks on the content of combat_stats_field.value
        assert "**Taijutsu:** 15" in combat_stats_field.value, f"Expected Taijutsu line not found in: {combat_stats_field.value}"
        assert "**Ninjutsu:** 10" in combat_stats_field.value, f"Expected Ninjutsu line not found in: {combat_stats_field.value}"
        assert "**Genjutsu:** 5" in combat_stats_field.value, f"Expected Genjutsu line not found in: {combat_stats_field.value}"
        
        # Verify other essential fields are present
        field_names = [field.name for field in sent_embed.fields]
        assert "📊 Stats" in field_names # Check for the generic stats field
        
        # Assert footer text
        assert sent_embed.footer is not None
        assert sent_embed.footer.text == "Use /stats for detailed stats and battle record."

    async def test_profile_no_character(self, character_cog, mock_interaction, mock_bot):
        """Test the /profile command when the user does not have a character."""
        # Arrange: Mock get_character to return None
        mock_bot.character_system.get_character.return_value = None
        
        # Act: Call the profile command
        await character_cog.profile.callback(character_cog, mock_interaction)
        
        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
        mock_bot.character_system.get_character.assert_awaited_once_with("1234567890")
        # Check that the correct followup message was sent
        mock_interaction.followup.send.assert_awaited_once_with(
            "You don't have a character yet! Use `/create` to start your journey.",
            ephemeral=True
        )

    async def test_stats_self_success(self, character_cog, mock_interaction, mock_bot):
        """Test the /stats command successfully viewing own stats."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_character = MagicMock()
        mock_character.id = user_id
        mock_character.name = "TestUser"
        # Core Stats
        mock_character.hp = 80
        mock_character.max_hp = 110
        mock_character.chakra = 40
        mock_character.max_chakra = 55
        mock_character.stamina = 60
        mock_character.max_stamina = 70
        mock_character.strength = 12
        mock_character.speed = 14
        mock_character.defense = 9
        mock_character.intelligence = 11
        mock_character.perception = 8
        mock_character.willpower = 13
        mock_character.chakra_control = 10
        # Combat Stats
        mock_character.taijutsu = 15
        mock_character.ninjutsu = 10
        mock_character.genjutsu = 5
        # Battle Record
        mock_character.wins = 5
        mock_character.losses = 2
        mock_character.draws = 1
        mock_character.wins_against_rank = {"Genin": 3, "Chunin": 2}
        mock_character.rarity = "Common" # Used for embed color

        mock_bot.character_system.get_character.return_value = mock_character

        # Act
        # Call stats command with user=None (for self)
        await character_cog.stats.callback(character_cog, mock_interaction, user=None)

        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        mock_interaction.followup.send.assert_awaited_once()

        args, kwargs = mock_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == f"📊 {mock_character.name}'s Stats & Record"
        assert sent_embed.footer.text == f"ID: {user_id}"

        # Check Core Stats field
        core_stats_field = discord.utils.get(sent_embed.fields, name="Core Stats")
        assert core_stats_field is not None
        assert f"❤️ **HP:** {mock_character.hp}/{mock_character.max_hp}" in core_stats_field.value
        assert f"💪 **Strength:** {mock_character.strength}" in core_stats_field.value

        # Check Combat Stats field
        combat_stats_field = discord.utils.get(sent_embed.fields, name="Combat Stats")
        assert combat_stats_field is not None
        assert f"🥋 **Taijutsu:** {mock_character.taijutsu}" in combat_stats_field.value

        # Check Battle Record field
        battle_record_field = discord.utils.get(sent_embed.fields, name="Battle Record")
        assert battle_record_field is not None
        assert f"🏆 **Wins:** {mock_character.wins}" in battle_record_field.value
        assert f"☠️ **Losses:** {mock_character.losses}" in battle_record_field.value
        assert "📈 **Win Rate:** 62.5%" in battle_record_field.value # 5 / (5+2+1) * 100

        # Check Wins vs Rank field
        wins_rank_field = discord.utils.get(sent_embed.fields, name="Wins vs Rank")
        assert wins_rank_field is not None
        assert "- vs Chunin: 2" in wins_rank_field.value
        assert "- vs Genin: 3" in wins_rank_field.value

    async def test_stats_self_no_character(self, character_cog, mock_interaction, mock_bot):
        """Test the /stats command when the user has no character."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_bot.character_system.get_character.return_value = None # No character exists

        # Act
        await character_cog.stats.callback(character_cog, mock_interaction, user=None)

        # Assert
        # The /stats command likely doesn't use thinking=True for this case
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        # Check that the error message was sent via followup
        mock_interaction.followup.send.assert_awaited_once_with(
            "You don't have a character yet! Use `/create` to start your journey.",
            ephemeral=True
        )
        # Ensure original response wasn't used
        mock_interaction.response.send_message.assert_not_called()

    async def test_stats_other_user_success(self, character_cog, mock_interaction, mock_bot):
        """Test the /stats command successfully viewing another user's stats."""
        # Arrange
        target_user_mock = MagicMock(spec=discord.User)
        target_user_mock.id = "1122334455"
        target_user_mock.display_name = "OtherUser"

        mock_character = MagicMock()
        mock_character.id = target_user_mock.id
        mock_character.name = target_user_mock.display_name
        # Add necessary stats for the embed
        mock_character.hp = 90
        mock_character.max_hp = 100
        mock_character.chakra = 50
        mock_character.max_chakra = 50
        mock_character.stamina = 80
        mock_character.max_stamina = 80
        mock_character.strength = 10
        mock_character.speed = 11
        mock_character.defense = 12
        mock_character.intelligence = 13
        mock_character.perception = 7
        mock_character.willpower = 9
        mock_character.chakra_control = 11
        mock_character.taijutsu = 8
        mock_character.ninjutsu = 12
        mock_character.genjutsu = 10
        mock_character.wins = 10
        mock_character.losses = 5
        mock_character.draws = 0
        mock_character.wins_against_rank = {"Genin": 10}
        mock_character.rarity = "Uncommon"

        mock_bot.character_system.get_character.return_value = mock_character

        # Act
        # Call stats command targeting another user
        await character_cog.stats.callback(character_cog, mock_interaction, user=target_user_mock)

        # Assert
        # Viewing others is not ephemeral
        mock_interaction.response.defer.assert_called_once_with(ephemeral=False) 
        # Ensure get_character is called with the target user's ID
        mock_bot.character_system.get_character.assert_awaited_once_with(target_user_mock.id)
        mock_interaction.followup.send.assert_awaited_once()

        args, kwargs = mock_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == f"📊 {target_user_mock.display_name}'s Stats & Record"
        assert sent_embed.footer.text == f"ID: {target_user_mock.id}"
        # Check a sample stat
        core_stats_field = discord.utils.get(sent_embed.fields, name="Core Stats")
        assert core_stats_field is not None
        assert f"❤️ **HP:** {mock_character.hp}/{mock_character.max_hp}" in core_stats_field.value
        # Check battle record
        battle_record_field = discord.utils.get(sent_embed.fields, name="Battle Record")
        assert battle_record_field is not None
        assert f"🏆 **Wins:** {mock_character.wins}" in battle_record_field.value
        assert "📈 **Win Rate:** 66.7%" in battle_record_field.value # 10 / (10+5+0) * 100

    async def test_stats_other_user_no_character(self, character_cog, mock_interaction, mock_bot):
        """Test the /stats command when viewing another user who has no character."""
        # Arrange
        target_user_mock = MagicMock(spec=discord.User)
        target_user_mock.id = "1122334455"
        target_user_mock.display_name = "OtherUser"

        mock_bot.character_system.get_character.return_value = None # Target user has no character

        # Act
        await character_cog.stats.callback(character_cog, mock_interaction, user=target_user_mock)

        # Assert
        # Viewing others is not ephemeral
        mock_interaction.response.defer.assert_called_once_with(ephemeral=False) 
        mock_bot.character_system.get_character.assert_awaited_once_with(target_user_mock.id)
        # The _get_character_or_error helper sends the message using mention format
        mock_interaction.followup.send.assert_awaited_once_with(
            f"User <@{target_user_mock.id}> does not have a character.", # Use mention format
            ephemeral=True
        )

    # --- /delete Command Tests ---

    @patch('HCshinobi.bot.cogs.character_commands.DeleteConfirmationView') # Patch the view class
    async def test_delete_command_initiate_success(self, MockDeleteView, character_cog, mock_interaction, mock_bot):
        """Test the /delete command successfully initiates the confirmation view."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_character = MagicMock(id=user_id)
        mock_character.name = "ToDelete" # Set name explicitly
        mock_bot.character_system.get_character.return_value = mock_character
        
        # Create a mock instance for the view that will be constructed
        mock_view_instance = MockDeleteView.return_value

        # Act
        await character_cog.delete.callback(character_cog, mock_interaction)

        # Assert
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        # Check that the view was instantiated correctly (using positional args)
        MockDeleteView.assert_called_once_with(character_cog, mock_interaction.user, mock_character)
        # Check that followup.send was called with the confirmation message and the view instance
        mock_interaction.followup.send.assert_awaited_once()
        args, kwargs = mock_interaction.followup.send.call_args
        # Check for key parts of the actual warning message
        assert "**Warning!**" in args[0]
        assert f"delete your character **{mock_character.name}**?" in args[0]
        assert "action cannot be undone" in args[0]
        assert kwargs.get('view') == mock_view_instance
        assert kwargs.get('ephemeral') == True # Followup inherits ephemeral from defer
        # Assert that the view's message attribute was set (important for timeout handling)
        assert mock_view_instance.message is not None 
        # Ensure original response wasn't used
        mock_interaction.response.send_message.assert_not_called()

    async def test_delete_command_no_character(self, character_cog, mock_interaction, mock_bot):
        """Test the /delete command when the user has no character."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_bot.character_system.get_character.return_value = None # No character

        # Act
        await character_cog.delete.callback(character_cog, mock_interaction)

        # Assert
        # Check deferral first, including thinking=True
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        # Check that the error message was sent via followup
        mock_interaction.followup.send.assert_awaited_once_with(
            "You don't have a character yet! Use `/create` to start your journey.",
            ephemeral=True
        )
        # Ensure original response wasn't used
        mock_interaction.response.send_message.assert_not_called()

    # TODO: Add tests for the DeleteConfirmationView interactions (confirm, cancel, timeout)
    # TODO: Add test for when player has clan but no character entry (legacy case)

    # --- /inventory Command Tests ---

    async def test_inventory_success_with_items(self, character_cog, mock_interaction, mock_bot):
        """Test the /inventory command successfully displays items."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_character = MagicMock(id=user_id)
        mock_character.name = "InvTester" # Set name explicitly
        # Mock inventory: Use item IDs as keys and quantities as values
        mock_character.inventory = {
            "kunai": 5,
            "shuriken": 10,
            "health_potion": 2
        }
        mock_bot.character_system.get_character.return_value = mock_character

        # Mock ItemRegistry correctly - target get_item
        mock_item_registry = MagicMock() # Use MagicMock for sync method get_item
        # Define the side effect for get_item
        def get_item_side_effect(item_id):
            items = {
                "kunai": {"name": "Kunai", "description": "Standard throwing knife.", "rarity": "Common"},
                "shuriken": {"name": "Shuriken", "description": "Throwing star.", "rarity": "Common"},
                "health_potion": {"name": "Health Potion", "description": "Restores health.", "rarity": "Uncommon"}
            }
            return items.get(item_id) # Return the dict or None
        
        mock_item_registry.get_item.side_effect = get_item_side_effect

        # Attach the mock registry directly to the cog instance
        character_cog.item_registry = mock_item_registry

        # Act
        await character_cog.inventory.callback(character_cog, mock_interaction)

        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        # Ensure the correct registry method was called for each item on the COG's registry
        assert character_cog.item_registry.get_item.call_count == len(mock_character.inventory)
        character_cog.item_registry.get_item.assert_any_call("kunai")
        character_cog.item_registry.get_item.assert_any_call("shuriken")
        character_cog.item_registry.get_item.assert_any_call("health_potion")
        
        mock_interaction.followup.send.assert_awaited_once()

        args, kwargs = mock_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        # Check title using the explicitly set name
        assert sent_embed.title == f"🎒 {mock_character.name}'s Inventory"
        # Check description contains formatted item lines
        assert len(sent_embed.fields) == 0 # No fields are used
        assert "**Kunai (Common)**: 5 - Standard throwing knife." in sent_embed.description
        assert "**Shuriken (Common)**: 10 - Throwing star." in sent_embed.description
        assert "**Health Potion (Uncommon)**: 2 - Restores health." in sent_embed.description

    async def test_inventory_empty(self, character_cog, mock_interaction, mock_bot):
        """Test the /inventory command when the inventory is empty."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_character = MagicMock(id=user_id)
        mock_character.name = "InvTester" # Set name explicitly
        mock_character.inventory = {} # Empty inventory
        mock_bot.character_system.get_character.return_value = mock_character
        
        # Mock ItemRegistry just in case (get_item shouldn't be called)
        mock_item_registry = MagicMock()
        mock_item_registry.get_item = MagicMock()
        mock_bot.item_registry = mock_item_registry

        # Act
        await character_cog.inventory.callback(character_cog, mock_interaction)

        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        # Ensure registry method not called for empty inv
        mock_bot.item_registry.get_item.assert_not_called()
        mock_interaction.followup.send.assert_awaited_once()

        args, kwargs = mock_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        # Check title using the explicitly set name
        assert sent_embed.title == f"🎒 {mock_character.name}'s Inventory"
        assert sent_embed.description == "Empty" # Correct expected description
        assert len(sent_embed.fields) == 0

    # --- /jutsu Command Tests ---

    @patch('HCshinobi.bot.cogs.character_commands.CharacterCommands._format_jutsu_list', new_callable=AsyncMock)
    async def test_jutsu_success_with_jutsu(self, mock_format_jutsu_list, character_cog, mock_interaction, mock_bot):
        """Test the /jutsu command successfully displays learned jutsu."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_character = MagicMock(id=user_id, name="JutsuUser")
        mock_known_jutsu_ids = ["fireball", "shadow_clone"]
        mock_character.jutsu = mock_known_jutsu_ids
        mock_bot.character_system.get_character.return_value = mock_character

        # Configure the mocked helper method
        expected_description = "**Fireball Jutsu (Ninjutsu)**: Rank C - Basic fire release technique.\n**Shadow Clone Jutsu (Ninjutsu)**: Rank B - Creates physical copies."
        mock_format_jutsu_list.return_value = expected_description

        # Act
        await character_cog.jutsu.callback(character_cog, mock_interaction)

        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        # Assert the helper method was called
        mock_format_jutsu_list.assert_awaited_once_with(mock_known_jutsu_ids)
        mock_interaction.followup.send.assert_awaited_once()

        args, kwargs = mock_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == f"📜 {mock_character.name}'s Known Jutsu"
        # Check description matches the mocked return value
        assert sent_embed.description == expected_description
        assert len(sent_embed.fields) == 0 # No fields should be used by jutsu command

    async def test_jutsu_empty(self, character_cog, mock_interaction, mock_bot):
        """Test the /jutsu command when the character knows no jutsu."""
        # Arrange
        user_id = mock_interaction.user.id
        mock_character = MagicMock(id=user_id, name="JutsuUser")
        mock_character.jutsu = [] # Empty list
        mock_bot.character_system.get_character.return_value = mock_character

        # Mock JutsuSystem just in case (shouldn't be called)
        mock_jutsu_system = MagicMock()
        mock_jutsu_system.get_jutsu = MagicMock()
        mock_bot.jutsu_system = mock_jutsu_system

        # Act
        await character_cog.jutsu.callback(character_cog, mock_interaction)

        # Assert
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_bot.character_system.get_character.assert_awaited_once_with(user_id)
        mock_jutsu_system.get_jutsu.assert_not_called() # Ensure get_jutsu not called
        mock_interaction.followup.send.assert_awaited_once()

        args, kwargs = mock_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert sent_embed.title == f"📜 {mock_character.name}'s Known Jutsu"
        assert "None learned" in sent_embed.description

# Removed invalid tag below 