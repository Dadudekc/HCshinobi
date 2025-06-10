"""
Utilities for creating Discord UI elements like embeds with consistent styling.
"""

import discord

# Adjust import path based on where this file is located relative to core
from ..core.constants import RarityTier

def get_rarity_color(rarity_str: str) -> discord.Color:
    """Get the discord color corresponding to a clan's rarity string.
    
    Args:
        rarity_str: The rarity string (e.g., 'Common', 'Legendary') 
                      obtained from clan data.

    Returns:
        discord.Color: The color associated with the rarity.
    """
    try:
        rarity_enum = RarityTier(rarity_str) # Convert string to Enum member
    except ValueError:
        # Handle cases where the string doesn't match a RarityTier value
        return discord.Color.default()

    color_map = {
        RarityTier.COMMON: discord.Color.light_grey(),
        RarityTier.UNCOMMON: discord.Color.green(),
        RarityTier.RARE: discord.Color.blue(),
        RarityTier.EPIC: discord.Color.purple(),
        RarityTier.LEGENDARY: discord.Color.gold()
    }
    return color_map.get(rarity_enum, discord.Color.default()) 