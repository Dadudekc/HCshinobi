"""Utility functions for creating Discord embeds."""
import discord
from typing import Optional, Dict, Any

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


def create_character_embed(
    character: Any, 
    currency_system: 'CurrencySystem', 
    achievements_data: Optional[Dict[str, Dict[str, Any]]] = None, 
    titles_data: Optional[Dict[str, Dict[str, Any]]] = None
) -> discord.Embed:
    """Create an embed for displaying character information.

    Args:
        character: The character data (either a Character object or dictionary)
        currency_system: The CurrencySystem instance to fetch the balance.
        achievements_data: Optional dictionary containing full achievement definitions.
        titles_data: Optional dictionary containing full title definitions.

    Returns:
        discord.Embed: The character embed
    """
    # Check if character is an object or dictionary and access fields accordingly
    if hasattr(character, 'name') and not isinstance(character, dict):
        # It's a Character object
        char_name = character.name
        char_rank = getattr(character, 'rank', 'Unranked')
        char_clan = getattr(character, 'clan', 'None')
        char_level = getattr(character, 'level', 1)
        char_exp = getattr(character, 'exp', 0)
        char_ryo = getattr(character, 'ryo', 0)
        char_spec = getattr(character, 'specialization', None)
        char_status = getattr(character, 'status', 'Idle')
        char_stats = getattr(character, 'stats', {})
        char_titles = getattr(character, 'titles', [])
        char_equipped_title = getattr(character, 'equipped_title', None)
        char_achievements = getattr(character, 'achievements', [])
        char_jutsu = getattr(character, 'jutsu', [])
        char_id = getattr(character, 'id', 'N/A')
    else:
        # It's a dictionary
        char_name = character['name']
        char_rank = character.get('rank', 'Unranked')
        char_clan = character.get('clan', 'None')
        char_level = character.get('level', 1)
        char_exp = character.get('exp', 0)
        char_ryo = character.get('ryo', 0)
        char_spec = character.get('specialization')
        char_status = character.get('status', 'Idle')
        char_stats = character.get('stats', {})
        char_titles = character.get('titles', [])
        char_equipped_title = character.get('equipped_title')
        char_achievements = character.get('achievements', [])
        char_jutsu = character.get('known_jutsu', [])
        char_id = character.get('id', 'N/A')

    embed = discord.Embed(
        title=f"📝 {char_name} [Rank: {char_rank}]",
        color=discord.Color.blue()
    )
    
    # Add character fields
    embed.add_field(
        name="Clan",
        value=char_clan,
        inline=True
    )
    embed.add_field(
        name="Level",
        value=str(char_level),
        inline=True
    )
    exp_needed = 100 * char_level
    embed.add_field(
        name="Experience",
        value=f"{char_exp}/{exp_needed}",
        inline=True
    )
    
    # Fetch Ryo from CurrencySystem
    ryo_balance = 0
    if currency_system and char_id != 'N/A':
        try:
            ryo_balance = currency_system.get_player_balance(char_id)
        except Exception as e:
            print(f"Error fetching balance for {char_id} in create_character_embed: {e}")
            ryo_balance = 'Error'
    
    embed.add_field(
        name="Ryo",
        value=f"💰 {ryo_balance:,}" if isinstance(ryo_balance, int) else f"💰 {ryo_balance}",
        inline=True
    )
    if char_spec:
        embed.add_field(
            name="Specialization",
            value=char_spec,
            inline=True
        )
    embed.add_field(
        name="Status",
        value=char_status,
        inline=True
    )

    # Add stats
    stats_text = (
        f"**Ninjutsu:** {char_stats.get('ninjutsu', 0)}\n"
        f"**Taijutsu:** {char_stats.get('taijutsu', 0)}\n"
        f"**Genjutsu:** {char_stats.get('genjutsu', 0)}\n"
        f"**Chakra Control:** {char_stats.get('chakra_control', 0)}\n"
        f"**Speed:** {char_stats.get('speed', 0)}\n"
        f"**Strength:** {char_stats.get('strength', 0)}\n"
        f"**Endurance:** {char_stats.get('endurance', 0)}\n"
        f"**Intelligence:** {char_stats.get('intelligence', 0)}"
    )
    embed.add_field(
        name="📊 Stats",
        value=stats_text,
        inline=False
    )

    # Add Titles
    if char_titles or char_equipped_title:
        title_lines = []
        if char_equipped_title:
            title_name = char_equipped_title
            if titles_data and char_equipped_title in titles_data:
                title_name = titles_data[char_equipped_title].get('name', char_equipped_title)
            title_lines.append(f"**{title_name} (Equipped)**")

        # Add other earned titles
        other_titles = [t for t in char_titles if t != char_equipped_title]
        if other_titles:
            if titles_data:
                other_title_names = [titles_data.get(t, {}).get('name', t) for t in other_titles]
                title_lines.extend(f"• {name}" for name in other_title_names)
            else:
                title_lines.extend(f"• {t}" for t in other_titles)

        if title_lines:
            embed.add_field(
                name="🎖️ Titles",
                value="\n".join(title_lines) if title_lines else "None",
                inline=False
            )
        else:
             embed.add_field(name="🎖️ Titles", value="None", inline=False)


    # Add Achievements
    if char_achievements:
        achievement_lines = []
        if achievements_data:
            for ach_key in char_achievements:
                ach_info = achievements_data.get(ach_key, {})
                name = ach_info.get('name', ach_key)
                achievement_lines.append(f"• {name}")
        else:
            achievement_lines.extend(f"• {ach_key}" for ach_key in char_achievements)

        embed.add_field(
            name="🏆 Achievements",
            value="\n".join(achievement_lines) if achievement_lines else "None",
            inline=False
        )
    else:
        embed.add_field(name="🏆 Achievements", value="None", inline=False)


    # Add known jutsu
    if char_jutsu:
        jutsu_display_limit = 5
        jutsu_text = "\n".join(f"• {j}" for j in char_jutsu[:jutsu_display_limit])
        if len(char_jutsu) > jutsu_display_limit:
            jutsu_text += f"\n*...and {len(char_jutsu) - jutsu_display_limit} more. Use `/known_jutsu` to see all.*"
        embed.add_field(
            name="📜 Known Jutsu",
            value=jutsu_text,
            inline=False
        )
    else:
        embed.add_field(name="📜 Known Jutsu", value="None Learned", inline=False)

    # Add Footer
    embed.set_footer(text=f"Character ID: {char_id}")

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
    
    # Add new fields for village, kekkei genkai and traits
    if clan.village:
        embed.add_field(
            name="Village",
            value=clan.village,
            inline=True
        )
    
    if clan.kekkei_genkai and len(clan.kekkei_genkai) > 0:
        embed.add_field(
            name="Kekkei Genkai",
            value=", ".join(clan.kekkei_genkai),
            inline=False
        )
    
    if clan.traits and len(clan.traits) > 0:
        embed.add_field(
            name="Traits",
            value=", ".join(clan.traits),
            inline=False
        )
    
    return embed 