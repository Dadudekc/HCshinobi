"""
Handles character progression viewing commands (achievements, titles).
Part of the CharacterCommands cog refactor.
"""
import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, List, TYPE_CHECKING
import logging

# Relative imports for core systems and utilities
from ...core.character import Character

# Type hint for the main cog
if TYPE_CHECKING:
    from .character_commands import CharacterCommands

logger = logging.getLogger(__name__)

# --- Title Equip View & Select --- #
class TitleEquipView(ui.View):
    def __init__(self, character_commands_cog: 'CharacterCommands', character: Character, options: List[discord.SelectOption]):
        super().__init__(timeout=180)
        self.character_commands_cog = character_commands_cog
        self.character = character
        
        # Add the select menu to the view
        self.add_item(TitleSelect(options))

class TitleSelect(discord.ui.Select):
    """Select menu for equipping titles."""
    def __init__(self, character_id: str, options: List[discord.SelectOption]):
        self.character_id = character_id
        # Dynamically set placeholder text
        placeholder = "Select a title to equip" if options else "No titles available"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id="title_equip_select")

    async def callback(self, interaction: discord.Interaction):
        # Get the view to access character and cog
        view: TitleEquipView = self.view
        if not view:
            await interaction.response.send_message("Error: Could not find the parent view.", ephemeral=True)
            return
            
        selected_title_key = self.values[0]
        character = view.character
        cog = view.character_commands_cog
        
        if not character:
            await interaction.response.send_message("Error: Character data not found.", ephemeral=True)
            return
            
        # Check if the selected title is different from the currently equipped one
        # Use getattr for safety in case equipped_title doesn't exist yet
        current_equipped = getattr(character, 'equipped_title', None)
        if current_equipped == selected_title_key:
            await interaction.response.send_message(f"➡️ Title '{selected_title_key}' is already equipped.", ephemeral=True)
            return

        # Update the character's equipped title
        character.equipped_title = selected_title_key
        save_success = await cog.character_system.save_character(character)

        if save_success:
            # Re-fetch titles data for display name
            title_data = cog.progression_engine.titles_data.get(selected_title_key) if cog.progression_engine else None
            display_name = title_data.get('name', selected_title_key) if title_data else selected_title_key
            
            await interaction.response.send_message(f"✅ Title **{display_name}** equipped!", ephemeral=True)
            cog.logger.info(f"User {interaction.user.id} equipped title: {selected_title_key}")
            
            # Optionally: Refresh the original /titles message to show the new equipped state
            try:
                new_embed = discord.Embed(title=f"🎖️ {character.name}'s Titles", color=discord.Color.dark_gold())
                earned_titles = character.titles
                equipped_title = character.equipped_title
                all_titles_data = cog.progression_engine.titles_data if cog.progression_engine else {}
                title_lines = []
                for title_key in sorted(list(earned_titles), key=lambda t: t != equipped_title):
                    t_data = all_titles_data.get(title_key)
                    if t_data:
                         name = t_data.get('name', title_key)
                         desc = t_data.get('description', 'No description.')
                         bonus = t_data.get('bonus_description', '')
                         prefix = "➡️ " if title_key == equipped_title else "• "
                         bonus_txt = f" ({bonus})" if bonus else ""
                         title_lines.append(f"{prefix}**{name}**: {desc}{bonus_txt}")
                    else:
                         prefix = "➡️ " if title_key == equipped_title else "• "
                         title_lines.append(f"{prefix}**{title_key}** (Data missing)")
                new_embed.description = "\n".join(title_lines)
                await interaction.edit_original_response(embed=new_embed, view=view) # Keep the view
            except Exception as e:
                cog.logger.error(f"Failed to refresh /titles message after equip: {e}")
                
        else:
            await interaction.response.send_message("❌ Failed to save equipped title.", ephemeral=True)
            # Revert the change locally if save failed?
            character.equipped_title = current_equipped # Revert to previous

# --- Commands Moved Here --- #

