from enum import Enum
from discord.ext import commands

class TrainingIntensity(Enum):
    LIGHT = "Light"
    MODERATE = "Moderate"
    INTENSE = "Intense"

TRAINING_ATTRIBUTES = {
    "strength": "Strength",
    "speed": "Speed",
    "defense": "Defense",
}

class TrainingView:
    pass

class TrainingCommands(commands.Cog):
    """Placeholder training commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
