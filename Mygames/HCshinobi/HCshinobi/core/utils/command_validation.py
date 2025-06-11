"""Command validation utilities for the bot."""
import logging
from typing import Dict, List, Optional
from discord.ext import commands
from discord import app_commands

logger = logging.getLogger(__name__)

def validate_command_map(bot: commands.Bot) -> Dict[str, List[str]]:
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
        "unused_groups": [],
        "orphaned_commands": []
    }
    
    # Track all command names and their locations
    command_map = {}
    group_map = {}
    
    # Get all registered commands
    for cmd in bot.tree.get_commands():
        if isinstance(cmd, app_commands.Group):
            group_map[cmd.name] = cmd
            continue
            
        if cmd.name in command_map:
            if "duplicates" not in validation_results:
                validation_results["duplicates"] = {}
            validation_results["duplicates"][cmd.name] = {
                "locations": command_map[cmd.name] + [cmd.parent.name if cmd.parent else "root"]
            }
        else:
            command_map[cmd.name] = [cmd.parent.name if cmd.parent else "root"]
            
        # Check for orphaned commands (commands without proper group binding)
        if hasattr(cmd, "group_name") and cmd.group_name:
            group = bot.tree.get_command(cmd.group_name)
            if not group:
                validation_results["orphaned_commands"].append({
                    "name": cmd.name,
                    "intended_group": cmd.group_name
                })
    
    # Check for unused groups
    registered_groups = set(group_map.keys())
    used_groups = set(cmd.parent.name for cmd in bot.tree.get_commands() if cmd.parent)
    validation_results["unused_groups"] = list(registered_groups - used_groups)
    
    return validation_results

async def post_setup_validation(bot: commands.Bot) -> None:
    """
    Run validation after bot setup and log results.
    
    Args:
        bot: The bot instance
    """
    logger.info("Running post-setup command validation...")
    
    validation_results = validate_command_map(bot)
    has_errors = False
    
    # Log duplicates
    if validation_results["duplicates"]:
        has_errors = True
        logger.error("Found duplicate commands:")
        for cmd_name, info in validation_results["duplicates"].items():
            logger.error(f"  • {cmd_name} found in: {', '.join(info['locations'])}")
    
    # Log missing bindings
    if validation_results["missing_bindings"]:
        has_errors = True
        logger.error("Found commands with missing group bindings:")
        for cmd in validation_results["missing_bindings"]:
            logger.error(f"  • {cmd}")
    
    # Log unused groups
    if validation_results["unused_groups"]:
        has_errors = True
        logger.warning("Found unused command groups:")
        for group in validation_results["unused_groups"]:
            logger.warning(f"  • {group}")
    
    # Log orphaned commands
    if validation_results["orphaned_commands"]:
        has_errors = True
        logger.error("Found orphaned commands:")
        for cmd in validation_results["orphaned_commands"]:
            logger.error(f"  • {cmd['name']} (intended group: {cmd['intended_group']})")
    
    if not has_errors:
        logger.info("✅ All commands validated successfully.")
    else:
        logger.error("❌ Command validation failed. See errors above.")
        raise RuntimeError("Command validation failed") 