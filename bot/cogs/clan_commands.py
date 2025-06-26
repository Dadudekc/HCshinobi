"""Placeholder clan commands."""

from discord import app_commands
from discord.ext import commands

class ClanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="my_clan", description="View your clan info")
    async def my_clan(self, interaction):
        await interaction.response.send_message(
            "Clan system not implemented yet.", ephemeral=True
        )

class ClanMissionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, *args) -> None:
        self.bot = bot

    @app_commands.command(name="clan_missions")
    async def clan_missions(self, interaction):
        await interaction.response.send_message("Clan missions not implemented yet.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClanCommands(bot))
    await bot.add_cog(ClanMissionCommands(bot))
