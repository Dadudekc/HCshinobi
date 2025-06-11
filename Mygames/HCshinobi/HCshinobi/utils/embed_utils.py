"""Utility functions for creating Discord embeds."""
import discord

def get_rarity_color(rarity: str) -> discord.Color:
    """Get the color for a clan's rarity."""
    rarity_colors = {
        "Ultra Rare": discord.Color.from_rgb(0, 0, 0),      # Black
        "Super Rare": discord.Color.from_rgb(255, 255, 255), # White
        "Rare": discord.Color.from_rgb(255, 215, 0),        # Gold
        "Uncommon": discord.Color.from_rgb(147, 112, 219),  # Purple
        "Common": discord.Color.from_rgb(169, 169, 169)     # Gray
    }
    return rarity_colors.get(rarity, discord.Color.blue())

def get_rarity_emoji(rarity: str) -> str:
    """Get the emoji for a clan's rarity."""
    rarity_emojis = {
        "Ultra Rare": "⚫",
        "Super Rare": "⚪",
        "Rare": "🟡",
        "Uncommon": "🟣",
        "Common": "⚪"
    }
    return rarity_emojis.get(rarity, "⚪")

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed with a red color scheme.
    
    Args:
        title: The title of the error embed
        description: The description/error message
        
    Returns:
        A discord.Embed object configured for error messages
    """
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    ) 