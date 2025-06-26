from discord import app_commands
from discord.ext import commands
from ...utils.embeds import create_error_embed

class MissionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mission_board", description="Show missions")
    async def mission_board(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("No missions are available for you right now. Try ranking up or leveling up!", ephemeral=True)

    @app_commands.command(name="mission_accept")
    async def mission_accept(self, interaction, mission_number: int):
        await interaction.response.send_message("No missions are available for you right now.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MissionCommands(bot))
