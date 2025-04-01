"""
Clan rolling module for the Naruto MMO Discord game.
Handles the clan assignment process for Discord users.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from HCshinobi.core.assignment_engine import ClanAssignmentEngine
from HCshinobi.core.token_system import TokenSystem, TokenError
from HCshinobi.core.personality_modifiers import PersonalityModifiers

# Try to get project logger, fall back to standard
try:
    from HCshinobi.utils.logging import get_logger
    logger = get_logger("rolling")
except ImportError:
    logger = logging.getLogger("rolling")


async def process_clan_roll(
    user_id: str,
    username: str,
    token_system: Optional[TokenSystem] = None,
    clan_engine: Optional[ClanAssignmentEngine] = None,
    personality_modifiers: Optional[PersonalityModifiers] = None
) -> Dict[str, Any]:
    """
    Process a clan roll request from Discord. Assigns clan purely based on weights.
    
    Args:
        user_id: Discord ID of the user
        username: Display name of the user
        token_system: TokenSystem instance (optional)
        clan_engine: ClanAssignmentEngine instance (optional)
        personality_modifiers: PersonalityModifiers instance (optional)
        
    Returns:
        Dict[str, Any]: The clan assignment result containing at least:
            - clan_name: Name of assigned clan
            - tokens_spent: Always 0 in this simplified version
            
    Raises:
        ValueError: If core systems are missing or assignment fails
    """
    # Default instances if not provided (for backward compatibility or testing)
    if token_system is None:
        logger.warning("No TokenSystem provided, creating default instance")
        token_system = TokenSystem()
        
    if clan_engine is None:
        logger.warning("No ClanAssignmentEngine provided, creating default instance")
        clan_engine = ClanAssignmentEngine()
        
    if personality_modifiers is None:
        logger.warning("No PersonalityModifiers provided, creating default instance")
        personality_modifiers = PersonalityModifiers()
    
    # Add a small delay for dramatic effect
    await asyncio.sleep(1.5)
    
    try:
        # Assign clan using the assignment engine - remove unused args
        result = clan_engine.assign_clan(
            player_id=user_id,
            player_name=username,
        )
        
        # Add tokens spent (always 0) to result for consistency
        result['tokens_spent'] = 0
        
        logger.info(f"User {user_id} assigned to clan {result['clan_name']}")
        return result
        
    except Exception as e:
        logger.error(f"Error during clan assignment for user {user_id}: {str(e)}", exc_info=True)
        raise ValueError(f"Clan assignment error: {str(e)}")


async def process_reroll(
    user_id: str,
    username: str,
    token_system: Optional[TokenSystem] = None,
    clan_engine: Optional[ClanAssignmentEngine] = None
) -> Dict[str, Any]:
    """
    Process a clan reroll request from Discord.
    
    Args:
        user_id: Discord ID of the user
        username: Display name of the user
        token_system: TokenSystem instance (optional)
        clan_engine: ClanAssignmentEngine instance (optional)
        
    Returns:
        Dict[str, Any]: The clan assignment result
        
    Raises:
        TokenError: If there's an issue with token usage or reroll eligibility
    """
    # Default instances if not provided
    if token_system is None:
        token_system = TokenSystem()
        
    if clan_engine is None:
        clan_engine = ClanAssignmentEngine()
    
    # Check reroll eligibility and use tokens
    success, message, remaining = token_system.use_tokens_for_reroll(user_id)
    
    if not success:
        raise TokenError(message)
    
    # Add a small delay for dramatic effect
    await asyncio.sleep(2)
    
    # Assign clan using the assignment engine
    result = clan_engine.assign_clan(
        player_id=user_id,
        player_name=username,
    )
    
    return result


# Helper functions for roll animations and presentations

async def create_roll_animation(message):
    """
    Create a rolling animation by editing a message multiple times.
    
    Args:
        message: The Discord message to edit
        
    Returns:
        None
    """
    frames = [
        "🎲 Rolling clan...",
        "🎲 Rolling clan..",
        "🎲 Rolling clan.",
        "🎲 Rolling clan..",
        "🎲 Rolling clan..."
    ]
    
    for frame in frames:
        await message.edit(content=frame)
        await asyncio.sleep(0.5)


async def create_legendary_animation(message):
    """
    Create a special animation for legendary clan rolls.
    
    Args:
        message: The Discord message to edit
        
    Returns:
        None
    """
    frames = [
        "✨ The spirits stir...",
        "✨✨ The ancestors watch...",
        "✨✨✨ A legendary clan has chosen you! ✨✨✨"
    ]
    
    for frame in frames:
        await message.edit(content=frame)
        await asyncio.sleep(1.0) 