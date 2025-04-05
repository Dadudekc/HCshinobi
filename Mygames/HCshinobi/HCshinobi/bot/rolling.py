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
    # Dependencies are now assumed to be available via a context or bot instance
    # that provides access to the initialized services.
    clan_engine: ClanAssignmentEngine,
    token_system: Optional[TokenSystem] = None,
    # Added parameters for personality and boost
    personality: Optional[str] = None,
    token_boost_clan: Optional[str] = None,
    token_count: int = 0
) -> Dict[str, Any]:
    """
    Process a clan roll request from Discord. Assigns clan purely based on weights.
    Uses the provided ClanAssignmentEngine instance.
    
    Args:
        user_id: Discord ID of the user
        username: Display name of the user
        clan_engine: Initialized ClanAssignmentEngine instance.
        token_system: Initialized TokenSystem instance (optional, if token usage is added).
        personality: Optional player personality choice.
        token_boost_clan: Optional clan name to boost with tokens.
        token_count: Number of tokens to use for boosting (0-3).
        
    Returns:
        Dict[str, Any]: The clan assignment result containing at least:
            - clan_name: Name of assigned clan
            - tokens_spent: Always 0 in this simplified version
            
    Raises:
        ValueError: If clan assignment fails internally.
    """
    # Remove the default instance creation
    # if token_system is None:
    #     logger.warning("No TokenSystem provided, creating default instance")
    #     token_system = TokenSystem()
        
    # if clan_engine is None:
    #     logger.warning("No ClanAssignmentEngine provided, creating default instance")
    #     clan_engine = ClanAssignmentEngine() # This was using the old/wrong version

    if clan_engine is None:
         logger.error("ClanAssignmentEngine was not provided to process_clan_roll.")
         raise ValueError("Clan Assignment Engine is required.")

    # Personality, token_boost_clan, and token_count are now passed as arguments

    # --- Optional: Add token consumption logic here if boosting costs tokens ---
    if token_count > 0:
        if token_system is None:
            logger.warning(f"User {user_id} attempted boost with {token_count} tokens, but TokenSystem is unavailable.")
            # Decide handling: proceed without cost, or raise error?
            # For now, let's log and proceed, assuming boost is free if system missing.
            pass
        else:
            try:
                # Assuming a method exists to use tokens for boosting
                # We might need to add this method to TokenSystem if it doesn't exist
                # success, message = token_system.use_tokens_for_boost(user_id, token_count)
                # if not success:
                #     logger.warning(f"Token boost failed for {user_id}: {message}")
                #     # Maybe raise an error or inform the user?
                #     # For now, just log and continue the assignment
                #     pass
                logger.info(f"User {user_id} is boosting with {token_count} tokens. (Consumption logic placeholder)") # Placeholder log
            except Exception as token_error:
                logger.error(f"Error using tokens for boost for user {user_id}: {token_error}", exc_info=True)
                # Decide handling: proceed without boost, raise error?
                # For now, log and proceed without boost?
                token_count = 0 # Reset token count on error? Or raise?
                token_boost_clan = None # Clear target clan too?
                # For safety, let's just log and continue the assignment for now
                pass
    # -----------------------------------------------------------------------

    try:
        # Call the assign_clan method on the provided engine instance
        assignment_result = clan_engine.assign_clan(
            player_id=user_id,
            player_name=username,
            personality=personality, # Use passed parameter
            token_boost_clan=token_boost_clan, # Use passed parameter
            token_count=token_count # Use passed parameter
        )
        
        if not assignment_result or "error" in assignment_result:
            error_msg = assignment_result.get("error", "Unknown error") if assignment_result else "No result"
            logger.error(f"Clan assignment failed for user {user_id}: {error_msg}")
            raise ValueError(f"Clan assignment failed: {error_msg}")
            
        # Simplify the return value for now
        return {
            "clan_name": assignment_result.get("assigned_clan", "Unknown"),
            "tokens_spent": token_count # Currently always 0
        }

    except Exception as e:
        logger.error(f"Unexpected error during clan roll processing for {user_id}: {e}", exc_info=True)
        # Re-raise or handle as appropriate for the calling context
        raise ValueError(f"Internal error during clan assignment: {e}")


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