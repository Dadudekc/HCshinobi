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
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from HCshinobi.core.utils import format_time_delta, pretty_print_duration
from HCshinobi.core.character import Character
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.missions.mission import Mission, MissionStatus
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from HCshinobi.utils.embed_utils import create_error_embed

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

logger = logging.getLogger(__name__)

class MissionCommands(commands.Cog):
    """Handles mission-related commands for the HCShinobi bot."""
    
    def __init__(self, bot: "HCBot"):
        self.bot = bot
        self.mission_system = bot.services.mission_system
        self.character_system = bot.services.character_system
        
    @app_commands.command(name="mission_board", description="View the available missions for your character")
    async def mission_board(self, interaction: discord.Interaction):
        """View the available missions for your character."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True) # Defer early
        
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
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get available missions
        available_missions = await self.mission_system.get_available_missions(user_id)
        if not available_missions:
            await interaction.followup.send("No missions are available for you right now.")
            return
            
        # Validate mission number
        if mission_number < 1 or mission_number > len(available_missions):
            await interaction.followup.send(f"Invalid mission number. Please choose between 1 and {len(available_missions)}.")
            return
            
        # Accept the mission
        mission = available_missions[mission_number - 1]
        success = await self.mission_system.accept_mission(user_id, mission)
        
        if success:
            await interaction.followup.send(f"You have accepted the mission: {mission.title}")
        else:
            await interaction.followup.send("Failed to accept mission. You may already have an active mission.")
    
    @app_commands.command(name="mission_progress", description="Check your current mission progress")
    async def mission_progress(self, interaction: discord.Interaction):
        """Check your current mission progress."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.followup.send("You don't have an active mission!")
            return
            
        # Get mission progress
        progress = await self.mission_system.get_mission_progress(user_id, active_mission)
        await interaction.followup.send(f"**Mission Progress:**\n{progress}")
    
    @app_commands.command(name="mission_roll", description="Roll for mission success")
    async def mission_roll(self, interaction: discord.Interaction):
        """Roll for mission success."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.followup.send("You don't have an active mission!")
            return
            
        # Roll for mission success
        result = await self.mission_system.roll_mission(user_id, active_mission)
        await interaction.followup.send(f"**Mission Roll Result:**\n{result}")
    
    @app_commands.command(name="mission_complete", description="Complete your current mission")
    async def mission_complete(self, interaction: discord.Interaction):
        """Complete your current mission."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.followup.send("You don't have an active mission!")
            return
            
        # Complete the mission
        success = await self.mission_system.complete_mission(user_id, active_mission)
        if success:
            await interaction.followup.send("Mission completed successfully!")
        else:
            await interaction.followup.send("Failed to complete mission. Make sure you've met all requirements.")
    
    @app_commands.command(name="mission_abandon", description="Abandon your current mission")
    async def mission_abandon(self, interaction: discord.Interaction):
        """Abandon your current mission."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.followup.send("You don't have an active mission!")
            return
            
        # Abandon the mission
        success = await self.mission_system.abandon_mission(user_id, active_mission)
        if success:
            await interaction.followup.send("Mission abandoned successfully.")
        else:
            await interaction.followup.send("Failed to abandon mission.")
    
    @app_commands.command(name="mission_history", description="View your mission history")
    async def mission_history(self, interaction: discord.Interaction):
        """View your mission history."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get mission history
        history = await self.mission_system.get_mission_history(user_id)
        if not history:
            await interaction.followup.send("You haven't completed any missions yet!")
            return
            
        # Format and send history
        history_text = "\n".join([f"- {m.title} ({m.status})" for m in history])
        await interaction.followup.send(f"**Mission History:**\n{history_text}")
    
    @app_commands.command(name="mission_simulate", description="Simulate a mission outcome")
    async def mission_simulate(self, interaction: discord.Interaction):
        """Simulate a mission outcome."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Get active mission
        active_mission = await self.mission_system.get_active_mission(user_id)
        if not active_mission:
            await interaction.followup.send("You don't have an active mission!")
            return
            
        # Simulate mission
        simulation = await self.mission_system.simulate_mission(user_id, active_mission)
        await interaction.followup.send(f"**Mission Simulation:**\n{simulation}")

    @app_commands.command(name="clan_mission_board", description="View the available clan missions")
    async def clan_mission_board(self, interaction: discord.Interaction):
        """View the available clan missions."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Check if character is in a clan
        if not character.clan:
            await interaction.response.send_message("You need to be in a clan to view clan missions. Join a clan first!", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True, thinking=True) # Defer early
        
        # Get available clan missions
        available_missions = await self.mission_system.get_available_clan_missions(character.clan)
        if not available_missions:
            await interaction.followup.send("No clan missions are available right now. Check back later!", ephemeral=True)
            return
            
        # Create an embed with mission information
        embed = discord.Embed(
            title="🏰 Clan Mission Board",
            description=f"Available clan missions for {character.clan}",
            color=discord.Color.purple()
        )
        
        for i, mission in enumerate(available_missions, 1):
            # Add fields for each mission
            mission_title = mission.get("title", "Unknown Mission")
            mission_rank = mission.get("required_rank", "Academy Student")
            mission_desc = mission.get("description", "No description available.")
            mission_reward = f"{mission.get('reward_exp', 0)} EXP, {mission.get('reward_ryo', 0)} Ryō"
            
            # Add clan-specific rewards if any
            if "clan_rewards" in mission:
                clan_rewards = mission["clan_rewards"]
                if "clan_exp" in clan_rewards:
                    mission_reward += f"\nClan EXP: {clan_rewards['clan_exp']}"
                if "clan_reputation" in clan_rewards:
                    mission_reward += f"\nClan Reputation: {clan_rewards['clan_reputation']}"
            
            # Indicate if it's a D20 mission
            is_d20 = "🎲 " if mission.get("is_d20_mission", False) else ""
            
            embed.add_field(
                name=f"{i}. {is_d20}{mission_title} ({mission_rank})",
                value=f"{mission_desc}\nReward: {mission_reward}",
                inline=False
            )
        
        embed.set_footer(text="Use /clan_mission_accept <number> to accept a clan mission")
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="clan_mission_accept", description="Accept a clan mission from the mission board")
    @app_commands.describe(mission_number="The number of the clan mission to accept")
    async def clan_mission_accept(self, interaction: discord.Interaction, mission_number: int):
        """Accept a clan mission from the mission board."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Check if character is in a clan
        if not character.clan:
            await interaction.response.send_message("You need to be in a clan to accept clan missions. Join a clan first!", ephemeral=True)
            return
            
        # Get available clan missions
        available_missions = await self.mission_system.get_available_clan_missions(character.clan)
        if not available_missions:
            await interaction.response.send_message("No clan missions are available right now. Check back later!", ephemeral=True)
            return
            
        # Check if mission number is valid
        if mission_number < 1 or mission_number > len(available_missions):
            await interaction.response.send_message(f"Invalid mission number. Please choose between 1 and {len(available_missions)}.", ephemeral=True)
            return
            
        # Get selected mission
        selected_mission = available_missions[mission_number - 1]
        mission_id = selected_mission.get("mission_id")
        
        # Assign clan mission
        success, message = await self.mission_system.assign_clan_mission(character.clan, mission_id, user_id)
        
        # If it's a D20 mission, show the first challenge
        if success and selected_mission.get("is_d20_mission", False):
            embed = discord.Embed(
                title=f"🎲 Clan Mission: {selected_mission['title']}",
                description=selected_mission.get("description", "No description available."),
                color=discord.Color.purple()
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
                
                embed.set_footer(text="Use /clan_mission_roll to attempt this challenge")
            else:
                embed.set_footer(text="This mission has no challenges defined.")
                
            await interaction.response.send_message(message, embed=embed)
        else:
            await interaction.response.send_message(message)
            
    @app_commands.command(name="clan_mission_progress", description="Check your active clan mission progress")
    async def clan_mission_progress(self, interaction: discord.Interaction):
        """Check your active clan mission progress."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Check if character is in a clan
        if not character.clan:
            await interaction.response.send_message("You need to be in a clan to check clan mission progress. Join a clan first!", ephemeral=True)
            return
            
        # Get active clan mission
        active_mission = await self.mission_system.get_active_clan_mission(character.clan)
        if not active_mission:
            await interaction.response.send_message("Your clan doesn't have an active mission. Use `/clan_mission_board` to view available clan missions.", ephemeral=True)
            return
            
        mission_def = active_mission.get("definition", {})
        mission_title = mission_def.get("title", "Unknown Mission")
        mission_desc = mission_def.get("description", "No description available.")
        progress = active_mission.get("progress", 0.0) * 100  # Convert to percentage
        
        # Create an embed with mission progress
        embed = discord.Embed(
            title=f"Clan Mission: {mission_title}",
            description=mission_desc,
            color=discord.Color.purple()
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
                    name="Current Challenge",
                    value=f"{current_challenge.get('title', 'Unknown')}\n{current_challenge.get('description', 'No description available.')}",
                    inline=False
                )
                embed.add_field(
                    name="Skills Required",
                    value=f"Primary: {current_challenge.get('primary_skill', 'none').title()}\n" +
                          (f"Secondary: {current_challenge.get('secondary_skill', 'none').title()}" if current_challenge.get('secondary_skill') else "No secondary skill"),
                    inline=True
                )
                embed.add_field(
                    name="Difficulty",
                    value=current_challenge.get("difficulty", "moderate").title(),
                    inline=True
                )
                
                embed.set_footer(text="Use /clan_mission_roll to attempt this challenge")
            else:
                embed.set_footer(text="All challenges completed! Use /clan_mission_complete to finish the mission.")
                
            # Add mission log if available
            if mission_log:
                log_text = "\n".join([f"• {entry}" for entry in mission_log[-5:]])  # Show last 5 entries
                embed.add_field(
                    name="Recent Activity",
                    value=log_text,
                    inline=False
                )
        else:
            # For non-D20 missions, just show progress
            embed.add_field(
                name="Progress",
                value=f"{progress:.1f}% complete",
                inline=False
            )
            
            # Add rewards information
            rewards = mission_def.get("rewards", {})
            reward_text = []
            if "exp" in rewards:
                reward_text.append(f"EXP: {rewards['exp']}")
            if "ryo" in rewards:
                reward_text.append(f"Ryō: {rewards['ryo']}")
            if "clan_rewards" in rewards:
                clan_rewards = rewards["clan_rewards"]
                if "clan_exp" in clan_rewards:
                    reward_text.append(f"Clan EXP: {clan_rewards['clan_exp']}")
                if "clan_reputation" in clan_rewards:
                    reward_text.append(f"Clan Reputation: {clan_rewards['clan_reputation']}")
                    
            if reward_text:
                embed.add_field(
                    name="Rewards",
                    value="\n".join(reward_text),
                    inline=False
                )
                
            embed.set_footer(text="Use /clan_mission_complete when you're ready to finish")
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clan_mission_roll", description="Attempt the current clan mission challenge")
    async def clan_mission_roll(self, interaction: discord.Interaction):
        """Attempt the current clan mission challenge."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Check if character is in a clan
        if not character.clan:
            await interaction.response.send_message("You need to be in a clan to attempt clan mission challenges. Join a clan first!", ephemeral=True)
            return
            
        # Get active clan mission
        active_mission = await self.mission_system.get_active_clan_mission(character.clan)
        if not active_mission:
            await interaction.response.send_message("Your clan doesn't have an active mission. Use `/clan_mission_board` to view available clan missions.", ephemeral=True)
            return
            
        # Check if it's a D20 mission
        if not active_mission.get("is_d20_mission", False):
            await interaction.response.send_message("This mission doesn't use the D20 system. Progress is tracked automatically.", ephemeral=True)
            return
            
        # Check if there are any challenges left
        d20_state = active_mission.get("d20_mission_state", {})
        current_challenge_index = d20_state.get("current_challenge_index", 0)
        challenges = active_mission.get("definition", {}).get("challenges", [])
        
        if current_challenge_index >= len(challenges):
            await interaction.response.send_message("All challenges have been completed! Use `/clan_mission_complete` to finish the mission.", ephemeral=True)
            return
            
        # Get current challenge
        current_challenge = challenges[current_challenge_index]
        
        # Calculate roll modifiers based on character skills
        primary_skill = current_challenge.get("primary_skill", "none")
        secondary_skill = current_challenge.get("secondary_skill")
        difficulty = current_challenge.get("difficulty", "moderate")
        
        # Get skill bonuses
        primary_bonus = character.get_skill_bonus(primary_skill)
        secondary_bonus = character.get_skill_bonus(secondary_skill) if secondary_skill else 0
        
        # Calculate total bonus
        total_bonus = primary_bonus + (secondary_bonus // 2)  # Secondary skill provides half bonus
        
        # Roll D20
        roll = await self.mission_system.roll_d20()
        total = roll + total_bonus
        
        # Determine success based on difficulty
        success = False
        if difficulty == "easy":
            success = total >= 10
        elif difficulty == "moderate":
            success = total >= 15
        elif difficulty == "hard":
            success = total >= 20
        else:  # very_hard
            success = total >= 25
            
        # Create result embed
        embed = discord.Embed(
            title=f"🎲 Clan Mission Challenge: {current_challenge.get('title', 'Unknown')}",
            description=f"Roll: {roll} + {total_bonus} (bonus) = {total}",
            color=discord.Color.green() if success else discord.Color.red()
        )
        
        # Add skill information
        embed.add_field(
            name="Skills Used",
            value=f"Primary ({primary_skill.title()}): +{primary_bonus}\n" +
                  (f"Secondary ({secondary_skill.title()}): +{secondary_bonus//2}" if secondary_skill else "No secondary skill"),
            inline=False
        )
        
        # Add difficulty information
        embed.add_field(
            name="Difficulty",
            value=f"{difficulty.title()} (DC: {10 if difficulty == 'easy' else 15 if difficulty == 'moderate' else 20 if difficulty == 'hard' else 25})",
            inline=True
        )
        
        # Add result
        if success:
            embed.add_field(
                name="Result",
                value="✅ Success! The challenge has been completed.",
                inline=False
            )
            
            # Update mission progress
            await self.mission_system.update_clan_mission_progress(character.clan, current_challenge_index + 1)
            
            # Add next challenge info if available
            if current_challenge_index + 1 < len(challenges):
                next_challenge = challenges[current_challenge_index + 1]
                embed.add_field(
                    name="Next Challenge",
                    value=f"{next_challenge.get('title', 'Unknown')}\n{next_challenge.get('description', 'No description available.')}",
                    inline=False
                )
                embed.set_footer(text="Use /clan_mission_roll to attempt the next challenge")
            else:
                embed.set_footer(text="All challenges completed! Use /clan_mission_complete to finish the mission.")
        else:
            embed.add_field(
                name="Result",
                value="❌ Failure! The challenge was not completed.",
                inline=False
            )
            embed.set_footer(text="Try again with /clan_mission_roll")
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="clan_mission_complete", description="Complete your current clan mission")
    async def clan_mission_complete(self, interaction: discord.Interaction):
        """Complete your current clan mission."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Check if character is in a clan
        if not character.clan:
            await interaction.response.send_message("You need to be in a clan to complete clan missions. Join a clan first!", ephemeral=True)
            return
            
        # Get active clan mission
        active_mission = await self.mission_system.get_active_clan_mission(character.clan)
        if not active_mission:
            await interaction.response.send_message("Your clan doesn't have an active mission. Use `/clan_mission_board` to view available clan missions.", ephemeral=True)
            return
            
        # Check if mission is complete
        if active_mission.get("is_d20_mission", False):
            d20_state = active_mission.get("d20_mission_state", {})
            current_challenge_index = d20_state.get("current_challenge_index", 0)
            challenges = active_mission.get("definition", {}).get("challenges", [])
            
            if current_challenge_index < len(challenges):
                await interaction.response.send_message("You haven't completed all challenges yet! Use `/clan_mission_roll` to continue.", ephemeral=True)
                return
        else:
            progress = active_mission.get("progress", 0.0)
            if progress < 1.0:
                await interaction.response.send_message("The mission isn't complete yet! Continue working on it.", ephemeral=True)
                return
                
        # Complete the mission
        success, message = await self.mission_system.complete_clan_mission(character.clan)
        
        if success:
            # Create success embed
            embed = discord.Embed(
                title="🎉 Clan Mission Completed!",
                description=message,
                color=discord.Color.green()
            )
            
            # Add rewards information
            rewards = active_mission.get("definition", {}).get("rewards", {})
            reward_text = []
            if "exp" in rewards:
                reward_text.append(f"EXP: {rewards['exp']}")
            if "ryo" in rewards:
                reward_text.append(f"Ryō: {rewards['ryo']}")
            if "clan_rewards" in rewards:
                clan_rewards = rewards["clan_rewards"]
                if "clan_exp" in clan_rewards:
                    reward_text.append(f"Clan EXP: {clan_rewards['clan_exp']}")
                if "clan_reputation" in clan_rewards:
                    reward_text.append(f"Clan Reputation: {clan_rewards['clan_reputation']}")
                    
            if reward_text:
                embed.add_field(
                    name="Rewards Earned",
                    value="\n".join(reward_text),
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {message}")
            
    @app_commands.command(name="clan_mission_abandon", description="Abandon your current clan mission")
    async def clan_mission_abandon(self, interaction: discord.Interaction):
        """Abandon your current clan mission."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Check if character is in a clan
        if not character.clan:
            await interaction.response.send_message("You need to be in a clan to abandon clan missions. Join a clan first!", ephemeral=True)
            return
            
        # Get active clan mission
        active_mission = await self.mission_system.get_active_clan_mission(character.clan)
        if not active_mission:
            await interaction.response.send_message("Your clan doesn't have an active mission. Use `/clan_mission_board` to view available clan missions.", ephemeral=True)
            return
            
        # Abandon the mission
        success, message = await self.mission_system.abandon_clan_mission(character.clan)
        
        if success:
            # Create success embed
            embed = discord.Embed(
                title="🚫 Clan Mission Abandoned",
                description=message,
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {message}")

async def setup(bot: "HCBot"):
    """Add the cog to the bot."""
    cog = MissionCommands(bot)
    await bot.add_cog(cog)
    
    # Register commands with the bot
    try:
        # Create mission group if it doesn't exist
        mission_group = None
        for cmd in bot.tree.get_commands():
            if cmd.name == "mission":
                mission_group = cmd
                break
                
        if not mission_group:
            mission_group = app_commands.Group(name="mission", description="Mission-related commands")
            bot.tree.add_command(mission_group)
            
        # Add subcommands to mission group
        mission_group.add_command(cog.mission_board)
        mission_group.add_command(cog.mission_accept)
        mission_group.add_command(cog.mission_progress)
        mission_group.add_command(cog.mission_roll)
        mission_group.add_command(cog.mission_complete)
        mission_group.add_command(cog.mission_abandon)
        mission_group.add_command(cog.mission_history)
        
        # Add clan mission commands
        mission_group.add_command(cog.clan_mission_board)
        mission_group.add_command(cog.clan_mission_accept)
        mission_group.add_command(cog.clan_mission_progress)
        mission_group.add_command(cog.clan_mission_roll)
        mission_group.add_command(cog.clan_mission_complete)
        mission_group.add_command(cog.clan_mission_abandon)
        
        logger.info("Added MissionCommands subcommands to 'mission' group.")
    except Exception as e:
        logger.error(f"Error registering mission commands: {e}", exc_info=True) 