import pytest
import discord
from discord import app_commands
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, List, Optional, Any, Tuple

from HCshinobi.bot.cogs.shop import ShopCommands, ShopView, ShopType
from HCshinobi.core.character import Character
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.jutsu_shop_system import JutsuShopSystem
from HCshinobi.core.equipment_shop_system import EquipmentShopSystem
from HCshinobi.core.constants import DEFAULT_SELL_MODIFIER


# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Bot instance."""
    bot = MagicMock(spec=commands.Bot)
    bot.tree = MagicMock(spec=app_commands.CommandTree)
    bot.services = MagicMock() # Mock the service container
    return bot

@pytest.fixture
def mock_interaction():
    """Fixture for a mocked Interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 123456789
    interaction.user.display_name = "TestUser"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.edit_original_response = AsyncMock()
    interaction.client = MagicMock(spec=commands.Bot) # Interaction needs a client
    return interaction

@pytest.fixture
def mock_character_system():
    """Fixture for a mocked CharacterSystem."""
    mock = AsyncMock(spec=CharacterSystem)
    mock.get_character = AsyncMock(return_value=None) # Default: Character doesn't exist
    mock.save_character = AsyncMock(return_value=True) # Default: Save succeeds
    # Mock add_item_to_inventory if it exists, otherwise patch Character later
    mock.add_item_to_inventory = AsyncMock(return_value=True)
    # Mock remove_item_from_inventory if it exists
    mock.remove_item_from_inventory = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_currency_system():
    """Fixture for a mocked CurrencySystem."""
    mock = MagicMock(spec=CurrencySystem)
    # Mock the combined method primarily
    mock.add_balance_and_save = MagicMock(return_value=True) # Default: succeeds
    mock.get_balance = MagicMock(return_value=1000) # Default: enough balance
    # Add mock for the check method, default to True
    mock.has_sufficient_funds = MagicMock(return_value=True)
    # Add mock for getting balance for error messages
    mock.get_player_balance = MagicMock(return_value=1000)
    # Add mocks for older/internal methods if used by helpers
    mock.add_balance = MagicMock(return_value=True)
    mock.save_currency_data = MagicMock()
    return mock

@pytest.fixture
def mock_jutsu_shop_system():
    """Fixture for a mocked JutsuShopSystem."""
    mock = AsyncMock(spec=JutsuShopSystem)
    # Example jutsu data
    mock.get_current_shop_inventory_details = MagicMock(return_value=[
        {'id': 'fireball_jutsu', 'name': 'Fireball Jutsu', 'price': 500, 'rank': 'C', 'type': 'ninjutsu', 'description': 'A basic fire jutsu.'},
        {'id': 'water_prison', 'name': 'Water Prison Jutsu', 'price': 1500, 'rank': 'B', 'type': 'ninjutsu', 'description': 'Traps target in water.'}
    ])
    mock.master_jutsu_data = { # Need this for buying logic checks
        'fireball_jutsu': {'id': 'fireball_jutsu', 'name': 'Fireball Jutsu', 'price': 500, 'rank': 'C', 'type': 'ninjutsu', 'shop_cost': 500},
        'water_prison': {'id': 'water_prison', 'name': 'Water Prison Jutsu', 'price': 1500, 'rank': 'B', 'type': 'ninjutsu', 'shop_cost': 1500},
        'shadow_clone': {'id': 'shadow_clone', 'name': 'Shadow Clone Jutsu', 'price': 1000, 'rank': 'C', 'type': 'ninjutsu', 'shop_cost': 1000}, # Not in current inventory
    }
    return mock

@pytest.fixture
def mock_equipment_shop_system():
    """Fixture for a mocked EquipmentShopSystem."""
    mock = AsyncMock(spec=EquipmentShopSystem)
    # Example equipment data
    mock.get_shop_inventory = MagicMock(return_value={
        'kunai': {'id': 'kunai', 'name': 'Kunai', 'price': 50, 'type': 'weapon', 'slot': 'hand'},
        'flak_jacket': {'id': 'flak_jacket', 'name': 'Flak Jacket', 'price': 1000, 'type': 'armor', 'slot': 'torso'}
    })
    return mock

@pytest.fixture
def mock_item_shop_data():
    """Fixture for mocked data loaded by _load_item_shop_data."""
    return {
        'basic_healing_salve': {'id': 'basic_healing_salve', 'name': 'Basic Healing Salve', 'price': 100, 'type': 'consumable', 'description': 'Heals minor wounds.'},
        'chakra_pill': {'id': 'chakra_pill', 'name': 'Chakra Pill', 'price': 250, 'type': 'consumable', 'description': 'Restores some chakra.'}
    }

@pytest.fixture
def shop_cog(mock_bot, mock_character_system, mock_currency_system, mock_jutsu_shop_system, mock_equipment_shop_system, mock_item_shop_data):
    """Fixture for an initialized ShopCommands cog with mocked dependencies."""
    # Assign mocked systems to the bot's mocked service container
    mock_bot.services.character_system = mock_character_system
    mock_bot.services.currency_system = mock_currency_system
    mock_bot.services.jutsu_shop_system = mock_jutsu_shop_system
    mock_bot.services.equipment_shop_system = mock_equipment_shop_system
    mock_bot.services.item_manager = MagicMock() # Add if ItemManager is used

    # Patch the _load_item_shop_data method to return our mock data
    with patch.object(ShopCommands, '_load_item_shop_data', return_value=mock_item_shop_data):
        cog = ShopCommands(mock_bot)
        # Manually assign systems if not done via services in __init__ (depends on cog's init)
        # cog.character_system = mock_character_system
        # cog.currency_system = mock_currency_system
        # ... etc ...
        return cog

@pytest.fixture
def sample_character():
    """Fixture for a sample Character object."""
    # Use list() to ensure a new list instance is created each time
    return Character(
        id="123456789",
        name="TestUser",
        level=10,
        rank="Chunin",
        inventory=list(['kunai', 'basic_healing_salve']), # Use list()
        jutsu=list(['fireball_jutsu']) # Use list()
    )

# --- Tests ---

# --- /shop view Tests ---

@pytest.mark.asyncio
async def test_shop_view_all_shops_success(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test /shop view with default 'all' filter and items available."""
    mock_character_system.get_character.return_value = sample_character
    
    # Call the command callback
    await shop_cog.view_shop.callback(shop_cog, mock_interaction)
    
    # Assert interaction response was called (to send the view)
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    
    # Check embed basics
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert embed.title == "🏪 HCShinobi Shop"
    assert len(embed.fields) > 0 # Should have fields for items
    
    # Check view basics
    assert 'view' in kwargs
    view = kwargs['view']
    assert isinstance(view, ShopView)
    assert view.current_filter == ShopType.ALL.value
    assert len(view.children) > 0 # Should have buttons/selects
    
    # Check that all item types are present in the initial view (assuming fixtures have items)
    assert any(item['type'] == 'consumable' for item in view.all_items)
    assert any(item['type'] == 'ninjutsu' for item in view.all_items)
    assert any(item['type'] == 'weapon' or item['type'] == 'armor' for item in view.all_items)

