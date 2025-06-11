"""
Command modules for HCShinobi
"""

# Import cogs from the new location
from HCshinobi.bot.cogs.currency import CurrencyCommands
from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.bot.cogs.battle_system import BattleSystemCommands
from HCshinobi.bot.cogs.training import TrainingCommands
from HCshinobi.bot.cogs.missions import MissionCommands
from HCshinobi.bot.cogs.clans import ClanCommands
from HCshinobi.bot.cogs.clan_commands import ClanMissionCommands
from HCshinobi.bot.cogs.loot_commands import LootCommands
from HCshinobi.bot.cogs.room import RoomCommands
from HCshinobi.bot.cogs.devlog import DevlogCommands
from HCshinobi.bot.cogs.announcements import AnnouncementCommands

# Type hint for Bot
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot as Bot

__all__ = [
    'CurrencyCommands',
    'CharacterCommands',
    'BattleSystemCommands',
    'TrainingCommands',
    'MissionCommands',
    'ClanCommands',
    'ClanMissionCommands',
    'LootCommands',
    'RoomCommands',
    'DevlogCommands',
    'AnnouncementCommands'
] 