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
from typing import Optional, List, Dict, Any

from ..core.utils import format_time_delta, pretty_print_duration
from ..core.character import Character

logger = logging.getLogger(__name__)

class MissionCommands(commands.Cog):
    """Handles mission-related commands for the HCShinobi bot."""
    
    def __init__(self, bot, mission_system=None, character_system=None):
        self.bot = bot
        self.mission_system = mission_system
        self.character_system = character_system
        self._init_commands()
        
    def _init_commands(self):
        """Register the commands with the bot."""
        logger.info("Initializing Mission Commands")
    
    @commands.command(name="mission_board")
    async def mission_board(self, ctx):
        """View the available missions for your character."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Get available missions
        available_missions = mission_system.get_available_missions(user_id)
        if not available_missions:
            await ctx.send("No missions are available for you right now. Try ranking up or leveling up!")
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
        
        embed.set_footer(text="Use !mission_accept <number> to accept a mission")
        await ctx.send(embed=embed)
    
    @commands.command(name="mission_accept")
    async def mission_accept(self, ctx, mission_number: int):
        """Accept a mission from the mission board."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Get available missions
        available_missions = mission_system.get_available_missions(user_id)
        if not available_missions:
            await ctx.send("No missions are available for you right now. Try ranking up or leveling up!")
            return
            
        # Check if mission number is valid
        if mission_number < 1 or mission_number > len(available_missions):
            await ctx.send(f"Invalid mission number. Please choose between 1 and {len(available_missions)}.")
            return
            
        # Get selected mission
        selected_mission = available_missions[mission_number - 1]
        mission_id = selected_mission.get("mission_id")
        
        # Assign mission to character
        success, message = mission_system.assign_mission(user_id, mission_id)
        
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
                
                embed.set_footer(text="Use !mission_roll to attempt this challenge")
            else:
                embed.set_footer(text="This mission has no challenges defined.")
                
            await ctx.send(message, embed=embed)
        else:
            await ctx.send(message)
    
    @commands.command(name="mission_progress")
    async def mission_progress(self, ctx):
        """Check your active mission progress."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Get active mission
        active_mission = mission_system.get_active_mission(user_id)
        if not active_mission:
            await ctx.send("You don't have an active mission. Use `!mission_board` to view available missions.")
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
                          (f"Secondary: {current_challenge.get('secondary_skill', 'none').title()}" if current_challenge.get('secondary_skill') else "No secondary skill"),
                    inline=True
                )
                embed.add_field(
                    name="Difficulty",
                    value=current_challenge.get("difficulty", "moderate").title(),
                    inline=True
                )
                
                embed.set_footer(text="Use !mission_roll to attempt this challenge")
            
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
            
            embed.set_footer(text="Use !mission_simulate to simulate mission progress (for testing)")
            
        # Add start time
        start_time = active_mission.get("start_time", "Unknown")
        if start_time != "Unknown":
            embed.add_field(
                name="Started",
                value=start_time.split('T')[0],  # Just show the date
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="mission_roll")
    async def mission_roll(self, ctx):
        """Roll for the current challenge in your D20 mission."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Get active mission
        active_mission = mission_system.get_active_mission(user_id)
        if not active_mission:
            await ctx.send("You don't have an active mission. Use `!mission_board` to view available missions.")
            return
            
        # Check if it's a D20 mission
        if not active_mission.get("is_d20_mission", False):
            await ctx.send("Your current mission is not a D20 mission. Use `!mission_progress` to check its status.")
            return
            
        # Process the challenge
        result = mission_system.process_d20_challenge(user_id)
        
        if not result.get("success", False):
            await ctx.send(result.get("message", "An error occurred while processing the challenge."))
            return
            
        # Get challenge result
        challenge_result = result.get("challenge_result", {})
        mission_progress = result.get("mission_progress", {})
        
        # Create an embed with the roll result
        embed = discord.Embed(
            title="🎲 Challenge Roll",
            color=discord.Color.gold()
        )
        
        # Handle combat vs. skill check
        if "combat_log" in challenge_result:
            # Combat challenge
            embed.description = "You engage in combat!"
            
            # Add combat results
            character_first = challenge_result.get("character_first", False)
            initiative = challenge_result.get("initiative", {})
            
            embed.add_field(
                name="Initiative",
                value=f"{character.name}: {initiative.get('character', 0)}\nEnemy: {initiative.get('enemy', 0)}" +
                      f"\n{character.name} {'acts first' if character_first else 'acts second'}",
                inline=False
            )
            
            # Add combat log
            combat_log = challenge_result.get("combat_log", [])
            if combat_log:
                log_text = "\n".join(combat_log)
                embed.add_field(
                    name="Combat",
                    value=log_text,
                    inline=False
                )
            
            # Add outcome
            outcome = challenge_result.get("outcome", "ongoing").title()
            embed.add_field(
                name="Outcome",
                value=outcome,
                inline=True
            )
            
            # Add health information
            char_hp = challenge_result.get("character_hp_remaining", character.hp)
            enemy_hp = challenge_result.get("enemy_hp_remaining", 0)
            
            embed.add_field(
                name="Health",
                value=f"{character.name}: {char_hp}/{character.hp}\nEnemy: {enemy_hp}/???",
                inline=True
            )
        else:
            # Skill check challenge
            roll = challenge_result.get("roll", 0)
            modifier = challenge_result.get("modifier", 0)
            total = challenge_result.get("total", 0)
            difficulty = challenge_result.get("difficulty", 15)
            success = challenge_result.get("success", False)
            
            # Get skill information
            primary_skill = challenge_result.get("primary_skill", "UNKNOWN")
            secondary_skill = challenge_result.get("secondary_skill")
            
            # Create roll result string
            roll_str = f"d20 ({roll}) + {modifier} = **{total}**"
            if secondary_skill:
                secondary_result = challenge_result.get("secondary_result", {})
                roll_str += f"\nSecondary Roll: d20 ({secondary_result.get('roll', 0)}) + {secondary_result.get('modifier', 0)} = **{secondary_result.get('total', 0)}**"
            
            # Add roll results
            embed.add_field(
                name=f"Skill Check: {primary_skill.title()}" + (f" + {secondary_skill.title()}" if secondary_skill else ""),
                value=roll_str,
                inline=False
            )
            
            # Add success/failure
            if challenge_result.get("critical_success", False):
                embed.add_field(
                    name="Result",
                    value="**CRITICAL SUCCESS!** 🌟",
                    inline=True
                )
                embed.color = discord.Color.gold()
            elif challenge_result.get("critical_failure", False):
                embed.add_field(
                    name="Result",
                    value="**CRITICAL FAILURE!** 💥",
                    inline=True
                )
                embed.color = discord.Color.red()
            else:
                embed.add_field(
                    name="Result",
                    value=f"{'SUCCESS ✅' if success else 'FAILURE ❌'} (DC {difficulty})",
                    inline=True
                )
                embed.color = discord.Color.green() if success else discord.Color.red()
        
        # Add mission progress
        current_challenge = mission_progress.get("current_challenge", 0)
        total_challenges = mission_progress.get("total_challenges", 0)
        
        if current_challenge and total_challenges:
            embed.add_field(
                name="Mission Progress",
                value=f"Challenge {current_challenge}/{total_challenges}",
                inline=True
            )
        
        # Add mission log
        mission_log = mission_progress.get("mission_log", [])
        if mission_log:
            log_text = mission_log[-1]  # Show only the most recent log entry
            embed.set_footer(text=log_text)
        
        # Check if the mission was completed
        if "mission_completion" in result:
            completion = result["mission_completion"]
            if completion[0]:  # If mission was successfully completed
                rewards = completion[2]
                
                # Add completion message
                embed.add_field(
                    name="Mission Complete!",
                    value=completion[1],
                    inline=False
                )
                
                # Add rewards
                rewards_text = f"EXP: {rewards.get('exp', 0)}\nRyō: {rewards.get('ryo', 0)}"
                if rewards.get('items'):
                    rewards_text += f"\nItems: {', '.join(rewards['items'])}"
                    
                embed.add_field(
                    name="Rewards",
                    value=rewards_text,
                    inline=False
                )
        elif "next_challenge" in challenge_result:
            # Show next challenge
            next_challenge = challenge_result["next_challenge"]
            embed.add_field(
                name=f"Next Challenge: {next_challenge.get('title', 'Unknown')}",
                value=next_challenge.get("description", "No description available."),
                inline=False
            )
            
        await ctx.send(embed=embed)
    
    @commands.command(name="mission_complete")
    async def mission_complete(self, ctx):
        """Complete your active mission (for missions that require external verification)."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Get active mission
        active_mission = mission_system.get_active_mission(user_id)
        if not active_mission:
            await ctx.send("You don't have an active mission. Use `!mission_board` to view available missions.")
            return
            
        # Check if it's a D20 mission
        if active_mission.get("is_d20_mission", False):
            await ctx.send("Your active mission is a D20 mission. Use `!mission_roll` to progress through challenges.")
            return
            
        # Complete the mission
        success, message, rewards = mission_system.complete_mission(user_id)
        
        if success:
            # Create embed for completion
            embed = discord.Embed(
                title="Mission Complete!",
                description=message,
                color=discord.Color.green()
            )
            
            # Add rewards
            rewards_text = f"EXP: {rewards.get('exp', 0)}\nRyō: {rewards.get('ryo', 0)}"
            if rewards.get('items'):
                rewards_text += f"\nItems: {', '.join(rewards['items'])}"
                
            embed.add_field(
                name="Rewards",
                value=rewards_text,
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(message)
    
    @commands.command(name="mission_abandon")
    async def mission_abandon(self, ctx):
        """Abandon your current mission."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Abandon the mission
        success, message = mission_system.abandon_mission(user_id)
        await ctx.send(message)
    
    @commands.command(name="mission_history")
    async def mission_history(self, ctx):
        """View your mission completion history."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Get completed missions
        completed_missions = mission_system.get_completed_missions(user_id)
        if not completed_missions:
            await ctx.send("You haven't completed any missions yet.")
            return
            
        # Create an embed with mission history
        embed = discord.Embed(
            title=f"Mission History for {character.name}",
            description=f"You have completed {sum(completed_missions.values())} missions.",
            color=discord.Color.blue()
        )
        
        for mission_id, count in completed_missions.items():
            # Get mission definition
            mission = mission_system.get_mission(mission_id)
            mission_title = mission.get("title", mission_id) if mission else mission_id
            
            embed.add_field(
                name=mission_title,
                value=f"Completed {count} times",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="mission_simulate")
    async def mission_simulate(self, ctx, progress: Optional[float] = 0.1):
        """Simulate progress on your active mission (for testing)."""
        user_id = ctx.author.id
        character_system = self.character_system or self.bot.get_cog("CharacterSystem")
        mission_system = self.mission_system or self.bot.get_cog("MissionSystem")
        
        if not character_system or not mission_system:
            await ctx.send("Character or Mission system is not available.")
            return
            
        # Check if user has a character
        character = character_system.get_character(user_id)
        if not character:
            await ctx.send("You don't have a character. Use `!create_character` to create one.")
            return
            
        # Get active mission
        active_mission = mission_system.get_active_mission(user_id)
        if not active_mission:
            await ctx.send("You don't have an active mission. Use `!mission_board` to view available missions.")
            return
            
        # Check if it's a D20 mission
        if active_mission.get("is_d20_mission", False):
            await ctx.send("Your active mission is a D20 mission. Use `!mission_roll` to progress through challenges.")
            return
            
        # Simulate mission progress
        success, message = mission_system.simulate_mission_progress(user_id, progress)
        
        if success and "complete" in message.lower():
            # Mission was completed by the simulation
            mission_def = active_mission.get("definition", {})
            mission_title = mission_def.get("title", "Unknown Mission")
            
            # Create embed for completion
            embed = discord.Embed(
                title="Mission Complete!",
                description=f"You have completed '{mission_title}'!",
                color=discord.Color.green()
            )
            
            # Parse rewards from the message
            rewards = {}
            if "EXP" in message:
                exp_parts = message.split("EXP: ")[1].split("\n")[0] if "EXP: " in message else "0"
                rewards["exp"] = int(exp_parts) if exp_parts.isdigit() else 0
                
            if "Ryō" in message:
                ryo_parts = message.split("Ryō: ")[1].split("\n")[0] if "Ryō: " in message else "0"
                rewards["ryo"] = int(ryo_parts) if ryo_parts.isdigit() else 0
            
            # Add rewards to embed
            rewards_text = f"EXP: {rewards.get('exp', 0)}\nRyō: {rewards.get('ryo', 0)}"
            embed.add_field(
                name="Rewards",
                value=rewards_text,
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(message)

async def setup(bot):
    """Add the mission commands to the bot."""
    await bot.add_cog(MissionCommands(bot)) 