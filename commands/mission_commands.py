"""Placeholder mission commands."""

from discord import app_commands
from discord.ext import commands

class MissionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mission_board", description="Show missions")
    async def mission_board(self, interaction):
        await interaction.response.send_message(
            "Mission system not implemented yet.", ephemeral=True
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MissionCommands(bot))
