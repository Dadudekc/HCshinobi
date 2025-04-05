"""
Handles character creation commands, views, and logic, with extra randomization
to make the personality quiz less predictable.
"""

import discord
from discord.ext import commands
from discord import ui
from typing import Optional, Dict, List, Tuple, Any, TYPE_CHECKING
import logging
import asyncio
import random
import uuid
import traceback

# Relative imports for core systems and utilities
from ...core.character import Character
from ...core.constants import RarityTier
from ...utils.discord_ui import get_rarity_color
from ...utils.embeds import create_character_embed

# Import the StarterBattle class
from .starter_battle import StarterBattle

if TYPE_CHECKING:
    from .character_commands import CharacterCommands

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------------
#  Personality Definition — Now only a base data structure; we shuffle it on the fly
# ------------------------------------------------------------------------------------

BASE_PERSONALITY_QUIZ = [
    {
        "question": "How do you approach a challenging problem?",
        "options": [
            {"label": "Analyze all possibilities systematically", "traits": ["Analytical", "Strategic"]},
            {"label": "Trust my instincts and intuition",         "traits": ["Intuitive", "Creative"]},
            {"label": "Persist until I find a solution",          "traits": ["Determined", "Resilient"]},
            {"label": "Seek advice from others",                  "traits": ["Sociable", "Kind"]}
        ]
    },
    {
        "question": "In a team, what role do you usually take?",
        "options": [
            {"label": "The strategist who plans ahead",     "traits": ["Strategic", "Analytical"]},
            {"label": "The protector who looks after others","traits": ["Protective", "Loyal"]},
            {"label": "The leader who takes charge",        "traits": ["Proud", "Noble"]},
            {"label": "The supportive member who helps",    "traits": ["Kind", "Sociable"]}
        ]
    },
    {
        "question": "How do you prefer to train and improve?",
        "options": [
            {"label": "Disciplined practice of fundamentals",   "traits": ["Disciplined", "Honorable"]},
            {"label": "Creative experimentation with new techniques","traits": ["Creative", "Intuitive"]},
            {"label": "Pushing my limits through intense effort","traits": ["Determined", "Energetic"]},
            {"label": "Studying and learning from masters",     "traits": ["Wise", "Analytical"]}
        ]
    },
    {
        "question": "What do you value most in yourself and others?",
        "options": [
            {"label": "Loyalty and reliability",   "traits": ["Loyal", "Honorable"]},
            {"label": "Intelligence and wisdom",   "traits": ["Wise", "Analytical"]},
            {"label": "Strength and determination","traits": ["Determined", "Proud"]},
            {"label": "Kindness and compassion",   "traits": ["Kind", "Protective"]}
        ]
    },
    {
        "question": "How do you react under pressure?",
        "options": [
            {"label": "Stay calm and assess the situation", "traits": ["Calm", "Analytical"]},
            {"label": "Act quickly and decisively",         "traits": ["Determined", "Energetic"]},
            {"label": "Adapt and find creative solutions",  "traits": ["Creative", "Resilient"]},
            {"label": "Stand firm with discipline and focus","traits": ["Disciplined", "Noble"]}
        ]
    }
]

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

# ------------------------------------------------------------------------------------
#                         Character Name Modal (unchanged)
# ------------------------------------------------------------------------------------

class CharacterNameModal(ui.Modal, title='Create Your Character'):
    """
    A Modal that prompts the user for their character's name, then launches
    the personality quiz in DM upon successful submission.
    """
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
        
        # Now, start the quiz in DMs
        try:
            dm_channel = interaction.user.dm_channel or await interaction.user.create_dm()
            
            # Create the quiz view (with randomization)
            quiz_view = PersonalityQuizView(self.character_commands_cog, name)
            
            # Create the initial quiz embed
            embed = quiz_view.create_question_embed()
            
            # Send the quiz view to the user's DMs
            await dm_channel.send(embed=embed, view=quiz_view)

            # Acknowledge so the interaction doesn't hang
            await interaction.response.send_message(
                f"Your character name **{name}** is noted! A quiz has been sent to your DMs to finish character creation.",
                ephemeral=True
            )
            
        except discord.Forbidden:
            # Bot cannot DM the user
            self.character_commands_cog.logger.warning(
                f"Cannot send DM to user {interaction.user.id}. Character creation aborted."
            )
            await interaction.response.send_message(
                "❌ I couldn't send you a DM for the quiz. Check your privacy settings or try again.",
                ephemeral=True
            )
        except Exception as e:
            self.character_commands_cog.logger.error(
                f"Error sending quiz to DMs for {interaction.user.id}: {e}", exc_info=True
            )
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True
            )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        self.character_commands_cog.logger.error(f'Error in CharacterNameModal: {error}', exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                'Oops! Something went wrong submitting the name. Please try again.',
                ephemeral=True
            )


