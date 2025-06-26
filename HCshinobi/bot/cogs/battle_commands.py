"""Placeholder battle commands."""

from discord.ext import commands

class BattleCommands(commands.Cog):
    """Simple placeholder for battle commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="battle")
    async def battle(self, ctx: commands.Context) -> None:
        await ctx.send("Battle system not implemented yet.")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BattleCommands(bot))
