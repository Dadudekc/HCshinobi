#!/usr/bin/env python
"""
Discord Cog for handling character profile commands.
Handles viewing and managing character profiles, including stats, appearance, and traits.
"""

import os
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, Any
import logging
from ..bot import HCShinobiBot
from ..core.character_manager import CharacterManager

logger = logging.getLogger(__name__)

class CharacterCreationView(discord.ui.View):
    """View for handling character creation interview responses."""
    
    def __init__(self, bot: HCShinobiBot, user_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.user_id = user_id
        self.character_data = {}
        self.current_question = 0
        self.questions = [
            {
                "question": "What drives your character? What motivates them to become a shinobi?",
                "field": "motivation",
                "type": "text"
            },
            {
                "question": "How does your character handle conflict? Are they aggressive, diplomatic, or strategic?",
                "field": "conflict_style",
                "type": "text"
            },
            {
                "question": "What's your character's greatest strength? Their greatest weakness?",
                "field": "strengths_weaknesses",
                "type": "text"
            },
            {
                "question": "What village does your character belong to? (Leaf, Sand, Mist, Cloud, or Stone)",
                "field": "village",
                "type": "choice",
                "choices": ["Leaf", "Sand", "Mist", "Cloud", "Stone"]
            },
            {
                "question": "What's your character's preferred combat style?",
                "field": "combat_style",
                "type": "choice",
                "choices": ["Taijutsu", "Ninjutsu", "Genjutsu", "Mixed", "Stealth"]
            }
        ]

    async def handle_response(self, interaction: discord.Interaction, response: str):
        """Handle the user's response to the current question."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This interview is not for you!", ephemeral=True)
            return

        current_q = self.questions[self.current_question]
        
        # Validate response if it's a choice question
        if current_q["type"] == "choice" and response not in current_q["choices"]:
            await interaction.response.send_message(
                f"Please choose one of: {', '.join(current_q['choices'])}",
                ephemeral=True
            )
            return

        # Store the response
        self.character_data[current_q["field"]] = response
        self.current_question += 1

        # If we have more questions, ask the next one
        if self.current_question < len(self.questions):
            next_q = self.questions[self.current_question]
            embed = discord.Embed(
                title="Character Creation Interview",
                description=next_q["question"],
                color=discord.Color.blue()
            )
            
            if next_q["type"] == "choice":
                embed.add_field(
                    name="Choices",
                    value="\n".join(f"• {choice}" for choice in next_q["choices"]),
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed)
        else:
            # Interview complete, generate character
            await self.generate_character(interaction)

    async def generate_character(self, interaction: discord.Interaction):
        """Generate the character based on interview responses."""
        # Use the AI service to generate character details
        prompt = f"""
        Create a detailed character profile based on these interview responses:
        - Motivation: {self.character_data.get('motivation', '')}
        - Conflict Style: {self.character_data.get('conflict_style', '')}
        - Strengths/Weaknesses: {self.character_data.get('strengths_weaknesses', '')}
        - Village: {self.character_data.get('village', '')}
        - Combat Style: {self.character_data.get('combat_style', '')}

        Generate a complete character profile including:
        1. Name and basic identity
        2. Detailed personality traits
        3. Physical appearance
        4. Background story
        5. Abilities and techniques
        6. Stats appropriate to their rank and style
        """
        
        try:
            # Get AI-generated character data
            character_data = await self.bot.ai_service.generate_character(prompt)
            
            # Save the character
            name = character_data["overview_identity"]["name"]
            self.bot.character_manager.save_character(name, character_data)
            
            # Create confirmation embed
            embed = discord.Embed(
                title="Character Created Successfully!",
                description=f"Your character **{name}** has been created based on your interview responses.",
                color=discord.Color.green()
            )
            
            # Add key details
            identity = character_data["overview_identity"]
            embed.add_field(
                name="Identity",
                value=f"**Village:** {identity['domain_affiliation']}\n"
                      f"**Role:** {identity['role_status']}\n"
                      f"**Titles:** {', '.join(identity['titles_epithets'])}",
                inline=False
            )
            
            # Add personality traits
            personality = character_data["personality_philosophy"]
            embed.add_field(
                name="Personality",
                value="\n".join(f"• {trait}" for trait in personality["personality_traits"]),
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error generating character: {e}")
            await interaction.response.edit_message(
                content="❌ There was an error generating your character. Please try again.",
                embed=None
            )

class ProfileCommands(commands.Cog):
    """Cog for viewing and managing character profiles."""
    
    def __init__(self, bot: HCShinobiBot):
        self.bot = bot
        self.character_manager = bot.character_manager
        logger.info("ProfileCommands Cog initialized.")

    @app_commands.command(name="create_character", description="Create a new character through an immersive interview process.")
    async def create_character(self, interaction: discord.Interaction) -> None:
        """
        Starts an immersive character creation interview.
        The AI will guide you through questions to create your character.
        """
        await interaction.response.defer(ephemeral=True)
        
        # Create the interview view
        view = CharacterCreationView(self.bot, interaction.user.id)
        
        # Start with the first question
        first_question = view.questions[0]
        embed = discord.Embed(
            title="Character Creation Interview",
            description=first_question["question"],
            color=discord.Color.blue()
        )
        
        if first_question["type"] == "choice":
            embed.add_field(
                name="Choices",
                value="\n".join(f"• {choice}" for choice in first_question["choices"]),
                inline=False
            )
        
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="profile", description="View a character's profile information.")
    @app_commands.describe(
        character="The name of the character to view (e.g., Cap, Chen).",
        user="Optional: The user whose profile to view. If not specified, shows your own profile."
    )
    async def profile(
        self,
        interaction: discord.Interaction,
        character: str,
        user: Optional[discord.User] = None
    ) -> None:
        """
        Displays a character's profile information in an embed message.
        Shows stats, appearance, traits, and other relevant information.
        """
        await interaction.response.defer(ephemeral=True)
        
        # Get character data
        char_data = self.character_manager.get_character(character)
        if not char_data:
            await interaction.followup.send(f"❌ Character '{character}' not found.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed(
            title=f"{char_data['overview_identity']['name']}",
            description=char_data.get('header_quote', ''),
            color=discord.Color.blue()
        )

        # Add identity information
        identity = char_data['overview_identity']
        embed.add_field(
            name="Identity",
            value=f"**Role:** {identity['role_status']}\n"
                  f"**Domain:** {identity['domain_affiliation']}\n"
                  f"**Titles:** {', '.join(identity['titles_epithets'])}",
            inline=False
        )

        # Add core traits
        embed.add_field(
            name="Core Traits",
            value="\n".join(f"• {trait}" for trait in identity['core_traits']),
            inline=False
        )

        # Add base stats
        stats = char_data['base_stats']
        embed.add_field(
            name="Base Stats",
            value=f"**HP:** {stats['hp']}\n"
                  f"**Chakra:** {stats['chakra_pool']}",
            inline=True
        )

        # Add physical appearance
        appearance = char_data['physical_appearance']
        embed.add_field(
            name="Appearance",
            value=f"**Form:** {appearance['digital_form']}\n"
                  f"**Symbol:** {appearance['symbolic_traits']}\n"
                  f"**Aura:** {appearance['aura']}",
            inline=False
        )

        # Add personality traits
        personality = char_data['personality_philosophy']
        embed.add_field(
            name="Personality",
            value="\n".join(f"• {trait}" for trait in personality['personality_traits']),
            inline=False
        )

        # Add techniques if available
        if 'dreamcraft_capabilities' in char_data:
            techniques = char_data['dreamcraft_capabilities']
            embed.add_field(
                name="Techniques",
                value="\n".join(f"• {tech}" for tech in techniques),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: HCShinobiBot):
    """Adds the ProfileCommands cog to the bot."""
    await bot.add_cog(ProfileCommands(bot))
    logger.info("ProfileCommands Cog loaded and added to bot.") 