import discord
from typing import Optional

class Theme:
    """Color themes for different notification types."""
    SYSTEM = discord.Color.blue()
    BATTLE = discord.Color.red()
    LORE = discord.Color.purple()
    ALERT = discord.Color.orange()
    UPDATE = discord.Color.green()
    TRAINING = discord.Color.gold()

def battle_alert(title: str, fighter_a: str, fighter_b: str, arena: str, time_str: str) -> discord.Embed:
    """Create a battle alert embed.
    
    Args:
        title: Alert title
        fighter_a: First fighter's name
        fighter_b: Second fighter's name
        arena: Battle location
        time_str: Time of battle
        
    Returns:
        Discord embed for battle alert
    """
    return discord.Embed(
        title=f"⚔️ {title}",
        description=f"**{fighter_a}** vs **{fighter_b}**\n📍 Location: *{arena}*\n🕒 Time: *{time_str}*",
        color=Theme.BATTLE
    ).set_footer(text="Prepare for battle...")

def server_announcement(title: str, message: str) -> discord.Embed:
    """Create a server announcement embed.
    
    Args:
        title: Announcement title
        message: Announcement content (supports markdown)
        
    Returns:
        Discord embed for server announcement
    """
    return discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=Theme.SYSTEM
    ).set_footer(text="Stay informed, stay sharp.")

def lore_drop(title: str, snippet: str, chapter: Optional[str] = None, image_url: Optional[str] = None) -> discord.Embed:
    """Create a lore drop embed.
    
    Args:
        title: Lore title
        snippet: Lore content (supports markdown)
        chapter: Optional chapter name
        image_url: Optional image URL
        
    Returns:
        Discord embed for lore drop
    """
    embed = discord.Embed(
        title=f"📖 {title}",
        description=snippet,
        color=Theme.LORE
    ).set_footer(text=f"Lore Drop{f' – {chapter}' if chapter else ''}")

    if image_url:
        embed.set_image(url=image_url)

    return embed

def system_update(title: str, version: str, changes: str, downtime: Optional[str] = None) -> discord.Embed:
    """Create a system update embed.
    
    Args:
        title: Update title
        version: Version number
        changes: List of changes (supports markdown)
        downtime: Optional downtime information
        
    Returns:
        Discord embed for system update
    """
    embed = discord.Embed(
        title=f"🔄 {title}",
        description=f"**Version:** `{version}`\n\n**Changes:**\n{changes}",
        color=Theme.UPDATE
    )
    
    if downtime:
        embed.add_field(name="Downtime", value=downtime, inline=False)
        
    embed.set_footer(text="Thank you for your patience!")
    return embed

def training_mission(title: str, description: str, difficulty: str, rewards: str) -> discord.Embed:
    """Create a training mission embed.
    
    Args:
        title: Mission title
        description: Mission description (supports markdown)
        difficulty: Mission difficulty
        rewards: Available rewards
        
    Returns:
        Discord embed for training mission
    """
    return discord.Embed(
        title=f"🎯 {title}",
        description=description,
        color=Theme.TRAINING
    ).add_field(
        name="Difficulty",
        value=f"**{difficulty}**",
        inline=True
    ).add_field(
        name="Rewards",
        value=rewards,
        inline=True
    ).set_footer(text="Ready to train?")

def system_alert(title: str, message: str, icon_url: Optional[str] = None) -> discord.Embed:
    """Create a system alert embed.
    
    Args:
        title: Alert title
        message: Alert content (supports markdown)
        icon_url: Optional icon URL
        
    Returns:
        Discord embed for system alert
    """
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=message,
        color=Theme.ALERT
    ).set_footer(text="System Alert")
    
    if icon_url:
        embed.set_thumbnail(url=icon_url)
        
    return embed 