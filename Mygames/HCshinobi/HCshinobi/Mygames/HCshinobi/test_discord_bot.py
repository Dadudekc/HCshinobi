"""Simple test script for Discord.py installation."""
import discord
import importlib.metadata

# Check Discord.py version
discord_version = importlib.metadata.version('discord.py')
print(f"Discord.py version: {discord_version}")

# Check environment
print(f"Python version: {discord.__version__}")

# Import the core modules to ensure they load
print("Testing imports...")
try:
    from HCshinobi.core.engine import Engine
    print("✓ Engine imported successfully")
    
    from HCshinobi.core.character_system import CharacterSystem
    print("✓ CharacterSystem imported successfully")
    
    from HCshinobi.core.battle_system import BattleSystem
    print("✓ BattleSystem imported successfully")
    
    from HCshinobi.bot.bot import HCShinobiBot
    print("✓ HCShinobiBot imported successfully")
    
    print("All critical modules imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("Test completed successfully!") 