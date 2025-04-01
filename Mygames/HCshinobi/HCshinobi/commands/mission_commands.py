"""Mission commands for the HCshinobi Discord bot."""
import discord
from discord import app_commands
from typing import Optional, List

from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.character_system import CharacterSystem
from ..utils.discord_ui import get_rarity_color
from ..core.constants import RarityTier

class MissionCommands:
    def __init__(self, mission_system: MissionSystem, character_system: CharacterSystem):
        self.mission_system = mission_system
        self.character_system = character_system
        self.logger = logging.getLogger(__name__)

    def register_commands(self, tree: app_commands.CommandTree):
        """Register all mission-related commands."""
        
        @tree.command(
            name="mission_board",
            description="View available missions"
        )
        async def mission_board(interaction: discord.Interaction):
            """View available missions."""
            # Get character for level check
            character = self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message(
                    "❌ You need a character to view missions! Use /create to create one.",
                    ephemeral=True
                )
                return
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = interaction.client.clan_data.get_clan(clan_name) if clan_name else None
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            # Get available missions
            available_missions = self.mission_system.get_available_missions(character.level)
            
            # Create embed
            embed = discord.Embed(
                title="📋 Mission Board",
                description=f"Available missions for {character.name} (Level {character.level})",
                color=rarity_color
            )
            
            if not available_missions:
                embed.add_field(
                    name="No Available Missions",
                    value="There are no missions available for your level at the moment.",
                    inline=False
                )
            else:
                # Group missions by rank
                missions_by_rank = {}
                for mission in available_missions:
                    if mission.rank not in missions_by_rank:
                        missions_by_rank[mission.rank] = []
                    missions_by_rank[mission.rank].append(mission)
                
                # Add missions to embed by rank
                for rank in sorted(missions_by_rank.keys()):
                    missions = missions_by_rank[rank]
                    value = ""
                    for mission in missions:
                        value += f"**{mission.title}**\n"
                        value += f"ID: `{mission.mission_id}`\n"
                        value += f"Location: {mission.location}\n"
                        value += f"Rewards: {mission.reward_exp} EXP, {mission.reward_ryo} Ryo\n"
                        value += f"Time Limit: {mission.time_limit}\n\n"
                    embed.add_field(
                        name=f"Rank {rank} Missions",
                        value=value,
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
        
        @tree.command(
            name="mission_accept",
            description="Accept a mission"
        )
        async def mission_accept(
            interaction: discord.Interaction,
            mission_id: str
        ):
            """Accept a mission."""
            # Get character
            character = self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message(
                    "❌ You need a character to accept missions! Use /create to create one.",
                    ephemeral=True
                )
                return
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = interaction.client.clan_data.get_clan(clan_name) if clan_name else None
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            # Accept the mission
            success, message = self.mission_system.accept_mission(str(interaction.user.id), mission_id)
            
            if not success:
                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True
                )
                return
            
            # Get mission details
            mission = self.mission_system.available_missions[mission_id]
            
            # Create embed
            embed = discord.Embed(
                title="✅ Mission Accepted",
                description=f"**{mission.title}**",
                color=rarity_color
            )
            
            embed.add_field(
                name="Details",
                value=f"**Rank:** {mission.rank}\n"
                      f"**Location:** {mission.location}\n"
                      f"**Time Limit:** {mission.time_limit}\n"
                      f"**Rewards:** {mission.reward_exp} EXP, {mission.reward_ryo} Ryo",
                inline=False
            )
            
            embed.add_field(
                name="Objectives",
                value="\n".join(f"• {objective}" for objective in mission.objectives),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        
        @tree.command(
            name="mission_progress",
            description="Check your active missions"
        )
        async def mission_progress(interaction: discord.Interaction):
            """Check active missions."""
            # Get character
            character = self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message(
                    "❌ You need a character to check missions! Use /create to create one.",
                    ephemeral=True
                )
                return
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = interaction.client.clan_data.get_clan(clan_name) if clan_name else None
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            # Get active missions
            active_missions = self.mission_system.get_active_missions(str(interaction.user.id))
            
            # Create embed
            embed = discord.Embed(
                title="📋 Active Missions",
                description=f"Current missions for {character.name}",
                color=rarity_color
            )
            
            if not active_missions:
                embed.add_field(
                    name="No Active Missions",
                    value="You don't have any active missions at the moment.",
                    inline=False
                )
            else:
                for mission in active_missions:
                    progress = self.mission_system.get_mission_progress(
                        str(interaction.user.id),
                        mission.mission_id
                    )
                    
                    if progress:
                        value = f"**Description:** {mission.description}\n"
                        value += f"**Location:** {mission.location}\n"
                        value += f"**Time Remaining:** {progress['time_remaining']}\n"
                        value += f"**Rewards:** {progress['rewards']['exp']} EXP, {progress['rewards']['ryo']} Ryo\n\n"
                        value += "**Objectives:**\n"
                        value += "\n".join(f"• {objective}" for objective in mission.objectives)
                        
                        embed.add_field(
                            name=f"{mission.title} (Rank {mission.rank})",
                            value=value,
                            inline=False
                        )
            
            await interaction.response.send_message(embed=embed)
        
        @tree.command(
            name="mission_complete",
            description="Complete a mission"
        )
        async def mission_complete(
            interaction: discord.Interaction,
            mission_id: str
        ):
            """Complete a mission."""
            # Get character
            character = self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message(
                    "❌ You need a character to complete missions! Use /create to create one.",
                    ephemeral=True
                )
                return
            
            # Get clan info and rarity/color
            clan_name = character.clan
            clan_info = interaction.client.clan_data.get_clan(clan_name) if clan_name else None
            clan_rarity_str = "Unknown"
            rarity_color = discord.Color.default()
            if clan_info:
                clan_rarity_str = clan_info.get('rarity', RarityTier.COMMON.value)
                rarity_color = get_rarity_color(clan_rarity_str)
            
            # Complete the mission
            success, message, rewards = self.mission_system.complete_mission(
                str(interaction.user.id),
                mission_id
            )
            
            if not success:
                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True
                )
                return
            
            # Get mission details
            mission = self.mission_system.available_missions[mission_id]
            
            # Create embed
            embed = discord.Embed(
                title="🏆 Mission Completed!",
                description=f"**{mission.title}**",
                color=rarity_color
            )
            
            embed.add_field(
                name="Rewards",
                value=f"**Experience:** +{rewards['exp']}\n"
                      f"**Ryo:** +{rewards['ryo']}",
                inline=False
            )
            
            # Apply rewards
            character.gain_exp(rewards['exp'])
            # TODO: Add ryo to character's wallet
            
            await interaction.response.send_message(embed=embed) 