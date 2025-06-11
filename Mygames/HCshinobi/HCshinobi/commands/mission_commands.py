import logging
from discord.ext import commands
from typing import Optional

class MissionCommands(commands.Cog):
    """Handles mission-related commands for the HCShinobi bot."""
    
    def __init__(self, bot, mission_system=None, character_system=None, progression_engine=None):
        """Initialize mission commands.
        
        Args:
            bot: The bot instance
            mission_system: The mission system service
            character_system: The character system service
            progression_engine: The progression engine service
        """
        self.bot = bot
        self.mission_system = mission_system or getattr(bot.services, 'mission_system', None)
        self.character_system = character_system or getattr(bot.services, 'character_system', None)
        self.progression_engine = progression_engine or getattr(bot.services, 'progression_engine', None)
        self.logger = logging.getLogger(__name__)

    @commands.command(name="mission_board")
    async def mission_board(self, ctx):
        """Display available missions."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            missions = await self.mission_system.get_available_missions()
            if not missions:
                await ctx.followup.send("No missions are currently available.")
                return
            
            # Format and send mission board
            mission_list = "\n".join([f"{i+1}. {m.title}" for i, m in enumerate(missions)])
            await ctx.followup.send(f"**Available Missions:**\n{mission_list}")
        except Exception as e:
            self.logger.error(f"Error in mission_board: {e}")
            await ctx.followup.send("An error occurred while fetching missions.")

    @commands.command(name="mission_accept")
    async def mission_accept(self, ctx, mission_number: int):
        """Accept a mission by its number."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            character = await self.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.followup.send("You don't have a character yet!")
                return

            missions = await self.mission_system.get_available_missions()
            if not missions:
                await ctx.followup.send("No missions are currently available.")
                return

            if mission_number < 1 or mission_number > len(missions):
                await ctx.followup.send("Invalid mission number!")
                return

            mission = missions[mission_number - 1]
            success = await self.mission_system.accept_mission(character, mission)
            
            if success:
                await ctx.followup.send(f"You have accepted the mission: {mission.title}")
            else:
                await ctx.followup.send("Failed to accept mission. You may already have an active mission.")
        except Exception as e:
            self.logger.error(f"Error in mission_accept: {e}")
            await ctx.followup.send("An error occurred while accepting the mission.")

    @commands.command(name="mission_progress")
    async def mission_progress(self, ctx):
        """Check progress of current mission."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            character = await self.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.followup.send("You don't have a character yet!")
                return

            active_mission = await self.mission_system.get_active_mission(character)
            if not active_mission:
                await ctx.followup.send("You don't have an active mission!")
                return

            progress = await self.mission_system.get_mission_progress(character, active_mission)
            await ctx.followup.send(f"**Mission Progress:**\n{progress}")
        except Exception as e:
            self.logger.error(f"Error in mission_progress: {e}")
            await ctx.followup.send("An error occurred while checking mission progress.")

    @commands.command(name="mission_roll")
    async def mission_roll(self, ctx):
        """Roll for mission success."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            character = await self.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.followup.send("You don't have a character yet!")
                return

            active_mission = await self.mission_system.get_active_mission(character)
            if not active_mission:
                await ctx.followup.send("You don't have an active mission!")
                return

            result = await self.mission_system.roll_mission(character, active_mission)
            await ctx.followup.send(f"**Mission Roll Result:**\n{result}")
        except Exception as e:
            self.logger.error(f"Error in mission_roll: {e}")
            await ctx.followup.send("An error occurred while rolling for mission success.")

    @commands.command(name="mission_complete")
    async def mission_complete(self, ctx):
        """Complete current mission."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            character = await self.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.followup.send("You don't have a character yet!")
                return

            active_mission = await self.mission_system.get_active_mission(character)
            if not active_mission:
                await ctx.followup.send("You don't have an active mission!")
                return

            success = await self.mission_system.complete_mission(character, active_mission)
            if success:
                await ctx.followup.send("Mission completed successfully!")
            else:
                await ctx.followup.send("Failed to complete mission. Make sure you've met all requirements.")
        except Exception as e:
            self.logger.error(f"Error in mission_complete: {e}")
            await ctx.followup.send("An error occurred while completing the mission.")

    @commands.command(name="mission_abandon")
    async def mission_abandon(self, ctx):
        """Abandon current mission."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            character = await self.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.followup.send("You don't have a character yet!")
                return

            active_mission = await self.mission_system.get_active_mission(character)
            if not active_mission:
                await ctx.followup.send("You don't have an active mission!")
                return

            success = await self.mission_system.abandon_mission(character, active_mission)
            if success:
                await ctx.followup.send("Mission abandoned successfully.")
            else:
                await ctx.followup.send("Failed to abandon mission.")
        except Exception as e:
            self.logger.error(f"Error in mission_abandon: {e}")
            await ctx.followup.send("An error occurred while abandoning the mission.")

    @commands.command(name="mission_history")
    async def mission_history(self, ctx):
        """View mission history."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            character = await self.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.followup.send("You don't have a character yet!")
                return

            history = await self.mission_system.get_mission_history(character)
            if not history:
                await ctx.followup.send("You haven't completed any missions yet!")
                return

            history_text = "\n".join([f"- {m.title} ({m.status})" for m in history])
            await ctx.followup.send(f"**Mission History:**\n{history_text}")
        except Exception as e:
            self.logger.error(f"Error in mission_history: {e}")
            await ctx.followup.send("An error occurred while fetching mission history.")

    @commands.command(name="mission_simulate")
    async def mission_simulate(self, ctx):
        """Simulate a mission outcome."""
        await ctx.response.defer(ephemeral=True, thinking=True)
        try:
            character = await self.character_system.get_character(ctx.author.id)
            if not character:
                await ctx.followup.send("You don't have a character yet!")
                return

            active_mission = await self.mission_system.get_active_mission(character)
            if not active_mission:
                await ctx.followup.send("You don't have an active mission!")
                return

            simulation = await self.mission_system.simulate_mission(character, active_mission)
            await ctx.followup.send(f"**Mission Simulation:**\n{simulation}")
        except Exception as e:
            self.logger.error(f"Error in mission_simulate: {e}")
            await ctx.followup.send("An error occurred while simulating the mission.") 