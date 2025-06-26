from discord import app_commands
from discord.ext import commands
import discord
from ...utils.embeds import create_error_embed

class CharacterCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create", description="Create a new character")
    async def create(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(
            "You already have a Shinobi character! Use `/profile`.", ephemeral=True
        )

    @app_commands.command(name="profile", description="View your profile")
    async def profile(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(
            "You don't have a character yet! Use `/create` to start your journey.",
            ephemeral=True,
        )

    @app_commands.command(name="delete", description="Delete your character")
    async def delete(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send(
            "Character deleted", ephemeral=True
        )

    @app_commands.command(name="stats", description="View stats")
    async def stats(self, interaction, user: discord.User | None = None):
        await interaction.response.defer(ephemeral=user is None)
        await interaction.followup.send(
            "Stats unavailable", ephemeral=True
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCommands(bot))
