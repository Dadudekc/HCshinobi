"""
Quest Commands for HCShinobi Discord bot.

This module handles the commands related to quests:
- Viewing available quests
- Accepting quests
- Checking active quests
- Completing quests
- Tracking quest progress
"""

import logging
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from HCshinobi.core.utils import format_time_delta, pretty_print_duration
from HCshinobi.core.character import Character
from HCshinobi.core.quest_system import QuestSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.utils.embed_utils import create_error_embed

# Type checking to avoid circular imports
if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

logger = logging.getLogger(__name__)

class QuestCommands(commands.Cog):
    """Handles quest-related commands for the HCShinobi bot."""
    
    def __init__(self, bot: "HCBot"):
        self.bot = bot
        self.quest_system = bot.services.quest_system
        self.character_system = bot.services.character_system
        
    @app_commands.command(name="quest_board", description="View the available quests for your character")
    async def quest_board(self, interaction: discord.Interaction):
        """View the available quests for your character."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True) # Defer early
        
        # Get available quests using user_id
        available_quests = await self.quest_system.get_available_quests(user_id)
        if not available_quests:
            await interaction.followup.send("No quests are available for you right now. Try ranking up or leveling up!")
            return
            
        # Create an embed with quest information
        embed = discord.Embed(
            title="📜 Quest Board",
            description=f"Available quests for {character.name} ({character.rank})",
            color=discord.Color.blue()
        )
        
        for i, quest in enumerate(available_quests, 1):
            # Add fields for each quest
            quest_title = quest.get("title", "Unknown Quest")
            quest_rank = quest.get("required_rank", "Academy Student")
            quest_desc = quest.get("description", "No description available.")
            quest_reward = f"{quest.get('reward_exp', 0)} EXP, {quest.get('reward_ryo', 0)} Ryō"
            
            # Add quest-specific rewards if any
            if "quest_rewards" in quest:
                quest_rewards = quest["quest_rewards"]
                if "items" in quest_rewards:
                    quest_reward += f"\nItems: {', '.join(quest_rewards['items'])}"
                if "skills" in quest_rewards:
                    quest_reward += f"\nSkills: {', '.join(quest_rewards['skills'])}"
            
            embed.add_field(
                name=f"{i}. {quest_title} ({quest_rank})",
                value=f"{quest_desc}\nReward: {quest_reward}",
                inline=False
            )
        
        embed.set_footer(text="Use /quest_accept <number> to accept a quest")
        await interaction.followup.send(embed=embed)
        
    @app_commands.command(name="quest_accept", description="Accept a quest from the quest board")
    @app_commands.describe(quest_number="The number of the quest to accept")
    async def quest_accept(self, interaction: discord.Interaction, quest_number: int):
        """Accept a quest from the quest board."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get available quests using user_id
        available_quests = await self.quest_system.get_available_quests(user_id)
        if not available_quests:
            await interaction.response.send_message("No quests are available for you right now. Try ranking up or leveling up!", ephemeral=True)
            return
            
        # Check if quest number is valid
        if quest_number < 1 or quest_number > len(available_quests):
            await interaction.response.send_message(f"Invalid quest number. Please choose between 1 and {len(available_quests)}.", ephemeral=True)
            return
            
        # Get selected quest
        selected_quest = available_quests[quest_number - 1]
        quest_id = selected_quest.get("quest_id")
        
        # Assign quest to character
        success, message = await self.quest_system.assign_quest(user_id, quest_id)
        
        if success:
            # Create success embed
            embed = discord.Embed(
                title=f"📜 Quest Accepted: {selected_quest['title']}",
                description=selected_quest.get("description", "No description available."),
                color=discord.Color.green()
            )
            
            # Add quest objectives
            if "objectives" in selected_quest:
                objectives = selected_quest["objectives"]
                objective_text = []
                for obj in objectives:
                    objective_text.append(f"• {obj.get('description', 'Unknown objective')}")
                embed.add_field(
                    name="Objectives",
                    value="\n".join(objective_text),
                    inline=False
                )
                
            # Add rewards information
            rewards = selected_quest.get("rewards", {})
            reward_text = []
            if "exp" in rewards:
                reward_text.append(f"EXP: {rewards['exp']}")
            if "ryo" in rewards:
                reward_text.append(f"Ryō: {rewards['ryo']}")
            if "quest_rewards" in rewards:
                quest_rewards = rewards["quest_rewards"]
                if "items" in quest_rewards:
                    reward_text.append(f"Items: {', '.join(quest_rewards['items'])}")
                if "skills" in quest_rewards:
                    reward_text.append(f"Skills: {', '.join(quest_rewards['skills'])}")
                    
            if reward_text:
                embed.add_field(
                    name="Rewards",
                    value="\n".join(reward_text),
                    inline=False
                )
                
            embed.set_footer(text="Use /quest_progress to check your progress")
            await interaction.response.send_message(message, embed=embed)
        else:
            await interaction.response.send_message(message)
            
    @app_commands.command(name="quest_progress", description="Check your active quest progress")
    async def quest_progress(self, interaction: discord.Interaction):
        """Check your active quest progress."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active quest
        active_quest = await self.quest_system.get_active_quest(user_id)
        if not active_quest:
            await interaction.response.send_message("You don't have an active quest. Use `/quest_board` to view available quests.", ephemeral=True)
            return
            
        quest_def = active_quest.get("definition", {})
        quest_title = quest_def.get("title", "Unknown Quest")
        quest_desc = quest_def.get("description", "No description available.")
        
        # Create an embed with quest progress
        embed = discord.Embed(
            title=f"📜 Quest: {quest_title}",
            description=quest_desc,
            color=discord.Color.blue()
        )
        
        # Add objectives and their progress
        if "objectives" in quest_def:
            objectives = quest_def["objectives"]
            objective_progress = active_quest.get("objective_progress", {})
            
            for i, obj in enumerate(objectives):
                obj_id = obj.get("id", str(i))
                progress = objective_progress.get(obj_id, 0)
                required = obj.get("required", 1)
                
                # Create progress bar
                progress_bar = "█" * int(progress/required * 10) + "░" * (10 - int(progress/required * 10))
                progress_text = f"{progress}/{required} [{progress_bar}]"
                
                embed.add_field(
                    name=f"Objective {i+1}: {obj.get('description', 'Unknown objective')}",
                    value=progress_text,
                    inline=False
                )
                
        # Add rewards information
        rewards = quest_def.get("rewards", {})
        reward_text = []
        if "exp" in rewards:
            reward_text.append(f"EXP: {rewards['exp']}")
        if "ryo" in rewards:
            reward_text.append(f"Ryō: {rewards['ryo']}")
        if "quest_rewards" in rewards:
            quest_rewards = rewards["quest_rewards"]
            if "items" in quest_rewards:
                reward_text.append(f"Items: {', '.join(quest_rewards['items'])}")
            if "skills" in quest_rewards:
                reward_text.append(f"Skills: {', '.join(quest_rewards['skills'])}")
                
        if reward_text:
            embed.add_field(
                name="Rewards",
                value="\n".join(reward_text),
                inline=False
            )
            
        # Check if quest is complete
        is_complete = await self.quest_system.is_quest_complete(user_id)
        if is_complete:
            embed.set_footer(text="Quest complete! Use /quest_complete to finish")
        else:
            embed.set_footer(text="Continue working on your objectives")
            
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="quest_complete", description="Complete your current quest")
    async def quest_complete(self, interaction: discord.Interaction):
        """Complete your current quest."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active quest
        active_quest = await self.quest_system.get_active_quest(user_id)
        if not active_quest:
            await interaction.response.send_message("You don't have an active quest. Use `/quest_board` to view available quests.", ephemeral=True)
            return
            
        # Check if quest is complete
        is_complete = await self.quest_system.is_quest_complete(user_id)
        if not is_complete:
            await interaction.response.send_message("Your quest isn't complete yet! Use `/quest_progress` to check your objectives.", ephemeral=True)
            return
            
        # Complete the quest
        success, message = await self.quest_system.complete_quest(user_id)
        
        if success:
            # Create success embed
            embed = discord.Embed(
                title="🎉 Quest Completed!",
                description=message,
                color=discord.Color.green()
            )
            
            # Add rewards information
            rewards = active_quest.get("definition", {}).get("rewards", {})
            reward_text = []
            if "exp" in rewards:
                reward_text.append(f"EXP: {rewards['exp']}")
            if "ryo" in rewards:
                reward_text.append(f"Ryō: {rewards['ryo']}")
            if "quest_rewards" in rewards:
                quest_rewards = rewards["quest_rewards"]
                if "items" in quest_rewards:
                    reward_text.append(f"Items: {', '.join(quest_rewards['items'])}")
                if "skills" in quest_rewards:
                    reward_text.append(f"Skills: {', '.join(quest_rewards['skills'])}")
                    
            if reward_text:
                embed.add_field(
                    name="Rewards Earned",
                    value="\n".join(reward_text),
                    inline=False
                )
                
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {message}")
            
    @app_commands.command(name="quest_abandon", description="Abandon your current quest")
    async def quest_abandon(self, interaction: discord.Interaction):
        """Abandon your current quest."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        # Get active quest
        active_quest = await self.quest_system.get_active_quest(user_id)
        if not active_quest:
            await interaction.response.send_message("You don't have an active quest. Use `/quest_board` to view available quests.", ephemeral=True)
            return
            
        # Abandon the quest
        success, message = await self.quest_system.abandon_quest(user_id)
        
        if success:
            # Create success embed
            embed = discord.Embed(
                title="🚫 Quest Abandoned",
                description=message,
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {message}")
            
    @app_commands.command(name="quest_history", description="View your quest history")
    async def quest_history(self, interaction: discord.Interaction):
        """View your quest history."""
        user_id = str(interaction.user.id)
            
        # Check if user has a character
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.response.send_message("You don't have a character. Use `/create` to create one.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True) # Defer early
        
        # Get quest history
        quest_history = await self.quest_system.get_quest_history(user_id)
        if not quest_history:
            await interaction.followup.send("You haven't completed any quests yet!", ephemeral=True)
            return
            
        # Create an embed with quest history
        embed = discord.Embed(
            title="📚 Quest History",
            description=f"Completed quests for {character.name}",
            color=discord.Color.blue()
        )
        
        for quest in quest_history:
            quest_title = quest.get("title", "Unknown Quest")
            completion_date = quest.get("completion_date", "Unknown date")
            quest_desc = quest.get("description", "No description available.")
            
            embed.add_field(
                name=f"{quest_title} (Completed: {completion_date})",
                value=quest_desc,
                inline=False
            )
            
        await interaction.followup.send(embed=embed)

async def setup(bot: "HCBot"):
    """Add the cog to the bot."""
    cog = QuestCommands(bot)
    await bot.add_cog(cog)
    
    # Register commands with the bot
    try:
        # Create quest group if it doesn't exist
        quest_group = None
        for cmd in bot.tree.get_commands():
            if cmd.name == "quest":
                quest_group = cmd
                break
                
        if not quest_group:
            quest_group = app_commands.Group(name="quest", description="Quest-related commands")
            bot.tree.add_command(quest_group)
            
        # Add subcommands to quest group
        quest_group.add_command(cog.quest_board)
        quest_group.add_command(cog.quest_accept)
        quest_group.add_command(cog.quest_progress)
        quest_group.add_command(cog.quest_complete)
        quest_group.add_command(cog.quest_abandon)
        quest_group.add_command(cog.quest_history)
        
        logger.info("Added QuestCommands subcommands to 'quest' group.")
    except Exception as e:
        logger.error(f"Error registering quest commands: {e}", exc_info=True) 