from discord.ext import commands
from ...utils.embeds import create_error_embed
from ...utils.battle_ui import render_battle_view

class BattleSystemCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, services=None) -> None:
        self.bot = bot
        self.services = services

    @commands.command(name="battle")
    async def battle(self, ctx: commands.Context):
        await ctx.send(embed=create_error_embed("Battle system not implemented yet."), view=render_battle_view())

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BattleSystemCommands(bot))
