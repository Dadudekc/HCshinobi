import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, call
import pytest_asyncio

# Assume these imports are correct relative to your project structure
from HCshinobi.commands.currency_commands import CurrencyCommands
# Systems are now mocked via conftest.py fixtures

@pytest_asyncio.fixture
async def currency_cog(mock_bot, mock_currency_system, mock_clan_system):
    """Creates an instance of the CurrencyCommands cog with pre-configured mocks."""
    # Configure default mock behaviors
    mock_currency_system.get_balance.return_value = 1000
    mock_currency_system.claim_daily_reward.return_value = 100
    mock_currency_system.transfer_currency.return_value = True
    mock_currency_system.get_clan_bonus.return_value = 0

    mock_clan_system.get_player_clan.return_value = None

    # Reset mocks before each test using this fixture
    mock_currency_system.reset_mock()
    mock_clan_system.reset_mock()

    # Instantiate the cog with the bot and the mocked systems
    # CurrencyCommands expects bot, currency_system, clan_system
    cog = CurrencyCommands(mock_bot, mock_currency_system, mock_clan_system)
    yield cog

# --- Tests ---

@pytest.mark.asyncio
async def test_balance_command(currency_cog, mock_ctx, mock_currency_system, mock_clan_system):
    """Test the !balance command."""
    await currency_cog.balance(mock_ctx)

    # Verify systems were called
    mock_clan_system.get_player_clan.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.get_balance.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.get_clan_bonus.assert_not_called() # No clan in default mock

    # Verify response embed (basic check)
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert "1,000" in embed.description # Check if balance is mentioned
    assert embed.title == "💰 Ryō Balance"

@pytest.mark.asyncio
async def test_balance_command_with_clan_bonus(currency_cog, mock_ctx, mock_currency_system, mock_clan_system):
    """Test the !balance command when the player is in a clan with a bonus."""
    mock_clan_system.get_player_clan.return_value = "TestClan"
    mock_currency_system.get_clan_bonus.return_value = 10 # 10% bonus

    await currency_cog.balance(mock_ctx)

    # Verify systems were called
    mock_clan_system.get_player_clan.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.get_balance.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.get_clan_bonus.assert_called_once_with("TestClan")

    # Verify response embed includes clan bonus
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Clan Bonus"
    assert "+10%" in embed.fields[0].value
    assert "TestClan" in embed.fields[0].value

@pytest.mark.asyncio
async def test_daily_command(currency_cog, mock_ctx, mock_currency_system, mock_clan_system):
    """Test the !daily command."""
    await currency_cog.daily(mock_ctx)

    # Verify systems were called
    mock_clan_system.get_player_clan.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.claim_daily_reward.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.get_clan_bonus.assert_not_called() # No clan in default mock

    # Verify response embed
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert "100" in embed.description # Check if claimed amount is mentioned
    assert embed.title == "🎁 Daily Reward"

@pytest.mark.asyncio
async def test_daily_command_with_clan_bonus(currency_cog, mock_ctx, mock_currency_system, mock_clan_system):
    """Test the !daily command with a clan bonus."""
    mock_clan_system.get_player_clan.return_value = "BonusClan"
    mock_currency_system.get_clan_bonus.return_value = 5 # 5% bonus
    mock_currency_system.claim_daily_reward.return_value = 200 # Assume base daily is 200

    await currency_cog.daily(mock_ctx)

     # Verify systems were called
    mock_clan_system.get_player_clan.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.claim_daily_reward.assert_called_once_with(str(mock_ctx.author.id))
    mock_currency_system.get_clan_bonus.assert_called_once_with("BonusClan")

    # Verify response embed includes calculated bonus
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert "200" in embed.description # Base amount
    assert len(embed.fields) == 1
    assert embed.fields[0].name == "Clan Bonus"
    # 5% of 200 is 10
    assert "+10 Ryō" in embed.fields[0].value
    assert "BonusClan" in embed.fields[0].value


@pytest.mark.asyncio
async def test_transfer_command_success(currency_cog, mock_ctx, mock_currency_system, mock_recipient):
    """Test the !transfer command for a successful transfer."""
    amount_to_transfer = 500
    await currency_cog.transfer(mock_ctx, recipient=mock_recipient, amount=amount_to_transfer)

    # Verify transfer was attempted
    mock_currency_system.transfer_currency.assert_called_once_with(
        str(mock_ctx.author.id), str(mock_recipient.id), amount_to_transfer
    )

    # Verify success message
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert "Transfer Complete" in embed.title
    assert str(amount_to_transfer) in embed.description
    assert mock_recipient.mention in embed.description
    assert embed.color == discord.Color.green()

@pytest.mark.asyncio
async def test_transfer_command_insufficient_funds(currency_cog, mock_ctx, mock_currency_system, mock_recipient):
    """Test the !transfer command when the sender has insufficient funds."""
    mock_currency_system.transfer_currency.return_value = False # Simulate failure
    amount_to_transfer = 5000 # More than default balance

    await currency_cog.transfer(mock_ctx, recipient=mock_recipient, amount=amount_to_transfer)

    # Verify transfer was attempted
    mock_currency_system.transfer_currency.assert_called_once_with(
        str(mock_ctx.author.id), str(mock_recipient.id), amount_to_transfer
    )

    # Verify failure message
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert "Transfer Failed" in embed.title
    assert "enough Ryō" in embed.description
    assert embed.color == discord.Color.red()

@pytest.mark.asyncio
async def test_transfer_command_invalid_amount(currency_cog, mock_ctx, mock_currency_system, mock_recipient):
    """Test the !transfer command with zero or negative amount."""
    # Test zero amount
    await currency_cog.transfer(mock_ctx, recipient=mock_recipient, amount=0)
    mock_ctx.send.assert_called_once_with("Amount must be greater than 0!")
    mock_currency_system.transfer_currency.assert_not_called() # Should not attempt transfer

    mock_ctx.send.reset_mock() # Reset for next check
    mock_currency_system.transfer_currency.reset_mock()

    # Test negative amount
    await currency_cog.transfer(mock_ctx, recipient=mock_recipient, amount=-100)
    mock_ctx.send.assert_called_once_with("Amount must be greater than 0!")
    mock_currency_system.transfer_currency.assert_not_called()
