"""Utility helpers to create basic embeds."""

import discord


def create_error_embed(message: str) -> discord.Embed:
    embed = discord.Embed(title="Error", description=message, color=discord.Color.red())
    return embed


def create_character_embed(name: str) -> discord.Embed:
    embed = discord.Embed(title=f"{name}'s Profile")
    return embed


def create_clan_embed(name: str) -> discord.Embed:
    embed = discord.Embed(title=f"Clan: {name}")
    return embed
