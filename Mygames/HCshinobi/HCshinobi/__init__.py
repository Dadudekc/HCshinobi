"""
HCShinobi Bot - A Discord bot for managing a Naruto-themed RPG
"""

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('HCshinobi')

# Base directory for the project
BASE_DIR = Path(__file__).parent.parent

# Version info
__version__ = "0.1.0"
__author__ = "HCShinobi Team"

# Defer heavy imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

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
from HCshinobi.bot.config import BotConfig

# Export command loader
from HCshinobi.commands.loader import load_commands 