@pytest.mark.asyncio
async def test_shop_view_specific_filter_success(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test /shop view with a specific filter (e.g., jutsu)."""
    mock_character_system.get_character.return_value = sample_character

    # Call the command callback
    await shop_cog.view_shop.callback(shop_cog, mock_interaction, shop_type=ShopType.JUTSU.value)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    view = kwargs['view']
    embed = kwargs['embed']

    assert isinstance(view, ShopView)
    assert view.current_filter == ShopType.JUTSU.value
    # Check that only jutsu items are built into the view initially
    assert all(item['type'] == 'ninjutsu' for item in view.all_items if view.current_filter == ShopType.JUTSU.value)
    assert embed.title == "🏪 HCShinobi Shop"
    assert any("Fireball Jutsu" in field.name for field in embed.fields) # Check specific item

@pytest.mark.asyncio
async def test_shop_view_empty_category(shop_cog, mock_interaction, mock_character_system, sample_character, mock_jutsu_shop_system):
    """Test /shop view when a specific category (jutsu) is empty."""
    mock_character_system.get_character.return_value = sample_character
    mock_jutsu_shop_system.get_current_shop_inventory_details.return_value = [] # No jutsu

    # Re-initialize cog with the modified mock (necessary due to how fixtures work)
    with patch.object(ShopCommands, '_load_item_shop_data', return_value=shop_cog.item_shop_data):
        cog = ShopCommands(shop_cog.bot)
        cog.jutsu_shop_system = mock_jutsu_shop_system # Ensure updated mock is used
        cog.equipment_shop_system = shop_cog.equipment_shop_system
        cog.item_shop_data = shop_cog.item_shop_data
        cog.character_system = mock_character_system
        cog.currency_system = shop_cog.currency_system

    # Call the command callback on the temporary cog instance
    await cog.view_shop.callback(cog, mock_interaction, shop_type=ShopType.JUTSU.value)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs['embed']

    assert embed.title == "🏪 HCShinobi Shop"
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "No Items Available"
    assert "jutsu" in embed.fields[0].value.lower()

@pytest.mark.asyncio
async def test_shop_view_all_shops_empty(shop_cog, mock_interaction, mock_character_system, sample_character, mock_jutsu_shop_system, mock_equipment_shop_system):
    """Test /shop view when all shop categories are empty."""
    mock_character_system.get_character.return_value = sample_character
    mock_jutsu_shop_system.get_current_shop_inventory_details.return_value = []
    mock_equipment_shop_system.get_shop_inventory.return_value = {}
    # Patch _load_item_shop_data for this specific test case
    with patch.object(ShopCommands, '_load_item_shop_data', return_value={}):
        cog = ShopCommands(shop_cog.bot) # Re-init to use patched load data
        cog.jutsu_shop_system = mock_jutsu_shop_system
        cog.equipment_shop_system = mock_equipment_shop_system
        cog.character_system = mock_character_system
        cog.currency_system = shop_cog.currency_system

        # Call the command callback on the temporary cog instance
        await cog.view_shop.callback(cog, mock_interaction, shop_type=ShopType.ALL.value)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    # Check the direct message content instead of embed
    assert "All shops are currently empty or unavailable" in args[0]
    assert kwargs.get('ephemeral') is True

@pytest.mark.asyncio
async def test_shop_view_no_character(shop_cog, mock_interaction, mock_character_system):
    """Test /shop view when the user has no character."""
    mock_character_system.get_character.return_value = None # Ensure no character exists
    
    # Call the method directly on the cog instance
    # Revert: Call the command callback
    await shop_cog.view_shop.callback(shop_cog, mock_interaction)
    
    # View command defers, check defer and followup
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You need a character to view the shop! Use `/character create`.", 
        ephemeral=True
    )

# --- /shop buy Tests ---

@pytest.mark.asyncio
async def test_shop_buy_consumable_success(shop_cog, mock_interaction, mock_character_system, mock_currency_system, sample_character):
    """Test successfully buying a consumable item."""
    item_id = 'basic_healing_salve'
    item_price = shop_cog.item_shop_data[item_id]['price']
    user_id = str(mock_interaction.user.id)
    
    mock_character_system.get_character.return_value = sample_character
    mock_currency_system.has_sufficient_funds.return_value = True
    initial_inventory = sample_character.inventory[:]
    
    # Call the internal logic method directly
    success, message, item_data = await shop_cog._buy_consumable_item(user_id, item_id)
    
    # Assert return value
    assert success is True
    assert "Successfully bought" in message
    assert item_data['id'] == item_id
    
    # Verify side effects (character loaded, currency checked, currency deducted, character saved)
    mock_character_system.get_character.assert_called_once_with(user_id)
    mock_currency_system.has_sufficient_funds.assert_called_once_with(user_id, item_price)
    # Check the correct currency method was called - _buy_consumable_item uses add_balance + save_currency_data
    mock_currency_system.add_balance.assert_called_once_with(user_id, -item_price)
    mock_currency_system.save_currency_data.assert_called_once()
    mock_character_system.save_character.assert_called_once_with(sample_character)
    
    # Verify item was added to inventory
    assert item_id in sample_character.inventory
    assert len(sample_character.inventory) == len(initial_inventory) + 1

@pytest.mark.asyncio
async def test_shop_buy_equipment_success(shop_cog, mock_interaction, mock_character_system, mock_currency_system, mock_equipment_shop_system, sample_character):
    """Test successfully buying an equipment item."""
    item_id = 'kunai'
    item_price = mock_equipment_shop_system.get_shop_inventory()[item_id]['price']
    user_id = str(mock_interaction.user.id)
    
    mock_character_system.get_character.return_value = sample_character
    mock_currency_system.has_sufficient_funds.return_value = True
    initial_inventory = sample_character.inventory[:]

    # Call the internal logic method directly
    # Assume an _buy_equipment_item method exists, or test via buy_item if it handles dispatch
    # Let's assume buy_item dispatches - need to test buy_item and mock _buy_equipment_item
    # Reverting: Test the buy_item command but check calls to _buy_equipment_item
    
    # Mock the specific helper that buy_item should call
    shop_cog._buy_equipment_item = AsyncMock(return_value=(True, f"Successfully purchased {item_id}", {'id': item_id}))
    shop_cog._buy_consumable_item = AsyncMock() # Ensure other helpers aren't called
    shop_cog._buy_jutsu_scroll = AsyncMock()

    await shop_cog.buy_item.callback(shop_cog, mock_interaction, item_id=item_id)

    # Assert the correct helper was called
    shop_cog._buy_equipment_item.assert_called_once_with(user_id, item_id)
    shop_cog._buy_consumable_item.assert_not_called()
    shop_cog._buy_jutsu_scroll.assert_not_called()
    
    # Assert interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert "Successfully purchased" in args[0]
    assert item_id in args[0]
    
    # We are not testing the internals of _buy_equipment_item here, only the dispatch logic of buy_item

@pytest.mark.asyncio
async def test_shop_buy_jutsu_success(shop_cog, mock_interaction, mock_character_system, mock_currency_system, mock_jutsu_shop_system, sample_character):
    """Test successfully buying a jutsu scroll by checking buy_item dispatch."""
    item_id = 'water_prison' # Not already known by sample_character
    user_id = str(mock_interaction.user.id)
    
    # Mock the specific helper that buy_item should call
    shop_cog._buy_jutsu_scroll = AsyncMock(return_value=(True, f"Successfully learned {item_id}", {'id': item_id}))
    shop_cog._buy_consumable_item = AsyncMock()
    shop_cog._buy_equipment_item = AsyncMock()

    await shop_cog.buy_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Assert the correct helper was called
    shop_cog._buy_jutsu_scroll.assert_called_once_with(user_id, item_id)
    shop_cog._buy_consumable_item.assert_not_called()
    shop_cog._buy_equipment_item.assert_not_called()
    
    # Assert interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert "Successfully learned" in args[0]
    assert item_id in args[0]

@pytest.mark.asyncio
async def test_shop_buy_insufficient_funds(shop_cog, mock_interaction, mock_character_system, mock_currency_system, sample_character):
    """Test buying an item when the user doesn't have enough Ryō."""
    item_id = 'chakra_pill'
    item_data = shop_cog.item_shop_data[item_id]
    item_price = item_data['price']
    item_name = item_data['name']
    current_balance = item_price - 50 # Not enough
    user_id = str(mock_interaction.user.id)

    mock_character_system.get_character.return_value = sample_character
    mock_currency_system.has_sufficient_funds.return_value = False
    mock_currency_system.get_player_balance.return_value = current_balance
    
    # Call the internal logic directly
    success, message, _ = await shop_cog._buy_consumable_item(user_id, item_id)
    
    # Assert internal logic return
    assert success is False
    assert "Insufficient Ryō" in message
    assert f"Cost: {item_price:,}" in message
    assert f"Your Balance: {current_balance:,}" in message

    # Verify side effects (only checks, no changes)
    mock_character_system.get_character.assert_called_once_with(user_id)
    mock_currency_system.has_sufficient_funds.assert_called_once_with(user_id, item_price)
    mock_currency_system.get_player_balance.assert_called_once_with(user_id)
    mock_currency_system.add_balance.assert_not_called()
    mock_character_system.save_character.assert_not_called()

@pytest.mark.asyncio
async def test_shop_buy_item_not_found(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test buying an item ID that doesn't exist in any shop."""
    item_id = 'non_existent_item'
    user_id = str(mock_interaction.user.id)
    mock_character_system.get_character.return_value = sample_character # Character must exist for buy_item to proceed
    
    # Mock helpers to simulate item not found within them
    shop_cog._buy_consumable_item = AsyncMock(return_value=(False, f"Item ID '{item_id}' not found in shop.", None))
    shop_cog._buy_equipment_item = AsyncMock(return_value=(False, f"Item ID '{item_id}' not found in shop.", None))
    shop_cog._buy_jutsu_scroll = AsyncMock(return_value=(False, f"'{item_id}' is not currently available.", None))

    # Call the main command which dispatches
    await shop_cog.buy_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Assert interaction response shows the generic not found message
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with(
        f"❌ Item '{item_id}' not found in any shop.", # This is the message from buy_item itself
        ephemeral=True
    )
    # Ensure helpers were actually tried (at least one)
    assert shop_cog._buy_consumable_item.called or shop_cog._buy_equipment_item.called or shop_cog._buy_jutsu_scroll.called

@pytest.mark.asyncio
async def test_shop_buy_no_character(shop_cog, mock_interaction, mock_character_system):
    """Test buying an item when the user has no character."""
    item_id = 'kunai'
    mock_character_system.get_character.return_value = None
    
    # Call the command callback
    await shop_cog.buy_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Check character was checked
    mock_character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    # Check interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You need a character to buy items! Use `/character create`.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_shop_buy_jutsu_already_known(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test buying a jutsu the user already knows."""
    item_id = 'fireball_jutsu' # Already known by sample_character
    jutsu_name = shop_cog.jutsu_shop_system.master_jutsu_data[item_id]['name']
    user_id = str(mock_interaction.user.id)
    mock_character_system.get_character.return_value = sample_character

    # Mock the helper to return the specific message
    shop_cog._buy_jutsu_scroll = AsyncMock(return_value=(False, f"You already know '{jutsu_name}'.\n", None))
    shop_cog._buy_consumable_item = AsyncMock()
    shop_cog._buy_equipment_item = AsyncMock()
    
    await shop_cog.buy_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Check correct helper called
    shop_cog._buy_jutsu_scroll.assert_called_once_with(user_id, item_id)
    # Check interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with(
        f"❌ You already know '{jutsu_name}'.", # buy_item command adds the emoji
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_shop_buy_jutsu_rank_too_low(shop_cog, mock_interaction, mock_character_system, mock_currency_system, mock_jutsu_shop_system, sample_character):
    """Test buying a jutsu when the character rank is too low."""
    item_id = 'water_prison' # Rank B
    jutsu_data = mock_jutsu_shop_system.master_jutsu_data[item_id]
    jutsu_name = jutsu_data['name']
    required_rank = 'Chunin'
    sample_character.rank = 'Genin'
    user_id = str(mock_interaction.user.id)
    
    mock_character_system.get_character.return_value = sample_character

    # Mock the helper to return the specific message
    expected_message = f"⚠️ Rank Requirement Not Met: Your rank ({sample_character.rank}) is too low..."
    shop_cog._buy_jutsu_scroll = AsyncMock(return_value=(False, expected_message, None))
    shop_cog._buy_consumable_item = AsyncMock()
    shop_cog._buy_equipment_item = AsyncMock()

    await shop_cog.buy_item.callback(shop_cog, mock_interaction, item_id=item_id)

    # Check correct helper called
    shop_cog._buy_jutsu_scroll.assert_called_once_with(user_id, item_id)
    # Check interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    # Check the message content (allowing for slight variations)
    assert f"rank ({sample_character.rank}) is too low" in args[0]
    assert f"(Rank {jutsu_data['rank']})" in args[0]
    assert kwargs.get('ephemeral') is True
    
@pytest.mark.asyncio
async def test_shop_buy_save_character_fails(shop_cog, mock_interaction, mock_character_system, mock_currency_system, sample_character):
    """Test rollback logic when saving the character fails after purchase."""
    item_id = 'chakra_pill'
    item_price = shop_cog.item_shop_data[item_id]['price']
    user_id = str(mock_interaction.user.id)
    initial_inventory = sample_character.inventory[:]

    mock_character_system.get_character.return_value = sample_character
    mock_currency_system.has_sufficient_funds.return_value = True
    mock_character_system.save_character.return_value = False # Simulate save failure
    # Mock currency system add_balance for rollback check
    mock_currency_system.add_balance = MagicMock(return_value=True) 

    # Call the internal logic directly
    success, message, _ = await shop_cog._buy_consumable_item(user_id, item_id)

    # Assert internal logic return
    assert success is False
    assert "Transaction failed! Could not save character changes" in message

    # Verify initial steps happened
    mock_character_system.get_character.assert_called_once_with(user_id)
    mock_currency_system.has_sufficient_funds.assert_called_once_with(user_id, item_price)
    # Check original currency deduction call
    mock_currency_system.add_balance.assert_any_call(user_id, -item_price)
    
    # Verify save failure
    mock_character_system.save_character.assert_called_once_with(sample_character)
    
    # Verify rollback calls 
    # Currency rollback check (positive amount)
    mock_currency_system.add_balance.assert_any_call(user_id, item_price)
    # Check currency save was called after rollback
    assert mock_currency_system.save_currency_data.call_count >= 2 # Once for deduction, once for rollback

    # Verify inventory state is rolled back (check contents, sort for consistent order)
    assert sorted(sample_character.inventory) == sorted(initial_inventory)

# --- /shop sell Tests ---

@pytest.mark.asyncio
async def test_shop_sell_consumable_success(shop_cog, mock_interaction, mock_character_system, mock_currency_system, sample_character):
    """Test successfully selling a consumable item the character owns."""
    item_id = 'basic_healing_salve' # Owned by sample_character
    item_data = shop_cog.item_shop_data[item_id]
    item_name = item_data['name']
    sell_price = int(item_data['price'] * DEFAULT_SELL_MODIFIER)
    user_id = str(mock_interaction.user.id)
    
    mock_character_system.get_character.return_value = sample_character
    initial_inventory = sample_character.inventory[:]
    
    # Mock the sell logic directly for this item type (assuming it exists)
    # If sell_item handles dispatch, mock helper instead.
    # Let's assume sell_item calls the logic internally based on item type found.
    
    # Call the main sell command callback
    await shop_cog.sell_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Verify side effects: character loaded, currency added, character saved
    mock_character_system.get_character.assert_called_once_with(user_id)
    mock_currency_system.add_balance_and_save.assert_called_once_with(user_id, sell_price)
    mock_character_system.save_character.assert_called_once_with(sample_character)
    
    # Verify item was removed from inventory
    assert item_id not in sample_character.inventory
    assert len(sample_character.inventory) == len(initial_inventory) - 1
    
    # Verify interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert isinstance(kwargs.get('embed'), discord.Embed) # Check embed is sent
    embed = kwargs['embed']
    assert "Item Sold" in embed.title
    assert item_name in embed.description
    assert f"for {sell_price} Ryō" in embed.description # Check for plain price

@pytest.mark.asyncio
async def test_shop_sell_equipment_success(shop_cog, mock_interaction, mock_character_system, mock_currency_system, mock_equipment_shop_system, sample_character):
    """Test successfully selling an equipment item the character owns."""
    item_id = 'kunai' # Owned by sample_character
    item_data = mock_equipment_shop_system.get_shop_inventory()[item_id]
    item_name = item_data['name']
    sell_price = int(item_data['price'] * DEFAULT_SELL_MODIFIER)
    user_id = str(mock_interaction.user.id)

    mock_character_system.get_character.return_value = sample_character
    initial_inventory = sample_character.inventory[:]
    
    # Call the main sell command callback
    await shop_cog.sell_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Verify side effects
    mock_character_system.get_character.assert_called_once_with(user_id)
    mock_currency_system.add_balance_and_save.assert_called_once_with(user_id, sell_price)
    mock_character_system.save_character.assert_called_once_with(sample_character)
    
    # Verify item was removed
    assert item_id not in sample_character.inventory
    assert len(sample_character.inventory) == len(initial_inventory) - 1

    # Verify interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert isinstance(kwargs.get('embed'), discord.Embed) # Check embed is sent
    embed = kwargs['embed']
    assert "Item Sold" in embed.title
    assert item_name in embed.description
    assert f"for {sell_price} Ryō" in embed.description # Check for plain price

@pytest.mark.asyncio
async def test_shop_sell_item_not_owned(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test selling an item the character does not own."""
    item_id = 'chakra_pill' # Not owned by sample_character
    user_id = str(mock_interaction.user.id)
    mock_character_system.get_character.return_value = sample_character
    initial_inventory = sample_character.inventory[:]
    
    # Call the main sell command callback
    await shop_cog.sell_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Verify checks and response
    mock_character_system.get_character.assert_called_once_with(user_id)
    # Verify inventory unchanged
    assert sorted(sample_character.inventory) == sorted(initial_inventory)
    # Verify interaction response 
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with(
        f"❌ You do not have '{item_id}' in your inventory.", # Message comes from sell_item check
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_shop_sell_item_no_sell_price(shop_cog, mock_interaction, mock_character_system, mock_currency_system, sample_character):
    """Test selling an item that exists in inventory but has no shop data (unsellable)."""
    item_id = 'quest_item_unsellable'
    user_id = str(mock_interaction.user.id)
    sample_character.inventory.append(item_id) # Add unsellable item
    mock_character_system.get_character.return_value = sample_character
    initial_inventory = sample_character.inventory[:]

    # Call the main sell command callback
    await shop_cog.sell_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    # Verify checks and response
    mock_character_system.get_character.assert_called_once_with(user_id)
    # Verify inventory is unchanged because item is unsellable
    assert sorted(sample_character.inventory) == sorted(initial_inventory)
    mock_currency_system.add_balance_and_save.assert_not_called()
    mock_character_system.save_character.assert_not_called()
    # Verify interaction response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with(
        f"❌ Item '{item_id}' cannot be sold (price not found or invalid).",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_shop_sell_no_character(shop_cog, mock_interaction, mock_character_system):
    """Test selling an item when the user has no character."""
    item_id = 'kunai'
    mock_character_system.get_character.return_value = None
    
    # Call the command callback
    await shop_cog.sell_item.callback(shop_cog, mock_interaction, item_id=item_id)
    
    mock_character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    # Verify response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You need a character to sell items.", # Updated expected message
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_shop_sell_save_character_fails(shop_cog, mock_interaction, mock_character_system, mock_currency_system, sample_character):
    """Test rollback logic when saving the character fails after selling."""
    item_id = 'kunai'
    item_data = shop_cog.equipment_shop_system.get_shop_inventory()[item_id]
    sell_price = int(item_data['price'] * DEFAULT_SELL_MODIFIER)
    user_id = str(mock_interaction.user.id)

    mock_character_system.get_character.return_value = sample_character
    mock_character_system.save_character.return_value = False # Simulate save failure
    mock_currency_system.add_balance_and_save.side_effect = [True, True] # Add Ryo, then remove for rollback
    initial_inventory = sample_character.inventory[:]

    # Call the command callback
    await shop_cog.sell_item.callback(shop_cog, mock_interaction, item_id=item_id)

    # Verify initial steps
    mock_character_system.get_character.assert_called_once_with(user_id)
    # Check currency was added initially
    mock_currency_system.add_balance_and_save.assert_any_call(user_id, sell_price)
    
    # Verify save failure
    mock_character_system.save_character.assert_called_once_with(sample_character)
    
    # Verify rollback calls for currency
    assert mock_currency_system.add_balance_and_save.call_count == 2
    calls = mock_currency_system.add_balance_and_save.call_args_list
    assert calls[0] == call(user_id, sell_price) # Initial addition
    assert calls[1] == call(user_id, -sell_price) # Rollback deduction

    # Verify inventory state is rolled back (sort for consistent order)
    assert sorted(sample_character.inventory) == sorted(initial_inventory)

    # Verify final error message 
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    args, kwargs = mock_interaction.followup.send.call_args
    assert "❌ Transaction failed! Could not save character changes after selling." in args[0]
    assert kwargs.get('ephemeral') is True

# --- /shop sell Autocomplete Tests ---

@pytest.mark.asyncio
async def test_sell_item_autocomplete_success(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test autocomplete suggests items the character owns with correct names."""
    # Ensure sample character inventory matches available item/equipment data
    sample_character.inventory = sorted(['kunai', 'basic_healing_salve'])
    mock_character_system.get_character.return_value = sample_character
    
    current_input = ""
    choices = await shop_cog.sell_item_autocomplete(mock_interaction, current_input)
    
    mock_character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    
    assert len(choices) == 2
    
    # Expected choices (value=id, name=Name (Type))
    expected_choices = sorted([
        app_commands.Choice(name='Kunai (Weapon)', value='kunai'),
        app_commands.Choice(name='Basic Healing Salve (Consumable)', value='basic_healing_salve')
    ], key=lambda c: c.value) # Sort by value (id) for comparison
    
    # Sort actual choices by value for consistent comparison
    actual_choices = sorted(choices, key=lambda c: c.value)
    
    # Compare lists of Choice objects
    assert actual_choices == expected_choices

@pytest.mark.asyncio
async def test_sell_item_autocomplete_filtering(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test autocomplete filters suggestions based on current input."""
    sample_character.inventory = ['kunai', 'basic_healing_salve', 'chakra_pill']
    mock_character_system.get_character.return_value = sample_character
    
    # Simulate typing "salve"
    current_input = "salve"
    choices = await shop_cog.sell_item_autocomplete(mock_interaction, current_input)
    
    mock_character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    
    assert len(choices) == 1
    assert choices[0].name == 'Basic Healing Salve (Consumable)'
    assert choices[0].value == 'basic_healing_salve'
    
    # Simulate typing "kU"
    current_input = "kU" 
    choices = await shop_cog.sell_item_autocomplete(mock_interaction, current_input)
    
    assert len(choices) == 1
    assert choices[0].name == 'Kunai (Weapon)'
    assert choices[0].value == 'kunai'

@pytest.mark.asyncio
async def test_sell_item_autocomplete_empty_inventory(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test autocomplete returns no suggestions for empty inventory."""
    sample_character.inventory = [] # Empty inventory
    mock_character_system.get_character.return_value = sample_character
    
    choices = await shop_cog.sell_item_autocomplete(mock_interaction, "kun")
    
    mock_character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    assert len(choices) == 0

@pytest.mark.asyncio
async def test_sell_item_autocomplete_no_character(shop_cog, mock_interaction, mock_character_system):
    """Test autocomplete returns no suggestions if character doesn't exist."""
    mock_character_system.get_character.return_value = None
    
    choices = await shop_cog.sell_item_autocomplete(mock_interaction, "any")
    
    mock_character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    assert len(choices) == 0

@pytest.mark.asyncio
async def test_sell_item_autocomplete_limit(shop_cog, mock_interaction, mock_character_system, sample_character):
    """Test that autocomplete suggestions are limited (to 25)."""
    # Create a large inventory (more than 25 items)
    sample_character.inventory = [f"item_{i:02d}" for i in range(30)]
    mock_character_system.get_character.return_value = sample_character
    
    choices = await shop_cog.sell_item_autocomplete(mock_interaction, "item")
    
    mock_character_system.get_character.assert_called_once_with(str(mock_interaction.user.id))
    assert len(choices) == 25 # Discord limits autocomplete choices

# Remove the original placeholder test
# @pytest.mark.asyncio
# async def test_placeholder():
#     assert True 