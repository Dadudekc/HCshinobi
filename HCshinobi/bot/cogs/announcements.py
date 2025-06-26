from discord import app_commands
from discord.ext import commands

class AnnouncementCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="announce")
    async def announce(self, interaction, title: str, message: str):
        await interaction.response.defer(ephemeral=True)
        if not message:
            await interaction.followup.send("Announcement message cannot be empty", ephemeral=True)
        else:
            await interaction.followup.send(ephemeral=True)

    @app_commands.command(name="check_permissions")
    async def check_permissions(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(embed=commands.Embed())

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnnouncementCommands(bot))
