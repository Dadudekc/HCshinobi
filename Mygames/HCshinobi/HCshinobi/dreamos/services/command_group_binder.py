"""Service for dynamic command group binding."""
from typing import List, Optional
import logging
from discord.ext import commands

logger = logging.getLogger(__name__)

def bind_commands_to_group(bot: commands.Bot, cog: commands.Cog, group_name: str, command_names: List[str]) -> None:
    """
    Bind commands from a cog to a command group.
    
    Args:
        bot: The bot instance
        cog: The cog containing the commands
        group_name: The name of the command group
        command_names: List of command names to bind
    """
    try:
        group = bot.tree.get_command(group_name)
        if not group:
            logger.warning(f"Command group '{group_name}' not found")
            return
            
        for name in command_names:
            command = getattr(cog, name, None)
            if command:
                group.add_command(command)
                logger.debug(f"Bound command '{name}' to group '{group_name}'")
            else:
                logger.warning(f"Command '{name}' not found in cog")
                
    except Exception as e:
        logger.error(f"Error binding commands to group '{group_name}': {e}", exc_info=True)

def validate_command_map(bot: commands.Bot) -> dict:
    """
    Validate the command map and check for potential issues.
    
    Args:
        bot: The bot instance
        
    Returns:
        dict: Validation results including duplicates, missing bindings, and unused groups
    """
    validation_results = {
        "duplicates": {},
        "missing_bindings": [],
        "unused_groups": []
    }
    
    # Track all command names and their locations
    command_map = {}
    
    # Get all registered commands
    for cog in bot.cogs.values():
        for command in cog.get_commands():
            if command.name in command_map:
                if "duplicates" not in validation_results:
                    validation_results["duplicates"] = {}
                validation_results["duplicates"][command.name] = {
                    "locations": command_map[command.name] + [cog.__class__.__name__]
                }
            else:
                command_map[command.name] = [cog.__class__.__name__]
                
    # Check for missing group bindings
    for cog in bot.cogs.values():
        if hasattr(cog, "group_name"):
            group = bot.tree.get_command(cog.group_name)
            if not group:
                validation_results["missing_bindings"].append(cog.group_name)
                
    # Check for unused groups
    all_groups = set()
    for cog in bot.cogs.values():
        if hasattr(cog, "group_name"):
            all_groups.add(cog.group_name)
            
    registered_groups = set(bot.tree.get_commands())
    validation_results["unused_groups"] = list(registered_groups - all_groups)
    
    return validation_results 