# ------------------------------------------------------------------------------------
#                     Personality Quiz View with Randomization
# ------------------------------------------------------------------------------------

class PersonalityQuizView(ui.View):
    """
    A View that asks the user a series of personality questions to recommend a clan,
    but randomizes question/option order to make the quiz harder to "game."
    """
    def __init__(self, character_commands_cog: 'CharacterCommands', name: str, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.character_commands_cog = character_commands_cog
        self.name = name
        self.trait_scores: Dict[str, int] = {}
        self.message: Optional[discord.Message] = None

        # Randomize the quiz data at initialization
        self.quiz_data = self._get_randomized_quiz(BASE_PERSONALITY_QUIZ)
        self.current_question_idx = 0

    @staticmethod
    def _get_randomized_quiz(base_quiz: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Returns a deep copy of the quiz data with:
          1) Questions in random order.
          2) Options in random order within each question.
        """
        # Copy the data to avoid mutating the global base
        quiz_copy = []
        for q in base_quiz:
            # Copy each question dict and shuffle its options
            question_dict = {
                "question": q["question"],
                "options": random.sample(q["options"], len(q["options"]))  # shuffled options
            }
            quiz_copy.append(question_dict)
        
        # Shuffle the order of questions
        random.shuffle(quiz_copy)
        return quiz_copy

    def create_question_embed(self) -> discord.Embed:
        """
        Create an Embed for the current question in the quiz.
        """
        question_data = self.quiz_data[self.current_question_idx]
        embed = discord.Embed(
            title="Personality Quiz",
            description=(
                f"Question {self.current_question_idx + 1}/{len(self.quiz_data)}:\n"
                f"{question_data['question']}"
            ),
            color=discord.Color.blue()
        )
        # Present each randomized option
        for i, option in enumerate(question_data["options"]):
            embed.add_field(
                name=f"Option {i+1}",
                value=option['label'],
                inline=False
            )
        embed.set_footer(text="This quiz will help determine which clan suits your personality.")
        return embed
    
    async def update_quiz(self, interaction: discord.Interaction, selected_option_index: int):
        # Defer to avoid immediate timeouts
        if not interaction.response.is_done():
            await interaction.response.defer()

        # Safeguard
        if self.current_question_idx >= len(self.quiz_data):
            self.character_commands_cog.logger.warning(
                f"Quiz already finished (Q={self.current_question_idx}). User: {interaction.user.id}"
            )
            return

        question_data = self.quiz_data[self.current_question_idx]
        try:
            chosen_option = question_data["options"][selected_option_index]
            traits = chosen_option['traits']
        except (IndexError, KeyError) as e:
            self.character_commands_cog.logger.error(
                f"IndexError accessing quiz traits: Q={self.current_question_idx}, "
                f"Option={selected_option_index}, user={interaction.user.id}: {e}"
            )
            await interaction.followup.send(
                "❌ An internal error occurred with the quiz options. Please try `/create` again.",
                ephemeral=True
            )
            self.stop()
            return

        # Update trait scores
        for trait in traits:
            self.trait_scores[trait] = self.trait_scores.get(trait, 0) + 1

        # Next question or finish
        self.current_question_idx += 1
        if self.current_question_idx < len(self.quiz_data):
            embed = self.create_question_embed()
            try:
                await interaction.edit_original_response(embed=embed, view=self)
            except discord.NotFound:
                await interaction.followup.send(embed=embed, view=self)
        else:
            await self.finish_quiz(interaction)

    async def finish_quiz(self, interaction: discord.Interaction):
        """
        Finalize the quiz, compute recommended clan, and show a confirmation View.
        """
        try:
            top_traits, recommended_clan = self.get_clan_recommendation()

            embed = discord.Embed(
                title="Personality Quiz Results",
                description=f"Your dominant traits are: **{', '.join(top_traits)}**",
                color=discord.Color.gold()
            )

            # Retrieve recommended clan data
            if not self.character_commands_cog.clan_data:
                self.character_commands_cog.logger.error(
                    f"ClanData unavailable finishing quiz for user {interaction.user.id}."
                )
                await interaction.edit_original_response(
                    content="❌ Internal error: Clan data service unavailable.",
                    embed=None,
                    view=None
                )
                self.stop()
                return

            clan_data = self.character_commands_cog.clan_data.get_clan(recommended_clan)
            if clan_data is None:
                self.character_commands_cog.logger.error(
                    f"No data found for recommended clan '{recommended_clan}' "
                    f"(user {interaction.user.id})."
                )
                await interaction.edit_original_response(
                    content="❌ Internal error: recommended clan data not found.",
                    embed=None,
                    view=None
                )
                self.stop()
                return

            rarity_str = clan_data.get('rarity', RarityTier.COMMON.value)
            try:
                rarity_enum = RarityTier(rarity_str)
            except ValueError:
                rarity_enum = RarityTier.COMMON

            # Build clan display info with rarity and village if available
            clan_display = f"**{recommended_clan}** ({rarity_enum.value})"
            if 'village' in clan_data and clan_data['village']:
                clan_display += f" | {clan_data['village']}"

            embed.add_field(
                name="Recommended Clan",
                value=clan_display,
                inline=False
            )

            # Add kekkei genkai information if available
            if 'kekkei_genkai' in clan_data and clan_data['kekkei_genkai']:
                if isinstance(clan_data['kekkei_genkai'], list) and clan_data['kekkei_genkai']:
                    embed.add_field(
                        name="Kekkei Genkai",
                        value=", ".join(clan_data['kekkei_genkai']),
                        inline=True
                    )
                elif isinstance(clan_data['kekkei_genkai'], str) and clan_data['kekkei_genkai']:
                    embed.add_field(
                        name="Kekkei Genkai",
                        value=clan_data['kekkei_genkai'],
                        inline=True
                    )

            # Add traits information if available
            if 'traits' in clan_data and clan_data['traits']:
                if isinstance(clan_data['traits'], list) and clan_data['traits']:
                    embed.add_field(
                        name="Traits",
                        value=", ".join(clan_data['traits']),
                        inline=True
                    )
                elif isinstance(clan_data['traits'], str) and clan_data['traits']:
                    embed.add_field(
                        name="Traits",
                        value=clan_data['traits'],
                        inline=True
                    )

            if 'lore' in clan_data:
                embed.add_field(
                    name="Clan Lore",
                    value=clan_data['lore'],
                    inline=False
                )

            # Build the confirmation view
            confirm_view = ClanConfirmationView(
                self.character_commands_cog,
                self.name,
                recommended_clan
            )
            await interaction.edit_original_response(embed=embed, view=confirm_view)
            self.stop()

        except Exception as e:
            self.character_commands_cog.logger.error(
                f"Error finishing quiz for user {interaction.user.id}: {e}",
                exc_info=True
            )
            try:
                await interaction.edit_original_response(
                    content="❌ An unexpected error occurred finishing the quiz. Try `/create` again.",
                    embed=None,
                    view=None
                )
            except Exception:
                pass
            finally:
                self.stop()

    def get_clan_recommendation(self) -> Tuple[List[str], str]:
        """
        Based on the user's final trait scores, pick the top traits, 
        then do a random-weighted selection of suitable clans, factoring in rarity
        and adding a small random "fudge factor" to reduce predictability.
        """
        # Sort traits by descending score
        sorted_traits = sorted(self.trait_scores.items(), key=lambda x: x[1], reverse=True)
        top_traits = [trait for trait, score in sorted_traits[:3]]

        # Build a clan_scores map from these traits
        clan_scores = {}
        for trait, _score in sorted_traits:
            if trait in PERSONALITY_TRAITS:
                for clan in PERSONALITY_TRAITS[trait]:
                    clan_scores[clan] = clan_scores.get(clan, 0) + _score

        # Build a weighted list (factoring rarity + random offset)
        # The better the user matched a clan, the higher the base score
        # Then we reduce or boost score based on clan rarity, plus a random fudge
        weighted_clans = []
        for clan_name, base_score in clan_scores.items():
            # If the clan isn't recognized in data, skip
            cdata = self.character_commands_cog.clan_data.get_clan(clan_name)
            if not cdata:
                continue

            rarity_str = cdata.get('rarity', RarityTier.COMMON.value)
            rarity_factor = {
                RarityTier.COMMON.value: 1.0,
                RarityTier.UNCOMMON.value: 0.7,
                RarityTier.RARE.value: 0.4,
                RarityTier.EPIC.value: 0.2,
                RarityTier.LEGENDARY.value: 0.1
            }.get(rarity_str, 1.0)

            # Add a small random fudge factor (±20% of base_score * rarity_factor)
            # So even with perfect picks, there's some unpredictability
            fudge_range = (base_score * rarity_factor) * 0.2
            random_offset = random.uniform(-fudge_range, fudge_range)

            final_weight = (base_score * rarity_factor) + random_offset
            if final_weight < 0:
                final_weight = 0.01  # never be zero exactly

            weighted_clans.append((clan_name, final_weight))

        if weighted_clans:
            total_weight = sum(weight for _, weight in weighted_clans)
            if total_weight > 0:
                pick = random.uniform(0, total_weight)
                current = 0
                for clan_name, weight in weighted_clans:
                    current += weight
                    if current >= pick:
                        return top_traits, clan_name

        # Fallback if no valid clans or total_weight=0
        if self.character_commands_cog.clan_data:
            common_clans = self.character_commands_cog.clan_data.get_clans_by_rarity(RarityTier.COMMON)
            if common_clans:
                chosen = random.choice(common_clans)
                return top_traits, chosen['name']
        return top_traits, "Civilian"

    # --------------------------------------------------------------------------------
    #                          Button Handlers for Quiz
    # --------------------------------------------------------------------------------
    @ui.button(label="Option 1", style=discord.ButtonStyle.primary, custom_id="quiz_opt_1")
    async def option_1(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 0)
    
    @ui.button(label="Option 2", style=discord.ButtonStyle.primary, custom_id="quiz_opt_2")
    async def option_2(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 1)
    
    @ui.button(label="Option 3", style=discord.ButtonStyle.primary, custom_id="quiz_opt_3")
    async def option_3(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 2)
    
    @ui.button(label="Option 4", style=discord.ButtonStyle.primary, custom_id="quiz_opt_4")
    async def option_4(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_quiz(interaction, 3)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(
                    content="The personality quiz has timed out. Please try again with `/create`.",
                    view=None
                )
            except discord.NotFound:
                pass
            except Exception as e:
                logger.error(f"Error editing message on PersonalityQuizView timeout: {e}")
        self.stop()


# ------------------------------------------------------------------------------------
#            Clan ConfirmationView, ClanSelectionView, and creation logic
# ------------------------------------------------------------------------------------

class ClanConfirmationView(ui.View):
    """Unchanged logic, but references the new PersonalityQuizView randomization."""
    def __init__(self, character_commands_cog: 'CharacterCommands', name: str, recommended_clan: str):
        super().__init__(timeout=180)
        self.character_commands_cog = character_commands_cog
        self.name = name
        self.recommended_clan = recommended_clan
        self.message: Optional[discord.Message] = None

    @ui.button(label="Accept this Clan", style=discord.ButtonStyle.success, custom_id="clan_confirm_accept")
    async def accept_clan(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await _create_character_logic(
            self.character_commands_cog, interaction, self.name, self.recommended_clan
        )
        self.stop()

    @ui.button(label="Choose Another Clan", style=discord.ButtonStyle.secondary, custom_id="clan_confirm_choose")
    async def choose_another(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        clan_selection_view = ClanSelectionView(self.character_commands_cog, self.name)
        await clan_selection_view.start(interaction) 
        self.stop()

    @ui.button(label="Skip & Create Character", style=discord.ButtonStyle.primary, custom_id="clan_confirm_skip")
    async def skip_clan(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await _create_character_logic(self.character_commands_cog, interaction, self.name, "Civilian")
        self.stop()

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(
                    content="Clan confirmation timed out. Please try `/create` again.",
                    view=None
                )
            except discord.NotFound:
                pass
            except Exception as e:
                logger.error(f"Error editing message on ClanConfirmationView timeout: {e}")
        self.stop()


class ClanSelectionView(ui.View):
    """
    Allows manual selection of a clan from a dropdown (unchanged).
    """
    def __init__(self, character_commands_cog: 'CharacterCommands', name: str):
        super().__init__(timeout=180)
        self.character_commands_cog = character_commands_cog
        self.name = name
        self.clan_data = character_commands_cog.clan_data
        self.message: Optional[discord.Message] = None

        self.clan_select = self.create_clan_select()
        self.add_item(self.clan_select)

    async def start(self, interaction: discord.Interaction):
        embed = self.create_clan_selection_embed()
        if not self.clan_select.options:
            await interaction.edit_original_response(
                content="❌ Error: No clans could be loaded for selection.",
                embed=None,
                view=None
            )
            self.stop()
            return

        await interaction.edit_original_response(embed=embed, view=self)
        self.message = await interaction.original_response()

    def create_clan_selection_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Manual Clan Selection",
            description="Choose your desired clan from the list below.",
            color=discord.Color.purple()
        )

    def create_clan_select(self) -> ui.Select:
        options = []
        if self.clan_data:
            all_clans = self.clan_data.get_all_clans().values()
            for clan in sorted(all_clans, key=lambda c: c.get('name', '')):
                clan_name = clan.get('name')
                rarity = clan.get('rarity', RarityTier.COMMON.value)
                desc = clan.get('description', 'No description')[:80]  # Shortened to make room for village
                village = clan.get('village', '')
                
                # Create a description with village if available
                display_desc = f"{rarity}"
                if village:
                    display_desc += f" - {village}"
                    
                # Truncate description if needed
                if len(display_desc + desc) > 100:
                    # Discord limit for SelectOption descriptions
                    available_space = 100 - len(display_desc) - 3  # -3 for the " - " separator
                    desc = desc[:available_space] + "..."
                
                full_desc = f"{display_desc} - {desc}" if desc else display_desc
                
                if clan_name:
                    options.append(discord.SelectOption(
                        label=clan_name,
                        description=full_desc,
                        value=clan_name
                    ))
        else:
            self.character_commands_cog.logger.error(
                "ClanData service unavailable during ClanSelectionView initialization."
            )
        options = options[:25]
        return ui.Select(
            placeholder="Select a clan",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="clan_select_manual"
        )

    @ui.select(cls=ui.Select, options=[], placeholder="Select a clan", custom_id="clan_select_manual")
    async def clan_select_callback(self, interaction: discord.Interaction, select: ui.Select):
        selected_clan = select.values[0]
        await interaction.response.defer()
        await _create_character_logic(
            self.character_commands_cog, interaction, self.name, selected_clan
        )
        self.stop()

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(
                    content="Clan selection timed out. Please try `/create` again.",
                    view=None
                )
            except discord.NotFound:
                pass
            except Exception as e:
                logger.error(f"Error editing message on ClanSelectionView timeout: {e}")
        self.stop()


# ------------------------------------------------------------------------------------
#                      Helper Functions — unchanged except docstring
# ------------------------------------------------------------------------------------

async def _process_character_creation(
    cog: 'CharacterCommands',
    interaction: discord.Interaction,
    name: str
):
    """
    Called from the /create command to start the character creation flow.
    Displays the CharacterNameModal, which triggers the personality quiz in a DM.
    """
    try:
        modal = CharacterNameModal(cog)
        await interaction.response.send_modal(modal)
    except Exception as e:
        cog.logger.error(f"Error in _process_character_creation: {e}", exc_info=True)
        if not interaction.response.is_done():
            try:
                await interaction.followup.send(
                    "❌ An error occurred while processing your command. Please try again later.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                cog.logger.warning(
                    "Interaction already responded in _process_character_creation error handling."
                )
            except Exception as ie:
                cog.logger.error(
                    f"Failed to send followup in _process_character_creation: {ie}"
                )


async def _create_character_logic(
    cog: 'CharacterCommands',
    interaction: discord.Interaction,
    name: str,
    clan: str = "Civilian"
):
    """
    Core logic for actually creating/saving a Character, once the user has
    either chosen or skipped clan selection.
    """
    user_id = str(interaction.user.id)
    cog.logger.info(f"Attempting character creation for user {user_id}: Name='{name}', Clan='{clan}'")

    try:
        clan_data = cog.clan_data.get_clan(clan) if cog.clan_data else None
        starting_jutsu = clan_data.get('starting_jutsu', []) if clan_data else []

        character = Character(
            id=user_id,
            name=name,
            clan=clan,
            jutsu=starting_jutsu
        )

        save_success = await cog.character_system.save_character(character)
        if not save_success:
            await interaction.followup.send(
                "❌ Failed to save character data. Please try again.",
                ephemeral=True
            )
            return

        # Update the in-memory cache
        cog.character_system.characters[user_id] = character
        cog.logger.info(
            f"Successfully created and cached character '{name}' ({clan}) for user {user_id}."
        )

        # Start the academy entrance battle
        try:
            # Get the battle system - try both possible methods
            battle_system = None
            loot_system = None
            
            # Try directly from bot services if available
            if hasattr(cog.bot, 'services') and hasattr(cog.bot.services, 'get_battle_manager'):
                battle_system = cog.bot.services.get_battle_manager()
                cog.logger.info(f"Retrieved battle_system from services: {battle_system is not None}")
            
            # Otherwise try from the Battle cog
            if battle_system is None:
                battle_cog = cog.bot.get_cog('Battle') or cog.bot.get_cog('BattleCommands') or cog.bot.get_cog('BattleSystemCommands')
                if battle_cog and hasattr(battle_cog, 'get_battle_system'):
                    battle_system = battle_cog.get_battle_system()
                    cog.logger.info(f"Retrieved battle_system from cog {battle_cog.__class__.__name__}: {battle_system is not None}")
                # Also try battle_manager attribute
                elif battle_cog and hasattr(battle_cog, 'battle_manager'):
                    battle_system = battle_cog.battle_manager
                    cog.logger.info(f"Retrieved battle_manager from cog {battle_cog.__class__.__name__}: {battle_system is not None}")
            
            # Try getting the loot system
            loot_cog = cog.bot.get_cog('Loot') or cog.bot.get_cog('LootCommands') or cog.bot.get_cog('LootSystem')
            if loot_cog and hasattr(loot_cog, 'get_loot_system'):
                loot_system = loot_cog.get_loot_system()
                cog.logger.info(f"Retrieved loot_system from cog {loot_cog.__class__.__name__}: {loot_system is not None}")
            elif loot_cog and hasattr(loot_cog, 'loot_system'):
                loot_system = loot_cog.loot_system
                cog.logger.info(f"Retrieved loot_system attribute from cog {loot_cog.__class__.__name__}: {loot_system is not None}")
            
            # Get the currency system (this seems to work already)
            currency_cog = cog.bot.get_cog('Currency')
            currency_system = currency_cog.get_system() if currency_cog else None

            embed = create_character_embed(character, currency_system=currency_system)
            embed.title = "✅ Character Created!"

            await interaction.followup.send(embed=embed, ephemeral=False)
            
            # Give a moment for the user to see their character info
            await asyncio.sleep(2)
            
            if battle_system and loot_system:
                starter_battle = StarterBattle(
                    battle_system=battle_system,
                    character_system=cog.character_system,
                    currency_system=currency_system,
                    loot_system=loot_system
                )
                
                await starter_battle.start_entrance_battle(interaction, character)
            else:
                cog.logger.warning(f"Could not start entrance battle for {user_id}: Battle or Loot system not available")
                # Continue with character creation without the battle
                await interaction.followup.send(
                    "You've successfully created your character! The academy entrance test will be available soon.",
                    ephemeral=False
                )
        except Exception as battle_error:
            cog.logger.error(f"Error starting entrance battle for {user_id}: {battle_error}", exc_info=True)
            # Continue with character creation without the battle
            await interaction.followup.send(
                "You've successfully created your character! There was an issue with the academy entrance test, but you can proceed with your ninja journey.",
                ephemeral=False
            )

    except Exception as e:
        cog.logger.error(
            f"Error in _create_character_logic for user {user_id}: {e}",
            exc_info=True
        )
        traceback.print_exc()
        await interaction.followup.send(
            f"❌ An unexpected error occurred during character creation: {e}",
            ephemeral=True
        )
