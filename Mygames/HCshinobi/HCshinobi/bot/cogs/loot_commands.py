"""
Loot commands cog for HCShinobi.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from HCshinobi.core.loot_system import LootSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.utils.embed_utils import create_error_embed

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

logger = logging.getLogger(__name__)

class LootCommands(commands.Cog):
    """Commands related to loot."""
    
    def __init__(self, bot: "HCBot"):
        self.bot = bot
        self.loot_system = bot.services.loot_system
        self.character_system = bot.services.character_system 