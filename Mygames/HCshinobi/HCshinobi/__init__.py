"""
HCShinobi - A Discord bot for managing ninja clans and missions
"""

__version__ = "1.0.0"
__author__ = "HCShinobi Team"

import importlib
import pkgutil
from pathlib import Path
from typing import List, Type

import discord
from discord.ext import commands

# Import core modules
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.training_system import TrainingSystem
from HCshinobi.core.quest_system import QuestSystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.clan_missions import ClanMissions
from HCshinobi.core.loot_system import LootSystem
from HCshinobi.core.room_system import RoomSystem
from HCshinobi.core.currency_system import CurrencySystem

# Import bot modules
from HCshinobi.bot.bot import HCBot
from HCshinobi.bot.config import BotConfig

async def load_commands(bot: commands.Bot) -> List[Type[commands.Cog]]:
    """
    Automatically load all command modules from the commands package.
    
    Args:
        bot: The Discord bot instance
        
    Returns:
        List of loaded command cogs
    """
    loaded_cogs = []
    commands_path = Path(__file__).parent / "commands"
    
    # Find all Python modules in the commands directory
    for _, name, is_pkg in pkgutil.iter_modules([str(commands_path)]):
        if not is_pkg and not name.startswith('_'):
            try:
                # Import the module
                module = importlib.import_module(f"HCshinobi.commands.{name}")
                
                # If the module has a setup function, call it
                if hasattr(module, 'setup'):
                    await module.setup(bot)
                    loaded_cogs.append(module)
                    
            except Exception as e:
                print(f"Error loading command module {name}: {e}")
    
    return loaded_cogs 