"""
Theme constants for the bot.
"""

import discord

class Theme:
    """Theme constants for the bot."""
    
    # General colors
    PRIMARY = discord.Color.blue()
    SUCCESS = discord.Color.green()
    ERROR = discord.Color.red()
    WARNING = discord.Color.orange()
    INFO = discord.Color.light_grey()
    
    # Feature-specific colors
    BATTLE = discord.Color.dark_red()
    LORE = discord.Color.purple()
    CLAN = discord.Color.gold()
    MISSION = discord.Color.dark_green()
    SYSTEM = discord.Color.dark_blue()
    TRAINING = discord.Color.teal()
    
    # Status colors
    ONLINE = discord.Color.green()
    OFFLINE = discord.Color.red()
    IDLE = discord.Color.orange()
    DND = discord.Color.dark_red()
    
    # Special colors
    RARE = discord.Color.gold()
    EPIC = discord.Color.purple()
    LEGENDARY = discord.Color.orange()
    MYTHIC = discord.Color.red() 