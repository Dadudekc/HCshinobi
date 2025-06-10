"""
Mission Commands for HCShinobi Discord bot.

This module handles the commands related to missions:
- Viewing available missions
- Accepting missions
- Checking active missions
- Completing missions
- Rolling for mission challenges (d20 system)
"""

import logging
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select
from typing import Optional, List, Dict, Any

from HCshinobi.core.utils import format_time_delta, pretty_print_duration
from HCshinobi.core.character import Character
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.missions.mission import Mission, MissionStatus
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.progression_engine import ShinobiProgressionEngine

logger = logging.getLogger(__name__)

class MissionCommands(commands.Cog):
    """Handles mission-related commands for the HCShinobi bot."""
    
    def __init__(self, bot: 'HCShinobiBot', mission_system: MissionSystem, character_system: CharacterSystem):
        self.bot = bot
        self.mission_system = mission_system
        self.character_system = character_system
        
    @app_commands.command(name="mission_board", description="View the available missions for your character")
    async def mission_board(self, interaction: discord.Interaction):
        """View the available missions for your character."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True) # Defer early
        
        # Get available missions using user_id
        available_missions = await self.mission_system.get_available_missions(user_id)
        if not available_missions:
            await interaction.followup.send("No missions are available for you right now. Try ranking up or leveling up!")
            return
            
        # Create an embed with mission information
        embed = discord.Embed(
            title="🗒️ Mission Board",
            description=f"Available missions for {character.name} ({character.rank})",
            color=discord.Color.blue()
        )
        
        for i, mission in enumerate(available_missions, 1):
            # Add fields for each mission
            mission_title = mission.get("title", "Unknown Mission")
            mission_rank = mission.get("required_rank", "Academy Student")
            mission_desc = mission.get("description", "No description available.")
            mission_reward = f"{mission.get('reward_exp', 0)} EXP, {mission.get('reward_ryo', 0)} Ryō"
            
            # Indicate if it's a D20 mission
            is_d20 = "🎲 " if mission.get("is_d20_mission", False) else ""
            
            embed.add_field(
                name=f"{i}. {is_d20}{mission_title} ({mission_rank})",
                value=f"{mission_desc}\nReward: {mission_reward}",
                inline=False
            )
        
        embed.set_footer(text="Use /mission_accept <number> to accept a mission")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="mission_accept", description="Accept a mission from the mission board")
    @app_commands.describe(mission_number="The number of the mission to accept")
    async def mission_accept(self, interaction: discord.Interaction, mission_number: int):
        """Accept a mission from the mission board."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get available missions using user_id
        available_missions = await self.mission_system.get_available_missions(user_id)
        if not available_missions:
            await interaction.response.send_message("No missions are available for you right now. Try ranking up or leveling up!", ephemeral=True)
            return
            
        # Check if mission number is valid
        if mission_number < 1 or mission_number > len(available_missions):
            await interaction.response.send_message(f"Invalid mission number. Please choose between 1 and {len(available_missions)}.", ephemeral=True)
            return
            
        # Get selected mission
        selected_mission = available_missions[mission_number - 1]
        mission_id = selected_mission.get("mission_id")
        
        # Assign mission to character
        success, message = await self.mission_system.assign_mission(user_id, mission_id)
        
        # If it's a D20 mission, show the first challenge
        if success and selected_mission.get("is_d20_mission", False):
            embed = discord.Embed(
                title=f"🎲 Mission: {selected_mission['title']}",
                description=selected_mission.get("description", "No description available."),
                color=discord.Color.green()
            )
            
            # Add first challenge info
            if "challenges" in selected_mission and len(selected_mission["challenges"]) > 0:
                first_challenge = selected_mission["challenges"][0]
                embed.add_field(
                    name=f"First Challenge: {first_challenge.get('title', 'Unknown')}",
                    value=first_challenge.get("description", "No description available."),
                    inline=False
                )
                embed.add_field(
                    name="Skills Required",
                    value=f"Primary: {first_challenge.get('primary_skill', 'none').title()}\n" +
                          (f"Secondary: {first_challenge.get('secondary_skill', 'none').title()}" if first_challenge.get('secondary_skill') else "No secondary skill"),
                    inline=True
                )
                embed.add_field(
                    name="Difficulty",
                    value=first_challenge.get("difficulty", "moderate").title(),
                    inline=True
                )
                
                embed.set_footer(text="Use /mission_roll to attempt this challenge")
            else:
                embed.set_footer(text="This mission has no challenges defined.")
                
            await interaction.response.send_message(message, embed=embed)
        else:
            await interaction.response.send_message(message)
    
    @app_commands.command(name="mission_progress", description="Check your active mission progress")
    async def mission_progress(self, interaction: discord.Interaction):
        """Check your active mission progress."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.response.send_message("You don't have an active mission. Use `/mission_board` to view available missions.", ephemeral=True)
            return
            
        mission_def = active_mission.get("definition", {})
        mission_title = mission_def.get("title", "Unknown Mission")
        mission_desc = mission_def.get("description", "No description available.")
        progress = active_mission.get("progress", 0.0) * 100  # Convert to percentage
        
        # Create an embed with mission progress
        embed = discord.Embed(
            title=f"Mission: {mission_title}",
            description=mission_desc,
            color=discord.Color.blue()
        )
        
        # Check if it's a D20 mission
        if active_mission.get("is_d20_mission", False) and "d20_mission_state" in active_mission:
            d20_state = active_mission["d20_mission_state"]
            current_challenge_index = d20_state.get("current_challenge_index", 0)
            completed_challenges = d20_state.get("completed_challenges", [])
            mission_log = d20_state.get("mission_log", [])
            
            # Get all challenges
            challenges = mission_def.get("challenges", [])
            total_challenges = len(challenges)
            
            # Add progress information
            embed.add_field(
                name="Progress",
                value=f"{len(completed_challenges)}/{total_challenges} challenges completed ({progress:.1f}%)",
                inline=False
            )
            
            # Add current challenge information
            if current_challenge_index < total_challenges:
                current_challenge = challenges[current_challenge_index]
                embed.add_field(
                    name=f"Current Challenge: {current_challenge.get('title', 'Unknown')}",
                    value=current_challenge.get("description", "No description available."),
                    inline=False
                )
                embed.add_field(
                    name="Skills Required",
                    value=f"Primary: {current_challenge.get('primary_skill', 'none').title()}\n" +
                          (f"Secondary: {first_challenge.get('secondary_skill', 'none').title()}" if first_challenge.get('secondary_skill') else "No secondary skill"),
                    inline=True
                )
                embed.add_field(
                    name="Difficulty",
                    value=current_challenge.get("difficulty", "moderate").title(),
                    inline=True
                )
                
                embed.set_footer(text="Use /mission_roll to attempt this challenge")
            
            # Add mission log
            if mission_log:
                log_text = "\n".join(mission_log[-5:])  # Show last 5 log entries
                embed.add_field(
                    name="Mission Log",
                    value=log_text,
                    inline=False
                )
        else:
            # Regular mission progress
            embed.add_field(
                name="Progress",
                value=f"{progress:.1f}%",
                inline=True
            )
            
            # Add objectives
            objectives = active_mission.get("objectives_complete", [])
            if objectives:
                obj_text = "\n".join([f"✅ {obj}" for obj in objectives])
                embed.add_field(
                    name="Completed Objectives",
                    value=obj_text,
                    inline=False
                )
            
            # Add time remaining
            time_remaining = active_mission.get("time_remaining")
            if time_remaining:
                embed.add_field(
                    name="Time Remaining",
                    value=pretty_print_duration(time_remaining),
                    inline=True
                )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="mission_roll", description="Attempt the current mission challenge")
    async def mission_roll(self, interaction: discord.Interaction):
        """Attempt the current mission challenge."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.response.send_message("You don't have an active mission. Use `/mission_board` to view available missions.", ephemeral=True)
            return
            
        # Check if it's a D20 mission
        if not active_mission.get("is_d20_mission", False):
            await interaction.response.send_message("This mission doesn't use the D20 system.", ephemeral=True)
            return
            
        # Get current challenge
        d20_state = active_mission.get("d20_mission_state", {})
        current_challenge_index = d20_state.get("current_challenge_index", 0)
        challenges = active_mission.get("definition", {}).get("challenges", [])
        
        if current_challenge_index >= len(challenges):
            await interaction.response.send_message("You've completed all challenges for this mission!", ephemeral=True)
            return
            
        current_challenge = challenges[current_challenge_index]
        
        # Roll for the challenge
        success, message, roll_result = await self.mission_system.roll_mission_challenge(user_id)
        
        # Create embed with roll result
        embed = discord.Embed(
            title=f"🎲 Challenge Roll: {current_challenge.get('title', 'Unknown')}",
            description=message,
            color=discord.Color.green() if success else discord.Color.red()
        )
        
        # Add roll details
        if roll_result:
            embed.add_field(
                name="Roll Details",
                value=f"Roll: {roll_result.get('roll', '?')}\n"
                      f"Modifier: {roll_result.get('modifier', '?')}\n"
                      f"Total: {roll_result.get('total', '?')}\n"
                      f"DC: {roll_result.get('dc', '?')}",
                inline=True
            )
            
            # Add skill bonuses
            skill_bonuses = roll_result.get("skill_bonuses", {})
            if skill_bonuses:
                bonus_text = "\n".join([f"{skill}: +{bonus}" for skill, bonus in skill_bonuses.items()])
                embed.add_field(
                    name="Skill Bonuses",
                    value=bonus_text,
                    inline=True
                )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="mission_complete", description="Complete your current mission")
    async def mission_complete(self, interaction: discord.Interaction):
        """Complete your current mission."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.response.send_message("You don't have an active mission. Use `/mission_board` to view available missions.", ephemeral=True)
            return
            
        # Complete the mission
        success, message = await self.mission_system.complete_mission(user_id)
        
        if success:
            # Create success embed
            embed = discord.Embed(
                title="✅ Mission Complete!",
                description=message,
                color=discord.Color.green()
            )
            
            # Add rewards
            rewards = active_mission.get("rewards", {})
            if rewards:
                reward_text = []
                if "exp" in rewards:
                    reward_text.append(f"EXP: {rewards['exp']}")
                if "ryo" in rewards:
                    reward_text.append(f"Ryō: {rewards['ryo']}")
                if "items" in rewards:
                    reward_text.append(f"Items: {', '.join(rewards['items'])}")
                
                embed.add_field(
                    name="Rewards",
                    value="\n".join(reward_text),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    
    @app_commands.command(name="mission_abandon", description="Abandon your current mission")
    async def mission_abandon(self, interaction: discord.Interaction):
        """Abandon your current mission."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.response.send_message("You don't have an active mission. Use `/mission_board` to view available missions.", ephemeral=True)
            return
            
        # Abandon the mission
        success, message = await self.mission_system.abandon_mission(user_id)
        
        if success:
            embed = discord.Embed(
                title="❌ Mission Abandoned",
                description=message,
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    
    @app_commands.command(name="mission_history", description="View your mission history")
    async def mission_history(self, interaction: discord.Interaction):
        """View your mission history."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get mission history
        history = await self.mission_system.get_mission_history(user_id)
        if not history:
            await interaction.response.send_message("You haven't completed any missions yet.", ephemeral=True)
            return
            
        # Create embed with mission history
        embed = discord.Embed(
            title="📜 Mission History",
            description=f"Mission history for {character.name}",
            color=discord.Color.blue()
        )
        
        # Add completed missions
        for mission in history[:10]:  # Show last 10 missions
            mission_title = mission.get("title", "Unknown Mission")
            completion_time = mission.get("completion_time", "Unknown")
            rewards = mission.get("rewards", {})
            
            reward_text = []
            if "exp" in rewards:
                reward_text.append(f"EXP: {rewards['exp']}")
            if "ryo" in rewards:
                reward_text.append(f"Ryō: {rewards['ryo']}")
            
            embed.add_field(
                name=f"✅ {mission_title}",
                value=f"Completed: {completion_time}\nRewards: {', '.join(reward_text)}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="mission_simulate", description="[Admin] Simulate mission progress")
    @app_commands.describe(progress="The amount of progress to simulate (0.0 to 1.0)")
    @app_commands.checks.has_permissions(administrator=True)
    async def mission_simulate(self, interaction: discord.Interaction, progress: Optional[float] = 0.1):
        """Simulate mission progress (Admin only)."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.response.send_message("You don't have an active mission. Use `/mission_board` to view available missions.", ephemeral=True)
            return
            
        # Simulate progress
        success, message = await self.mission_system.simulate_progress(user_id, progress)
        
        if success:
            embed = discord.Embed(
                title="⚡ Mission Progress Simulated",
                description=message,
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(message, ephemeral=True)

async def setup(bot: 'HCShinobiBot'):
    """Add the cog to the bot."""
    # Fetch required services from the bot's service container
    mission_system = getattr(bot.services, 'mission_system', None)
    character_system = getattr(bot.services, 'character_system', None)
    
    if not mission_system:
        logger.error("MissionSystem service not found in bot.services. Cannot load MissionCommands.")
        raise AttributeError("MissionSystem service not found in bot.services.")
    if not character_system:
        logger.error("CharacterSystem service not found in bot.services. Cannot load MissionCommands.")
        raise AttributeError("CharacterSystem service not found in bot.services.")

    await bot.add_cog(MissionCommands(
        bot,
        mission_system, # Pass the fetched service
        character_system  # Pass the fetched service
    )) 
    logger.info("MissionCommands Cog loaded successfully.") 