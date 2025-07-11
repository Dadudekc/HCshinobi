"""Common helpers for creating Discord embeds used throughout the bot."""

from __future__ import annotations

from typing import Iterable, Optional

import discord


def create_error_embed(message: str) -> discord.Embed:
    """Return a red embed with an error message."""

    return discord.Embed(
        title="Error",
        description=message,
        color=discord.Color.red(),
    )


def create_success_embed(message: str) -> discord.Embed:
    """Return a green embed with a success message."""

    return discord.Embed(
        title="Success",
        description=message,
        color=discord.Color.green(),
    )


def create_info_embed(title: str, message: str) -> discord.Embed:
    """Return a blue embed with an info message."""

    return discord.Embed(
        title=title,
        description=message,
        color=discord.Color.blue(),
    )


def create_character_embed(name: str, clan: Optional[str] = None) -> discord.Embed:
    """Create a basic character profile embed.

    Parameters
    ----------
    name:
        Name of the character.
    clan:
        Optional clan affiliation to display.
    """

    embed = discord.Embed(title=f"{name}'s Profile", color=discord.Color.blurple())
    if clan:
        embed.add_field(name="Clan", value=clan, inline=False)
    return embed


def create_clan_embed(
    name: str,
    description: str,
    *,
    rarity: Optional[str] = None,
    members: Optional[Iterable[str]] = None,
) -> discord.Embed:
    """Create an embed describing a clan."""

    embed = discord.Embed(title=f"{name} Clan", description=description)
    if rarity:
        embed.add_field(name="Rarity", value=rarity, inline=True)
    if members is not None:
        embed.add_field(name="Members", value=str(len(list(members))), inline=True)
    return embed


__all__ = [
    "create_error_embed",
    "create_success_embed",
    "create_info_embed",
    "create_character_embed",
    "create_clan_embed",
]
