from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

class ClanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="view_clan")
    async def view_clan(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("This command is not implemented yet.")

    @app_commands.command(name="create_clan")
    async def create_clan(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("This command is not implemented yet.")

    @app_commands.command(name="join_clan")
    async def join_clan(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("This command is not implemented yet.")

    @app_commands.command(name="leave_clan")
    async def leave_clan(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("This command is not implemented yet.")

    @app_commands.command(name="clan_members")
    async def clan_members(self, interaction: discord.Interaction, clan_name: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("This command is not implemented yet.")

    @app_commands.command(name="clan_leaderboard")
    async def clan_leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("This command is not implemented yet.")

    @app_commands.command(name="my_clan")
    async def my_clan(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.followup.send("This command is not implemented yet.")
