"""Placeholder character commands."""

from discord import app_commands
from discord.ext import commands

from HCshinobi.utils.embeds import create_error_embed

class CharacterCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create", description="Create a new character")
    async def create(self, interaction):
        await interaction.response.send_message(
            embed=create_error_embed("Character system not implemented yet."),
            ephemeral=True,
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCommands(bot))
