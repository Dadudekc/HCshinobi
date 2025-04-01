"""Character commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import ui # Import ui for Modals
from typing import Optional, List, Dict, Any, Tuple, Union
import logging
import asyncio
from datetime import datetime, timedelta
import random
from discord import app_commands
import uuid
import traceback

from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_data import ClanData
from ..utils.discord_ui import get_rarity_color
from ..core.constants import RarityTier

# Role configuration
ROLE_CONFIG = {
    # Level roles
    "level_roles": {
        5: "Genin",
        10: "Chunin",
        20: "Jonin",
        30: "ANBU",
        50: "Kage"
    },
    # Clan roles - automatically assigned based on character clan
    "clan_roles": True,
    # Specialization roles
    "specialization_roles": {
        "Taijutsu": "Taijutsu Specialist",
        "Ninjutsu": "Ninjutsu Specialist",
        "Genjutsu": "Genjutsu Specialist"
    }
}

# Personality traits and corresponding clan affinities
PERSONALITY_TRAITS = {
    "Analytical": ["Nara", "Aburame"],
    "Creative": ["Uzumaki", "Yamanaka"],
    "Determined": ["Uchiha", "Sarutobi"],
    "Energetic": ["Inuzuka", "Uzumaki"],
    "Honorable": ["Sarutobi", "Senju"],
    "Intuitive": ["Yamanaka", "Hyuga"],
    "Loyal": ["Inuzuka", "Akimichi"],
    "Kind": ["Akimichi", "Senju"],
    "Strategic": ["Nara", "Uchiha"],
    "Proud": ["Uchiha", "Hyuga"],
    "Protective": ["Senju", "Akimichi"],
    "Resilient": ["Uzumaki", "Sarutobi"],
    "Sociable": ["Yamanaka", "Akimichi"],
    "Disciplined": ["Hyuga", "Aburame"],
    "Wise": ["Sarutobi", "Nara"],
    "Noble": ["Senju", "Hyuga"],
    "Calm": ["Aburame", "Nara"]
}

# Quiz questions to determine personality traits
PERSONALITY_QUIZ = [
    {
        "question": "How do you approach a challenging problem?",
        "options": [
            {"label": "Analyze all possibilities systematically", "traits": ["Analytical", "Strategic"]},
            {"label": "Trust my instincts and intuition", "traits": ["Intuitive", "Creative"]},
            {"label": "Persist until I find a solution", "traits": ["Determined", "Resilient"]},
            {"label": "Seek advice from others", "traits": ["Sociable", "Kind"]}
        ]
    },
    {
        "question": "In a team, what role do you usually take?",
        "options": [
            {"label": "The strategist who plans ahead", "traits": ["Strategic", "Analytical"]},
            {"label": "The protector who looks after others", "traits": ["Protective", "Loyal"]},
            {"label": "The leader who takes charge", "traits": ["Proud", "Noble"]},
            {"label": "The supportive member who helps everyone", "traits": ["Kind", "Sociable"]}
        ]
    },
    {
        "question": "How do you prefer to train and improve?",
        "options": [
            {"label": "Disciplined practice of fundamentals", "traits": ["Disciplined", "Honorable"]},
            {"label": "Creative experimentation with new techniques", "traits": ["Creative", "Intuitive"]},
            {"label": "Pushing my limits through intense effort", "traits": ["Determined", "Energetic"]},
            {"label": "Studying and learning from masters", "traits": ["Wise", "Analytical"]}
        ]
    },
    {
        "question": "What do you value most in yourself and others?",
        "options": [
            {"label": "Loyalty and reliability", "traits": ["Loyal", "Honorable"]},
            {"label": "Intelligence and wisdom", "traits": ["Wise", "Analytical"]},
            {"label": "Strength and determination", "traits": ["Determined", "Proud"]},
            {"label": "Kindness and compassion", "traits": ["Kind", "Protective"]}
        ]
    },
    {
        "question": "How do you react under pressure?",
        "options": [
            {"label": "Stay calm and assess the situation", "traits": ["Calm", "Analytical"]},
            {"label": "Act quickly and decisively", "traits": ["Determined", "Energetic"]},
            {"label": "Adapt and find creative solutions", "traits": ["Creative", "Resilient"]},
            {"label": "Stand firm with discipline and focus", "traits": ["Disciplined", "Noble"]}
        ]
    }
]

# --- Character Creation Modal ---
class CharacterNameModal(ui.Modal, title='Create Your Character'):
    name_input = ui.TextInput(
        label='Character Name',
        placeholder='Enter your desired character name (3-20 characters)',
        min_length=3,
        max_length=20,
        required=True
    )

    def __init__(self, character_commands_cog: 'CharacterCommands'):
        super().__init__()
        self.character_commands_cog = character_commands_cog

    async def on_submit(self, interaction: discord.Interaction):
        name = self.name_input.value.strip()
        await self.character_commands_cog._process_character_creation(interaction, name)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logging.error(f'Error in CharacterNameModal: {error}', exc_info=True)
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)
# --- End Character Creation Modal ---

# --- Personality Quiz View ---
class PersonalityQuizView(ui.View):
    def __init__(self, character_commands_cog: 'CharacterCommands', name: str, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.character_commands_cog = character_commands_cog
        self.name = name
        self.current_question = 0
        self.trait_scores = {}
        self.message = None
        
    async def start_quiz(self, interaction: discord.Interaction):
        embed = self.create_question_embed()
        await interaction.response.send_message(embed=embed, view=self)
        self.message = await interaction.original_response()
    
    def create_question_embed(self) -> discord.Embed:
        """Create embed for the current question"""
        question_data = PERSONALITY_QUIZ[self.current_question]
        embed = discord.Embed(
            title="Personality Quiz",
            description=f"Question {self.current_question + 1}/{len(PERSONALITY_QUIZ)}: {question_data['question']}",
            color=discord.Color.blue()
        )
        
        # Add options as fields
        for i, option in enumerate(question_data['options']):
            embed.add_field(
                name=f"Option {i+1}",
                value=option['label'],
                inline=False
            )
        
        embed.set_footer(text="This quiz will help determine which clan suits your personality.")
        return embed
    
    async def update_quiz(self, interaction: discord.Interaction, selected_option_index: int):
        """Update quiz after an option is selected"""
        # Record trait scores
        traits = PERSONALITY_QUIZ[self.current_question]['options'][selected_option_index]['traits']
        for trait in traits:
            self.trait_scores[trait] = self.trait_scores.get(trait, 0) + 1
        
        # Move to next question or finish
        self.current_question += 1
        if self.current_question < len(PERSONALITY_QUIZ):
            embed = self.create_question_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Quiz finished, create character with recommended clan
            await self.finish_quiz(interaction)
    
    async def finish_quiz(self, interaction: discord.Interaction):
        """Process quiz results and create character"""
        # Get top traits and matching clans
        top_traits, recommended_clan = self.get_clan_recommendation()
        
        # Create embed to show results
        embed = discord.Embed(
            title="Personality Quiz Results",
            description=f"Based on your answers, your dominant traits are: **{', '.join(top_traits)}**",
            color=discord.Color.gold()
        )
        
        # Get clan data for more details
        clan_data = self.character_commands_cog.clan_data.get_clan(recommended_clan)
        rarity = RarityTier(clan_data.get('rarity', RarityTier.COMMON.value))
        rarity_color = get_rarity_color(rarity.value)
        
        embed.add_field(
            name="Recommended Clan",
            value=f"**{recommended_clan}** ({rarity.value})",
            inline=False
        )
        
        if clan_data and 'lore' in clan_data:
            embed.add_field(
                name="Clan Lore",
                value=clan_data['lore'],
                inline=False
            )
        
        # Add confirmation buttons
        confirm_view = ClanConfirmationView(self.character_commands_cog, self.name, recommended_clan)
        await interaction.response.edit_message(embed=embed, view=confirm_view)
    
    def get_clan_recommendation(self) -> Tuple[List[str], str]:
        """Determine top traits and recommended clan based on quiz answers"""
        # Get top traits
        sorted_traits = sorted(self.trait_scores.items(), key=lambda x: x[1], reverse=True)
        top_traits = [trait for trait, score in sorted_traits[:3]]
        
        # Collect clans associated with top traits
        clan_scores = {}
        for trait in top_traits:
            if trait in PERSONALITY_TRAITS:
                for clan in PERSONALITY_TRAITS[trait]:
                    clan_scores[clan] = clan_scores.get(clan, 0) + 1
        
        # Determine clan rarities
        clan_rarities = {}
        for clan in clan_scores:
            clan_data = self.character_commands_cog.clan_data.get_clan(clan)
            if clan_data:
                rarity = clan_data.get('rarity', RarityTier.COMMON.value)
                clan_rarities[clan] = rarity
        
        # Weight clan selection based on rarity and personality match
        # Give higher scores to better personality matches, but respect rarity
        available_clans = []
        for clan, score in clan_scores.items():
            rarity = clan_rarities.get(clan, RarityTier.COMMON.value)
            rarity_factor = {
                RarityTier.COMMON.value: 1.0,
                RarityTier.UNCOMMON.value: 0.7,
                RarityTier.RARE.value: 0.4,
                RarityTier.EPIC.value: 0.2,
                RarityTier.LEGENDARY.value: 0.1
            }.get(rarity, 1.0)
            
            # Add clan with its weighted score
            weighted_score = score * rarity_factor
            available_clans.append((clan, weighted_score))
        
        # Select clan based on weighted random selection
        if available_clans:
            total_weight = sum(weight for _, weight in available_clans)
            rand_val = random.uniform(0, total_weight)
            
            cumulative_weight = 0
            for clan, weight in available_clans:
                cumulative_weight += weight
                if cumulative_weight >= rand_val:
                    return top_traits, clan
        
        # Fallback: if no clan matches or selection fails, return a random common clan
        common_clans = self.character_commands_cog.clan_data.get_clans_by_rarity(RarityTier.COMMON)
        if common_clans:
            return top_traits, random.choice(common_clans)['name']
        else:
            return top_traits, "Civilian"  # Ultimate fallback
    
    @ui.button(label="Option 1", style=discord.ButtonStyle.primary)
    async def option_1(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 0)
    
    @ui.button(label="Option 2", style=discord.ButtonStyle.primary)
    async def option_2(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 1)
    
    @ui.button(label="Option 3", style=discord.ButtonStyle.primary)
    async def option_3(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 2)
    
    @ui.button(label="Option 4", style=discord.ButtonStyle.primary)
    async def option_4(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 3)
    
    async def on_timeout(self):
        """Handle timeout"""
        if self.message:
            await self.message.edit(content="The personality quiz has timed out. Please try again.", view=None)

# --- Clan Confirmation View ---
class ClanConfirmationView(ui.View):
    def __init__(self, character_commands_cog: 'CharacterCommands', name: str, recommended_clan: str):
        super().__init__(timeout=180)
        self.character_commands_cog = character_commands_cog
        self.name = name
        self.recommended_clan = recommended_clan
    
    @ui.button(label="Accept this Clan", style=discord.ButtonStyle.success)
    async def accept_clan(self, interaction: discord.Interaction, button: ui.Button):
        await self.character_commands_cog._create_character_logic(interaction, self.name, clan=self.recommended_clan)
        self.stop()
    
    @ui.button(label="Choose Another Clan", style=discord.ButtonStyle.secondary)
    async def choose_another(self, interaction: discord.Interaction, button: ui.Button):
        # Show clan selection view
        clan_view = ClanSelectionView(self.character_commands_cog, self.name)
        await clan_view.start(interaction)
        self.stop()
    
    @ui.button(label="Skip & Create Character", style=discord.ButtonStyle.primary)
    async def skip_clan(self, interaction: discord.Interaction, button: ui.Button):
        # Create character with default Civilian clan
        await self.character_commands_cog._create_character_logic(interaction, self.name)
        self.stop()
    
    async def on_timeout(self):
        # Default to accepting the recommended clan on timeout
        for child in self.children:
            child.disabled = True

# --- Clan Selection View ---
class ClanSelectionView(ui.View):
    def __init__(self, character_commands_cog: 'CharacterCommands', name: str):
        super().__init__(timeout=180)
        self.character_commands_cog = character_commands_cog
        self.name = name
        self.current_page = 0
        self.clans_per_page = 5
        self.message = None
        self.clan_data = character_commands_cog.clan_data
        
    async def start(self, interaction: discord.Interaction):
        """Start the clan selection process"""
        embed = self.create_clan_selection_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        self.message = await interaction.original_response()
    
    def create_clan_selection_embed(self) -> discord.Embed:
        """Create embed for clan selection"""
        # Group clans by rarity
        clans_by_rarity = {}
        for rarity in [RarityTier.COMMON, RarityTier.UNCOMMON, RarityTier.RARE, RarityTier.EPIC, RarityTier.LEGENDARY]:
            clans_by_rarity[rarity.value] = self.clan_data.get_clans_by_rarity(rarity)
        
        # Create embed
        embed = discord.Embed(
            title="Select Your Clan",
            description="Choose a clan for your character. Rarer clans have better bonuses but are harder to get.",
            color=discord.Color.blue()
        )
        
        # Add each rarity section
        for rarity in [RarityTier.COMMON, RarityTier.UNCOMMON, RarityTier.RARE, RarityTier.EPIC, RarityTier.LEGENDARY]:
            clans = clans_by_rarity[rarity.value]
            if clans:
                clan_list = "\n".join([f"• **{clan['name']}**: {clan.get('lore', 'No lore available')[:50]}..." for clan in clans])
                embed.add_field(
                    name=f"{rarity.value} Clans",
                    value=clan_list or "None available",
                    inline=False
                )
        
        embed.set_footer(text="Use the buttons below to select a clan. Common clans are easier to join.")
        return embed
    
    @ui.select(
        placeholder="Select a clan",
        min_values=1,
        max_values=1,
        options=[] # Will be populated in setup method
    )
    async def clan_select(self, interaction: discord.Interaction, select: ui.Select):
        clan_name = select.values[0]
        await self.character_commands_cog._create_character_logic(interaction, self.name, clan=clan_name)
        self.stop()
    
    def setup_select_options(self):
        """Setup the select menu options with available clans"""
        # Clear existing options
        self.clan_select.options = []
        
        # Get all clans
        all_clans = self.clan_data.get_all_clans()
        
        # Add each clan as an option
        for clan in all_clans:
            clan_name = clan['name']
            rarity = clan.get('rarity', RarityTier.COMMON.value)
            
            # Create option
            self.clan_select.options.append(
                discord.SelectOption(
                    label=clan_name,
                    description=f"{rarity} Clan - {clan.get('lore', 'No description')[:50]}...",
                    value=clan_name
                )
            )
    
    @ui.button(label="Back to Quiz Results", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        # Return to the quiz results and recommended clan
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout"""
        if self.message:
            await self.message.edit(content="Clan selection timed out. Please try again with the /create command.", view=None)

