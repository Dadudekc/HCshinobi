from discord import app_commands
from discord.ext import commands
from ...utils.embeds import create_error_embed

class TrainingCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="train")
    async def train(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("You must create a character first using `/create`.", ephemeral=True)

    @app_commands.command(name="training_status")
    async def training_status(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("You are not currently training and have no active cooldown.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TrainingCommands(bot))
