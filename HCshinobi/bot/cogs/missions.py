"""
ShinobiOS Mission Commands - Integrated with battle simulation.
"""

import asyncio
import json
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ...core.missions.shinobios_engine import ShinobiOSEngine
from ...core.missions.shinobios_mission import ShinobiOSMission, BattleMissionType
from ...core.missions.mission import MissionDifficulty
from ...utils.embeds import create_error_embed, create_success_embed, create_info_embed

class MissionCommands(commands.Cog):
    """Mission Commands with ShinobiOS Battle Integration"""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.engine = ShinobiOSEngine()
        self.active_missions: Dict[str, ShinobiOSMission] = {}
        self.player_missions: Dict[str, str] = {}  # user_id -> mission_id
        
    def _load_character_data(self, user_id: str) -> Optional[Dict]:
        """Load character data for a user"""
        try:
            with open(f"data/characters/{user_id}.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def _create_battle_embed(self, mission: ShinobiOSMission, title: str = "Mission Status") -> discord.Embed:
        """Create a mission status embed"""
        if not mission.battle_state:
            return create_error_embed("Battle not initialized")
        
        embed = discord.Embed(
            title=f"⚔️ {title}",
            description=f"**Mission:** {mission.title}\n**Environment:** {mission.battle_state.environment.name if mission.battle_state.environment else 'Unknown'}",
            color=0x00ff00
        )
        
        # Add participants
        players = mission.battle_state.get_players()
        enemies = mission.battle_state.get_enemies()
        
        if players:
            player_text = "\n".join([
                f"🟢 **{p.name}** - HP: {p.stats.health}/{p.stats.max_health} | Chakra: {p.stats.chakra}/{p.stats.max_chakra}"
                for p in players
            ])
            embed.add_field(name="🎯 Players", value=player_text, inline=False)
        
        if enemies:
            enemy_text = "\n".join([
                f"🔴 **{e.name}** - HP: {e.stats.health}/{e.stats.max_health} | Level: {e.stats.level}"
                for e in enemies
            ])
            embed.add_field(name="👹 Enemies", value=enemy_text, inline=False)
        
        # Add objectives
        if mission.battle_state.objectives:
            objectives_text = "\n".join([
                f"• {obj}" for obj in mission.battle_state.objectives
            ])
            embed.add_field(name="🎯 Objectives", value=objectives_text, inline=False)
        
        # Add recent actions
        if mission.battle_state.battle_log:
            recent_actions = mission.battle_state.battle_log[-3:]
            action_text = "\n".join([
                f"**{action['actor']}** used {action['jutsu']} on {action['target']} - {action['damage']} damage"
                for action in recent_actions
            ])
            embed.add_field(name="⚡ Recent Actions", value=action_text, inline=False)
        
        embed.set_footer(text=f"Turn: {mission.battle_state.current_turn} | Battle ID: {mission.battle_id}")
        return embed

    @app_commands.command(name="mission_board", description="Show available missions")
    async def mission_board(self, interaction: discord.Interaction):
        """Show available missions with ShinobiOS integration"""
        embed = discord.Embed(
            title="📋 Mission Board",
            description="Available ShinobiOS Battle Missions",
            color=0x0099ff
        )
        
        # Show mission types
        embed.add_field(
            name="🎯 Mission Types",
            value="• **D-Rank**: Basic training missions\n• **C-Rank**: Escort and delivery\n• **B-Rank**: Combat missions\n• **A-Rank**: High-risk operations\n• **S-Rank**: Legendary challenges",
            inline=False
        )
        
        embed.add_field(
            name="🌍 Environments",
            value="• **Forest**: Stealth and nature jutsu\n• **Desert**: Harsh conditions\n• **Mountain**: High-altitude combat\n• **Urban**: Close-quarters battle\n• **Underground**: Confined spaces\n• **Water**: Aquatic combat\n• **Volcanic**: Extreme conditions",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ Commands",
            value="• `/shinobios_mission` - Start a battle mission\n• `/battle_action` - Execute combat actions\n• `/mission_status` - Check mission progress\n• `/available_jutsu` - View your jutsu\n• `/abandon_mission` - Leave current mission",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shinobios_mission", description="Start a ShinobiOS battle mission")
    @app_commands.describe(
        difficulty="Mission difficulty (D/C/B/A/S)",
        environment="Battle environment (forest/desert/mountain/urban/underground/water/volcanic)"
    )
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name="D-Rank", value="D"),
            app_commands.Choice(name="C-Rank", value="C"),
            app_commands.Choice(name="B-Rank", value="B"),
            app_commands.Choice(name="A-Rank", value="A"),
            app_commands.Choice(name="S-Rank", value="S")
        ],
        environment=[
            app_commands.Choice(name="Forest", value="forest"),
            app_commands.Choice(name="Desert", value="desert"),
            app_commands.Choice(name="Mountain", value="mountain"),
            app_commands.Choice(name="Urban", value="urban"),
            app_commands.Choice(name="Underground", value="underground"),
            app_commands.Choice(name="Water", value="water"),
            app_commands.Choice(name="Volcanic", value="volcanic")
        ]
    )
    async def start_shinobios_mission(self, interaction: discord.Interaction, 
                                     difficulty: str, environment: str):
        """Start a new ShinobiOS battle mission"""
        user_id = str(interaction.user.id)
        
        # Check if player is already in a mission
        if user_id in self.player_missions:
            mission_id = self.player_missions[user_id]
            if mission_id in self.active_missions:
                await interaction.response.send_message(
                    embed=create_error_embed("You are already in an active mission!"),
                    ephemeral=True
                )
                return
        
        # Load character data
        character_data = self._load_character_data(user_id)
        if not character_data:
            await interaction.response.send_message(
                embed=create_error_embed("Character not found! Create a character first."),
                ephemeral=True
            )
            return
        
        # Create mission
        mission = ShinobiOSMission(
            engine=self.engine,
            id=str(random.randint(10000, 99999)),
            title=f"{difficulty}-Rank Mission: {environment.title()} Battle",
            description=f"An intense battle in the {environment} environment",
            difficulty=difficulty,
            village=character_data.get("village", "Unknown"),
            reward={"experience": 100, "currency": 50},
            duration=timedelta(hours=2)
        )
        
        # Initialize battle
        players = [{
            "user_id": user_id,
            "name": character_data.get("name", interaction.user.display_name),
            "level": character_data.get("level", 1),
            "stats": character_data.get("stats", {})
        }]
        
        mission.initialize_battle(players, environment)
        
        # Store mission
        self.active_missions[mission.id] = mission
        self.player_missions[user_id] = mission.id
        
        # Create opening narration
        opening_narration = self._generate_opening_narration(mission, character_data)
        
        embed = discord.Embed(
            title="🌅 Mission Started",
            description=opening_narration,
            color=0x00ff00
        )
        embed.add_field(
            name="Mission Details",
            value=f"**Difficulty:** {difficulty}-Rank\n**Environment:** {environment.title()}\n**Duration:** 2 hours",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Send initial battle status
        battle_embed = self._create_battle_embed(mission, "Battle Commenced")
        await interaction.followup.send(embed=battle_embed)
    
    def _generate_opening_narration(self, mission: ShinobiOSMission, character_data: Dict) -> str:
        """Generate immersive opening narration"""
        environment = mission.battle_state.environment.name if mission.battle_state.environment else "Unknown"
        character_name = character_data.get("name", "Shinobi")
        
        narrations = {
            "forest": f"The dense canopy of the forest filters sunlight as **{character_name}** moves silently through the undergrowth. The air is thick with the scent of earth and leaves, and every rustle could be friend or foe...",
            "desert": f"The scorching sun beats down mercilessly as **{character_name}** trudges through the endless dunes. The heat distorts the horizon, and survival itself becomes a battle...",
            "mountain": f"High in the rocky peaks, **{character_name}** navigates treacherous terrain. The thin air makes every movement more difficult, but the high ground offers strategic advantage...",
            "urban": f"Among the towering buildings and narrow alleys, **{character_name}** moves like a shadow. The urban environment provides both cover and danger in equal measure...",
            "underground": f"In the depths of the underground caverns, **{character_name}** relies on heightened senses. The confined space amplifies every sound and makes escape difficult...",
            "water": f"On the vast expanse of water, **{character_name}** must adapt to an environment where solid ground is scarce. The water both hinders and enhances certain techniques...",
            "volcanic": f"Amidst the unstable volcanic terrain, **{character_name}** faces not just enemies but the very environment itself. The heat and unstable ground make every step dangerous..."
        }
        
        return narrations.get(environment.lower(), f"**{character_name}** prepares for battle in the {environment}...")

    @app_commands.command(name="battle_action", description="Execute a battle action")
    @app_commands.describe(
        jutsu="Jutsu to use",
        target="Target to attack (enemy number or 'auto')"
    )
    async def battle_action(self, interaction: discord.Interaction, jutsu: str, target: str = "auto"):
        """Execute a battle action"""
        user_id = str(interaction.user.id)
        
        # Check if player is in a mission
        if user_id not in self.player_missions:
            await interaction.response.send_message(
                embed=create_error_embed("You are not in an active mission!"),
                ephemeral=True
            )
            return
        
        mission_id = self.player_missions[user_id]
        if mission_id not in self.active_missions:
            await interaction.response.send_message(
                embed=create_error_embed("Mission not found!"),
                ephemeral=True
            )
            return
        
        mission = self.active_missions[mission_id]
        
        # Determine target
        target_id = target
        if target.lower() == "auto":
            enemies = mission.battle_state.get_enemies()
            if enemies:
                target_id = enemies[0].user_id
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("No enemies to target!"),
                    ephemeral=True
                )
                return
        
        # Execute action
        try:
            result = await mission.execute_player_action(user_id, jutsu, target_id)
            
            if not result["success"]:
                await interaction.response.send_message(
                    embed=create_error_embed(result["error"]),
                    ephemeral=True
                )
                return
            
            # Create action embed
            action = result["action"]
            embed = discord.Embed(
                title="⚔️ Battle Action",
                description=action["narration"],
                color=0xff6600
            )
            embed.add_field(
                name="Action Details",
                value=f"**Jutsu:** {action['jutsu']}\n**Target:** {action['target']}\n**Damage:** {action['damage']}\n**Success:** {'✅' if action['success'] else '❌'}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Execute enemy turn
            enemy_actions = await mission.execute_enemy_turn()
            
            if enemy_actions:
                enemy_embed = discord.Embed(
                    title="👹 Enemy Actions",
                    color=0xff0000
                )
                
                for action in enemy_actions:
                    enemy_embed.add_field(
                        name=f"{action['actor']} → {action['target']}",
                        value=f"**{action['jutsu']}** - {action['damage']} damage\n{action['narration']}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=enemy_embed)
            
            # Check mission completion
            completion = result["completion_status"]
            if completion["completed"]:
                if completion["status"] == "success":
                    await self._handle_mission_success(interaction, mission)
                else:
                    await self._handle_mission_failure(interaction, mission)
            else:
                # Send updated mission status
                mission_embed = self._create_battle_embed(mission, "Mission Status")
                await interaction.followup.send(embed=mission_embed)
                
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error executing action: {str(e)}"),
                ephemeral=True
            )

    async def _handle_mission_success(self, interaction: discord.Interaction, mission: ShinobiOSMission):
        """Handle mission success"""
        user_id = str(interaction.user.id)
        
        # Create success embed
        embed = discord.Embed(
            title="🎉 Mission Success!",
            description="You have emerged victorious from the battle!",
            color=0x00ff00
        )
        embed.add_field(
            name="Rewards",
            value=f"**Experience:** +{mission.reward.get('experience', 0)}\n**Currency:** +{mission.reward.get('currency', 0)}",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        # Clean up mission
        self._cleanup_mission(mission.id)

    async def _handle_mission_failure(self, interaction: discord.Interaction, mission: ShinobiOSMission):
        """Handle mission failure"""
        embed = discord.Embed(
            title="💀 Mission Failed",
            description="You have been defeated in battle...",
            color=0xff0000
        )
        
        await interaction.followup.send(embed=embed)
        
        # Clean up mission
        self._cleanup_mission(mission.id)

    def _cleanup_mission(self, mission_id: str):
        """Clean up completed mission"""
        if mission_id in self.active_missions:
            mission = self.active_missions[mission_id]
            
            # Remove from player missions
            for user_id, mid in list(self.player_missions.items()):
                if mid == mission_id:
                    del self.player_missions[user_id]
            
            # Remove from active missions
            del self.active_missions[mission_id]

    @app_commands.command(name="mission_status", description="Check current mission status")
    async def mission_status(self, interaction: discord.Interaction):
        """Check current mission status"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.player_missions:
            await interaction.response.send_message(
                embed=create_error_embed("You are not in an active mission!"),
                ephemeral=True
            )
            return
        
        mission_id = self.player_missions[user_id]
        if mission_id not in self.active_missions:
            await interaction.response.send_message(
                embed=create_error_embed("Mission not found!"),
                ephemeral=True
            )
            return
        
        mission = self.active_missions[mission_id]
        mission_embed = self._create_battle_embed(mission, "Current Mission Status")
        
        await interaction.response.send_message(embed=mission_embed)

    @app_commands.command(name="available_jutsu", description="Show available jutsu")
    async def available_jutsu(self, interaction: discord.Interaction):
        """Show available jutsu for current character"""
        user_id = str(interaction.user.id)
        
        # Load character data
        character_data = self._load_character_data(user_id)
        if not character_data:
            await interaction.response.send_message(
                embed=create_error_embed("Character not found!"),
                ephemeral=True
            )
            return
        
        # Create character stats
        character_stats = self.engine.create_shinobi(
            name=character_data.get("name", "Shinobi"),
            level=character_data.get("level", 1),
            **character_data.get("stats", {})
        )
        
        # Get available jutsu
        available_jutsu = self.engine.get_available_jutsu(character_stats)
        
        embed = discord.Embed(
            title="📜 Available Jutsu",
            description=f"Jutsu available to **{character_stats.name}** (Level {character_stats.level})",
            color=0x0099ff
        )
        
        for jutsu in available_jutsu:
            embed.add_field(
                name=f"🔥 {jutsu.name}",
                value=f"**Cost:** {jutsu.chakra_cost} Chakra\n**Damage:** {jutsu.damage}\n**Accuracy:** {jutsu.accuracy}%\n**Element:** {jutsu.element}\n**Range:** {jutsu.range}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="abandon_mission", description="Abandon current mission")
    async def abandon_mission(self, interaction: discord.Interaction):
        """Abandon current mission"""
        user_id = str(interaction.user.id)
        
        if user_id not in self.player_missions:
            await interaction.response.send_message(
                embed=create_error_embed("You are not in an active mission!"),
                ephemeral=True
            )
            return
        
        mission_id = self.player_missions[user_id]
        if mission_id not in self.active_missions:
            await interaction.response.send_message(
                embed=create_error_embed("Mission not found!"),
                ephemeral=True
            )
            return
        
        # Clean up mission
        self._cleanup_mission(mission_id)
        
        embed = discord.Embed(
            title="🏳️ Mission Abandoned",
            description="You have abandoned your current mission.",
            color=0xffff00
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MissionCommands(bot))
