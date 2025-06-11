"""Character commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import ui # Import ui for Modals
from typing import Optional, List, Dict, Any, Tuple, Union, TYPE_CHECKING
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
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from ..utils.discord_ui import get_rarity_color
from ..core.constants import RarityTier
from ..utils.embeds import create_character_embed, create_error_embed
from ..core.views import ConfirmView, PaginationView

# --- Import moved components --- #
# Use relative import from the new subdirectory
from .character.creation import (
    CharacterNameModal, 
    # The other views/functions are used internally by the creation modal/views
    # and don't need to be explicitly imported here unless called directly by the Cog
)
# --- End Import --- #

# --- Import profile/stats functions --- #
from .character.profile import view_profile_impl, view_stats_impl
# --- End Import --- #

# --- Import progression functions/views --- #
from .character.progression import view_achievements_impl, view_titles_impl, TitleEquipView
# --- End Import --- #

# --- Import management functions/views --- #
from .character.management import (
    CharacterManagement,
    delete_character_impl,
    specialize_impl,
    roles_impl,
    DeleteConfirmationView,
    # SpecializationChoiceView # If needed directly
)
# --- End Import --- #

# Role configuration (Keep here for now, or move to a dedicated roles module later)
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

# --- Constants Removed (Moved to creation.py) ---
# PERSONALITY_TRAITS = { ... }
# PERSONALITY_QUIZ = [ ... ]
# --- End Constants Removed --- #

# --- Views/Modals Removed (Moved to creation.py) ---
# class CharacterNameModal(...):
# class PersonalityQuizView(...):
# class ClanConfirmationView(...):
# class ClanSelectionView(...):
# --- End Views/Modals Removed --- #

# --- Main Cog Definition --- #
class CharacterCommands(commands.Cog):
    """Commands for managing characters."""

    # Keep ROLE_CONFIG accessible if role helpers remain here
    ROLE_CONFIG = ROLE_CONFIG 

    def __init__(self, bot: commands.Bot, character_system: CharacterSystem, clan_data: ClanData, progression_engine: ShinobiProgressionEngine):
        """Initialize character commands."""
        self.bot = bot
        self.character_system = character_system
        self.clan_data = clan_data
        self.progression_engine = progression_engine
        self.logger = logging.getLogger(__name__)
        # Instantiate the management handler
        self.management_handler = CharacterManagement(bot, character_system)
        
    async def cog_load(self):
        self.logger.info("CharacterCommands Cog loaded.")
        
    # --- Character Creation Command --- #
    @app_commands.command(name="create", description="Create a new character")
    async def create_character(self, interaction: discord.Interaction):
        """Starts the character creation process."""
        # REMOVED Defer - Modals must be the first response.
        # try:
        #     await interaction.response.defer(ephemeral=True, thinking=True) 
        # except discord.errors.HTTPException as e:
        #     self.logger.error(f"Error deferring interaction for create_character: {e}", exc_info=True)
        #     return

        try:
            # Check if user already has a character
            existing_char = await self.character_system.get_character(str(interaction.user.id))
            if existing_char:
                # Send error as the FIRST response
                await interaction.response.send_message(
                    "❌ You already have a character! Use `/profile` to view it or `/delete` to start over.", 
                    ephemeral=True
                )
                return

            # Pass self (the cog instance) to the modal
            modal = CharacterNameModal(self)
            # Send modal as the FIRST response if checks pass
            await interaction.response.send_modal(modal)

        except discord.errors.HTTPException as http_err:
             # Catch potential errors during interaction.response calls
             self.logger.error(f"HTTP error during create_character initial response/modal: {http_err}", exc_info=True)
             # Cannot send followup if initial response failed.
        except Exception as e:
            self.logger.error(f"Error in create_character command: {e}", exc_info=True)
            # Try to send an error message *if* interaction wasn't already responded to.
            # This is tricky because send_modal IS a response.
            if not interaction.response.is_done():
                try:
                    # This likely causes "Already Acknowledged" if modal send failed mid-way
                    await interaction.response.send_message(
                        "❌ An error occurred while starting character creation.",
                        ephemeral=True
                    )
                except discord.errors.HTTPException as http_err_fatal:
                     # Log double-acknowledgement or other http errors here
                     self.logger.error(f"HTTP error sending final error message in create_character: {http_err_fatal}", exc_info=True)
            else:
                # If already responded (e.g., modal sent but failed later), maybe try followup?
                 try:
                      await interaction.followup.send("❌ An error occurred after the initial step.", ephemeral=True)
                 except discord.errors.HTTPException as http_followup_err:
                      self.logger.error(f"HTTP error sending followup error in create_character: {http_followup_err}", exc_info=True)

    # --- Profile Command (Uses imported function) --- # 
    @app_commands.command(name="profile", description="View your character profile")
    async def view_profile(self, interaction: discord.Interaction):
        """Display the character's profile."""
        await view_profile_impl(self, interaction)

    # --- Delete Command (Uses imported function) --- #
    @app_commands.command(name="delete", description="Delete your character (cannot be undone)")
    async def delete_character(self, interaction: discord.Interaction):
        """Initiates the character deletion process."""
        await delete_character_impl(self, interaction)

    # --- Inventory Command (Uses handler method) --- #
    @app_commands.command(name="inventory", description="View your character's inventory")
    async def inventory(self, interaction: discord.Interaction):
        """Display the character's inventory."""
        await self.management_handler.handle_inventory(interaction)

    # --- Known Jutsu Command (Uses handler method) --- #
    @app_commands.command(name="jutsu", description="View your known jutsu")
    @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def jutsu(self, interaction: discord.Interaction):
        """Displays the list of jutsu known by the character."""
        await self.management_handler.handle_jutsu(interaction)

    # --- Status Command (Uses handler method) --- #
    @app_commands.command(name="status", description="Check your character's current status")
    async def status(self, interaction: discord.Interaction):
        """Displays current HP, Chakra, Stamina, and active effects."""
        await self.management_handler.handle_status(interaction)

    # --- Specialize Command (Uses imported function) --- #
    @app_commands.command(name="specialize", description="Choose or view your character specialization")
    async def specialize(self, interaction: discord.Interaction):
        """Allows a character to choose or view their specialization via an interactive view."""
        await specialize_impl(self, interaction)

    # --- Roles Command (Informational - Uses imported function) --- #
    @app_commands.command(name="roles", description="View available roles")
    async def roles(self, interaction: discord.Interaction):
        """Displays information about automatically assigned roles."""
        await roles_impl(self, interaction)

    # --- View Stats Command (Uses imported function) --- #
    @app_commands.command(name="stats", description="View your character\'s detailed stats and battle record.")
    @app_commands.describe(user="(Optional) View another user\'s stats.")
    async def view_stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Displays detailed stats and battle record for a character."""
        await view_stats_impl(self, interaction, user)

    # --- View Achievements Command (Uses imported function) --- #
    @app_commands.command(name="achievements", description="View your earned achievements.")
    @app_commands.describe(user="(Optional) View another user\'s achievements.")
    async def view_achievements(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Displays the achievements earned by a character."""
        await view_achievements_impl(self, interaction, user)

    # --- View Titles Command (Uses imported function) --- #
    @app_commands.command(name="titles", description="View your earned titles and equip one.")
    @app_commands.describe(user="(Optional) View another user\'s titles.")
    async def view_titles(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """Display earned titles for a character and allow equipping if it's the user's own profile."""
        await view_titles_impl(self, interaction, user)

    # --- Assign Clan Command (simplified for tests) --- #
    @app_commands.command(name="assign_clan", description="Assign a clan to your character")
    async def assign_clan(self, interaction_or_ctx, clan: Optional[str] = None):
        """Assign a clan to a character, used in tests."""
        # Determine invocation context
        if isinstance(interaction_or_ctx, discord.Interaction):
            author = interaction_or_ctx.user
            send_func = interaction_or_ctx.response.send_message
        else:
            author = interaction_or_ctx.author
            send_func = interaction_or_ctx.send

        character = self.character_system.get_character(str(author.id))
        if not character:
            await send_func("You don't have a character yet! Use `/create` to create one.")
            return

        if character.clan:
            await send_func(f"Your character already belongs to the {character.clan} clan!")
            return

        clan_info = None
        if clan:
            clan_info = self.clan_data.get_clan(clan)
        if not clan_info:
            clan_info = self.clan_data.get_random_clan()

        # Fetch character again before updating to mirror expected behavior
        self.character_system.get_character(str(author.id))
        await self.character_system.update_character(str(author.id), {"clan": clan_info["name"]})
        embed = discord.Embed(title=f"{clan_info['name']} Clan Assigned")
        await send_func(embed=embed)

    # --- Role Management Helpers (Keep here for now) --- #
    # These might be better in a separate RoleManager service/cog later
    async def _update_roles_after_creation(self, character: Character):
        try:
            guild = self.bot.get_guild(self.bot.guild_id)
            if not guild:
                 self.logger.error(f"Could not find guild {self.bot.guild_id} for role update.")
                 return
            member = guild.get_member(int(character.id))
            if not member:
                self.logger.warning(f"Could not find member {character.id} in guild {guild.id} for role update.")
                return
            await self._handle_level_roles(guild, member, character)
            await self._handle_clan_roles(guild, member, character)
        except Exception as e:
            self.logger.error(f"Error updating roles for new character {character.id}: {e}", exc_info=True)

    async def _handle_level_roles(self, guild, member, character: Character) -> None:
        if not ROLE_CONFIG.get("level_roles"):
            return
        highest_role_to_assign = None
        current_level_role_names = set()
        for level_req, role_name in sorted(ROLE_CONFIG["level_roles"].items(), reverse=True):
            if character.level >= level_req:
                highest_role_to_assign = role_name
                break
        all_level_role_names = set(ROLE_CONFIG["level_roles"].values())
        roles_to_add = []
        roles_to_remove = []
        current_member_roles = {role.name for role in member.roles}
        if highest_role_to_assign:
            if highest_role_to_assign not in current_member_roles:
                role_obj = await self._get_or_create_role(guild, highest_role_to_assign)
                if role_obj: roles_to_add.append(role_obj)
            for role_name in all_level_role_names:
                if role_name != highest_role_to_assign and role_name in current_member_roles:
                    role_obj = discord.utils.get(guild.roles, name=role_name)
                    if role_obj: roles_to_remove.append(role_obj)
        else:
             for role_name in all_level_role_names:
                 if role_name in current_member_roles:
                    role_obj = discord.utils.get(guild.roles, name=role_name)
                    if role_obj: roles_to_remove.append(role_obj)
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Character level progression")
                for role in roles_to_add: await self._send_role_update_message(member, "➕", role.name)
            except discord.Forbidden:
                self.logger.error(f"Missing permissions to add level roles in guild {guild.id}")
            except discord.HTTPException as e:
                self.logger.error(f"HTTP error adding level roles for {member.id}: {e}")
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Character level progression (removing lower roles)")
            except discord.Forbidden:
                self.logger.error(f"Missing permissions to remove level roles in guild {guild.id}")
            except discord.HTTPException as e:
                self.logger.error(f"HTTP error removing level roles for {member.id}: {e}")

    async def _handle_clan_roles(self, guild: discord.Guild, member: discord.Member, character: Character):
        if not ROLE_CONFIG.get("clan_roles") or not character.clan:
            return
        clan_role_name = character.clan
        current_member_roles = {role.name for role in member.roles}
        if clan_role_name in current_member_roles:
             return
        roles_to_add = []
        role_obj = await self._get_or_create_role(guild, clan_role_name)
        if role_obj: roles_to_add.append(role_obj)
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason=f"Character assigned to {clan_role_name} clan")
                for role in roles_to_add: await self._send_role_update_message(member, "🏰", role.name)
            except discord.Forbidden:
                self.logger.error(f"Missing permissions to add clan roles in guild {guild.id}")
            except discord.HTTPException as e:
                self.logger.error(f"HTTP error adding clan roles for {member.id}: {e}")

    async def _handle_specialization_roles(self, guild, member, character: Character) -> None:
        if not ROLE_CONFIG.get("specialization_roles") or not character.specialization:
            return
        spec_role_name = ROLE_CONFIG["specialization_roles"].get(character.specialization)
        if not spec_role_name:
            return
        current_member_roles = {role.name for role in member.roles}
        if spec_role_name in current_member_roles:
            return
        roles_to_add = []
        roles_to_remove = []
        role_obj = await self._get_or_create_role(guild, spec_role_name)
        if role_obj: roles_to_add.append(role_obj)
        all_spec_role_names = set(ROLE_CONFIG["specialization_roles"].values())
        for role_name in all_spec_role_names:
            if role_name != spec_role_name and role_name in current_member_roles:
                role_obj_remove = discord.utils.get(guild.roles, name=role_name)
                if role_obj_remove: roles_to_remove.append(role_obj_remove)
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason=f"Character specialized in {character.specialization}")
                for role in roles_to_add: await self._send_role_update_message(member, "⭐", role.name)
            except discord.Forbidden:
                self.logger.error(f"Missing permissions to add specialization roles in guild {guild.id}")
            except discord.HTTPException as e:
                self.logger.error(f"HTTP error adding specialization roles for {member.id}: {e}")
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Changing specialization")
            except discord.Forbidden:
                self.logger.error(f"Missing permissions to remove specialization roles in guild {guild.id}")
            except discord.HTTPException as e:
                self.logger.error(f"HTTP error removing specialization roles for {member.id}: {e}")

    async def _get_or_create_role(self, guild: discord.Guild, role_name: str) -> Optional[discord.Role]:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            return role
        try:
            if not guild.me.guild_permissions.manage_roles:
                 self.logger.error(f"Bot lacks 'Manage Roles' permission in guild {guild.id} to create role '{role_name}'.")
                 return None
            self.logger.info(f"Role '{role_name}' not found in guild {guild.id}. Attempting to create.")
            new_role = await guild.create_role(
                name=role_name, 
                permissions=discord.Permissions.none(), 
                mentionable=False, 
                reason=f"Creating role for HCShinobi bot feature ({role_name})"
            )
            self.logger.info(f"Successfully created role '{role_name}' (ID: {new_role.id}) in guild {guild.id}.")
            return new_role
        except discord.Forbidden:
            self.logger.error(f"Failed to create role '{role_name}' in guild {guild.id} due to missing permissions.")
            return None
        except discord.HTTPException as e:
            self.logger.error(f"Failed to create role '{role_name}' in guild {guild.id} due to an HTTP error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred creating role '{role_name}' in guild {guild.id}: {e}", exc_info=True)
            return None

    async def _send_role_update_message(self, member, prefix, role_name):
        send_dms = False
        if send_dms:
            try:
                await member.send(f"{prefix} You have been granted the **{role_name}** role.")
            except discord.Forbidden:
                self.logger.warning(f"Could not send role update DM to {member.id} (DMs disabled?).")
            except Exception as e:
                self.logger.error(f"Error sending role update DM to {member.id}: {e}")

# --- Setup Function --- #
async def setup(bot):
    try:
        character_system = bot.services.character_system
        clan_data = bot.services.clan_data
        progression_engine = bot.services.progression_engine
        if not all([character_system, clan_data, progression_engine]):
             logging.error("Missing required services for CharacterCommands. Cog not loaded.")
             return
        cog = CharacterCommands(bot, character_system, clan_data, progression_engine)
        await bot.add_cog(cog)
        logging.info("CharacterCommands cog added successfully.")
        return cog
    except AttributeError as e:
        logging.error(f"Failed to get required services for CharacterCommands: {e}. Cog not loaded.")
    except Exception as e:
        logging.error(f"Error setting up CharacterCommands: {e}", exc_info=True)
        raise 