async def view_achievements_impl(cog: 'CharacterCommands', interaction: discord.Interaction, user: Optional[discord.User] = None):
    """Implementation for the /achievements command."""
    target_user = user or interaction.user
    target_user_id = str(target_user.id)
    is_self = target_user.id == interaction.user.id

    try:
        character = await cog.character_system.get_character(target_user_id)
        if not character:
            message = "❌ You need to create a character first! Use `/create`." if is_self else f"❌ User {target_user.display_name} does not have a character."
            await interaction.response.send_message(message, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🏆 {character.name}'s Achievements",
            color=discord.Color.gold()
        )
        if hasattr(target_user, 'display_avatar') and target_user.display_avatar:
            embed.set_thumbnail(url=target_user.display_avatar.url)

        # Ensure progression engine is available
        if not cog.progression_engine:
             await interaction.response.send_message("❌ Achievement data service is currently unavailable.", ephemeral=True)
             cog.logger.error("ProgressionEngine not available for /achievements command.")
             return
             
        if not character.achievements:
            embed.description = "No achievements earned yet." if is_self else f"{target_user.display_name} has not earned any achievements yet."
        else:
            earned_achievements = []
            for ach_key in sorted(list(character.achievements)):
                ach_data = cog.progression_engine.achievements_data.get(ach_key)
                if ach_data:
                    name = ach_data.get('name', ach_key)
                    description = ach_data.get('description', 'No description available.')
                    exp_reward = ach_data.get('exp_reward', 0)
                    entry = f"**{name}**" 
                    if description: entry += f": {description}"
                    if exp_reward > 0: entry += f" (+{exp_reward} EXP)"
                    earned_achievements.append(f"• {entry}")
                else:
                    earned_achievements.append(f"• {ach_key} (Data missing)")
            
            if not earned_achievements:
                 embed.description = "No achievements earned yet." if is_self else f"{target_user.display_name} has not earned any achievements yet."
            else:
                embed.description = "\n".join(earned_achievements)
                
        await interaction.response.send_message(embed=embed, ephemeral=not is_self)

    except Exception as e:
        cog.logger.error(f"Error viewing achievements for {target_user_id}: {e}", exc_info=True)
        message = "❌ An error occurred retrieving your achievements." if is_self else "❌ An error occurred retrieving achievements for that user."
        await interaction.response.send_message(message, ephemeral=True)

async def view_titles_impl(cog: 'CharacterCommands', interaction: discord.Interaction, user: Optional[discord.User] = None):
    """Implementation for the /titles command."""
    target_user = user or interaction.user
    target_user_id = str(target_user.id)
    is_self = target_user.id == interaction.user.id

    try:
        character = await cog.character_system.get_character(target_user_id)
        if not character:
            message = "❌ You need a character first (`/create`)." if is_self else f"❌ User {target_user.display_name} has no character."
            await interaction.response.send_message(message, ephemeral=True)
            return

        # Ensure progression engine is available
        if not cog.progression_engine:
             await interaction.response.send_message("❌ Title data service is currently unavailable.", ephemeral=True)
             cog.logger.error("ProgressionEngine not available for /titles command.")
             return
             
        embed = discord.Embed(
            title=f"🎖️ {character.name}'s Titles",
            color=discord.Color.dark_gold()
        )
        if hasattr(target_user, 'display_avatar') and target_user.display_avatar:
            embed.set_thumbnail(url=target_user.display_avatar.url)

        earned_titles = character.titles
        equipped_title = getattr(character, 'equipped_title', None) # Use getattr for safety
        all_titles_data = cog.progression_engine.titles_data

        if not earned_titles:
            embed.description = "No titles earned yet."
        else:
            title_lines = []
            select_options = [] # For the dropdown

            # Sort titles, maybe put equipped first?
            sorted_titles = sorted(list(earned_titles), key=lambda t: t != equipped_title) 

            for title_key in sorted_titles:
                title_data = all_titles_data.get(title_key)
                if title_data:
                    name = title_data.get('name', title_key)
                    description = title_data.get('description', 'No description available.')
                    bonus_desc = title_data.get('bonus_description', '')
                    prefix = "➡️ " if title_key == equipped_title else "• "
                    bonus_text = f" ({bonus_desc})" if bonus_desc else ""
                    title_lines.append(f"{prefix}**{name}**: {description}{bonus_text}")
                    
                    if is_self:
                        select_options.append(discord.SelectOption(
                            label=name,
                            description=bonus_desc[:100] or description[:100],
                            value=title_key,
                            default= (title_key == equipped_title)
                        ))
                else:
                    prefix = "➡️ " if title_key == equipped_title else "• "
                    title_lines.append(f"{prefix}**{title_key}** (Data missing)")
                    if is_self:
                        select_options.append(discord.SelectOption(
                            label=title_key,
                            description="(Data missing)",
                            value=title_key,
                            default=(title_key == equipped_title)
                        ))
                        
            embed.description = "\n".join(title_lines)

        # Add view with dropdown only if it's the user viewing their own titles and they have titles
        view = None
        if is_self and earned_titles and select_options:
            # Limit options to 25 for Discord UI
            view = TitleEquipView(cog, character, select_options[:25])

        await interaction.response.send_message(embed=embed, view=view, ephemeral=not is_self)

    except Exception as e:
        cog.logger.error(f"Error viewing titles for {target_user_id}: {e}", exc_info=True)
        message = "❌ An error occurred retrieving your titles." if is_self else "❌ An error occurred retrieving titles for that user."
        await interaction.response.send_message(message, ephemeral=True) 