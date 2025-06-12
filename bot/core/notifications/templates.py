import discord
from typing import Optional
import json
import os
import logging

logger = logging.getLogger(__name__)

# --- Load Template Configuration --- #
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'announcement_templates.json')

_templates_config = {}
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        _templates_config = json.load(f)
    logger.info(f"Successfully loaded announcement templates from {CONFIG_PATH}")
except FileNotFoundError:
    logger.error(f"ERROR: Announcement template config file not found at {CONFIG_PATH}. Using default fallbacks.")
except json.JSONDecodeError as e:
    logger.error(f"ERROR: Failed to parse announcement template config file {CONFIG_PATH}: {e}. Using default fallbacks.")
except Exception as e:
    logger.error(f"An unexpected error occurred while loading {CONFIG_PATH}: {e}", exc_info=True)

def _get_template(template_name: str) -> dict:
    """Helper to safely get a template config, with fallback."""
    return _templates_config.get(template_name, {})

def _format_string(format_str: Optional[str], **kwargs) -> str:
    """Safely format a string, returning empty string if format_str is None."""
    return format_str.format(**kwargs) if format_str else ""

def _get_color(template_config: dict, default_color: discord.Color) -> discord.Color:
    """Safely get color from config, falling back to default."""
    color_hex = template_config.get('color')
    if color_hex:
        try:
            return discord.Color(int(color_hex.lstrip('#'), 16))
        except ValueError:
            logger.warning(f"Invalid color format '{color_hex}' in config. Using default.")
    return default_color

# --- Embed Creation Functions --- #

def battle_alert(title: str, fighter_a: str, fighter_b: str, arena: str, time_str: str) -> discord.Embed:
    """Create a battle alert embed using config."""
    config = _get_template('battle_alert')
    
    embed = discord.Embed(
        title=_format_string(config.get('title_format'), title=title),
        description=_format_string(config.get('description_format'), fighter_a=fighter_a, fighter_b=fighter_b, arena=arena, time_str=time_str),
        color=_get_color(config, discord.Color.red()) # Default red
    )
    if footer := config.get('footer_text'):
        embed.set_footer(text=footer)
    
    return embed

def server_announcement(title: str, message: str) -> discord.Embed:
    """Create a server announcement embed using config."""
    config = _get_template('server_announcement')
    
    embed = discord.Embed(
        title=_format_string(config.get('title_format'), title=title),
        description=_format_string(config.get('description_format'), message=message),
        color=_get_color(config, discord.Color.blue()) # Default blue
    )
    if footer := config.get('footer_text'):
        embed.set_footer(text=footer)
    
    return embed

def lore_drop(title: str, snippet: str, chapter: Optional[str] = None, image_url: Optional[str] = None) -> discord.Embed:
    """Create a lore drop embed using config."""
    config = _get_template('lore_drop')
    
    embed = discord.Embed(
        title=_format_string(config.get('title_format'), title=title),
        description=_format_string(config.get('description_format'), snippet=snippet),
        color=_get_color(config, discord.Color.purple()) # Default purple
    )

    # Handle footer with optional chapter
    footer_format = config.get('footer_format', "Lore Drop{chapter_suffix}") # Default format
    chapter_suffix = f' – {chapter}' if chapter else ''
    embed.set_footer(text=_format_string(footer_format, chapter_suffix=chapter_suffix))

    if image_url:
        embed.set_image(url=image_url)

    return embed

def system_update(title: str, version: str, changes: str, downtime: Optional[str] = None) -> discord.Embed:
    """Create a system update embed using config."""
    config = _get_template('system_update')
    
    embed = discord.Embed(
        title=_format_string(config.get('title_format'), title=title),
        description=_format_string(config.get('description_format'), version=version, changes=changes),
        color=_get_color(config, discord.Color.green()) # Default green
    )
    
    # Handle optional fields
    field_config = config.get('fields', {})
    if downtime and 'Downtime' in field_config:
        embed.add_field(name="Downtime", value=_format_string(field_config['Downtime'], downtime=downtime), inline=False)
        
    if footer := config.get('footer_text'):
        embed.set_footer(text=footer)
    return embed

def training_mission(title: str, description: str, difficulty: str, rewards: str) -> discord.Embed:
    """Create a training mission embed using config."""
    config = _get_template('training_mission')
    
    embed = discord.Embed(
        title=_format_string(config.get('title_format'), title=title),
        description=_format_string(config.get('description_format'), description=description),
        color=_get_color(config, discord.Color.gold()) # Default gold
    )
    
    # Handle fields
    field_config = config.get('fields', {})
    if 'Difficulty' in field_config:
         embed.add_field(
            name="Difficulty",
            value=_format_string(field_config['Difficulty'], difficulty=difficulty),
            inline=True
         )
    if 'Rewards' in field_config:
        embed.add_field(
            name="Rewards",
            value=_format_string(field_config['Rewards'], rewards=rewards),
            inline=True
        )
        
    if footer := config.get('footer_text'):
        embed.set_footer(text=footer)
    return embed

def system_alert(title: str, message: str, icon_url: Optional[str] = None) -> discord.Embed:
    """Create a system alert embed using config."""
    config = _get_template('system_alert')
    
    embed = discord.Embed(
        title=_format_string(config.get('title_format'), title=title),
        description=_format_string(config.get('description_format'), message=message),
        color=_get_color(config, discord.Color.orange()) # Default orange
    )
    
    if footer := config.get('footer_text'):
        embed.set_footer(text=footer)
    
    if icon_url:
        embed.set_thumbnail(url=icon_url)
        
    return embed 