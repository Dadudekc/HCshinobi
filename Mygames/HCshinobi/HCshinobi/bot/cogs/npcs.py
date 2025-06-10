#!/usr/bin/env python
"""
Discord Cog for handling NPC-related commands.
Handles NPC management and interaction functions, including converting players to NPCs,
listing NPCs, and autocompleting clan names. Designed for admin use and for enhancing
in-game narrative.

Dependencies are injected via the bot object, including:
    - NPCManager: for NPC management operations.
    - ClanData: for accessing merged clan data (includes basic info and extended details).
    - OpenAIClient: (optional) for AI-generated death stories.
    
If core modules are not available, dummy classes are used as a fallback.
"""

import os
import sys
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, TYPE_CHECKING
import random
import logging

# Import core services via dependency injection; if they fail, use dummy classes.
try:
    from ...core.npc_manager import NPCManager
    from ...core.clan_data import ClanData
except ImportError as e:
    logging.warning(f"Core modules missing for NPC cog: {e}. Using dummy classes.")
    class NPCManager:
        def get_all_npcs(self, status="Active") -> List[dict]:
            return []
        def convert_player_to_npc(self, player_id, player_name, clan_name: str, death_story: Optional[str] = None, **kwargs) -> Optional[dict]:
            return {"name": f"NPC_{player_name}", "clan": clan_name or "Unknown", "status": "Active"}
        def get_clans(self) -> List[dict]:
            return []
    class ClanData:
        def get_all_clans(self) -> List[dict]:
            return []

if TYPE_CHECKING:
    from ..bot import HCShinobiBot
    from ...utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# Maximum allowed length for a death story field
MAX_DEATH_STORY_LENGTH = 1024

# --- Define NPCPromptGenerator locally ---
class NPCPromptGenerator:
    """Generates prompts, specifically death stories using OpenAI."""
    def __init__(self, openai_client: "OpenAIClient"):
        self.openai_client = openai_client

    async def generate_death_story(self, player_name: str, player_clan: str) -> str:
        """Uses the configured OpenAI model to generate a fitting death story."""
        if not self.openai_client:
            logger.warning("Attempted to generate death story without an OpenAI client.")
            return "Fell in battle."
        prompt = (
            f"Narrate the final moments of a shinobi named {player_name} from the {player_clan} clan in the style of Naruto. "
            f"Describe their death briefly and impactfully. Keep it under {MAX_DEATH_STORY_LENGTH // 2} characters. "
            f"Focus on the circumstances (e.g., mission, betrayal, protecting someone, overwhelming odds)."
        )
        try:
            response = await self.openai_client.get_chatgpt_response(prompt)
            if response:
                cleaned_response = response.strip().strip('"\'')
                return cleaned_response[:MAX_DEATH_STORY_LENGTH]
            else:
                logger.warning(f"OpenAI returned an empty response for {player_name}'s death story prompt.")
                return "Fell silently in the shadows."
        except Exception as e:
            logger.error(f"Error generating death story with OpenAI for {player_name}: {e}", exc_info=True)
            return "Met their end under mysterious circumstances."


