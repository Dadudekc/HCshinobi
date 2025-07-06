"""Placeholder battle commands."""

from discord.ext import commands

from HCshinobi.utils.embeds import create_error_embed
from HCshinobi.utils.battle_ui import render_battle_view

class BattleCommands(commands.Cog):
    """Simple placeholder for battle commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="battle")
    async def battle(self, ctx: commands.Context) -> None:
        await ctx.send(
            embed=create_error_embed("Battle system not implemented yet."),
            view=render_battle_view(),
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BattleCommands(bot))
