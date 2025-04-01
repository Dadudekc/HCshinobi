"""Utility functions for creating Discord embeds."""
import discord
from typing import Optional

from ..core.clan import Clan


def create_error_embed(
    title: str,
    description: str,
    color: Optional[discord.Color] = None
) -> discord.Embed:
    """Create an error embed.
    
    Args:
        title: The embed title
        description: The embed description
        color: The embed color (default: red)
        
    Returns:
        discord.Embed: The error embed
    """
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=color or discord.Color.red()
    )
    return embed


def create_success_embed(
    title: str,
    description: str,
    color: Optional[discord.Color] = None
) -> discord.Embed:
    """Create a success embed.
    
    Args:
        title: The embed title
        description: The embed description
        color: The embed color (default: green)
        
    Returns:
        discord.Embed: The success embed
    """
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=color or discord.Color.green()
    )
    return embed


def create_info_embed(
    title: str,
    description: str,
    color: Optional[discord.Color] = None
) -> discord.Embed:
    """Create an info embed.
    
    Args:
        title: The embed title
        description: The embed description
        color: The embed color (default: blue)
        
    Returns:
        discord.Embed: The info embed
    """
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=color or discord.Color.blue()
    )
    return embed


def create_warning_embed(
    title: str,
    description: str,
    color: Optional[discord.Color] = None
) -> discord.Embed:
    """Create a warning embed.
    
    Args:
        title: The embed title
        description: The embed description
        color: The embed color (default: yellow)
        
    Returns:
        discord.Embed: The warning embed
    """
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=color or discord.Color.yellow()
    )
    return embed


def create_loading_embed(
    title: str,
    description: str,
    color: Optional[discord.Color] = None
) -> discord.Embed:
    """Create a loading embed.
    
    Args:
        title: The embed title
        description: The embed description
        color: The embed color (default: blurple)
        
    Returns:
        discord.Embed: The loading embed
    """
    embed = discord.Embed(
        title=f"⏳ {title}",
        description=description,
        color=color or discord.Color.blurple()
    )
    return embed


def create_character_embed(character: dict) -> discord.Embed:
    """Create an embed for displaying character information.
    
    Args:
        character: The character data dictionary
        
    Returns:
        discord.Embed: The character embed
    """
    embed = discord.Embed(
        title=f"📝 {character['name']}",
        color=discord.Color.blue()
    )
    
    # Add character fields
    embed.add_field(
        name="Clan",
        value=character.get("clan", "None"),
        inline=True
    )
    embed.add_field(
        name="Level",
        value=str(character.get("level", 1)),
        inline=True
    )
    embed.add_field(
        name="Experience",
        value=f"{character.get('exp', 0)}/100",
        inline=True
    )
    
    # Add stats
    stats = character.get("stats", {})
    stats_text = (
        f"**Ninjutsu:** {stats.get('ninjutsu', 0)}\n"
        f"**Taijutsu:** {stats.get('taijutsu', 0)}\n"
        f"**Genjutsu:** {stats.get('genjutsu', 0)}\n"
        f"**Chakra Control:** {stats.get('chakra_control', 0)}\n"
        f"**Speed:** {stats.get('speed', 0)}\n"
        f"**Strength:** {stats.get('strength', 0)}"
    )
    embed.add_field(
        name="Stats",
        value=stats_text,
        inline=False
    )
    
    # Add jutsu
    jutsu = character.get("jutsu", [])
    if jutsu:
        embed.add_field(
            name="Jutsu",
            value="\n".join(f"• {j}" for j in jutsu),
            inline=False
        )
    
    return embed


def create_clan_embed(clan: Clan, color: Optional[int] = None) -> discord.Embed:
    """Create a Discord embed for a clan.
    
    Args:
        clan: Clan to create embed for
        color: Optional color override
        
    Returns:
        Discord embed
    """
    embed = discord.Embed(
        title=clan.name,
        description=clan.description,
        color=color or 0xFFFFFF
    )
    
    embed.add_field(
        name="Rarity",
        value=clan.rarity.title(),
        inline=True
    )
    
    embed.add_field(
        name="Members",
        value=str(len(clan.members)),
        inline=True
    )
    
    return embed 