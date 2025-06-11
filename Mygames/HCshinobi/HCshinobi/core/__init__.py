"""
Core functionality for HCShinobi
"""

from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.training_system import TrainingSystem
from HCshinobi.core.quest_system import QuestSystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.clan_missions import ClanMissions
from HCshinobi.core.loot_system import LootSystem
from HCshinobi.core.room_system import RoomSystem

__all__ = [
    'ClanAssignmentEngine',
    'CharacterSystem',
    'CurrencySystem',
    'BattleSystem',
    'TrainingSystem',
    'QuestSystem',
    'ClanSystem',
    'ClanMissions',
    'LootSystem',
    'RoomSystem'
]

# Avoid importing modules directly here to prevent circular dependencies.
# Modules should import directly what they need.

# You can still define __all__ if you want to control `from . import *`,
# but it's generally better to use explicit imports anyway.

# Example: Keep __all__ empty or minimal
# __all__ = []

# Commented out original imports:
# from .clan import Clan
# from .clan_system import ClanSystem
# from .character import Character
# from .character_system import CharacterSystem
# from .currency_system import CurrencySystem
# from .battle_system import BattleSystem
# from .token_system import TokenSystem 