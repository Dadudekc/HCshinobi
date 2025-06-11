"""
Handles character profile and stats viewing commands.
Part of the CharacterCommands cog refactor.
"""
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, TYPE_CHECKING
import logging

# Relative imports for core systems and utilities
from ...core.character import Character
from ...utils.discord_ui import get_rarity_color
from ...utils.embeds import create_character_embed

# Type hint for the main cog
if TYPE_CHECKING:
    from .character_commands import CharacterCommands

logger = logging.getLogger(__name__)

# --- Commands Moved Here --- #

async def view_profile_impl(cog: 'CharacterCommands', interaction: discord.Interaction):
    """Implementation for the /profile command."""
    # Defer the interaction early to acknowledge it once.
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.HTTPException as e:
        cog.logger.error(f"Error deferring interaction for profile view: {e}", exc_info=True)
        # Cannot followup if defer failed
        return

    try:
        character = await cog.character_system.get_character(str(interaction.user.id))
        if not character:
            try:
                await interaction.followup.send(
                    "❌ You don\'t have a character yet! Use `/create` to make one.",
                    ephemeral=True
                )
            except discord.errors.HTTPException as http_err:
                cog.logger.error(f"HTTP error sending followup for no profile: {http_err}", exc_info=True)
            return

        # --- Get CurrencySystem --- #
        currency_system = None
        currency_cog = cog.bot.get_cog('Currency')
        if currency_cog:
             currency_system = currency_cog.get_system()
        else:
             cog.logger.error("CurrencyCog not found, cannot display balance in profile.")
             # Proceed without balance if cog not found
        # --- End Get CurrencySystem --- #

        # Pass currency_system to the embed creation function
        embed = create_character_embed(character, currency_system=currency_system)
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.errors.HTTPException as http_err:
            cog.logger.error(f"HTTP error sending profile embed followup: {http_err}", exc_info=True)

    except Exception as e:
        cog.logger.error(f"Error viewing profile for {interaction.user.id}: {e}", exc_info=True)
        try:
            await interaction.followup.send(
                "❌ An error occurred while retrieving your profile.",
                ephemeral=True
            )
        except discord.errors.HTTPException as http_err:
             cog.logger.error(f"HTTP error sending profile error followup: {http_err}", exc_info=True)

async def view_stats_impl(cog: 'CharacterCommands', interaction: discord.Interaction, user: Optional[discord.User] = None):
    """Implementation for the /stats command."""
    target_user = user or interaction.user
    target_user_id = str(target_user.id)
    is_self = target_user.id == interaction.user.id

    # Defer early. Make it non-ephemeral if viewing others, ephemeral if viewing self.
    try:
        await interaction.response.defer(ephemeral=is_self)
    except discord.errors.HTTPException as e:
        cog.logger.error(f"Error deferring interaction for stats view: {e}", exc_info=True)
        # Cannot followup if defer failed
        return

    try:
        character = await cog.character_system.get_character(target_user_id)
        if not character:
            message = "❌ You don't have a character yet! Use `/create`." if is_self else f"❌ User {target_user.display_name} does not have a character."
            try:
                await interaction.followup.send(message, ephemeral=True) # Error message always ephemeral
            except discord.errors.HTTPException as http_err:
                 cog.logger.error(f"HTTP error sending followup for no stats character: {http_err}", exc_info=True)
            return

        embed = discord.Embed(
            title=f"📊 {character.name}'s Stats & Record", 
            color=get_rarity_color(character.rarity)
        )
        # Ensure user object has display_avatar attribute
        if hasattr(target_user, 'display_avatar') and target_user.display_avatar:
            embed.set_thumbnail(url=target_user.display_avatar.url)

        # Core Stats
        stats_str = (
            f"❤️ **HP:** {character.hp}/{character.max_hp}\n"
            f"🌀 **Chakra:** {character.chakra}/{character.max_chakra}\n"
            f"🏃 **Stamina:** {character.stamina}/{character.max_stamina}\n"
            f"💪 **Strength:** {character.strength}\n"
            f"💨 **Speed:** {character.speed}\n"
            f"🛡️ **Defense:** {character.defense}\n"
            f"🧠 **Intelligence:** {character.intelligence}\n"
            f"👁️ **Perception:** {character.perception}\n"
            f"💖 **Willpower:** {character.willpower}\n"
            f"✨ **Chakra Control:** {character.chakra_control}"
        )
        embed.add_field(name="Core Stats", value=stats_str, inline=True)

        # Combat Stats
        combat_stats_str = (
            f"🥋 **Taijutsu:** {character.taijutsu}\n"
            f"🥷 **Ninjutsu:** {character.ninjutsu}\n"
            f"👻 **Genjutsu:** {character.genjutsu}"
        )
        embed.add_field(name="Combat Stats", value=combat_stats_str, inline=True)

        # Battle Record
        total_battles = character.wins + character.losses + character.draws
        win_rate = (character.wins / total_battles * 100) if total_battles > 0 else 0
        record_str = (
            f"🏆 **Wins:** {character.wins}\n"
            f"☠️ **Losses:** {character.losses}\n"
            f"⚖️ **Draws:** {character.draws}\n"
            f"📈 **Win Rate:** {win_rate:.1f}%"
        )
        embed.add_field(name="Battle Record", value=record_str, inline=False)

        # Wins vs Rank (Optional, can be long)
        if character.wins_against_rank:
             wins_vs_rank_str = "\n".join([f"- vs {rank}: {count}" for rank, count in sorted(character.wins_against_rank.items())])
             embed.add_field(name="Wins vs Rank", value=wins_vs_rank_str, inline=False)
             
        embed.set_footer(text=f"ID: {character.id}")
        try:
            # Followup respects original defer ephemeral state unless overridden
            await interaction.followup.send(embed=embed) 
        except discord.errors.HTTPException as http_err:
             cog.logger.error(f"HTTP error sending stats embed followup: {http_err}", exc_info=True)

    except Exception as e:
        cog.logger.error(f"Error viewing stats for {target_user_id}: {e}", exc_info=True)
        message = "❌ An error occurred while retrieving your stats." if is_self else "❌ An error occurred retrieving stats for that user."
        try:
            # Error message always ephemeral
            await interaction.followup.send(message, ephemeral=True)
        except discord.errors.HTTPException as http_err:
             cog.logger.error(f"HTTP error sending stats error followup: {http_err}", exc_info=True)

def get_rarity_color(rarity: str) -> int:
    """Get the Discord color code for a given rarity.
    
    Args:
        rarity: The rarity level (e.g., "Common", "Rare", "Epic", "Legendary")
        
    Returns:
        int: Discord color code (hex as integer)
    """
    rarity_colors = {
        "Common": 0x969696,    # Gray
        "Uncommon": 0x2ecc71,  # Green
        "Rare": 0x3498db,      # Blue
        "Epic": 0x9b59b6,      # Purple
        "Legendary": 0xf1c40f, # Gold
        "Mythic": 0xe74c3c     # Red
    }
    return rarity_colors.get(rarity, 0x969696)  # Default to gray if rarity unknown 