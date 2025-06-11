#!/usr/bin/env python
"""
Discord Cog for handling character creation and management.
"""

import os
import json
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, List
from ..bot import HCShinobiBot

logger = logging.getLogger(__name__)

class CharacterCommands(commands.Cog):
    """Cog for handling character creation and management."""
    
    def __init__(self, bot: HCShinobiBot):
        self.bot = bot
        self.character_manager = bot.character_manager
        logger.info("CharacterCommands Cog initialized.")

    @app_commands.command(
        name="create_character",
        description="Create a new character profile."
    )
    @app_commands.describe(
        name="Your character's name",
        role_status="Your character's role (e.g., Genin, Chunin, Jounin)",
        domain_affiliation="Your character's village or domain",
        titles="Optional: Any titles or epithets your character has",
        core_traits="Key personality traits (comma-separated)",
        hp="Base HP value",
        chakra_pool="Base chakra pool value",
        digital_form="Your character's digital form description",
        symbolic_traits="Symbolic traits or markings",
        aura="Your character's aura description",
        personality_traits="Personality traits (comma-separated)"
    )
    async def create_character(
        self,
        interaction: discord.Interaction,
        name: str,
        role_status: str,
        domain_affiliation: str,
        titles: Optional[str] = None,
        core_traits: str = "",
        hp: int = 100,
        chakra_pool: int = 100,
        digital_form: str = "",
        symbolic_traits: str = "",
        aura: str = "",
        personality_traits: str = ""
    ) -> None:
        """Create a new character profile."""
        await interaction.response.defer(ephemeral=True)
        
        # Convert comma-separated strings to lists
        titles_list = [t.strip() for t in titles.split(",")] if titles else []
        core_traits_list = [t.strip() for t in core_traits.split(",")] if core_traits else []
        personality_traits_list = [t.strip() for t in personality_traits.split(",")] if personality_traits else []

        # Create character data structure
        character_data = {
            "header_quote": "",  # Can be added later
            "overview_identity": {
                "name": name,
                "role_status": role_status,
                "domain_affiliation": domain_affiliation,
                "titles_epithets": titles_list,
                "core_traits": core_traits_list,
                "relative_power_standing": "To be determined"
            },
            "base_stats": {
                "hp": hp,
                "chakra_pool": chakra_pool
            },
            "physical_appearance": {
                "digital_form": digital_form,
                "symbolic_traits": symbolic_traits,
                "aura": aura
            },
            "personality_philosophy": {
                "personality_traits": personality_traits_list
            },
            "dreamcraft_capabilities": {
                "techniques": []
            }
        }

        try:
            # Save character data
            character_file = os.path.join(self.character_manager.character_dir, f"{name}.json")
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, indent=4, ensure_ascii=False)

            # Reload characters in the manager
            self.character_manager.reload_characters()

            # Create success embed
            embed = discord.Embed(
                title="✅ Character Created",
                description=f"Successfully created character profile for **{name}**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Basic Info",
                value=f"**Role:** {role_status}\n"
                      f"**Domain:** {domain_affiliation}\n"
                      f"**Titles:** {', '.join(titles_list) if titles_list else 'None'}",
                inline=False
            )
            embed.add_field(
                name="Stats",
                value=f"**HP:** {hp}\n"
                      f"**Chakra:** {chakra_pool}",
                inline=True
            )
            embed.add_field(
                name="Appearance",
                value=f"**Form:** {digital_form}\n"
                      f"**Symbol:** {symbolic_traits}\n"
                      f"**Aura:** {aura}",
                inline=False
            )
            embed.add_field(
                name="Personality",
                value="\n".join(f"• {trait}" for trait in personality_traits_list),
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Character '{name}' created by {interaction.user.name}")

        except Exception as e:
            logger.error(f"Error creating character: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ Failed to create character. Please try again or contact an administrator.",
                ephemeral=True
            )

    @create_character.error
    async def create_character_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors for the create_character command."""
        if isinstance(error, app_commands.CommandInvokeError):
            logger.error(f"Error in create_character command: {error}", exc_info=True)
            await interaction.followup.send(
                "❌ An error occurred while creating your character. Please try again.",
                ephemeral=True
            )
        else:
            logger.error(f"Unexpected error in create_character command: {error}", exc_info=True)
            await interaction.followup.send(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True
            )

async def setup(bot: HCShinobiBot):
    """Adds the CharacterCommands cog to the bot."""
    await bot.add_cog(CharacterCommands(bot))
    logger.info("CharacterCommands Cog loaded and added to bot.") 