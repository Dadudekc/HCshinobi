"""Placeholder room commands."""
from discord.ext import commands


class RoomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoomCommands(bot))
