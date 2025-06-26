"""Placeholder training commands."""
from discord.ext import commands


class TrainingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


class TrainingView:  # Minimal stub for tests
    pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrainingCommands(bot))
