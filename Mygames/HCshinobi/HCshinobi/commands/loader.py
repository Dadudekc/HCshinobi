"""
Command loader module for HCShinobi bot.
Handles dynamic loading of command modules.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import List, Type

from discord.ext import commands

async def load_commands(bot: commands.Bot) -> List[Type[commands.Cog]]:
    """
    Automatically load all command modules from the commands package.
    
    Args:
        bot: The Discord bot instance
        
    Returns:
        List of loaded command cogs
    """
    loaded_cogs = []
    commands_path = Path(__file__).parent
    
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