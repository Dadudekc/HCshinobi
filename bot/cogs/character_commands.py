"""Simplified character command cog."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class CharacterCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create", description="Create a character")
    async def create(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        services = getattr(self.bot, "services", None)
        if not services:
            await interaction.followup.send("Service container not available", ephemeral=True)
            return
        char = await services.character_system.get_character(interaction.user.id)
        if char:
            await interaction.followup.send("You already have a Shinobi character! Use `/profile`.", ephemeral=True)
            return
        result = await services.character_system.create_character(interaction.user.id, interaction.user.display_name, "")
        embed = discord.Embed(title="Character Created!", description=f"Welcome, {result.name}!", color=discord.Color.green())
        embed.add_field(name="Level", value=str(result.level))
        embed.add_field(name="Rank", value=result.rank)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="View your character")
    async def profile(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        services = getattr(self.bot, "services", None)
        char = await services.character_system.get_character(interaction.user.id)
        if not char:
            await interaction.followup.send("You don't have a character yet! Use `/create` to start your journey.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{interaction.user.display_name}'s Shinobi Profile")
        embed.add_field(name="👤 Name", value=char.name, inline=False)
        embed.add_field(name="⚜️ Clan", value=getattr(char, "clan", "N/A"), inline=False)
        embed.add_field(name="📈 Level", value=str(char.level), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="Delete your character")
    async def delete(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        services = getattr(self.bot, "services", None)
        char = await services.character_system.get_character(interaction.user.id)
        if not char:
            await interaction.followup.send("You don't have a character yet! Use `/create` to start your journey.", ephemeral=True)
            return
        await services.character_system.delete_character(interaction.user.id)
        await interaction.followup.send("🗑️ Your character has been deleted.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCommands(bot))
