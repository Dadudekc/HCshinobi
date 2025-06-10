import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

# Assuming QuestCommands is in HCshinobi.commands.quest_commands
from HCshinobi.commands.quest_commands import QuestCommands 
# Assuming QuestSystem/CharacterSystem are in HCshinobi.core
from HCshinobi.core.quest_system import QuestSystem # Adjust path if needed
from HCshinobi.core.character_system import CharacterSystem
# Assuming Character is in HCshinobi.models
from HCshinobi.models.character import Character 
# Assuming Bot is defined somewhere
# from HCshinobi.bot import HCShinobiBot 

# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Bot instance."""
    return MagicMock()

@pytest.fixture
def mock_quest_system():
    """Fixture for a mocked QuestSystem."""
    mock = AsyncMock(spec=QuestSystem)
    mock.get_available_quests = AsyncMock()
    mock.accept_quest = AsyncMock()
    mock.get_active_quest = AsyncMock()
    mock.complete_quest = AsyncMock()
    mock.abandon_quest = AsyncMock()
    mock.get_quest_history = AsyncMock()
    return mock

@pytest.fixture
def mock_character_system():
    """Fixture for a mocked CharacterSystem."""
    mock = AsyncMock(spec=CharacterSystem)
    mock.get_character = AsyncMock()
    # Add a sample character to return
    sample_char = MagicMock(spec=Character)
    sample_char.id = 123456789
    sample_char.name = "TestCharacter"
    sample_char.rank = "Genin"
    # Add other attributes if QuestCommands checks them
    mock.get_character.return_value = sample_char 
    return mock

@pytest.fixture
def mock_ctx():
    """Fixture for a mocked discord.ext.commands.Context."""
    ctx = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.id = 123456789
    ctx.author.mention = "<@123456789>"
    ctx.author.display_name = "TestUser"
    ctx.send = AsyncMock()
    return ctx

@pytest.fixture
def quest_cog(mock_bot, mock_quest_system, mock_character_system):
    """Fixture for the QuestCommands cog instance."""
    # Adjust constructor based on actual QuestCommands.__init__
    # Assuming simple init for now
    cog = QuestCommands(bot=mock_bot, quest_system=mock_quest_system, character_system=mock_character_system)
    return cog

# --- Test Cases ---

# TODO: Add tests for !quests
# TODO: Add tests for !accept_quest
# TODO: Add tests for !active_quests
# TODO: Add tests for !complete_quest
# TODO: Add tests for !abandon_quest
# TODO: Add tests for !quest_history 

# --- !quests Tests ---

@pytest.mark.asyncio
async def test_quests_success(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !quests command successfully displays available quests."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    available_quests_data = [
        {'id': 'quest1', 'title': 'Deliver Package', 'rank': 'D', 'description': 'Desc 1', 'reward_exp': 50, 'reward_ryo': 100},
        {'id': 'quest2', 'title': 'Escort Client', 'rank': 'C', 'description': 'Desc 2', 'reward_exp': 150, 'reward_ryo': 300}
    ]
    mock_quest_system.get_available_quests.return_value = available_quests_data

    await quest_cog.quests(mock_ctx)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.get_available_quests.assert_awaited_once_with(character)
    mock_ctx.send.assert_awaited_once()
    args, kwargs = mock_ctx.send.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert "Available Quests" in embed.title
    assert f"for {character.name}" in embed.description
    assert len(embed.fields) == len(available_quests_data)
    assert available_quests_data[0]['title'] in embed.fields[0].name
    assert available_quests_data[1]['title'] in embed.fields[1].name
    assert str(available_quests_data[0]['reward_ryo']) in embed.fields[0].value

@pytest.mark.asyncio
async def test_quests_no_character(quest_cog, mock_ctx, mock_character_system):
    """Test !quests command when the user has no character."""
    mock_character_system.get_character.return_value = None
    user_id = str(mock_ctx.author.id)

    await quest_cog.quests(mock_ctx)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_ctx.send.assert_awaited_once_with("You need to create a character first using `/create`.")

