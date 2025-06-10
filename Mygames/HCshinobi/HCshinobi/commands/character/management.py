"""
Handles character management commands (delete, inventory, jutsu, status, specialize, roles).
Part of the CharacterCommands cog refactor.
"""
import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import logging

# Relative imports for core systems and utilities
from ...core.character import Character
from ...core.character_system import CharacterSystem
from ...utils.embeds import create_character_embed
from ...utils.discord_ui import get_rarity_color # Needed for roles command example
from HCshinobi.core.item_registry import ItemRegistry  # Add import
from HCshinobi.core.jutsu_system import JutsuSystem  # Add import

# Type hint for the main cog
if TYPE_CHECKING:
    from .character_commands import CharacterCommands

logger = logging.getLogger(__name__)

# --- Delete Confirmation View --- #
class DeleteConfirmationView(ui.View):
    def __init__(self, character_commands_cog: 'CharacterCommands', user: discord.User, character):
        super().__init__(timeout=60)
        self.character_commands_cog = character_commands_cog
        self.user = user
        self.character = character
        self.message = None # Set when sent

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the original user to interact
        return interaction.user.id == self.user.id

    @ui.button(label="Yes, Delete My Character", style=discord.ButtonStyle.danger, custom_id="delete_confirm_yes")
    async def confirm_delete(self, interaction: discord.Interaction, button: ui.Button):
        # Double check interaction user just in case interaction_check fails
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return

        # Defer the interaction as deletion might take time
        await interaction.response.defer(ephemeral=True) 

        try:
            success = await self.character_commands_cog.character_system.delete_character(str(self.user.id))
            if success:
                # Use followup after defer
                await interaction.followup.send("🗑️ Your character has been deleted.", ephemeral=True)
                self.character_commands_cog.logger.info(f"Character {self.character.name} (User: {self.user.id}) deleted by user confirmation.")
            else:
                await interaction.followup.send("❌ Failed to delete character data.", ephemeral=True)
        except Exception as e:
            self.character_commands_cog.logger.error(f"Error during confirmed character deletion for {self.user.id}: {e}", exc_info=True)
            # Send followup error
            await interaction.followup.send("❌ An error occurred during deletion.", ephemeral=True)
        finally:
            self.stop()

    @ui.button(label="No, Keep My Character", style=discord.ButtonStyle.success, custom_id="delete_confirm_no")
    async def cancel_delete(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This is not for you!", ephemeral=True)
            return
        
        # Edit the original message
        # Check if the original message reference exists
        if self.message:
             await self.message.edit(content="✅ Character deletion cancelled.", view=None)
        else: # Fallback if message reference lost
             await interaction.response.send_message("✅ Character deletion cancelled.", ephemeral=True)
             
        self.character_commands_cog.logger.info(f"Character deletion cancelled by user {self.user.id}.")
        self.stop()

    async def on_timeout(self):
        if self.message:
            try:
                # Edit the original message to indicate timeout
                await self.message.edit(content="Character deletion confirmation timed out.", view=None)
            except discord.NotFound:
                 pass # Message might have been deleted
            except Exception as e:
                 self.character_commands_cog.logger.error(f"Error editing message on DeleteConfirmationView timeout: {e}")
        self.stop()
        
# --- Specialization Choice View (Example structure, assuming it exists) --- #
class SpecializationChoiceView(ui.View):
     def __init__(self, cog: 'CharacterCommands', character: Character, specializations: List[str]):
         super().__init__(timeout=180)
         self.cog = cog
         self.character = character
         self.add_item(SpecializationSelect(specializations))

class SpecializationSelect(ui.Select):
    def __init__(self, specializations: List[str]):
        options = [discord.SelectOption(label=spec, value=spec) for spec in specializations]
        super().__init__(placeholder="Choose your specialization...", min_values=1, max_values=1, options=options, custom_id="spec_select")

    async def callback(self, interaction: discord.Interaction):
        view: SpecializationChoiceView = self.view
        if not view:
             await interaction.response.send_message("Error: View not found.", ephemeral=True)
             return
             
        selected_spec = self.values[0]
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Attempt to set the specialization
            view.character.specialization = selected_spec
            save_success = await view.cog.character_system.save_character(view.character)
            if not save_success:
                 await interaction.followup.send("❌ Failed to save specialization. Please try again.", ephemeral=True)
                 view.character.specialization = None # Revert 
                 return
                 
            # Handle specialization roles if needed (logic might be in the main cog)
            # await view.cog._handle_specialization_roles(interaction.guild, interaction.user, view.character)
            
            await interaction.followup.send(
                f"✅ You have specialized in **{selected_spec}**!", 
                ephemeral=True
            )
            view.stop()
        except Exception as e:
            view.cog.logger.error(f"Error setting specialization via view for {interaction.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred while setting specialization.", ephemeral=True)
            view.stop()

# --- Commands Moved Here --- #

async def delete_character_impl(cog: 'CharacterCommands', interaction: discord.Interaction):
    """Implementation for the /delete command."""
    # Defer first
    try:
        await interaction.response.defer(ephemeral=True, thinking=True)
    except discord.errors.HTTPException as e:
        cog.logger.error(f"Error deferring interaction for delete_character: {e}", exc_info=True)
        return
        
    try:
        character = await cog.character_system.get_character(str(interaction.user.id))
        if not character:
            try:
                await interaction.followup.send("❌ You don't have a character to delete.", ephemeral=True)
            except discord.errors.HTTPException as http_err:
                 cog.logger.error(f"HTTP error sending delete no-char followup: {http_err}", exc_info=True)
            return

        view = DeleteConfirmationView(cog, interaction.user, character)
        # Send the confirmation view using followup
        try:
            await interaction.followup.send(
                f"🚨 **Warning!** Are you sure you want to delete your character **{character.name}**? This action cannot be undone.",
                view=view,
                ephemeral=True
            )
            # Store message reference for timeout handling in the view
            # Get the message object from the followup
            view.message = await interaction.original_response() 
        except discord.errors.HTTPException as http_err:
             cog.logger.error(f"HTTP error sending delete confirmation followup: {http_err}", exc_info=True)
             return # Stop if we can't send the confirmation

    except Exception as e:
        cog.logger.error(f"Error initiating delete character for {interaction.user.id}: {e}", exc_info=True)
        # Try to send error via followup
        try:
            await interaction.followup.send(
                "❌ An error occurred while trying to delete your character.",
                ephemeral=True
            )
        except discord.errors.HTTPException as http_err_fatal:
             cog.logger.error(f"HTTP error sending delete fatal error followup: {http_err_fatal}", exc_info=True)

class CharacterManagement(commands.Cog):
    def __init__(self, bot, character_system):
        self.bot = bot
        self.character_system = character_system
        self.item_registry = ItemRegistry()
        self.jutsu_system = JutsuSystem()
        
    async def _format_inventory(self, inventory: Any) -> str:
        """Format inventory items with their details from ItemRegistry."""
        if not inventory:
            return "Empty"
        
        formatted_items = []
        
        # Check if inventory is a dictionary (expected format)
        if isinstance(inventory, dict):
            for item_id, quantity in inventory.items():
                item_details = self.item_registry.get_item(item_id)
                if item_details:
                    name = item_details.get("name", "Unknown Item")
                    rarity = item_details.get("rarity", "Common")
                    formatted_items.append(f"{name} ({rarity}) x{quantity}")
                else:
                    formatted_items.append(f"Unknown Item ({item_id}) x{quantity}")
        # Handle if inventory is a list
        elif isinstance(inventory, list):
            # Count occurrences of each item
            item_counts = {}
            for item_id in inventory:
                if item_id in item_counts:
                    item_counts[item_id] += 1
                else:
                    item_counts[item_id] = 1
            
            # Format each unique item
            for item_id, quantity in item_counts.items():
                item_details = self.item_registry.get_item(item_id)
                if item_details:
                    name = item_details.get("name", "Unknown Item")
                    rarity = item_details.get("rarity", "Common")
                    formatted_items.append(f"{name} ({rarity}) x{quantity}")
                else:
                    formatted_items.append(f"Unknown Item ({item_id}) x{quantity}")
        else:
            # Unknown format
            formatted_items.append(f"Inventory data in unsupported format: {type(inventory).__name__}")
            logger.warning(f"Encountered inventory in unexpected format: {type(inventory).__name__}")
            
        return "\n".join(formatted_items)

    async def handle_inventory(self, interaction: discord.Interaction):
        """Handles displaying the character's inventory."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            logger.error(f"Error deferring interaction for inventory: {e}", exc_info=True)
            return

        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                try:
                    await interaction.followup.send("❌ You don't have a character yet!", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    logger.error(f"HTTP error sending inventory no-char followup: {http_err}", exc_info=True)
                return
                
            inventory_text = await self._format_inventory(character.inventory)
            
            # Get rarity color based on clan instead of directly from character
            rarity_color = discord.Color.default()
            clan_name = character.clan
            clan_data_system = getattr(self.bot.services, 'clan_data', None)
            if clan_data_system and clan_name:
                clan_info = clan_data_system.get_clan(clan_name)
                if clan_info and 'rarity' in clan_info:
                    rarity_color = get_rarity_color(clan_info['rarity'])
            
            embed = discord.Embed(
                title=f"🎒 {character.name}'s Inventory",
                description=inventory_text,
                color=rarity_color
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.errors.HTTPException as http_err:
                 logger.error(f"HTTP error sending inventory embed followup: {http_err}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error displaying inventory: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while retrieving your inventory.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                 logger.error(f"HTTP error sending inventory fatal error followup: {http_err_fatal}", exc_info=True)

    async def _format_jutsu_list(self, jutsu_ids: List[str]) -> str:
        """Format jutsu list with details from JutsuSystem."""
        if not jutsu_ids:
            return "No jutsu learned yet"
            
        formatted_jutsu = []
        for jutsu_id in jutsu_ids:
            jutsu_details = self.jutsu_system.get_jutsu(jutsu_id)
            if jutsu_details:
                name = jutsu_details.get("name", "Unknown Jutsu")
                rank = jutsu_details.get("rank", "Unknown")
                description = jutsu_details.get("description", "No description available")
                formatted_jutsu.append(f"**{name}** ({rank})\n{description}")
            else:
                formatted_jutsu.append(f"Unknown Jutsu ({jutsu_id})")
                
        return "\n\n".join(formatted_jutsu)

    async def handle_jutsu(self, interaction: discord.Interaction):
        """Handles displaying the character's known jutsu."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            logger.error(f"Error deferring interaction for known_jutsu: {e}", exc_info=True)
            return # Cannot followup if defer failed

        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                try:
                    await interaction.followup.send("❌ You don't have a character yet!", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    logger.error(f"HTTP error sending known_jutsu no-char followup: {http_err}", exc_info=True)
                return
                
            jutsu_text = await self._format_jutsu_list(character.jutsu)
            
            # Get rarity color based on clan instead of directly from character
            rarity_color = discord.Color.default()
            clan_name = character.clan
            clan_data_system = getattr(self.bot.services, 'clan_data', None)
            if clan_data_system and clan_name:
                clan_info = clan_data_system.get_clan(clan_name)
                if clan_info and 'rarity' in clan_info:
                    rarity_color = get_rarity_color(clan_info['rarity'])
            
            embed = discord.Embed(
                title=f"📜 {character.name}'s Known Jutsu",
                description=jutsu_text,
                color=rarity_color
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.errors.HTTPException as http_err:
                 logger.error(f"HTTP error sending known_jutsu embed followup: {http_err}", exc_info=True)
            
        except Exception as e:
            logger.error(f"Error displaying known jutsu: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while retrieving your known jutsu.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                 logger.error(f"HTTP error sending known_jutsu fatal error followup: {http_err_fatal}", exc_info=True)

    async def _format_status_effects(self, character: Any) -> str:
        """Format active status effects, buffs, and debuffs."""
        if not hasattr(character, 'status_effects') or not character.status_effects:
            return "No active status effects"
            
        formatted_effects = []
        for effect in character.status_effects:
            effect_type = effect.get("type", "Unknown")
            duration = effect.get("duration", "Unknown")
            description = effect.get("description", "No description available")
            
            # Add appropriate emoji based on effect type
            emoji = {
                "buff": "🟢",
                "debuff": "🔴",
                "status": "🟡"
            }.get(effect_type, "⚪")
            
            formatted_effects.append(f"{emoji} **{effect_type.title()}** ({duration})\n{description}")
                
        return "\n\n".join(formatted_effects)

    async def handle_status(self, interaction: discord.Interaction):
        """Handles displaying the character's active status effects."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            logger.error(f"Error deferring interaction for status: {e}", exc_info=True)
            return

        try:
            character = await self.character_system.get_character(str(interaction.user.id))
            if not character:
                try:
                    await interaction.followup.send("❌ You don't have a character yet!", ephemeral=True)
                except discord.errors.HTTPException as http_err:
                    logger.error(f"HTTP error sending status no-char followup: {http_err}", exc_info=True)
                return
                
            # Get rarity color based on clan
            rarity_color = discord.Color.default()
            clan_name = character.clan
            clan_data_system = getattr(self.bot.services, 'clan_data', None)
            if clan_data_system and clan_name:
                clan_info = clan_data_system.get_clan(clan_name)
                if clan_info and 'rarity' in clan_info:
                    rarity_color = get_rarity_color(clan_info['rarity'])

            embed = discord.Embed(
                title=f"🩺 {character.name}'s Status",
                color=rarity_color
            )
            embed.add_field(name="Health", value=f"{character.hp}/{character.max_hp} HP", inline=True)
            embed.add_field(name="Chakra", value=f"{character.chakra}/{character.max_chakra} CP", inline=True)
            embed.add_field(name="Stamina", value=f"{character.stamina}/{character.max_stamina} SP", inline=True)
            
            # Add status effects
            effects_text = await self._format_status_effects(character)
            embed.add_field(name="Active Effects", value=effects_text, inline=False)
            
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.errors.HTTPException as http_err:
                 logger.error(f"HTTP error sending status embed followup: {http_err}", exc_info=True)

        except Exception as e:
            logger.error(f"Error displaying status: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while retrieving your status.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                 logger.error(f"HTTP error sending status fatal error followup: {http_err_fatal}", exc_info=True)

async def specialize_impl(cog: 'CharacterCommands', interaction: discord.Interaction):
    """Implementation for the /specialize command using interactive view."""
    await interaction.response.defer(ephemeral=True)
    
    try:
        character = await cog.character_system.get_character(str(interaction.user.id))
        if not character:
            await interaction.followup.send("❌ You need a character first! Use `/create`.", ephemeral=True)
            return
            
        # Check if character meets prerequisite (e.g., level)
        # min_level_for_spec = 10 # Example
        # if character.level < min_level_for_spec:
        #     await interaction.followup.send(f"❌ You must be at least level {min_level_for_spec} to specialize.", ephemeral=True)
        #     return

        # Create and start the view
        # Import AVAILABLE_SPECIALIZATIONS from constants
        try:
             from ...core.constants import AVAILABLE_SPECIALIZATIONS
        except ImportError:
             cog.logger.error("Could not import AVAILABLE_SPECIALIZATIONS from core.constants.")
             await interaction.followup.send("❌ Internal error: Could not load available specializations list.", ephemeral=True)
             return
             
        view = SpecializeView(cog.management_handler, character, AVAILABLE_SPECIALIZATIONS)
        await view.start(interaction)
        
    except Exception as e:
        cog.logger.error(f"Error initiating specialization view for {interaction.user.id}: {e}", exc_info=True)
        await interaction.followup.send("❌ An unexpected error occurred while opening specialization menu.", ephemeral=True)

async def roles_impl(cog: 'CharacterCommands', interaction: discord.Interaction):
    """Implementation for the /roles command."""
    # Defer first
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.HTTPException as e:
        cog.logger.error(f"Error deferring interaction for roles: {e}", exc_info=True)
        return
        
    # Access ROLE_CONFIG (assuming it's accessible via cog or imported)
    role_config = getattr(cog, 'ROLE_CONFIG', {})
    
    embed = discord.Embed(title="🤖 Automatic Role Information", color=discord.Color.blurple())
    description = "This server automatically assigns roles based on your character progress:\n\n"
    
    level_roles = role_config.get("level_roles", {})
    clan_roles_enabled = role_config.get("clan_roles", False)
    spec_roles = role_config.get("specialization_roles", {})
    
    if level_roles:
        description += "**Level Roles:**\n"
        for level, role_name in sorted(level_roles.items()):
            description += f"• Level {level}: `{role_name}`\n"
        description += "\n"
        
    if clan_roles_enabled:
        description += "**Clan Roles:**\n"
        description += "• Roles are assigned based on your character's clan (e.g., `Uchiha`, `Hyuga`).\n\n"
    
    if spec_roles:
        description += "**Specialization Roles:**\n"
        for spec, role_name in spec_roles.items():
            description += f"• Specializing in {spec}: `{role_name}`\n"
        description += "\n"
        
    embed.description = description
    embed.set_footer(text="Roles are updated automatically when your character levels up, changes clan, or specializes.")
    try:
        await interaction.followup.send(embed=embed, ephemeral=True) 
    except discord.errors.HTTPException as http_err:
         cog.logger.error(f"HTTP error sending roles embed followup: {http_err}", exc_info=True) 

# --- NEW: Specialize View --- #
class SpecializeView(ui.View):
    def __init__(self, management_cog: 'CharacterManagement', character: Character, available_specializations: List[str]):
        super().__init__(timeout=180)
        self.management_cog = management_cog
        self.character = character
        self.message = None # Store the interaction message
        
        # Dynamically create buttons for each specialization
        for spec in available_specializations:
            self.add_item(SpecializationButton(spec, self))

    async def start(self, interaction: discord.Interaction):
        embed = self.create_embed()
        await interaction.followup.send(embed=embed, view=self, ephemeral=True)
        self.message = await interaction.original_response()
        
    def create_embed(self) -> discord.Embed:
        current_spec = self.character.specialization or "None"
        embed = discord.Embed(
            title="⭐ Choose Specialization",
            description=f"Your current specialization: **{current_spec}**\n\nChoose a path to focus your training:",
            color=discord.Color.purple()
        )
        # Maybe add descriptions of specializations later?
        return embed

    async def handle_selection(self, interaction: discord.Interaction, specialization: str):
        """Callback handler for button presses."""
        await interaction.response.defer(ephemeral=True)
        
        if self.character.specialization == specialization:
            await interaction.followup.send(f"✅ You are already specialized in **{specialization}**.", ephemeral=True)
            return
            
        try:
            self.character.specialization = specialization
            save_success = await self.management_cog.character_system.save_character(self.character)
            
            if not save_success:
                 # Revert if save failed
                 self.character.specialization = None # Or revert to previous if needed
                 await interaction.followup.send("❌ Failed to save specialization. Please try again.", ephemeral=True)
                 return
                 
            # Role handling (if implemented)
            # await self.management_cog._handle_specialization_roles(interaction.guild, interaction.user, self.character)
            
            await interaction.followup.send(f"✅ You have specialized in **{specialization}**!", ephemeral=True)
            self.stop() # Stop the view after successful selection
            # Update original message if possible
            if self.message:
                 try: await self.message.edit(content=f"Specialization set to {specialization}.", view=None)
                 except discord.NotFound: pass
                 except discord.HTTPException: pass
                 
        except Exception as e:
            self.management_cog.logger.error(f"Error setting specialization via view for {interaction.user.id}: {e}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred while setting specialization.", ephemeral=True)
            self.stop()

    async def on_timeout(self):
        if self.message:
            try: await self.message.edit(content="Specialization choice timed out.", view=None)
            except discord.NotFound: pass
            except discord.HTTPException: pass
        self.stop()

class SpecializationButton(ui.Button):
    def __init__(self, specialization: str, parent_view: SpecializeView):
        super().__init__(
            label=specialization,
            style=discord.ButtonStyle.primary,
            custom_id=f"spec_btn_{specialization.lower()}"
        )
        self.specialization = specialization
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.handle_selection(interaction, self.specialization)

# --- End Specialize View --- #

def get_rarity_color(rarity: str) -> int:
    # Implementation of get_rarity_color function
    # This is a placeholder and should be replaced with the actual implementation
    return discord.Color.default() 