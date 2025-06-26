from discord import app_commands
from discord.ext import commands
from ...utils.embeds import create_error_embed

class CurrencyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="balance", description="Check balance")
    async def balance(self, interaction):
        await interaction.response.send_message(embed=create_error_embed("Currency system not implemented yet."), ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CurrencyCommands(bot))
