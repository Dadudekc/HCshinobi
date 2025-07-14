"""
Character Commands - Enhanced with Jutsu System Integration
Handles character creation, management, and jutsu progression.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any
import json
import os
import logging
from datetime import datetime

from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.unified_jutsu_system import UnifiedJutsuSystem
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.utils.embeds import create_success_embed, create_error_embed, create_info_embed

async def handle_command_error(interaction: discord.Interaction, error: Exception, command_name: str):
    """Helper function to handle command errors consistently."""
    import traceback
    tb = traceback.format_exc()
    logging.error(f"❌ ERROR in /{command_name} command:")
    logging.error(f"   User: {interaction.user.name} ({interaction.user.id})")
    logging.error(f"   Error: {error}")
    logging.error(f"   Traceback:\n{tb}")
    
    error_msg = f"❌ **Error in /{command_name}:**\n```{str(error)}```\n**Error ID:** `{id(error)}`"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)
    except Exception as e2:
        logging.error(f"❌ Failed to send error message: {e2}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An error occurred while using /{command_name}. Please try again.", ephemeral=True)
        except:
            pass

class CharacterCommands(commands.Cog):
    """Enhanced character commands with jutsu system integration."""
    
    def __init__(self, bot):
        self.bot = bot
        self.character_system = CharacterSystem()
        self.jutsu_system = UnifiedJutsuSystem()
        self.clan_engine = ClanAssignmentEngine()

    async def _safe_response(self, interaction: discord.Interaction, content=None, embed=None, ephemeral=False):
        """Safely respond to an interaction, handling expired interactions gracefully."""
        try:
            if interaction.response.is_done():
                # Interaction already responded to, use followup
                await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral)
            else:
                # First response, use response.send_message
                await interaction.response.send_message(content=content, embed=embed, ephemeral=ephemeral)
        except discord.errors.NotFound:
            # Interaction expired (error code 10062)
            logging.warning(f"Interaction expired for user {interaction.user.id} in {interaction.command.name}")
            # Try to send a DM as fallback
            try:
                if embed:
                    await interaction.user.send(embed=embed)
                elif content:
                    await interaction.user.send(content)
            except:
                logging.error(f"Failed to send DM fallback to user {interaction.user.id}")
        except Exception as e:
            logging.error(f"Error responding to interaction: {e}")

    @app_commands.command(name="create", description="Create a new character")
    @app_commands.describe(
        name="Your character's name",
        clan="Your character's clan (optional - will be randomly assigned if not specified)"
    )
    async def create_character(self, interaction: discord.Interaction, name: str, clan: Optional[str] = None):
        """Create a new character with optional clan assignment."""
        try:
            logging.info(f"🔧 /create command called by {interaction.user.name} ({interaction.user.id}) with name='{name}', clan='{clan}'")
            
            user_id = interaction.user.id
            
            # Check if character already exists
            existing_character = await self.character_system.get_character(user_id)
            if existing_character:
                logging.info(f"⚠️ User {interaction.user.name} already has character: {existing_character.name}")
                await self._safe_response(
                    interaction,
                    embed=create_error_embed("You already have a character! Use `/delete_character` to remove it first."),
                    ephemeral=True
                )
                return
            
            # Assign clan if not specified
            if not clan:
                logging.info(f"🔧 Assigning random clan for {interaction.user.name}")
                clan_result = self.clan_engine.assign_clan(str(user_id))
                clan = clan_result["clan"]
                clan_rarity = clan_result.get("rarity", "Common")
                logging.info(f"✅ Assigned clan: {clan} ({clan_rarity})")
            else:
                clan_rarity = "Custom"
                logging.info(f"✅ Using custom clan: {clan}")
            
            # Create character
            logging.info(f"🔧 Creating character for {interaction.user.name}...")
            character = await self.character_system.create_character(user_id, name, clan)
            logging.info(f"✅ Character created: {character.name}")
            
            # Initialize with basic jutsu
            character.jutsu = ["Basic Attack"]  # Start with basic attack
            logging.info(f"✅ Initialized with Basic Attack jutsu")
            
            # Save the updated character
            await self.character_system.save_character(character)
            logging.info(f"✅ Character saved successfully")
            
            # Create success embed
            embed = create_success_embed(f"Character **{name}** created successfully!")
            embed.add_field(name="Clan", value=f"{clan} ({clan_rarity})", inline=True)
            embed.add_field(name="Level", value="1", inline=True)
            embed.add_field(name="Starting Jutsu", value="Basic Attack", inline=True)
            
            await self._safe_response(interaction, embed=embed)
            logging.info(f"✅ /create command completed successfully for {interaction.user.name}")
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logging.error(f"❌ ERROR in /create command:")
            logging.error(f"   User: {interaction.user.name} ({interaction.user.id})")
            logging.error(f"   Name: {name}, Clan: {clan}")
            logging.error(f"   Error: {e}")
            logging.error(f"   Traceback:\n{tb}")
            
            error_msg = f"❌ **Error creating character:**\n```{str(e)}```\n**Error ID:** `{id(e)}`"
            try:
                await self._safe_response(interaction, content=error_msg, ephemeral=True)
            except Exception as e2:
                logging.error(f"❌ Failed to send error message: {e2}")

    @app_commands.command(name="profile", description="View your character profile")
    async def view_profile(self, interaction: discord.Interaction):
        """View detailed character profile with jutsu information."""
        try:
            logging.info(f"🔧 /profile command called by {interaction.user.name} ({interaction.user.id})")
            
            user_id = interaction.user.id
            character = await self.character_system.get_character(user_id)
            
            if not character:
                logging.info(f"⚠️ User {interaction.user.name} has no character")
                await self._safe_response(
                    interaction,
                    embed=create_error_embed("You don't have a character! Use `/create` to create one."),
                    ephemeral=True
                )
                return
            
            logging.info(f"✅ Found character: {character.name} (Level {character.level})")
            
            # Character data is already loaded in the character object
            
            # Create profile embed
            embed = discord.Embed(
                title=f"🥷 {character.name}'s Profile",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            # Basic info
            embed.add_field(name="Clan", value=character.clan or "None", inline=True)
            embed.add_field(name="Level", value=str(character.level), inline=True)
            embed.add_field(name="Rank", value=character.rank, inline=True)
            
            # Stats
            embed.add_field(name="HP", value=f"{character.hp}/{character.max_hp}", inline=True)
            embed.add_field(name="Chakra", value=f"{character.chakra}/{character.max_chakra}", inline=True)
            embed.add_field(name="Stamina", value=f"{character.stamina}/{character.max_stamina}", inline=True)
            
            # Combat stats
            embed.add_field(name="Strength", value=str(character.strength), inline=True)
            embed.add_field(name="Defense", value=str(character.defense), inline=True)
            embed.add_field(name="Speed", value=str(character.speed), inline=True)
            
            # Ninja arts
            embed.add_field(name="Ninjutsu", value=str(character.ninjutsu), inline=True)
            embed.add_field(name="Genjutsu", value=str(character.genjutsu), inline=True)
            embed.add_field(name="Taijutsu", value=str(character.taijutsu), inline=True)
            
            # Jutsu count
            jutsu_count = len(character.jutsu)
            embed.add_field(name="Jutsu Known", value=str(jutsu_count), inline=True)
            embed.add_field(name="Experience", value=str(character.exp), inline=True)
            embed.add_field(name="Ryo", value="0", inline=True)  # Ryo not implemented yet
            
            # Battle record
            embed.add_field(name="Wins", value=str(character.wins), inline=True)
            embed.add_field(name="Losses", value=str(character.losses), inline=True)
            embed.add_field(name="Draws", value=str(character.draws), inline=True)
            
            embed.set_footer(text=f"Character ID: {character.id}")
            
            await self._safe_response(interaction, embed=embed)
            logging.info(f"✅ /profile command completed successfully for {interaction.user.name}")
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logging.error(f"❌ ERROR in /profile command:")
            logging.error(f"   User: {interaction.user.name} ({interaction.user.id})")
            logging.error(f"   Error: {e}")
            logging.error(f"   Traceback:\n{tb}")
            
            error_msg = f"❌ **Error viewing profile:**\n```{str(e)}```\n**Error ID:** `{id(e)}`"
            try:
                await self._safe_response(interaction, content=error_msg, ephemeral=True)
            except Exception as e2:
                logging.error(f"❌ Failed to send error message: {e2}")

    @app_commands.command(name="jutsu", description="View your learned jutsu and available jutsu")
    async def view_jutsu(self, interaction: discord.Interaction):
        """View character's jutsu with detailed information."""
        try:
            logging.info(f"🔧 /jutsu command called by {interaction.user.name} ({interaction.user.id})")
            
            user_id = interaction.user.id
            character = await self.character_system.get_character(user_id)
            
            if not character:
                logging.info(f"⚠️ User {interaction.user.name} has no character")
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have a character! Use `/create` to create one."),
                    ephemeral=True
                )
                return
            
            logging.info(f"✅ Found character: {character.name} (Level {character.level})")
            
            character_data = self.character_system._character_to_dict(character)
            learned_jutsu = character_data.get("jutsu", [])
            available_jutsu = self.jutsu_system.get_available_jutsu(character_data)
            unlockable_jutsu = self.jutsu_system.get_unlockable_jutsu(character_data)
            
            logging.info(f"📊 Jutsu stats for {character.name}: Learned={len(learned_jutsu)}, Available={len(available_jutsu)}, Unlockable={len(unlockable_jutsu)}")
            
            # Create jutsu embed
            embed = discord.Embed(
                title=f"🥷 {character.name}'s Jutsu",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            # Learned jutsu
            if learned_jutsu:
                jutsu_info = []
                for jutsu_name in learned_jutsu:
                    jutsu_data = self.jutsu_system.get_jutsu_info(jutsu_name)
                    if jutsu_data:
                        element_emoji = self._get_element_emoji(jutsu_data["element"])
                        rarity_color = self._get_rarity_color(jutsu_data["rarity"])
                        jutsu_info.append(f"{element_emoji} **{jutsu_name}** ({jutsu_data['rarity']}) - {jutsu_data['damage']} damage")
                
                embed.add_field(
                    name=f"📚 Learned Jutsu ({len(learned_jutsu)})",
                    value="\n".join(jutsu_info) if jutsu_info else "None",
                    inline=False
                )
            else:
                embed.add_field(name="📚 Learned Jutsu", value="None", inline=False)
            
            # Available but not learned jutsu
            available_not_learned = [jutsu for jutsu in available_jutsu if jutsu not in learned_jutsu]
            if available_not_learned:
                embed.add_field(
                    name=f"🔓 Available to Learn ({len(available_not_learned)})",
                    value="\n".join([f"• {jutsu}" for jutsu in available_not_learned[:5]]),
                    inline=False
                )
                if len(available_not_learned) > 5:
                    embed.add_field(name="", value=f"... and {len(available_not_learned) - 5} more", inline=False)
            
            # Unlockable jutsu (close to unlocking)
            if unlockable_jutsu:
                embed.add_field(
                    name=f"🔒 Close to Unlocking ({len(unlockable_jutsu)})",
                    value="\n".join([f"• {jutsu['name']} - Missing: {', '.join(jutsu['missing_requirements'][:2])}" for jutsu in unlockable_jutsu[:3]]),
                    inline=False
                )
            
            embed.set_footer(text="Use /unlock_jutsu to learn new jutsu")
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"✅ /jutsu command completed successfully for {interaction.user.name}")
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logging.error(f"❌ ERROR in /jutsu command:")
            logging.error(f"   User: {interaction.user.name} ({interaction.user.id})")
            logging.error(f"   Error: {e}")
            logging.error(f"   Traceback:\n{tb}")
            
            error_msg = f"❌ **Error viewing jutsu:**\n```{str(e)}```\n**Error ID:** `{id(e)}`"
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(error_msg, ephemeral=True)
                else:
                    await interaction.response.send_message(error_msg, ephemeral=True)
            except Exception as e2:
                logging.error(f"❌ Failed to send error message: {e2}")
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("❌ An error occurred while viewing your jutsu. Please try again.", ephemeral=True)
                except:
                    pass

    @app_commands.command(name="unlock_jutsu", description="Unlock a new jutsu if you meet the requirements")
    @app_commands.describe(jutsu_name="The name of the jutsu to unlock")
    async def unlock_jutsu(self, interaction: discord.Interaction, jutsu_name: str):
        """Unlock a jutsu if the character meets all requirements."""
        try:
            logging.info(f"🔧 /unlock_jutsu command called by {interaction.user.name} ({interaction.user.id}) for jutsu: {jutsu_name}")
            
            user_id = interaction.user.id
            character = await self.character_system.get_character(user_id)
            
            if not character:
                logging.info(f"⚠️ User {interaction.user.name} has no character")
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have a character! Use `/create` to create one."),
                    ephemeral=True
                )
                return
            
            logging.info(f"✅ Found character: {character.name} (Level {character.level})")
            
            character_data = self.character_system._character_to_dict(character)
            
            # Check if already learned
            if jutsu_name in character_data.get("jutsu", []):
                logging.info(f"⚠️ User {interaction.user.name} already knows {jutsu_name}")
                await interaction.response.send_message(
                    embed=create_error_embed(f"You already know **{jutsu_name}**!"),
                    ephemeral=True
                )
                return
            
            # Try to unlock the jutsu
            logging.info(f"🔧 Attempting to unlock {jutsu_name} for {character.name}...")
            success = self.jutsu_system.unlock_jutsu_for_character(character_data, jutsu_name)
            
            if success:
                # Save updated character
                character.jutsu = character_data["jutsu"]
                self.character_system._save_character_to_file(character)
                logging.info(f"✅ Successfully unlocked {jutsu_name} for {character.name}")
                
                # Get jutsu info for embed
                jutsu_info = self.jutsu_system.get_jutsu_info(jutsu_name)
                
                embed = create_success_embed(f"🎉 Successfully learned **{jutsu_name}**!")
                if jutsu_info:
                    element_emoji = self._get_element_emoji(jutsu_info["element"])
                    embed.add_field(name="Element", value=f"{element_emoji} {jutsu_info['element'].title()}", inline=True)
                    embed.add_field(name="Damage", value=str(jutsu_info["damage"]), inline=True)
                    embed.add_field(name="Chakra Cost", value=str(jutsu_info["chakra_cost"]), inline=True)
                    embed.add_field(name="Rarity", value=jutsu_info["rarity"], inline=True)
                    embed.add_field(name="Description", value=jutsu_info["description"], inline=False)
                
                await interaction.response.send_message(embed=embed)
                logging.info(f"✅ /unlock_jutsu command completed successfully for {interaction.user.name}")
            else:
                # Show what's missing
                jutsu_info = self.jutsu_system.get_jutsu_info(jutsu_name)
                if not jutsu_info:
                    logging.warning(f"❌ Invalid jutsu name: {jutsu_name}")
                    await interaction.response.send_message(
                        embed=create_error_embed(f"**{jutsu_name}** is not a valid jutsu!"),
                        ephemeral=True
                    )
                    return
                
                missing_requirements = []
                
                # Level requirement
                if character.level < jutsu_info["level_requirement"]:
                    missing_requirements.append(f"Level {jutsu_info['level_requirement']}")
                
                # Stat requirements
                for stat, required_value in jutsu_info["stat_requirements"].items():
                    current_value = character_data.get(stat, 0)
                    if current_value < required_value:
                        missing_requirements.append(f"{stat.title()} {required_value}")
                
                # Achievement requirements
                for achievement in jutsu_info["achievement_requirements"]:
                    if achievement not in character_data.get("achievements", []):
                        missing_requirements.append(f"Achievement: {achievement}")
                
                logging.info(f"⚠️ {character.name} cannot learn {jutsu_name}. Missing: {missing_requirements}")
                
                embed = create_error_embed(f"Cannot learn **{jutsu_name}**!")
                embed.add_field(
                    name="Missing Requirements",
                    value="\n".join([f"• {req}" for req in missing_requirements]),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await handle_command_error(interaction, e, "unlock_jutsu")

    @app_commands.command(name="jutsu_info", description="Get detailed information about a jutsu")
    @app_commands.describe(jutsu_name="The name of the jutsu to get info about")
    async def jutsu_info(self, interaction: discord.Interaction, jutsu_name: str):
        """Get detailed information about a specific jutsu."""
        try:
            logging.info(f"🔧 /jutsu_info command called by {interaction.user.name} ({interaction.user.id}) for jutsu: {jutsu_name}")
            
            jutsu_data = self.jutsu_system.get_jutsu_info(jutsu_name)
            
            if not jutsu_data:
                logging.warning(f"❌ Invalid jutsu name requested: {jutsu_name}")
                await interaction.response.send_message(
                    embed=create_error_embed(f"**{jutsu_name}** is not a valid jutsu!"),
                    ephemeral=True
                )
                return
            
            logging.info(f"✅ Found jutsu info for: {jutsu_name}")
            
            # Create jutsu info embed
            embed = discord.Embed(
                title=f"🥷 {jutsu_name}",
                description=jutsu_data["description"],
                color=self._get_rarity_color(jutsu_data["rarity"]),
                timestamp=datetime.utcnow()
            )
            
            element_emoji = self._get_element_emoji(jutsu_data["element"])
            embed.add_field(name="Element", value=f"{element_emoji} {jutsu_data['element'].title()}", inline=True)
            embed.add_field(name="Damage", value=str(jutsu_data["damage"]), inline=True)
            embed.add_field(name="Chakra Cost", value=str(jutsu_data["chakra_cost"]), inline=True)
            embed.add_field(name="Accuracy", value=f"{jutsu_data['accuracy']}%", inline=True)
            embed.add_field(name="Range", value=jutsu_data["range"].title(), inline=True)
            embed.add_field(name="Rarity", value=jutsu_data["rarity"], inline=True)
            embed.add_field(name="Level Requirement", value=str(jutsu_data["level_requirement"]), inline=True)
            
            # Stat requirements
            if jutsu_data["stat_requirements"]:
                stat_reqs = "\n".join([f"• {stat.title()}: {value}" for stat, value in jutsu_data["stat_requirements"].items()])
                embed.add_field(name="Stat Requirements", value=stat_reqs, inline=True)
            
            # Achievement requirements
            if jutsu_data["achievement_requirements"]:
                achievement_reqs = "\n".join([f"• {achievement}" for achievement in jutsu_data["achievement_requirements"]])
                embed.add_field(name="Achievement Requirements", value=achievement_reqs, inline=True)
            
            # Special effects
            if jutsu_data["special_effects"]:
                effects = "\n".join([f"• {effect.replace('_', ' ').title()}" for effect in jutsu_data["special_effects"]])
                embed.add_field(name="Special Effects", value=effects, inline=False)
            
            embed.set_footer(text=f"Rarity: {jutsu_data['rarity']}")
            
            await interaction.response.send_message(embed=embed)
            logging.info(f"✅ /jutsu_info command completed successfully for {interaction.user.name}")
            
        except Exception as e:
            await handle_command_error(interaction, e, "jutsu_info")

    @app_commands.command(name="progression", description="View your character's progression and available jutsu")
    async def view_progression(self, interaction: discord.Interaction):
        """View detailed character progression information."""
        try:
            logging.info(f"🔧 /progression command called by {interaction.user.name} ({interaction.user.id})")
            
            user_id = interaction.user.id
            character = await self.character_system.get_character(user_id)
            
            if not character:
                logging.info(f"⚠️ User {interaction.user.name} has no character")
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have a character! Use `/create` to create one."),
                    ephemeral=True
                )
                return
            
            logging.info(f"✅ Found character: {character.name} (Level {character.level})")
            
            character_data = self.character_system._character_to_dict(character)
            
            # Get progression info
            progression_info = self.bot.services.progression_engine.get_progression_info(character_data)
            
            # Create progression embed
            embed = discord.Embed(
                title=f"📈 {character.name}'s Progression",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            # Level and rank info
            embed.add_field(
                name="🎯 Level & Rank",
                value=f"**Level:** {progression_info['current_level']}\n"
                      f"**Rank:** {progression_info['rank']}\n"
                      f"**Total EXP:** {progression_info['current_exp']:,}",
                inline=True
            )
            
            # Experience progress
            progress_bar = self._create_progress_bar(progression_info['progress_percentage'])
            embed.add_field(
                name="📊 Experience Progress",
                value=f"**Progress:** {progression_info['exp_progress']}/{progression_info['exp_needed']}\n"
                      f"**{progress_bar}** {progression_info['progress_percentage']:.1f}%\n"
                      f"**Next Level:** {progression_info['next_level_exp']:,} EXP",
                inline=True
            )
            
            # Jutsu summary
            embed.add_field(
                name="🥷 Jutsu Summary",
                value=f"**Learned:** {progression_info['jutsu_learned']}\n"
                      f"**Available:** {progression_info['jutsu_available']}\n"
                      f"**Can Learn:** {progression_info['jutsu_unlockable']}",
                inline=True
            )
            
            # Show jutsu that can be learned
            available_jutsu = self.jutsu_system.get_available_jutsu(character_data)
            learned_jutsu = character_data.get("jutsu", [])
            unlockable_jutsu = [jutsu for jutsu in available_jutsu if jutsu not in learned_jutsu]
            
            if unlockable_jutsu:
                jutsu_list = []
                for jutsu_name in unlockable_jutsu[:5]:  # Show first 5
                    jutsu_info = self.jutsu_system.get_jutsu_info(jutsu_name)
                    if jutsu_info:
                        element_emoji = self._get_element_emoji(jutsu_info["element"])
                        jutsu_list.append(f"{element_emoji} **{jutsu_name}** (Level {jutsu_info['level_requirement']})")
                
                embed.add_field(
                    name=f"🔓 Available to Learn ({len(unlockable_jutsu)})",
                    value="\n".join(jutsu_list),
                    inline=False
                )
                
                if len(unlockable_jutsu) > 5:
                    embed.add_field(name="", value=f"... and {len(unlockable_jutsu) - 5} more jutsu", inline=False)
            
            # Level rewards preview
            next_level = progression_info['current_level'] + 1
            try:
                level_rewards = self.bot.services.progression_engine.get_level_rewards(next_level)
                
                embed.add_field(
                    name=f"🎁 Level {next_level} Rewards",
                    value=f"**HP Bonus:** +{level_rewards['hp_bonus']}\n"
                          f"**Chakra Bonus:** +{level_rewards['chakra_bonus']}\n"
                          f"**Rank:** {level_rewards['rank']}\n"
                          f"**Jutsu Unlocks:** {len(level_rewards['unlockable_jutsu'])}",
                    inline=True
                )
            except Exception as e:
                # Fallback if progression engine is not available
                embed.add_field(
                    name=f"🎁 Level {next_level} Rewards",
                    value=f"**HP Bonus:** +{next_level * 15}\n"
                          f"**Chakra Bonus:** +{next_level * 10}\n"
                          f"**Rank:** {self._calculate_rank(next_level)}\n"
                          f"**Jutsu Unlocks:** Check with /jutsu",
                    inline=True
                )
            
            embed.set_footer(text="Use /unlock_jutsu to learn new jutsu")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await handle_command_error(interaction, e, "progression")

    def _create_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Create a visual progress bar."""
        filled = int((percentage / 100) * length)
        empty = length - filled
        return "█" * filled + "░" * empty

    @app_commands.command(name="auto_unlock_jutsu", description="Automatically unlock all jutsu you can learn")
    async def auto_unlock_jutsu(self, interaction: discord.Interaction):
        """Automatically unlock all jutsu that the character meets requirements for."""
        try:
            logging.info(f"🔧 /auto_unlock_jutsu command called by {interaction.user.name} ({interaction.user.id})")
            
            user_id = interaction.user.id
            character = await self.character_system.get_character(user_id)
            
            if not character:
                logging.info(f"⚠️ User {interaction.user.name} has no character")
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have a character! Use `/create` to create one."),
                    ephemeral=True
                )
                return
            
            logging.info(f"✅ Found character: {character.name} (Level {character.level})")
            
            character_data = self.character_system._character_to_dict(character)
            learned_jutsu = character_data.get("jutsu", [])
            available_jutsu = self.jutsu_system.get_available_jutsu(character_data)
            
            # Find jutsu that can be learned
            unlockable_jutsu = [jutsu for jutsu in available_jutsu if jutsu not in learned_jutsu]
            
            if not unlockable_jutsu:
                await interaction.response.send_message(
                    embed=create_info_embed("No new jutsu available to learn!"),
                    ephemeral=True
                )
                return
            
            # Unlock all available jutsu
            unlocked_count = 0
            unlocked_list = []
            
            for jutsu_name in unlockable_jutsu:
                success = self.jutsu_system.unlock_jutsu_for_character(character_data, jutsu_name)
                if success:
                    unlocked_count += 1
                    unlocked_list.append(jutsu_name)
            
            if unlocked_count > 0:
                # Save updated character
                character.jutsu = character_data["jutsu"]
                self.character_system._save_character_to_file(character)
                
                embed = create_success_embed(f"🎉 Successfully unlocked {unlocked_count} jutsu!")
                
                # Show unlocked jutsu
                jutsu_details = []
                for jutsu_name in unlocked_list[:10]:  # Show first 10
                    jutsu_info = self.jutsu_system.get_jutsu_info(jutsu_name)
                    if jutsu_info:
                        element_emoji = self._get_element_emoji(jutsu_info["element"])
                        jutsu_details.append(f"{element_emoji} **{jutsu_name}** ({jutsu_info['rarity']})")
                
                embed.add_field(
                    name="Unlocked Jutsu",
                    value="\n".join(jutsu_details),
                    inline=False
                )
                
                if len(unlocked_list) > 10:
                    embed.add_field(name="", value=f"... and {len(unlocked_list) - 10} more", inline=False)
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to unlock any jutsu!"),
                    ephemeral=True
                )
            
        except Exception as e:
            await handle_command_error(interaction, e, "auto_unlock_jutsu")

    def _get_element_emoji(self, element: str) -> str:
        """Get emoji for element type."""
        element_emojis = {
            "fire": "🔥",
            "water": "💧",
            "earth": "🌍",
            "lightning": "⚡",
            "wind": "💨",
            "none": "⚔️"
        }
        return element_emojis.get(element, "⚔️")
    
    def _get_rarity_color(self, rarity: str) -> int:
        """Get color for rarity."""
        rarity_colors = {
            "Common": 0x808080,      # Gray
            "Uncommon": 0x00ff00,    # Green
            "Rare": 0x0080ff,        # Blue
            "Epic": 0x8000ff,        # Purple
            "Legendary": 0xff8000    # Orange
        }
        return rarity_colors.get(rarity, 0x808080)
    
    def _calculate_rank(self, level: int) -> str:
        """Calculate ninja rank based on level."""
        if level >= 50:
            return "Kage"
        elif level >= 40:
            return "Jōnin"
        elif level >= 25:
            return "Chūnin"
        elif level >= 10:
            return "Genin"
        else:
            return "Academy Student"

    @app_commands.command(name="delete_character", description="Delete your character (irreversible)")
    async def delete_character(self, interaction: discord.Interaction):
        """Delete the user's character."""
        try:
            logging.info(f"🔧 /delete_character command called by {interaction.user.name} ({interaction.user.id})")
            
            user_id = interaction.user.id
            character = await self.character_system.get_character(user_id)
            
            if not character:
                logging.info(f"⚠️ User {interaction.user.name} has no character to delete")
                await interaction.response.send_message(
                    embed=create_error_embed("You don't have a character to delete!"),
                    ephemeral=True
                )
                return
            
            logging.info(f"⚠️ Deleting character: {character.name} for user {interaction.user.name}")
            
            # Delete character file
            character_file = f"data/characters/{user_id}.json"
            if os.path.exists(character_file):
                os.remove(character_file)
            
            # Remove from memory
            if str(user_id) in self.character_system.characters:
                del self.character_system.characters[str(user_id)]
            
            embed = create_success_embed(f"Character **{character.name}** has been deleted!")
            embed.add_field(name="Note", value="This action is irreversible. You can create a new character with `/create`.", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await handle_command_error(interaction, e, "delete_character")

async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(CharacterCommands(bot)) 