class NPCCommands(commands.Cog):
    """
    Cog for managing NPCs.
    
    - /mark_death: Mark a player as dead and convert them to an NPC.
    - /npc_list: List active NPCs, with optional clan filtering and autocomplete.
    
    Requires:
        - NPCManager for conversion and listing.
        - ClanData for retrieving merged clan information.
        - Optionally, OpenAIClient for AI-generated death stories.
    """
    def __init__(self, bot: "HCShinobiBot"):
        self.bot = bot
        self.npc_manager: NPCManager = getattr(bot, 'npc_manager', NPCManager())
        self.clan_data: ClanData = getattr(bot, 'clan_data', ClanData())
        self.openai_client: Optional["OpenAIClient"] = getattr(bot, 'openai_client', None)
        self.prompt_generator = NPCPromptGenerator(self.openai_client) if self.openai_client else None

        if not isinstance(self.npc_manager, NPCManager) or not isinstance(self.clan_data, ClanData):
            logger.warning("NPC or Clan services not properly initialized in the bot. NPC cog may have limited functionality.")
        if not self.openai_client:
            logger.warning("OpenAIClient is NOT available. Death story generation will use fallback text.")
        elif not self.prompt_generator:
            logger.warning("OpenAIClient is available, but NPCPromptGenerator failed to initialize.")

    @app_commands.command(
        name="mark_death",
        description="[Admin] Mark a player as dead and convert them to an NPC."
    )
    @app_commands.describe(
        user="The player to mark as dead",
        death_story="Optional description of how the player died (leave blank for AI generation)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def mark_death(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        death_story: Optional[str] = None
    ) -> None:
        """
        Converts a player into an NPC. If no death story is provided, and if OpenAIClient along with
        the prompt generator are available, an AI-generated story is used.
        """
        await interaction.response.defer(ephemeral=True)
        player_id = str(user.id)
        player_name = user.display_name

        logger.info(f"/mark_death invoked by {interaction.user.name} for {player_name} ({player_id})")

        # Fetch the player character to get clan info
        character_system = self.bot.services.get("character_system") if hasattr(self.bot, 'services') else None
        player_character = None
        player_clan = "Unknown"
        if character_system:
            try:
                player_character = await character_system.get_character(player_id)
                if player_character:
                    player_clan = player_character.clan if player_character.clan else "Clanless"
                    logger.info(f"Retrieved clan '{player_clan}' for player {player_name} ({player_id})")
                else:
                    logger.warning(f"Could not find character for player {player_id} during mark_death.")
            except Exception as char_err:
                logger.error(f"Error fetching character for {player_id}: {char_err}", exc_info=True)
        else:
            logger.warning("CharacterSystem not available, cannot fetch player clan for mark_death.")

        generated_story = False
        if not death_story and self.openai_client and self.prompt_generator:
            try:
                # Use the fetched player_clan
                death_story = await self.prompt_generator.generate_death_story(player_name, player_clan)
                generated_story = True
                logger.info(f"AI-generated death story for {player_name}: {death_story[:100]}...")
            except Exception as ai_err:
                logger.error(f"AI generation failed for {player_name}: {ai_err}", exc_info=True)
                death_story = "Fell in battle."
        elif not death_story:
            death_story = "Fell in battle."

        # Use the fetched player_clan for conversion
        player_clan_for_npc = player_clan # Use the value retrieved earlier

        try:
            npc_data = self.npc_manager.convert_player_to_npc(
                player_id=player_id, 
                player_name=player_name, 
                clan_name=player_clan_for_npc,
                death_story=death_story  # Pass the death story
            )
        except Exception as e:
            logger.error(f"Error converting player {player_id} to NPC: {e}", exc_info=True)
            await interaction.followup.send("An error occurred during conversion.", ephemeral=True)
            return

        if npc_data is None:
            await interaction.followup.send(f"Could not convert {user.mention} to an NPC.", ephemeral=True)
            return

        success_embed = discord.Embed(
            title="Player Converted to NPC",
            description=(f"{user.mention} has been marked as deceased and converted to NPC **{npc_data.get('name', 'Unnamed NPC')}**."),
            color=discord.Color.dark_grey()
        )
        success_embed.add_field(name="Former Player", value=user.mention, inline=True)
        success_embed.add_field(name="New NPC Name", value=npc_data.get('name', 'Unknown'), inline=True)
        success_embed.add_field(name="NPC Clan", value=npc_data.get('clan', 'Unknown'), inline=True)
        success_embed.add_field(name="NPC Status", value=npc_data.get('status', 'Unknown'), inline=True)
        if generated_story:
            success_embed.add_field(name="AI Generated Death Story", value=death_story or "N/A", inline=False)
        elif death_story:
            success_embed.add_field(name="Provided Death Story", value=death_story, inline=False)

        await interaction.followup.send(embed=success_embed, ephemeral=True)

        announce_embed = discord.Embed(
            title="A Shinobi Has Fallen",
            description=(f"{user.mention} has fallen and is now NPC **{npc_data.get('name', 'Unnamed NPC')}** "
                         f"({npc_data.get('clan', 'Unknown Clan')})."),
            color=discord.Color.dark_red()
        )
        if death_story:
            announce_embed.add_field(name="Final Moments", value=death_story, inline=False)

        announcement_channel = interaction.channel
        if announcement_channel and isinstance(announcement_channel, discord.TextChannel):
            try:
                await announcement_channel.send(embed=announce_embed)
            except discord.Forbidden:
                logger.warning(f"Insufficient permissions to post in {announcement_channel.name}.")
            except Exception as e:
                logger.error(f"Failed to send announcement: {e}", exc_info=True)

    @mark_death.error
    async def mark_death_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """Handles errors for /mark_death command."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You do not have permission for this command.", ephemeral=True)
        else:
            logger.error(f"Unexpected error in /mark_death: {error}", exc_info=True)
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

    async def clan_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """
        Provides autocomplete choices for clan names using merged clan data.
        """
        if not self.clan_data:
            return []
        try:
            all_clans_data = self.clan_data.get_all_clans()
            all_clans = [clan.get('name', '') for clan in all_clans_data if clan.get('name')]
        except Exception as e:
            logger.error(f"Error retrieving clans for autocomplete: {e}")
            return []

        if not current:
            return [app_commands.Choice(name=name, value=name) for name in all_clans[:25]]
        matches = [name for name in all_clans if current.lower() in name.lower()]
        return [app_commands.Choice(name=name, value=name) for name in matches[:25]]

    @app_commands.command(
        name="npc_list",
        description="List active NPCs in the game world."
    )
    @app_commands.describe(clan="Optional: Filter NPCs by clan name")
    @app_commands.autocomplete(clan=clan_autocomplete)
    async def npc_list(self, interaction: discord.Interaction, clan: Optional[str] = None) -> None:
        """Lists all active NPCs, optionally filtered by clan."""
        await interaction.response.defer()
        logger.info(f"{interaction.user.name} requested /npc_list (clan filter: {clan})")
        try:
            npcs = self.npc_manager.get_all_npcs(status="Active")
            if clan:
                npcs = [npc for npc in npcs if npc.get('clan') and npc['clan'].lower() == clan.lower()]
                title = f"Active NPCs from the {clan} Clan"
            else:
                title = "All Active NPCs"
        except Exception as e:
            logger.error(f"Error fetching NPCs: {e}", exc_info=True)
            await interaction.followup.send("An error occurred while fetching NPC data.", ephemeral=True)
            return

        if not npcs:
            embed_empty = discord.Embed(title=title, description="No active NPCs found.", color=discord.Color.blue())
            await interaction.followup.send(embed=embed_empty)
            return

        embed = discord.Embed(title=title, color=discord.Color.blue())
        description = ""
        MAX_LIST_LEN = 15
        for count, npc in enumerate(npcs):
            if count < MAX_LIST_LEN:
                description += f"- **{npc.get('name', 'Unnamed')}** ({npc.get('clan', 'Unknown Clan')})\n"
            else:
                description += f"\n...and {len(npcs) - MAX_LIST_LEN} more."
                break
        embed.description = description
        embed.set_footer(text=f"Total active NPCs: {len(npcs)}")
        await interaction.followup.send(embed=embed)

async def setup(bot: "HCShinobiBot") -> None:
    """Sets up the NPCCommands cog."""
    try:
        await bot.add_cog(NPCCommands(bot))
        logger.info("NPCCommands Cog loaded successfully.")
    except discord.app_commands.errors.CommandAlreadyRegistered as e:
        logger.warning(f"NPCCommands Cog not loaded because a command is already registered: {e}. Skipping duplicate registration.")
    except Exception as e:
        logger.exception(f"Unexpected error while loading NPCCommands Cog: {e}")
        raise