class CharacterCommands(commands.Cog):
    def __init__(self, bot, character_system: CharacterSystem, clan_data: ClanData):
        """Initialize the CharacterCommands class.
        
        Args:
            bot: The bot instance.
            character_system: The character system instance.
            clan_data: The clan data instance.
        """
        self.bot = bot
        self.character_system = character_system
        self.clan_data = clan_data
        self.logger = logging.getLogger(__name__)  # Initialize logger
        self.command_cooldowns = {}
        
        # Cache for role IDs to avoid fetching them repeatedly
        self.role_cache: Dict[str, int] = {}
        
        # Register slash commands
        self.register_commands(bot.tree)

    def register_commands(self, tree: app_commands.CommandTree) -> None:
        """Register character-related commands to the app command tree.
        
        Args:
            tree: The application command tree to register commands to.
        """
        self.logger.info(f"Registering character commands: create, profile, delete")
        
        # Check if commands already exist to avoid re-registration
        existing_commands = [cmd.name for cmd in tree.get_commands()]
        
        if "create" not in existing_commands:
            @tree.command(name="create", description="Create your Shinobi character")
            async def create_character(interaction: discord.Interaction):
                """Create a new character."""
                await interaction.response.send_modal(CharacterNameModal(self))
        
        if "profile" not in existing_commands:
            @tree.command(name="profile", description="View your or another user's character profile")
            @app_commands.describe(user="The user whose profile to view. If not provided, views your own profile.")
            async def profile(interaction: discord.Interaction, user: Optional[discord.User] = None):
                """View a character profile."""
                # If no user is specified, use the command invoker
                target_user = user or interaction.user
                
                # Check if the user has a character
                character = self.character_system.get_character(str(target_user.id))
                if not character:
                    if target_user.id == interaction.user.id:
                        await interaction.response.send_message("You don't have a character yet! Use `/create` to make one.")
                    else:
                        await interaction.response.send_message(f"{target_user.display_name} doesn't have a character yet!")
                    return
                
                # Create and send the embed
                embed = self._create_character_embed(character, target_user)
                await interaction.response.send_message(embed=embed)
        
        if "delete" not in existing_commands:
            @tree.command(name="delete", description="Delete your character (cannot be undone)")
            async def delete_character(interaction: discord.Interaction):
                """Delete your character."""
                await self.delete_character_slash(interaction)
                
        # Register any other character-related commands as needed

    def _create_character_embed(self, character, user) -> discord.Embed:
        """Create a Discord embed to display character information.
        
        Args:
            character: The character object
            user: The Discord user object
            
        Returns:
            A Discord embed containing the character information
        """
        # Get clan info for color
        clan_info = self.clan_data.get_clan(character.clan)
        clan_rarity_str = "Unknown"
        rarity_color = discord.Color.default()
        if clan_info:
            clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
            rarity_color = get_rarity_color(clan_rarity_str)
        
        # Create embed
        embed = discord.Embed(
            title=f"{character.name}'s Profile",
            description=f"Clan: {character.clan} ({clan_rarity_str})",
            color=rarity_color
        )
        
        # Add character info
        embed.add_field(name="Clan", value=character.clan if hasattr(character, 'clan') and character.clan else "None", inline=True)
        embed.add_field(name="Rank", value=character.rank if hasattr(character, 'rank') else "Academy Student", inline=True)
        embed.add_field(name="Specialization", value=character.specialization if hasattr(character, 'specialization') else "None", inline=True)
        
        # Add stats - handle both dictionary stats or individual attributes
        stats_text = ""
        if hasattr(character, 'stats') and isinstance(character.stats, dict):
            # If stats is a dictionary attribute
            for stat_name, stat_value in character.stats.items():
                stats_text += f"{stat_name.replace('_', ' ').title()}: **{stat_value}**\n"
        else:
            # Try to access individual stat attributes
            stat_attributes = [
                'ninjutsu', 'taijutsu', 'genjutsu', 'intelligence', 
                'strength', 'speed', 'stamina', 'chakra_control', 
                'perception', 'willpower'
            ]
            for stat_name in stat_attributes:
                if hasattr(character, stat_name):
                    stat_value = getattr(character, stat_name)
                    stats_text += f"{stat_name.replace('_', ' ').title()}: **{stat_value}**\n"
        
        embed.add_field(name="Stats", value=stats_text or "No stats available", inline=False)
        
        # Add inventory summary
        inventory_count = len(character.inventory) if hasattr(character, 'inventory') else 0
        embed.add_field(name="Inventory", value=f"{inventory_count} items", inline=True)
        
        # Add jutsu summary
        jutsu_count = len(character.jutsu) if hasattr(character, 'jutsu') else 0
        embed.add_field(name="Jutsu", value=f"Known: {jutsu_count}", inline=True)
        
        # Add experience
        embed.add_field(
            name="Experience",
            value=f"{character.exp}/{character.level * 100} XP",
            inline=True
        )
        
        # Set footer with character ID
        embed.set_footer(text=f"Character ID: {user.id}")
        
        # Set user avatar if available
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
            
        return embed

    async def _process_character_creation(self, interaction: discord.Interaction, name: str):
        """Process character creation after name is provided, with option for personality quiz."""
        # Validate name
        if len(name) < 3 or len(name) > 20:
            await interaction.response.send_message(
                "❌ Character name must be between 3 and 20 characters.",
                ephemeral=True
            )
            return
            
        # Create embed for quiz option
        embed = discord.Embed(
            title="Choose Your Path",
            description=f"**{name}**, you're about to begin your journey as a shinobi.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Personality Quiz",
            value="Take a short quiz to find the clan that best matches your personality.",
            inline=False
        )
        
        embed.add_field(
            name="Quick Start",
            value="Skip the quiz and start as a Civilian. You can join a clan later.",
            inline=False
        )
        
        # Create view with buttons
        class QuizOptionView(ui.View):
            def __init__(self, cog, char_name):
                super().__init__(timeout=180)
                self.cog = cog
                self.char_name = char_name
                
            @ui.button(label="Take Personality Quiz", style=discord.ButtonStyle.primary)
            async def take_quiz(self, interaction: discord.Interaction, button: ui.Button):
                quiz_view = PersonalityQuizView(self.cog, self.char_name)
                await quiz_view.start_quiz(interaction)
                self.stop()
                
            @ui.button(label="Skip & Create Character", style=discord.ButtonStyle.secondary)
            async def skip_quiz(self, interaction: discord.Interaction, button: ui.Button):
                await self.cog._create_character_logic(interaction, self.char_name)
                self.stop()
        
        # Send options to user
        await interaction.response.send_message(embed=embed, view=QuizOptionView(self, name))

    async def _create_character_logic(self, interaction: discord.Interaction, name: str, clan: str = "Civilian", from_modal: bool = False):
        """Core logic for creating a character, used by both direct name input and the Modal."""
        try:
            user_id = str(interaction.user.id)
            name = name.strip() # Ensure name is stripped

            # --- Character Creation ---
            character = Character(
                name=name,
                clan=clan,  # Use provided clan or default to Civilian
                level=1,
                exp=0,
                ninjutsu=10,
                taijutsu=10,
                genjutsu=10,
                intelligence=10,
                strength=10,
                speed=10,
                stamina=10,
                chakra_control=10,
                perception=10,
                willpower=10
            )
            self.character_system.characters[user_id] = character
            self.character_system.save_character(character)
            self.logger.info(f"Character '{name}' created for user {user_id} with clan {clan}")

            # --- Response Embed ---
            embed = discord.Embed(
                title="✅ Character Created!",
                description=f"Welcome, **{name}** of the **{clan}** clan! Your journey as a shinobi begins now.",
                color=discord.Color.green()
            )
            
            # Add clan info if available
            clan_info = self.clan_data.get_clan(clan)
            if clan_info:
                # Get clan bonuses
                bonuses = self.clan_data.get_clan_bonuses(clan)
                bonus_text = ", ".join([f"+{v} {k.title()}" for k, v in bonuses.items() if v > 0])
                
                # Get clan jutsu
                jutsu = self.clan_data.get_clan_jutsu(clan)
                jutsu_text = ", ".join(jutsu) if jutsu else "None"
                
                embed.add_field(
                    name="Clan Bonuses", 
                    value=bonus_text or "None",
                    inline=True
                )
                
                embed.add_field(
                    name="Starting Jutsu",
                    value=jutsu_text,
                    inline=True
                )
            
            embed.add_field(name="Next Steps", value=(
                "• Use `/profile` to view your stats\n"
                "• Use `/train` to improve your abilities\n"
                "• Use `/help` to see all available commands"
            ), inline=False)

            # --- Send Response ---
            # If the interaction was from a modal, we need to use followup.send
            # otherwise, we use the initial response.send_message
            response_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
            await response_method(embed=embed)

            # --- Update Roles ---
            if interaction.guild:
                try:
                    await self._update_roles_from_interaction(interaction, character)
                except Exception as e:
                    self.logger.error(f"Error updating roles after creation for {user_id}: {e}")

        except discord.errors.NotFound as e:
            self.logger.warning(f"Interaction not found during character creation for {interaction.user.id}: {e}")
        except discord.errors.InteractionResponded as e:
            self.logger.warning(f"Interaction already responded during character creation for {interaction.user.id}: {e}")
            # Try sending a followup if possible
            try:
                 await interaction.followup.send("Character creation process experienced an issue (already responded).", ephemeral=True)
            except:
                 pass # Ignore if followup fails
        except Exception as e:
            self.logger.error(f"Error in _create_character_logic for {interaction.user.id}: {e}", exc_info=True)
            # Try to respond with an error message
            try:
                response_method = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
                await response_method(
                    "❌ An unexpected error occurred during character creation. Please try again later.",
                    ephemeral=True
                )
            except: # Ignore errors during error reporting
                pass

    async def _update_roles_from_interaction(self, interaction: discord.Interaction, character: Character) -> None:
        """Update roles for a user based on interaction rather than ctx.

        Args:
            interaction: The Discord interaction
            character: The character object
        """
        # Ensure we have guild and member objects. For interactions, user is the member.
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        guild = interaction.guild

        if not guild or not member:
             self.logger.warning(f"Could not update roles for user {interaction.user.id}: Missing guild or member object.")
             return

        try:
            # Handle level roles
            await self._handle_level_roles(guild, member, character)

            # Handle clan roles
            if ROLE_CONFIG["clan_roles"]:
                await self._handle_clan_roles(guild, member, character)

            # Handle specialization roles
            if hasattr(character, 'specialization') and character.specialization:
                await self._handle_specialization_roles(guild, member, character)

            self.logger.info(f"Updated roles for {member.display_name} (ID: {member.id}) in guild {guild.name}")
        except discord.errors.Forbidden:
             self.logger.error(f"Permission error updating roles for {member.display_name} in guild {guild.name}. Check bot permissions.")
        except Exception as e:
            self.logger.error(f"Error updating roles for {member.display_name}: {e}", exc_info=True)

    async def profile_slash(self, interaction: discord.Interaction):
        """View your character profile with a slash command.
        
        Args:
            interaction: The interaction object
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check cooldown
            current_time = datetime.now()
            cooldown_until = self.command_cooldowns.get(f"{user_id}_profile")
            if cooldown_until and current_time < cooldown_until:
                time_left = (cooldown_until - current_time).total_seconds()
                await interaction.response.send_message(
                    f"⏰ This command is on cooldown. Try again in {time_left:.1f}s",
                    ephemeral=True
                )
                return
                
            # Set cooldown (10 seconds)
            self.command_cooldowns[f"{user_id}_profile"] = current_time + timedelta(seconds=10)
            
            # Get character
            character = self.character_system.get_character(user_id)
            if not character:
                await interaction.response.send_message(
                    "❌ You don't have a character yet! Use `/create` to get started.",
                    ephemeral=True
                )
                return
                
            # Get clan info
            clan_info = self.clan_data.get_clan(character.clan)
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            # Create embed
            embed = discord.Embed(
                title=f"{character.name}'s Profile",
                description=f"Clan: {character.clan} ({clan_rarity_str})",
                color=rarity_color
            )
            
            # Add character info
            embed.add_field(name="Clan", value=character.clan if hasattr(character, 'clan') and character.clan else "None", inline=True)
            embed.add_field(name="Rank", value=character.rank if hasattr(character, 'rank') else "Academy Student", inline=True)
            embed.add_field(name="Specialization", value=character.specialization if hasattr(character, 'specialization') else "None", inline=True)
            
            # Add stats
            stats_text = ""
            for stat_name, stat_value in character.stats.items():
                stats_text += f"{stat_name.replace('_', ' ').title()}: **{stat_value}**\n"
            embed.add_field(name="Stats", value=stats_text, inline=False)
            
            # Add inventory summary
            inventory_count = len(character.inventory) if hasattr(character, 'inventory') else 0
            embed.add_field(name="Inventory", value=f"{inventory_count} items", inline=True)
            
            # Add jutsu summary
            jutsu_count = len(character.jutsu) if hasattr(character, 'jutsu') else 0
            embed.add_field(name="Jutsu", value=f"Known: {jutsu_count}", inline=True)
            
            # Add experience
            embed.add_field(
                name="Experience",
                value=f"{character.exp}/{character.level * 100} XP",
                inline=True
            )
            
            # Set footer
            embed.set_footer(text=f"Character ID: {user_id}")
            
            await interaction.response.send_message(embed=embed)
        except discord.errors.NotFound:
            self.logger.warning(f"Interaction not found for profile_slash command")
        except discord.errors.InteractionResponded:
            self.logger.warning(f"Interaction already responded for profile_slash command")
        except Exception as e:
            self.logger.error(f"Error in profile_slash: {e}", exc_info=True)
            # Try to respond if we haven't already
            try:
                await interaction.response.send_message(
                    "❌ An error occurred while processing your command. Please try again later.",
                    ephemeral=True
                )
            except:
                pass
            
    async def assign_clan_slash(self, interaction: discord.Interaction, clan: str = None):
        """Assign a clan to your character with a slash command.
        
        Args:
            interaction: The interaction object
            clan: Optional clan name to assign
        """
        try:
            user_id = str(interaction.user.id)
            
            # Check cooldown
            current_time = datetime.now()
            cooldown_until = self.command_cooldowns.get(f"{user_id}_assign_clan")
            if cooldown_until and current_time < cooldown_until:
                time_left = (cooldown_until - current_time).total_seconds()
                await interaction.response.send_message(
                    f"⏰ This command is on cooldown. Try again in {time_left:.1f}s",
                    ephemeral=True
                )
                return
                
            # Set cooldown (5 minutes)
            self.command_cooldowns[f"{user_id}_assign_clan"] = current_time + timedelta(minutes=5)
            
            # Get character
            character = self.character_system.get_character(user_id)
            if not character:
                await interaction.response.send_message(
                    "❌ You don't have a character yet! Use `/create` to get started.",
                    ephemeral=True
                )
                return
                
            # If the character already has a clan, show error
            if hasattr(character, 'clan') and character.clan:
                await interaction.response.send_message(
                    f"❌ You are already a member of the {character.clan} clan!",
                    ephemeral=True
                )
                return
                
            # Get all available clans
            available_clans = self.clan_data.get_all_clans()
            
            # If no clan specified, show available clans
            if not clan:
                clan_info = []
                for clan_name, data in available_clans.items():
                    rarity = data.get('rarity', 'common').capitalize()
                    special_ability = data.get('special_ability', 'None')
                    clan_info.append(f"• **{clan_name}** ({rarity}) - {special_ability}")
                
                clan_list = "\n".join(clan_info)
                
                embed = discord.Embed(
                    title="Available Clans",
                    description=f"Choose a clan using `/assign_clan [clan_name]`:\n\n{clan_list}",
                    color=discord.Color.blue()
                )
                
                await interaction.response.send_message(embed=embed)
                return
                
            # Check if clan exists
            if clan.lower() not in [c.lower() for c in available_clans.keys()]:
                await interaction.response.send_message(
                    f"❌ Clan '{clan}' not found! Use `/assign_clan` to see available clans.",
                    ephemeral=True
                )
                return
                
            # Find the exact clan name (case-sensitive)
            clan_name = next((c for c in available_clans.keys() if c.lower() == clan.lower()), None)
            
            # Assign clan
            character.clan = clan_name
            self.character_system.save_character(character)
            
            # Get clan data
            clan_data = available_clans.get(clan_name, {})
            clan_rarity = clan_data.get('rarity', 'common')
            clan_ability = clan_data.get('special_ability', 'None')
            
            # Create response embed
            embed = discord.Embed(
                title=f"Welcome to the {clan_name} Clan!",
                description=f"You are now a member of the {clan_name} clan.",
                color=get_rarity_color(clan_rarity)
            )
            
            embed.add_field(
                name="Clan Ability",
                value=clan_ability,
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Update roles directly from interaction
            if interaction.guild:
                try:
                    await self._update_roles_from_interaction(interaction, character)
                except Exception as e:
                    self.logger.error(f"Error updating roles: {e}")
        except discord.errors.NotFound:
            self.logger.warning(f"Interaction not found for assign_clan_slash command")
        except discord.errors.InteractionResponded:
            self.logger.warning(f"Interaction already responded for assign_clan_slash command")
        except Exception as e:
            self.logger.error(f"Error in assign_clan_slash: {e}", exc_info=True)
            # Try to respond if we haven't already
            try:
                await interaction.response.send_message(
                    "❌ An error occurred while processing your command. Please try again later.",
                    ephemeral=True
                )
            except:
                pass
        
    async def cog_command_error(self, ctx, error):
        """Handle errors for all commands in this cog."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have permission to do that!")
        else:
            self.logger.error(f"Error in {ctx.command.name}: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            
    async def update_roles(self, ctx, character: Character) -> None:
        """Update roles for a user based on their character progression.
        
        Args:
            ctx: The command context
            character: The character object
        """
        member = ctx.author
        guild = ctx.guild
        
        if not guild or not member:
            return
        
        try:
            # Handle level roles
            await self._handle_level_roles(guild, member, character)
            
            # Handle clan roles
            if ROLE_CONFIG["clan_roles"]:
                await self._handle_clan_roles(guild, member, character)
                
            # Handle specialization roles
            if hasattr(character, 'specialization'):
                await self._handle_specialization_roles(guild, member, character)
                
            self.logger.info(f"Updated roles for {member.display_name} (ID: {member.id})")
        except Exception as e:
            self.logger.error(f"Error updating roles for {member.display_name}: {e}", exc_info=True)
    
    async def _handle_level_roles(self, guild, member, character: Character) -> None:
        """Handle level-based role assignments.
        
        Args:
            guild: The Discord guild
            member: The Discord member
            character: The character object
        """
        # Get all level roles
        level_roles = {}
        for level, role_name in ROLE_CONFIG["level_roles"].items():
            role = await self._get_or_create_role(guild, role_name)
            if role:
                level_roles[level] = role
        
        # Sort levels in descending order
        sorted_levels = sorted(level_roles.keys(), reverse=True)
        
        # Find the highest level role the character qualifies for
        qualified_role = None
        for level in sorted_levels:
            if character.level >= level:
                qualified_role = level_roles[level]
                break
        
        if not qualified_role:
            return
            
        # Remove all level roles
        for role in level_roles.values():
            if role in member.roles and role != qualified_role:
                await member.remove_roles(role, reason="Character level role update")
                
        # Add the qualified role if not already assigned
        if qualified_role not in member.roles:
            await member.add_roles(qualified_role, reason="Character level role update")
            await self._send_role_update_message(member, "Congratulations! You've earned a new rank:", qualified_role.name)
    
    async def _handle_clan_roles(self, guild, member, character: Character) -> None:
        """Handle clan-based role assignments.
        
        Args:
            guild: The Discord guild
            member: The Discord member
            character: The character object
        """
        # Get all clan names
        clan_names = list(self.clan_data.get_all_clans().keys())
        
        # Create a list to store clan roles
        clan_roles = []
        
        # Get or create the role for each clan
        for clan_name in clan_names:
            role = await self._get_or_create_role(guild, clan_name)
            if role:
                clan_roles.append(role)
        
        # Get the role corresponding to the character's clan
        character_clan_role = next((r for r in clan_roles if r.name == character.clan), None)
        
        # Remove all clan roles except the character's clan
        for role in clan_roles:
            if role in member.roles and role != character_clan_role:
                await member.remove_roles(role, reason="Character clan role update")
        
        # Add the character's clan role if not already assigned
        if character_clan_role and character_clan_role not in member.roles:
            await member.add_roles(character_clan_role, reason="Character clan role update")
            await self._send_role_update_message(member, "You've been assigned to clan:", character_clan_role.name)
    
    async def _handle_specialization_roles(self, guild, member, character: Character) -> None:
        """Handle specialization-based role assignments.
        
        Args:
            guild: The Discord guild
            member: The Discord member
            character: The character object
        """
        specialization_roles = {}
        for spec, role_name in ROLE_CONFIG["specialization_roles"].items():
            role = await self._get_or_create_role(guild, role_name)
            if role:
                specialization_roles[spec] = role
        
        # Get the character's specialization
        character_spec = getattr(character, 'specialization', None)
        character_spec_role = specialization_roles.get(character_spec, None)
        
        # Remove all specialization roles except the character's specialization
        for role in specialization_roles.values():
            if role in member.roles and role != character_spec_role:
                await member.remove_roles(role, reason="Character specialization role update")
        
        # Add the character's specialization role if not already assigned
        if character_spec_role and character_spec_role not in member.roles:
            await member.add_roles(character_spec_role, reason="Character specialization role update")
            await self._send_role_update_message(member, "You've specialized in:", character_spec_role.name)
            
    async def _get_or_create_role(self, guild, role_name: str) -> Optional[discord.Role]:
        """Get or create a role in the guild.
        
        Args:
            guild: The Discord guild
            role_name: The name of the role
            
        Returns:
            The role object or None if failed
        """
        # Check if the role is already cached
        cache_key = f"{guild.id}:{role_name}"
        if cache_key in self.role_cache:
            role = guild.get_role(self.role_cache[cache_key])
            if role:
                return role
        
        # Try to get the role
        role = discord.utils.get(guild.roles, name=role_name)
        
        # Create the role if it doesn't exist
        if not role:
            try:
                self.logger.info(f"Creating role '{role_name}' in guild {guild.name}")
                role = await guild.create_role(
                    name=role_name,
                    reason="Automatic role creation for character progression"
                )
            except Exception as e:
                self.logger.error(f"Failed to create role '{role_name}': {e}", exc_info=True)
                return None
        
        # Cache the role ID
        if role:
            self.role_cache[cache_key] = role.id
            
        return role
        
    async def _send_role_update_message(self, member, prefix: str, role_name: str) -> None:
        """Send a direct message to a member about a role update.
        
        Args:
            member: The Discord member
            prefix: The message prefix
            role_name: The name of the role
        """
        try:
            embed = discord.Embed(
                title="🎭 Role Update",
                description=f"{prefix} **{role_name}**",
                color=discord.Color.green()
            )
            await member.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Failed to send role update message to {member.display_name}: {e}")

    @commands.command(
        name="create",
        aliases=["new", "make"],
        description="Create a new character (Interactive)",
        help="Start an interactive character creation process. You'll be asked to name your character."
    )
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5 minutes cooldown
    async def create(self, ctx):
        """Create a new character.
        
        Args:
            ctx: The command context
        """
        try:
            player_id = str(ctx.author.id)
            
            # Check if user already has a character
            existing_character = self.character_system.get_character(player_id)
            if existing_character:
                await ctx.send(f"❌ You already have a character named **{existing_character.name}**! Use `/delete` if you want to start over.")
                return
            
            # Send prompt for character name
            await ctx.send("Let's create your character! What would you like to name your character? (3-20 characters)")
            
            # Wait for user response
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
                
            try:
                # Wait for name input
                name_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                name = name_msg.content.strip()
                
                # Validate name
                if len(name) < 3 or len(name) > 20:
                    await ctx.send("❌ Character name must be between 3 and 20 characters. Please try again.")
                    return
                
                # Create character
                character = Character(
                    name=name,
                    clan="Civilian",  # Default clan, will be changed with assign_clan
                    level=1,
                    exp=0,
                    ninjutsu=10,
                    taijutsu=10,
                    genjutsu=10,
                    intelligence=10,
                    strength=10,
                    speed=10,
                    stamina=10,
                    chakra_control=10,
                    perception=10,
                    willpower=10
                )
                # Store the character
                self.character_system.characters[player_id] = character
                self.character_system.save_character(character)
                
                # Create response embed
                embed = discord.Embed(
                    title="✅ Character Created!",
                    description=f"Welcome, **{name}**! Your journey as a shinobi begins now.",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Next Steps",
                    value=(
                        "• Use `/assign_clan` to join a clan\n"
                        "• Use `/profile` to view your stats\n"
                        "• Use `/help` to see all available commands"
                    ),
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
                # Update roles
                await self.update_roles(ctx, character)
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ Time's up! Character creation cancelled.")
                
        except Exception as e:
            self.logger.error(f"Error in create command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="profile",
        aliases=["char", "character"],
        description="View your character profile",
        help="Shows your character's stats, clan, inventory count, and jutsu count."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)  # 10 seconds cooldown
    async def profile(self, ctx):
        """View your character profile."""
        try:
            character = self.character_system.get_character(str(ctx.author.id))
            
            if not character:
                await ctx.send("❌ You don't have a character yet! Use `/create` to create one.")
                return
            
            # Update roles (in case they've changed since last check)
            await self.update_roles(ctx, character)
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = self.clan_data.get_clan(clan_name)
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            embed = discord.Embed(
                title=f"{character.name}'s Profile",
                description=f"Clan: {clan_name} ({clan_rarity_str})",
                color=rarity_color
            )
            
            # Add stats
            embed.add_field(
                name="Stats",
                value=f"Level: {character.level}\n"
                      f"HP: {character.hp}/{character.max_hp}\n"
                      f"Chakra: {character.chakra}/{character.max_chakra}\n"
                      f"Taijutsu: {character.taijutsu}\n"
                      f"Ninjutsu: {character.ninjutsu}\n"
                      f"Genjutsu: {character.genjutsu}",
                inline=False
            )
            
            # Add inventory count
            if hasattr(character, 'inventory'):
                inventory_count = sum(len(items) for items in character.inventory.values())
                embed.add_field(
                    name="Inventory",
                    value=f"Items: {inventory_count}",
                    inline=True
                )
            
            # Add jutsu count
            if hasattr(character, 'jutsu'):
                embed.add_field(
                    name="Jutsu",
                    value=f"Known: {len(character.jutsu)}",
                    inline=True
                )
            
            # Get member roles related to character progression
            member_roles = [role.name for role in ctx.author.roles 
                           if any(role.name == r for r in ROLE_CONFIG["level_roles"].values())
                           or role.name == character.clan
                           or any(role.name == r for r in ROLE_CONFIG["specialization_roles"].values())]
            
            if member_roles:
                embed.add_field(
                    name="Roles",
                    value=", ".join(member_roles),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in profile command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="delete",
        aliases=["remove", "erase"],
        description="Delete your character",
        help="Permanently delete your character. This action cannot be undone!"
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def delete(self, ctx):
        """Delete your character."""
        try:
            # Confirm deletion
            embed = discord.Embed(
                title="⚠️ Character Deletion",
                description="Are you sure you want to delete your character?\n"
                          "This action cannot be undone!\n\n"
                          "Type 'yes' to confirm or 'no' to cancel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']
            
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
                
                if msg.content.lower() == 'no':
                    await ctx.send("✅ Character deletion cancelled.")
                    return
                
                # Delete character
                if self.character_system.delete_character(str(ctx.author.id)):
                    await ctx.send("✅ Your character has been deleted!")
                else:
                    await ctx.send("❌ Failed to delete character. Please try again!")
                    
            except asyncio.TimeoutError:
                await ctx.send("❌ Character deletion timed out.")
                
        except Exception as e:
            self.logger.error(f"Error in delete command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="rename",
        aliases=["name"],
        description="Rename your character",
        help="Change your character's name. Must be between 3 and 20 characters."
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def rename(self, ctx, new_name: str):
        """Rename your character.
        
        Args:
            ctx: The command context
            new_name: The new name for your character
        """
        try:
            if len(new_name) < 3 or len(new_name) > 20:
                await ctx.send("❌ Name must be between 3 and 20 characters!")
                return
            
            if self.character_system.rename_character(str(ctx.author.id), new_name):
                await ctx.send(f"✅ Your character has been renamed to {new_name}!")
            else:
                await ctx.send("❌ Failed to rename character. Please try again!")
                
        except Exception as e:
            self.logger.error(f"Error in rename command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="assign_clan",
        aliases=["clan", "set_clan"],
        description="Assign a clan to your character",
        help="Assign or view available clans for your character."
    )
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5 minutes cooldown
    async def assign_clan(self, ctx, clan: Optional[str] = None):
        """Assign a clan to your character.
        
        Args:
            ctx: The command context
            clan: Optional clan name to assign
        """
        try:
            character = self.character_system.get_character(str(ctx.author.id))
            
            if not character:
                await ctx.send("❌ You don't have a character yet! Use `/create` to create one.")
                return
            
            if clan:
                # Validate clan exists
                if not self.clan_data.get_clan(clan):
                    await ctx.send("❌ Invalid clan! Use `/clans` to see available clans.")
                    return
                
                # Assign clan
                if self.character_system.assign_clan(str(ctx.author.id), clan):
                    # Update roles for the new clan
                    await self.update_roles(ctx, character)
                    await ctx.send(f"✅ Your character has been assigned to the {clan} clan!")
                else:
                    await ctx.send("❌ Failed to assign clan. Please try again!")
            else:
                # Show available clans
                clans = self.clan_data.get_all_clans()
                embed = discord.Embed(
                    title="Available Clans",
                    description="Use `/assign_clan <clan_name>` to assign a clan to your character.",
                    color=discord.Color.blue()
                )
                
                for clan_name, clan_info in clans.items():
                    rarity = clan_info.get('rarity', RarityTier.COMMON.value)
                    embed.add_field(
                        name=f"{clan_name} ({rarity})",
                        value=clan_info.get('description', 'No description available.'),
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in assign_clan command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="inventory",
        aliases=["inv", "items"],
        description="View your character's inventory",
        help="Shows your character's weapons, equipment, and consumables."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)  # 10 seconds cooldown
    async def inventory(self, ctx):
        """View your character's inventory."""
        try:
            character = self.character_system.get_character(str(ctx.author.id))
            
            if not character:
                await ctx.send("❌ You don't have a character yet! Use `/create` to create one.")
                return
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = self.clan_data.get_clan(clan_name)
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            embed = discord.Embed(
                title=f"{character.name}'s Inventory",
                description=f"Clan: {clan_name} ({clan_rarity_str})",
                color=rarity_color
            )
            
            # Add inventory sections
            if hasattr(character, 'inventory'):
                # Weapons
                if 'weapons' in character.inventory:
                    weapons = "\n".join(f"• {item}" for item in character.inventory['weapons'])
                    embed.add_field(name="Weapons", value=weapons or "None", inline=False)
                
                # Equipment
                if 'equipment' in character.inventory:
                    equipment = "\n".join(f"• {item}" for item in character.inventory['equipment'])
                    embed.add_field(name="Equipment", value=equipment or "None", inline=False)
                
                # Consumables
                if 'consumables' in character.inventory:
                    consumables = "\n".join(f"• {item}" for item in character.inventory['consumables'])
                    embed.add_field(name="Consumables", value=consumables or "None", inline=False)
            else:
                embed.add_field(
                    name="Empty Inventory",
                    value="Your character doesn't have any items yet.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in inventory command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="jutsu_list",
        aliases=["jutsu", "techniques"],
        description="View your character's known jutsu",
        help="Shows all jutsu your character knows, organized by rank."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)  # 10 seconds cooldown
    async def jutsu_list(self, ctx):
        """View your character's known jutsu."""
        try:
            character = self.character_system.get_character(str(ctx.author.id))
            
            if not character:
                await ctx.send("❌ You don't have a character yet! Use `/create` to create one.")
                return
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = self.clan_data.get_clan(clan_name)
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            embed = discord.Embed(
                title=f"{character.name}'s Jutsu",
                description=f"Clan: {clan_name} ({clan_rarity_str})",
                color=rarity_color
            )
            
            if hasattr(character, 'jutsu') and character.jutsu:
                # Group jutsu by rank
                jutsu_by_rank = {}
                for jutsu in character.jutsu:
                    rank = self.character_system.get_jutsu_rank(jutsu)
                    if rank not in jutsu_by_rank:
                        jutsu_by_rank[rank] = []
                    jutsu_by_rank[rank].append(jutsu)
                
                # Add jutsu to embed by rank
                for rank in sorted(jutsu_by_rank.keys(), reverse=True):
                    jutsu_list = "\n".join(f"• {jutsu}" for jutsu in sorted(jutsu_by_rank[rank]))
                    embed.add_field(
                        name=f"Rank {rank} Jutsu",
                        value=jutsu_list,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="No Jutsu",
                    value="Your character hasn't learned any jutsu yet.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in jutsu_list command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="status",
        aliases=["stats", "state"],
        description="Check your character's current status",
        help="Shows your character's current HP, chakra, active effects, and status conditions."
    )
    @commands.cooldown(1, 10, commands.BucketType.user)  # 10 seconds cooldown
    async def status(self, ctx):
        """Check your character's current status."""
        try:
            character = self.character_system.get_character(str(ctx.author.id))
            
            if not character:
                await ctx.send("❌ You don't have a character yet! Use `/create` to create one.")
                return
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = self.clan_data.get_clan(clan_name)
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            embed = discord.Embed(
                title=f"{character.name}'s Status",
                description=f"Clan: {clan_name} ({clan_rarity_str})",
                color=rarity_color
            )
            
            # Add current stats
            embed.add_field(
                name="Health",
                value=f"HP: {character.hp}/{character.max_hp}",
                inline=True
            )
            embed.add_field(
                name="Chakra",
                value=f"Chakra: {character.chakra}/{character.max_chakra}",
                inline=True
            )
            
            # Add active effects
            if hasattr(character, 'active_effects') and character.active_effects:
                effects = "\n".join(f"• {effect}" for effect in character.active_effects)
                embed.add_field(
                    name="Active Effects",
                    value=effects,
                    inline=False
                )
            
            # Add status conditions
            if hasattr(character, 'status_conditions') and character.status_conditions:
                conditions = "\n".join(f"• {condition}" for condition in character.status_conditions)
                embed.add_field(
                    name="Status Conditions",
                    value=conditions,
                    inline=False
                )
            
            # Add buffs/debuffs
            if hasattr(character, 'buffs') and character.buffs:
                buffs = "\n".join(f"• {buff}" for buff in character.buffs)
                embed.add_field(
                    name="Active Buffs",
                    value=buffs,
                    inline=False
                )
            
            if hasattr(character, 'debuffs') and character.debuffs:
                debuffs = "\n".join(f"• {debuff}" for debuff in character.debuffs)
                embed.add_field(
                    name="Active Debuffs",
                    value=debuffs,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in status command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="levelup",
        aliases=["level", "lvl"],
        description="Level up your character (admin command)",
        help="Manually level up a character. Admin only."
    )
    @commands.has_permissions(administrator=True)
    async def levelup(self, ctx, user: discord.Member, levels: int = 1):
        """Level up a character (admin command).
        
        Args:
            ctx: The command context
            user: The user to level up
            levels: Number of levels to add
        """
        try:
            character = self.character_system.get_character(str(user.id))
            
            if not character:
                await ctx.send(f"❌ {user.display_name} doesn't have a character!")
                return
                
            old_level = character.level
            new_level = old_level + levels
            
            # Update character level
            if hasattr(character, 'level'):
                character.level = new_level
                self.character_system.save_character(str(user.id), character)
                
                # Update roles
                await self.update_roles(ctx, character)
                
                await ctx.send(f"✅ {user.display_name}'s character has been leveled up from {old_level} to {new_level}!")
            else:
                await ctx.send(f"❌ Could not level up {user.display_name}'s character!")
                
        except Exception as e:
            self.logger.error(f"Error in levelup command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            
    @commands.command(
        name="specialize",
        aliases=["spec"],
        description="Specialize your character",
        help="Specialize in Taijutsu, Ninjutsu, or Genjutsu to gain special abilities."
    )
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def specialize(self, ctx, specialization: Optional[str] = None):
        """Specialize your character.
        
        Args:
            ctx: The command context
            specialization: The specialization (Taijutsu, Ninjutsu, or Genjutsu)
        """
        try:
            valid_specs = ["Taijutsu", "Ninjutsu", "Genjutsu"]
            
            character = self.character_system.get_character(str(ctx.author.id))
            
            if not character:
                await ctx.send("❌ You don't have a character yet! Use `/create` to create one.")
                return
                
            # Check if character is high enough level
            if character.level < 10:
                await ctx.send("❌ You need to be at least level 10 to specialize!")
                return
                
            if not specialization:
                # Show specialization options
                embed = discord.Embed(
                    title="Character Specialization",
                    description="Choose a specialization to focus your training:\n\n"
                               "Use `/specialize <type>` to select your path.",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Taijutsu",
                    value="Focus on physical combat techniques. Increases damage with physical attacks.",
                    inline=False
                )
                
                embed.add_field(
                    name="Ninjutsu",
                    value="Focus on chakra-based techniques. Reduces chakra costs for jutsu.",
                    inline=False
                )
                
                embed.add_field(
                    name="Genjutsu",
                    value="Focus on illusion techniques. Increases success rate of status effects.",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
                
            # Validate specialization
            if specialization not in valid_specs:
                await ctx.send(f"❌ Invalid specialization! Choose from: {', '.join(valid_specs)}")
                return
                
            # Set specialization
            if not hasattr(character, 'specialization'):
                # First time specializing
                character.specialization = specialization
                self.character_system.save_character(str(ctx.author.id), character)
                
                # Update roles
                await self.update_roles(ctx, character)
                
                await ctx.send(f"✅ You have specialized in {specialization}!")
            else:
                # Already specialized
                if character.specialization == specialization:
                    await ctx.send(f"❌ You are already specialized in {specialization}!")
                else:
                    # Change specialization (maybe require some cost in the future)
                    character.specialization = specialization
                    self.character_system.save_character(str(ctx.author.id), character)
                    
                    # Update roles
                    await self.update_roles(ctx, character)
                    
                    await ctx.send(f"✅ You have changed your specialization to {specialization}!")
                    
        except Exception as e:
            self.logger.error(f"Error in specialize command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            
    @commands.command(
        name="update_roles",
        aliases=["sync_roles"],
        description="Update character roles",
        help="Manually update your character's Discord roles based on progression."
    )
    @commands.cooldown(1, 60, commands.BucketType.user)  # 1 minute cooldown
    async def update_roles_command(self, ctx):
        """Manually update character roles."""
        try:
            character = self.character_system.get_character(str(ctx.author.id))
            
            if not character:
                await ctx.send("❌ You don't have a character yet! Use `/create` to create one.")
                return
                
            await self.update_roles(ctx, character)
            await ctx.send("✅ Your character roles have been updated!")
            
        except Exception as e:
            self.logger.error(f"Error in update_roles command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="roles",
        aliases=["myroles"],
        description="View available roles",
        help="Shows all available character progression roles."
    )
    @commands.cooldown(1, 30, commands.BucketType.user)  # 30 seconds cooldown
    async def roles(self, ctx):
        """View available character progression roles."""
        try:
            embed = discord.Embed(
                title="Character Progression Roles",
                description="These roles are automatically assigned based on your character's progression.",
                color=discord.Color.blue()
            )
            
            # Level roles
            level_roles = []
            for level, role_name in sorted(ROLE_CONFIG["level_roles"].items()):
                level_roles.append(f"Level {level}: **{role_name}**")
                
            embed.add_field(
                name="Rank Roles",
                value="\n".join(level_roles),
                inline=False
            )
            
            # Specialization roles
            spec_roles = []
            for spec, role_name in ROLE_CONFIG["specialization_roles"].items():
                spec_roles.append(f"{spec}: **{role_name}**")
                
            embed.add_field(
                name="Specialization Roles",
                value="\n".join(spec_roles),
                inline=False
            )
            
            # Clan roles
            if ROLE_CONFIG["clan_roles"]:
                embed.add_field(
                    name="Clan Roles",
                    value="Each clan has its own role that is automatically assigned.",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in roles command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(name="delete", help="Delete your character (cannot be undone)")
    async def delete_character_cmd(self, ctx):
        """Delete a character.
        
        Args:
            ctx: The command context
        """
        user_id = str(ctx.author.id)
        character = self.character_system.get_character(user_id)
        
        if not character:
            await ctx.send("❌ You don't have a character to delete!")
            return
            
        # Create confirmation message
        confirm_view = DeleteConfirmationView(self, ctx.author, character)
        await ctx.send(
            f"⚠️ **WARNING:** Are you sure you want to delete your character **{character.name}**?\n"
            "This action cannot be undone!",
            view=confirm_view
        )
        
    async def delete_character_slash(self, interaction: discord.Interaction):
        """Delete a character using slash command.
        
        Args:
            interaction: The interaction object
        """
        user_id = str(interaction.user.id)
        character = self.character_system.get_character(user_id)
        
        if not character:
            await interaction.response.send_message("❌ You don't have a character to delete!", ephemeral=True)
            return
            
        # Create confirmation message
        confirm_view = DeleteConfirmationView(self, interaction.user, character)
        await interaction.response.send_message(
            f"⚠️ **WARNING:** Are you sure you want to delete your character **{character.name}**?\n"
            "This action cannot be undone!",
            view=confirm_view,
            ephemeral=True
        )
        
    async def _delete_character(self, user, character):
        """Actually delete a character after confirmation.
        
        Args:
            user: The Discord user
            character: The character to delete
        """
        user_id = str(user.id)
        try:
            # Delete the character
            success = self.character_system.delete_character(user_id)
            
            if success:
                self.logger.info(f"Character {character.name} deleted for user {user_id}")
                return True, f"✅ Character **{character.name}** has been permanently deleted."
            else:
                self.logger.error(f"Failed to delete character for user {user_id}")
                return False, "❌ Failed to delete character. Please try again later."
        except Exception as e:
            self.logger.error(f"Error deleting character for user {user_id}: {e}", exc_info=True)
            return False, "❌ An error occurred while deleting your character. Please try again later."


# --- Delete Confirmation View ---
class DeleteConfirmationView(ui.View):
    def __init__(self, character_commands_cog: 'CharacterCommands', user: discord.User, character):
        super().__init__(timeout=60)
        self.character_commands_cog = character_commands_cog
        self.user = user
        self.character = character
        
    @ui.button(label="Yes, Delete My Character", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: ui.Button):
        """Confirm character deletion."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This is not your character to delete!", ephemeral=True)
            return
            
        # Process the deletion
        success, message = await self.character_commands_cog._delete_character(self.user, self.character)
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(content=message, view=self)
        self.stop()
        
    @ui.button(label="No, Keep My Character", style=discord.ButtonStyle.success)
    async def cancel_delete(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel character deletion."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This is not your character to delete!", ephemeral=True)
            return
            
        # Disable all buttons
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(content="✅ Character deletion cancelled.", view=self)
        self.stop()
        
    async def on_timeout(self):
        """Handle timeout."""
        # Disable all buttons on timeout
        for child in self.children:
            child.disabled = True
        
        try:
            # Try to edit the message if it still exists
            await self.message.edit(content="⏰ Character deletion request timed out.", view=self)
        except:
            pass

async def setup(bot):
    """Set up the character commands cog."""
    await bot.add_cog(CharacterCommands(bot, bot.character_system, bot.clan_data)) 