"""Placeholder clan mission commands."""
from discord.ext import commands


class ClanMissionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, *args, **kwargs) -> None:
        self.bot = bot


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClanMissionCommands(bot))
