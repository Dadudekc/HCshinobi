from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

class CurrencyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="balance", description="Check your balance")
    async def balance(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Currency system not implemented yet.")
