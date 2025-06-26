"""Placeholder battle type definitions."""
from enum import Enum
from typing import Callable


class StatusEffect(Enum):
    NONE = 0


BattleLogCallback = Callable[[str], None]
