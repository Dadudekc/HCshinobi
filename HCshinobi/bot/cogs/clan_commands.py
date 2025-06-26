from discord import app_commands
from discord.ext import commands
from ...utils.embeds import create_error_embed

class ClanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="my_clan", description="View your clan info")
    async def my_clan(self, interaction):
        await interaction.response.send_message("You have not been assigned a clan yet. Use `/roll_clan` to get started!", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClanCommands(bot))
