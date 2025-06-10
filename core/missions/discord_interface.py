"""
Discord interface for the mission system.
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from .mission import Mission, MissionStatus, MissionDifficulty
from .generator import MissionGenerator

logger = logging.getLogger(__name__)

class MissionInterface(commands.Cog):
    """Discord interface for the mission system."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_missions: Dict[str, List[Mission]] = {}
        self.player_missions: Dict[int, Mission] = {}
        self.kage_messages: Dict[str, str] = {
            "Leaf": "Hokage",
            "Sand": "Kazekage",
            "Mist": "Mizukage",
            "Cloud": "Raikage",
            "Stone": "Tsuchikage"
        }
        # Rate limiting
        self.command_locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.last_command: Dict[int, datetime] = {}
        self.command_cooldown = timedelta(seconds=2)  # Cooldown between commands
        self.mission_limit = 3  # Maximum active missions per user

    async def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user is rate limited.
        
        Args:
            user_id: The user's Discord ID
            
        Returns:
            True if user can proceed, False if rate limited
        """
        now = datetime.utcnow()
        if user_id in self.last_command:
            time_since_last = now - self.last_command[user_id]
            if time_since_last < self.command_cooldown:
                return False
        self.last_command[user_id] = now
        return True

    async def send_kage_message(self, user: discord.User, mission: Mission) -> None:
        """
        Send a secret mission message from the Kage.
        
        Args:
            user: The user to send the message to
            mission: The mission to send
        """
        kage_title = self.kage_messages.get(mission.village, "Kage")
        
        embed = discord.Embed(
            title=f"Secret Mission from the {kage_title}",
            description="*A mysterious message appears in your scroll...*",
            color=discord.Color.dark_red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Mission Rank",
            value=f"{mission.difficulty.value}-Rank",
            inline=True
        )
        embed.add_field(
            name="Time Limit",
            value=f"{mission.duration.total_seconds() / 3600:.1f} hours",
            inline=True
        )
        embed.add_field(
            name="Reward",
            value=f"{mission.reward['ryo']} Ryo + {mission.reward['exp']} EXP",
            inline=False
        )
        embed.add_field(
            name="Mission Details",
            value=mission.description,
            inline=False
        )
        
        if mission.requirements:
            reqs = []
            if "min_level" in mission.requirements:
                reqs.append(f"Minimum Level: {mission.requirements['min_level']}")
            if "team_size" in mission.requirements:
                reqs.append(f"Team Size: {mission.requirements['team_size']}")
            if "special_requirements" in mission.requirements:
                reqs.extend(mission.requirements["special_requirements"])
            
            embed.add_field(
                name="Requirements",
                value="\n".join(reqs),
                inline=False
            )
        
        embed.set_footer(text=f"From the {kage_title} of the {mission.village} Village")
        
        try:
            await user.send(embed=embed)
            logger.info(f"Sent mission {mission.id} to user {user.id}")
        except discord.Forbidden:
            logger.warning(f"Could not send DM to user {user.id}")

    @app_commands.command(name="mission")
    async def mission_command(
        self,
        interaction: discord.Interaction,
        difficulty: str,
        village: Optional[str] = None
    ) -> None:
        """
        Request a new mission.
        
        Args:
            interaction: The Discord interaction
            difficulty: The mission difficulty (D, C, B, A, S)
            village: Optional village to get mission from
        """
        await interaction.response.defer(ephemeral=True)
        
        # Check rate limit
        if not await self.check_rate_limit(interaction.user.id):
            await interaction.followup.send(
                "Please wait a moment before requesting another mission.",
                ephemeral=True
            )
            return
        
        # Use lock to prevent concurrent mission requests
        async with self.command_locks[interaction.user.id]:
            # Check active mission limit
            user_missions = [
                m for m in self.player_missions.values()
                if m.status == MissionStatus.IN_PROGRESS
            ]
            if len(user_missions) >= self.mission_limit:
                await interaction.followup.send(
                    f"You already have {self.mission_limit} active missions. "
                    "Complete some before taking new ones.",
                    ephemeral=True
                )
                return
            
            try:
                mission_difficulty = MissionDifficulty(difficulty.upper())
            except ValueError:
                await interaction.followup.send(
                    "Invalid difficulty! Please use D, C, B, A, or S.",
                    ephemeral=True
                )
                return
            
            if not village:
                # Get user's village from database or default to Leaf
                village = "Leaf"
            
            async with MissionGenerator() as generator:
                try:
                    mission = await generator.generate_mission(village, mission_difficulty)
                    
                    # Store mission
                    if village not in self.active_missions:
                        self.active_missions[village] = []
                    self.active_missions[village].append(mission)
                    self.player_missions[interaction.user.id] = mission
                    
                    # Send secret message
                    await self.send_kage_message(interaction.user, mission)
                    
                    await interaction.followup.send(
                        "A secret message has been sent to you from your Kage!",
                        ephemeral=True
                    )
                    
                except Exception as e:
                    logger.error(f"Error generating mission: {e}")
                    await interaction.followup.send(
                        "An error occurred while generating your mission. Please try again later.",
                        ephemeral=True
                    )

    @app_commands.command(name="missions")
    async def missions_command(self, interaction: discord.Interaction) -> None:
        """View your active missions."""
        await interaction.response.defer(ephemeral=True)
        
        if not await self.check_rate_limit(interaction.user.id):
            await interaction.followup.send(
                "Please wait a moment before checking missions again.",
                ephemeral=True
            )
            return
        
        async with self.command_locks[interaction.user.id]:
            user_missions = [
                mission for mission in self.player_missions.values()
                if mission.status == MissionStatus.IN_PROGRESS
            ]
            
            # Check for expired missions
            for mission in user_missions:
                if mission.check_expired():
                    logger.info(f"Mission {mission.id} expired for user {interaction.user.id}")
            
            # Filter out expired missions
            user_missions = [
                mission for mission in user_missions
                if mission.status == MissionStatus.IN_PROGRESS
            ]
            
            if not user_missions:
                await interaction.followup.send(
                    "You have no active missions.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="Your Active Missions",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            for mission in user_missions:
                time_left = mission.started_at + mission.duration - datetime.utcnow()
                hours_left = max(0, time_left.total_seconds() / 3600)
                
                embed.add_field(
                    name=f"{mission.title} ({mission.difficulty.value}-Rank)",
                    value=f"Time Remaining: {hours_left:.1f} hours\n"
                          f"Progress: {len(mission.progress)}/{len(mission.requirements)}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="complete_mission")
    async def complete_mission_command(
        self,
        interaction: discord.Interaction,
        mission_id: str
    ) -> None:
        """Complete a mission."""
        await interaction.response.defer(ephemeral=True)
        
        if not await self.check_rate_limit(interaction.user.id):
            await interaction.followup.send(
                "Please wait a moment before completing missions.",
                ephemeral=True
            )
            return
        
        async with self.command_locks[interaction.user.id]:
            mission = self.player_missions.get(interaction.user.id)
            if not mission or mission.id != mission_id:
                await interaction.followup.send(
                    "You don't have an active mission with that ID.",
                    ephemeral=True
                )
                return
            
            if mission.status != MissionStatus.IN_PROGRESS:
                await interaction.followup.send(
                    "This mission is not in progress.",
                    ephemeral=True
                )
                return
            
            # Check if mission has expired
            if mission.check_expired():
                await interaction.followup.send(
                    "This mission has expired!",
                    ephemeral=True
                )
                return
            
            # Check if all requirements are met
            if not all(
                key in mission.progress and mission.progress[key] >= value
                for key, value in mission.requirements.items()
                if isinstance(value, (int, float))
            ):
                await interaction.followup.send(
                    "You haven't met all the mission requirements yet!",
                    ephemeral=True
                )
                return
            
            mission.complete()
            
            # --- Give rewards --- #
            # TODO: Implement reward distribution - REMOVING COMMENT (Implemented)
            character = await self.character_system.get_character(str(interaction.user.id))
            currency_system = self.bot.services.currency_system 
            # Assume ProgressionEngine is accessible via CharacterSystem or services
            progression_engine = self.character_system.progression_engine or self.bot.services.progression_engine
            
            reward_msg_parts = ["Mission completed!"]
            save_needed = False
            
            if character and currency_system and progression_engine and mission.reward:
                ryo_reward = mission.reward.get('ryo', 0)
                exp_reward = mission.reward.get('exp', 0)
                item_rewards = mission.reward.get('items', []) # Expect list of item_id strings
                
                # 1. Add Ryo
                if ryo_reward > 0:
                    await currency_system.add_ryo(character.id, ryo_reward)
                    reward_msg_parts.append(f"Received **{ryo_reward:,}** Ryō.")
                    # Currency system handles its own saving
                    
                # 2. Add EXP
                if exp_reward > 0:
                    # Call grant_exp instead, passing the messages list
                    # await progression_engine.grant_exp(character.id, exp_reward, "mission completion", character=character, messages=reward_msg_parts)
                    grant_exp_result = await progression_engine.grant_exp(character.id, exp_reward, "mission completion", character=character)
                    
                    if grant_exp_result and grant_exp_result.get("messages"):
                         # Add messages from grant_exp (EXP gain, Level Up, Rank Up)
                         reward_msg_parts.extend(grant_exp_result["messages"]) 
                    else:
                         # Fallback message if grant_exp failed or returned nothing
                         reward_msg_parts.append(f"Gained **{exp_reward}** EXP.") 
                         
                    # grant_exp handles saving if level/rank changed
                    save_needed = False # Reset save flag as grant_exp handles it

                # 3. Add Items
                if item_rewards:
                    added_items_strs = []
                    item_manager = self.bot.services.item_manager # Get item manager
                    for item_id in item_rewards:
                        if character.add_item(item_id, 1):
                             item_name = item_manager.get_item_name(item_id) if item_manager else item_id
                             added_items_strs.append(f"**{item_name}**")
                             save_needed = True # Inventory changes require saving character
                        else:
                             logger.warning(f"Failed to add mission reward item '{item_id}' to character {character.id}")
                    if added_items_strs:
                         reward_msg_parts.append(f"Obtained items: {', '.join(added_items_strs)}.")
                         
                # 4. Save Character (if EXP or Items changed)
                if save_needed:
                    await self.character_system.save_character(character)
                    
            else:
                 logger.error(f"Missing systems or character or rewards for mission {mission_id} completion by {interaction.user.id}")
                 reward_msg_parts = ["Mission completed, but there was an error distributing rewards."]
                 
            # --- Send Final Message --- #
            # Remove the initial "Mission completed!" if grant_exp added messages
            if len(reward_msg_parts) > 1 and reward_msg_parts[0] == "Mission completed!":
                 reward_msg_parts.pop(0)
                 
            await interaction.followup.send(
                "\n".join(reward_msg_parts),
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Set up the mission interface."""
    await bot.add_cog(MissionInterface(bot)) 