@pytest.mark.asyncio
async def test_quests_none_available(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !quests command when no quests are available."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    mock_quest_system.get_available_quests.return_value = [] # No quests

    await quest_cog.quests(mock_ctx)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.get_available_quests.assert_awaited_once_with(character)
    mock_ctx.send.assert_awaited_once_with("There are no quests available for you right now. Try ranking up!")

# --- !accept_quest Tests ---

@pytest.mark.asyncio
async def test_accept_quest_success(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !accept_quest successfully."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    quest_id_to_accept = "quest1"
    success_message = f"Quest '{quest_id_to_accept}' accepted!"
    mock_quest_system.accept_quest.return_value = (True, success_message)

    await quest_cog.accept_quest(mock_ctx, quest_id=quest_id_to_accept)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.accept_quest.assert_awaited_once_with(character, quest_id_to_accept)
    mock_ctx.send.assert_awaited_once_with(success_message)

@pytest.mark.asyncio
async def test_accept_quest_no_character(quest_cog, mock_ctx, mock_character_system):
    """Test !accept_quest when the user has no character."""
    mock_character_system.get_character.return_value = None
    user_id = str(mock_ctx.author.id)

    await quest_cog.accept_quest(mock_ctx, quest_id="quest1")

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_ctx.send.assert_awaited_once_with("You need to create a character first using `/create`.")
    mock_quest_system.accept_quest.assert_not_awaited()

@pytest.mark.asyncio
async def test_accept_quest_failure(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !accept_quest when quest system returns failure."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    quest_id_to_accept = "quest_invalid"
    fail_message = "Quest is not available or you don't meet requirements."
    mock_quest_system.accept_quest.return_value = (False, fail_message)

    await quest_cog.accept_quest(mock_ctx, quest_id=quest_id_to_accept)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.accept_quest.assert_awaited_once_with(character, quest_id_to_accept)
    mock_ctx.send.assert_awaited_once_with(fail_message)

# --- !active_quests Tests ---

@pytest.mark.asyncio
async def test_active_quests_success(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !active_quests successfully displays the active quest."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    active_quest_data = {
        'id': 'quest_active', 
        'title': 'Active Mission', 
        'description': 'Current objective details.', 
        'progress': 0.5 # Example progress 
    }
    mock_quest_system.get_active_quest.return_value = active_quest_data

    await quest_cog.active_quests(mock_ctx)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.get_active_quest.assert_awaited_once_with(character)
    mock_ctx.send.assert_awaited_once()
    args, kwargs = mock_ctx.send.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert "Active Quest" in embed.title
    assert active_quest_data['title'] in embed.description
    assert "Progress" in embed.fields[0].name
    assert "50.0%" in embed.fields[0].value # Assuming progress is displayed as percentage

@pytest.mark.asyncio
async def test_active_quests_no_character(quest_cog, mock_ctx, mock_character_system):
    """Test !active_quests when the user has no character."""
    mock_character_system.get_character.return_value = None
    user_id = str(mock_ctx.author.id)

    await quest_cog.active_quests(mock_ctx)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_ctx.send.assert_awaited_once_with("You need to create a character first using `/create`.")
    mock_quest_system.get_active_quest.assert_not_awaited()

@pytest.mark.asyncio
async def test_active_quests_none_active(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !active_quests when the user has no active quest."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    mock_quest_system.get_active_quest.return_value = None # No active quest

    await quest_cog.active_quests(mock_ctx)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.get_active_quest.assert_awaited_once_with(character)
    mock_ctx.send.assert_awaited_once_with("You do not have an active quest. Use `!quests` to find one.")

# --- !complete_quest Tests ---

@pytest.mark.asyncio
async def test_complete_quest_success(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !complete_quest successfully."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    quest_id_to_complete = "quest_active"
    reward_data = {'exp': 100, 'ryo': 200}
    success_message = f"Quest '{quest_id_to_complete}' completed! Rewards: {reward_data['exp']} EXP, {reward_data['ryo']} Ryō."
    mock_quest_system.complete_quest.return_value = (True, success_message, reward_data)

    await quest_cog.complete_quest(mock_ctx, quest_id=quest_id_to_complete)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.complete_quest.assert_awaited_once_with(character, quest_id_to_complete)
    mock_ctx.send.assert_awaited_once_with(success_message)

@pytest.mark.asyncio
async def test_complete_quest_no_character(quest_cog, mock_ctx, mock_character_system):
    """Test !complete_quest when the user has no character."""
    mock_character_system.get_character.return_value = None
    user_id = str(mock_ctx.author.id)

    await quest_cog.complete_quest(mock_ctx, quest_id="quest_active")

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_ctx.send.assert_awaited_once_with("You need to create a character first using `/create`.")
    mock_quest_system.complete_quest.assert_not_awaited()

@pytest.mark.asyncio
async def test_complete_quest_failure(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !complete_quest when quest system returns failure."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    quest_id_to_complete = "quest_not_active_or_invalid"
    fail_message = "You cannot complete this quest. It might not be active or requirements aren't met."
    mock_quest_system.complete_quest.return_value = (False, fail_message, None)

    await quest_cog.complete_quest(mock_ctx, quest_id=quest_id_to_complete)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.complete_quest.assert_awaited_once_with(character, quest_id_to_complete)
    mock_ctx.send.assert_awaited_once_with(fail_message)

# --- !abandon_quest Tests ---

@pytest.mark.asyncio
async def test_abandon_quest_success(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !abandon_quest successfully."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    quest_id_to_abandon = "quest_active"
    success_message = f"Quest '{quest_id_to_abandon}' abandoned."
    mock_quest_system.abandon_quest.return_value = (True, success_message)

    await quest_cog.abandon_quest(mock_ctx, quest_id=quest_id_to_abandon)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.abandon_quest.assert_awaited_once_with(character, quest_id_to_abandon)
    mock_ctx.send.assert_awaited_once_with(success_message)

@pytest.mark.asyncio
async def test_abandon_quest_no_character(quest_cog, mock_ctx, mock_character_system):
    """Test !abandon_quest when the user has no character."""
    mock_character_system.get_character.return_value = None
    user_id = str(mock_ctx.author.id)

    await quest_cog.abandon_quest(mock_ctx, quest_id="quest_active")

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_ctx.send.assert_awaited_once_with("You need to create a character first using `/create`.")
    mock_quest_system.abandon_quest.assert_not_awaited()

@pytest.mark.asyncio
async def test_abandon_quest_failure(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !abandon_quest when quest system returns failure."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    quest_id_to_abandon = "quest_not_active"
    fail_message = "You cannot abandon this quest. It might not be active."
    mock_quest_system.abandon_quest.return_value = (False, fail_message)

    await quest_cog.abandon_quest(mock_ctx, quest_id=quest_id_to_abandon)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.abandon_quest.assert_awaited_once_with(character, quest_id_to_abandon)
    mock_ctx.send.assert_awaited_once_with(fail_message)

# --- !quest_history Tests ---

@pytest.mark.asyncio
async def test_quest_history_success(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !quest_history successfully displays the first page."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    history_data = [
        {'quest_id': 'q1', 'title': 'Old Quest 1', 'completion_time': '2023-10-26T10:00:00Z', 'status': 'Completed'},
        {'quest_id': 'q2', 'title': 'Old Quest 2', 'completion_time': '2023-10-25T15:30:00Z', 'status': 'Completed'}
    ]
    mock_quest_system.get_quest_history.return_value = (history_data, 1) # Data and total pages

    # Call with default page (1)
    await quest_cog.quest_history(mock_ctx, page=1)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.get_quest_history.assert_awaited_once_with(character, page=1)
    mock_ctx.send.assert_awaited_once()
    args, kwargs = mock_ctx.send.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert "Quest History" in embed.title
    assert f"for {character.name}" in embed.description
    assert len(embed.fields) == len(history_data)
    assert history_data[0]['title'] in embed.fields[0].name
    assert history_data[1]['title'] in embed.fields[1].name
    assert "Page 1/1" in embed.footer.text # Assuming page info in footer

@pytest.mark.asyncio
async def test_quest_history_no_character(quest_cog, mock_ctx, mock_character_system):
    """Test !quest_history when the user has no character."""
    mock_character_system.get_character.return_value = None
    user_id = str(mock_ctx.author.id)

    await quest_cog.quest_history(mock_ctx, page=1)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_ctx.send.assert_awaited_once_with("You need to create a character first using `/create`.")
    mock_quest_system.get_quest_history.assert_not_awaited()

@pytest.mark.asyncio
async def test_quest_history_no_history(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !quest_history when the user has no history."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    mock_quest_system.get_quest_history.return_value = ([], 0) # Empty list, 0 pages

    await quest_cog.quest_history(mock_ctx, page=1)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.get_quest_history.assert_awaited_once_with(character, page=1)
    mock_ctx.send.assert_awaited_once_with("You have no completed quests recorded.")

@pytest.mark.asyncio
async def test_quest_history_invalid_page(quest_cog, mock_ctx, mock_quest_system, mock_character_system):
    """Test !quest_history with an invalid (e.g., negative) page number."""
    character = mock_character_system.get_character.return_value
    user_id = str(mock_ctx.author.id)
    # System might return empty or raise an error for invalid page, testing the command's handling
    # Assuming the command checks page > 0 before calling system

    await quest_cog.quest_history(mock_ctx, page=0)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_quest_system.get_quest_history.assert_not_awaited() # System should not be called
    mock_ctx.send.assert_awaited_once_with("Page number must be 1 or greater.")

# TODO: Add tests for !quest_history 