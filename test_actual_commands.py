#!/usr/bin/env python3
"""
Comprehensive test script for HCShinobi character and jutsu commands.
Tests all actual commands that exist in the system.
"""

import asyncio
import discord
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.services import ServiceContainer
from HCshinobi.core.character import Character

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_success(self, test_name):
        self.passed += 1
        print(f"✅ {test_name}")
    
    def add_failure(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    def print_summary(self):
        print(f"\n{'='*50}")
        print(f"TEST SUMMARY")
        print(f"{'='*50}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        if self.errors:
            print(f"\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

async def setup_test_environment():
    """Set up the test environment with mock bot and services."""
    print("🔧 Setting up test environment...")
    
    # Create mock bot
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.logger = MagicMock()
    bot.loop = asyncio.get_event_loop()
    
    # Create test config
    config = BotConfig(
        token="test_token",
        battle_channel_id=11111,
        online_channel_id=22222,
        database_url="sqlite:///./test_data/test_db.sqlite",
        guild_id=12345,
        application_id=67890,
        log_level="DEBUG",
        command_prefix="!",
        data_dir="./test_data"
    )
    
    # Create services
    services = ServiceContainer(config)
    await services.initialize(bot=bot)
    bot.services = services
    
    # Create character commands cog
    character_cog = CharacterCommands(bot)
    
    return bot, services, character_cog

async def create_mock_interaction(user_id=123456789, user_name="TestUser"):
    """Create a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = user_id
    interaction.user.name = user_name
    interaction.user.display_name = user_name
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 12345
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    return interaction

async def test_create_command(character_cog, results):
    """Test the /create command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test creating a character
        await character_cog.create_character.callback(character_cog, interaction, name="TestNinja", clan="Konohagakure")
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Create Command - New Character")
            results.add_failure("Create Command - New Character", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            # Check embed or content
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("created successfully" in response_text.lower() or "welcome" in response_text.lower()):
                results.add_success("Create Command - New Character")
            else:
                results.add_failure("Create Command - New Character", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Create Command - New Character", str(e))

async def test_create_command_already_exists(character_cog, results):
    """Test the /create command when character already exists."""
    try:
        interaction = await create_mock_interaction()
        
        # Test creating a character that already exists
        await character_cog.create_character.callback(character_cog, interaction, name="TestNinja", clan="Konohagakure")
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Create Command - Already Exists")
            results.add_failure("Create Command - Already Exists", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("already exists" in response_text.lower() or "already have" in response_text.lower()):
                results.add_success("Create Command - Already Exists")
            else:
                results.add_failure("Create Command - Already Exists", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Create Command - Already Exists", str(e))

async def test_profile_command(character_cog, results):
    """Test the /profile command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test viewing profile
        await character_cog.view_profile.callback(character_cog, interaction)
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Profile Command")
            results.add_failure("Profile Command", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("profile" in response_text.lower() or "level" in response_text.lower()):
                results.add_success("Profile Command")
            else:
                results.add_failure("Profile Command", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Profile Command", str(e))

async def test_jutsu_command(character_cog, results):
    """Test the /jutsu command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test viewing jutsu
        await character_cog.view_jutsu.callback(character_cog, interaction)
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Jutsu Command")
            results.add_failure("Jutsu Command", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("jutsu" in response_text.lower()):
                results.add_success("Jutsu Command")
            else:
                results.add_failure("Jutsu Command", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Jutsu Command", str(e))

async def test_jutsu_info_command(character_cog, results):
    """Test the /jutsu_info command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test getting jutsu info
        await character_cog.jutsu_info.callback(character_cog, interaction, jutsu_name="Basic Attack")
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Jutsu Info Command")
            results.add_failure("Jutsu Info Command", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("basic attack" in response_text.lower() or "jutsu" in response_text.lower()):
                results.add_success("Jutsu Info Command")
            else:
                results.add_failure("Jutsu Info Command", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Jutsu Info Command", str(e))

async def test_progression_command(character_cog, results):
    """Test the /progression command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test viewing progression
        await character_cog.view_progression.callback(character_cog, interaction)
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Progression Command")
            results.add_failure("Progression Command", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("progression" in response_text.lower() or "level" in response_text.lower() or "exp" in response_text.lower()):
                results.add_success("Progression Command")
            else:
                results.add_failure("Progression Command", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Progression Command", str(e))

async def test_unlock_jutsu_command(character_cog, results):
    """Test the /unlock_jutsu command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test unlocking jutsu
        await character_cog.unlock_jutsu.callback(character_cog, interaction, jutsu_name="Fireball Jutsu")
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Unlock Jutsu Command")
            results.add_failure("Unlock Jutsu Command", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("unlock" in response_text.lower() or "jutsu" in response_text.lower()):
                results.add_success("Unlock Jutsu Command")
            else:
                results.add_failure("Unlock Jutsu Command", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Unlock Jutsu Command", str(e))

async def test_auto_unlock_jutsu_command(character_cog, results):
    """Test the /auto_unlock_jutsu command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test auto unlocking jutsu
        await character_cog.auto_unlock_jutsu.callback(character_cog, interaction)
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Auto Unlock Jutsu Command")
            results.add_failure("Auto Unlock Jutsu Command", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("unlock" in response_text.lower() or "jutsu" in response_text.lower()):
                results.add_success("Auto Unlock Jutsu Command")
            else:
                results.add_failure("Auto Unlock Jutsu Command", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Auto Unlock Jutsu Command", str(e))

async def test_delete_character_command(character_cog, results):
    """Test the /delete_character command."""
    try:
        interaction = await create_mock_interaction()
        
        # Test deleting character
        await character_cog.delete_character.callback(character_cog, interaction)
        
        # Verify response was called
        if interaction.response.send_message.call_count == 0:
            print("[DEBUG] send_message was NOT called for Delete Character Command")
            results.add_failure("Delete Character Command", "send_message was not called")
        else:
            print(f"[DEBUG] send_message call_args: {interaction.response.send_message.call_args}")
            kwargs = interaction.response.send_message.call_args.kwargs if interaction.response.send_message.call_args else None
            response_text = None
            if kwargs:
                if 'embed' in kwargs and hasattr(kwargs['embed'], 'description'):
                    response_text = kwargs['embed'].description
                elif 'content' in kwargs:
                    response_text = kwargs['content']
            if response_text and ("delete" in response_text.lower() or "confirm" in response_text.lower()):
                results.add_success("Delete Character Command")
            else:
                results.add_failure("Delete Character Command", f"Unexpected response: {response_text}")
            
    except Exception as e:
        results.add_failure("Delete Character Command", str(e))

async def main():
    """Run all tests."""
    print("🧪 Starting HCShinobi Character & Jutsu Commands Test Suite")
    print("=" * 60)
    
    results = TestResults()
    
    try:
        # Set up test environment
        bot, services, character_cog = await setup_test_environment()
        
        # Run all tests
        print("\n🔍 Testing Character & Jutsu Commands...")
        
        await test_create_command(character_cog, results)
        await test_create_command_already_exists(character_cog, results)
        await test_profile_command(character_cog, results)
        await test_jutsu_command(character_cog, results)
        await test_jutsu_info_command(character_cog, results)
        await test_progression_command(character_cog, results)
        await test_unlock_jutsu_command(character_cog, results)
        await test_auto_unlock_jutsu_command(character_cog, results)
        await test_delete_character_command(character_cog, results)
        
        # Clean up
        await services.shutdown()
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return
    
    # Print results
    results.print_summary()
    
    if results.failed == 0:
        print("\n🎉 All tests passed! Character and jutsu commands are working correctly.")
    else:
        print(f"\n⚠️ {results.failed} tests failed. Please review the errors above.")

if __name__ == "__main__":
    asyncio.run(main()) 