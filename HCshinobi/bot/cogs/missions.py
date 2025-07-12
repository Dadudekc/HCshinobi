"""
Interactive ShinobiOS Mission Commands - Integrated with battle simulation.

Enhanced with Discord UI components for interactive mission battles similar to Solomon and PvP battles.

Features:
- Interactive mission battle interface with Discord buttons
- Real-time mission battle updates
- Jutsu selection during missions
- Mission objectives tracking
- Enhanced battle embeds

Commands:
- /mission_board - View available mission types
- /shinobios_mission - Start interactive mission battle
- /mission_status - Check mission progress (enhanced with interactive resume)
- /abandon_mission - Leave current mission
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


class MissionBattleView(discord.ui.View):
    """Interactive view for mission battles with buttons."""
    
    def __init__(self, cog, mission: ShinobiOSMission, user_id: int):
        super().__init__(timeout=1800)  # 30 minute timeout for missions
        self.cog = cog
        self.mission = mission
        self.user_id = user_id
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the mission participant can use buttons."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your mission!", ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Get player's jutsu for selection
        character_data = self.cog._load_character_data(str(self.user_id))
        if not character_data:
            await interaction.followup.send("❌ Character data not found!", ephemeral=True)
            return
            
        jutsu_list = character_data.get("jutsu", ["Basic Attack", "Punch", "Kick"])
        
        # Create jutsu selection view
        jutsu_view = MissionJutsuSelectionView(self.cog, self.mission, jutsu_list, self.user_id)
        
        embed = discord.Embed(
            title="🎯 Select Your Jutsu",
            description="Choose which jutsu to use against the enemies:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=jutsu_view, ephemeral=True)
    
    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.gray, emoji="📊")
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = self.cog._create_battle_embed(self.mission, "📊 Mission Battle Status")
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎯 Objectives", style=discord.ButtonStyle.gray, emoji="🎯")
    async def objectives_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🎯 Mission Objectives",
            description=f"**Mission:** {self.mission.title}",
            color=discord.Color.blue()
        )
        
        if self.mission.battle_state and self.mission.battle_state.objectives:
            objectives_text = "\n".join([
                f"• {obj}" for obj in self.mission.battle_state.objectives
            ])
            embed.add_field(name="Current Objectives", value=objectives_text, inline=False)
        else:
            embed.add_field(name="Current Objectives", value="• Defeat all enemies\n• Complete the mission", inline=False)
        
        # Show mission progress
        if self.mission.battle_state:
            enemies = self.mission.battle_state.get_enemies()
            alive_enemies = [e for e in enemies if e.stats.health > 0]
            total_enemies = len(enemies)
            remaining_enemies = len(alive_enemies)
            
            embed.add_field(
                name="📊 Progress",
                value=f"Enemies remaining: {remaining_enemies}/{total_enemies}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🏃 Abandon", style=discord.ButtonStyle.gray, emoji="🏃")
    async def abandon_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Create confirmation view
        confirm_view = MissionAbandonConfirmationView(self.cog, self.mission, self.user_id)
        
        embed = discord.Embed(
            title="🏃 Abandon Mission?",
            description="Are you sure you want to abandon this mission? You'll lose all progress and won't receive any rewards.",
            color=discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, view=confirm_view, ephemeral=True)
    
    @discord.ui.button(label="ℹ️ Help", style=discord.ButtonStyle.gray, emoji="ℹ️")
    async def help_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="ℹ️ Mission Battle Help",
            description="**How Mission Battles Work:**",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⚔️ Combat Actions",
            value="• **Attack:** Choose a jutsu to attack enemies\n• **Status:** View current battle statistics\n• **Objectives:** Check mission goals and progress",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Mission Goals",
            value="• Complete all mission objectives\n• Defeat required enemies\n• Survive the encounter",
            inline=False
        )
        
        embed.add_field(
            name="🏆 Victory Conditions",
            value="• Complete all objectives\n• Defeat all enemies (if required)\n• Reach mission completion criteria",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class MissionJutsuSelectionView(discord.ui.View):
    """View for selecting jutsu during mission battles."""
    
    def __init__(self, cog, mission: ShinobiOSMission, jutsu_list: List[str], user_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.mission = mission
        self.jutsu_list = jutsu_list
        self.user_id = user_id
        
        # Add jutsu buttons (max 5 due to Discord limits)
        for i, jutsu in enumerate(jutsu_list[:5]):
            button = discord.ui.Button(
                label=jutsu,
                style=discord.ButtonStyle.primary,
                custom_id=f"jutsu_{i}"
            )
            button.callback = self.jutsu_callback
            self.add_item(button)
    
    async def jutsu_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get the selected jutsu
        button_id = interaction.data['custom_id']
        jutsu_index = int(button_id.split('_')[1])
        selected_jutsu = self.jutsu_list[jutsu_index]
        
        # Execute the mission attack
        await self.cog.execute_mission_attack(interaction, self.mission, selected_jutsu, self.user_id)


class MissionAbandonConfirmationView(discord.ui.View):
    """View for confirming mission abandon action."""
    
    def __init__(self, cog, mission: ShinobiOSMission, user_id: int):
        super().__init__(timeout=30)
        self.cog = cog
        self.mission = mission
        self.user_id = user_id
    
    @discord.ui.button(label="Yes, Abandon", style=discord.ButtonStyle.danger, emoji="🏃")
    async def confirm_abandon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.execute_mission_abandon(interaction, self.mission, self.user_id)
    
    @discord.ui.button(label="No, Continue", style=discord.ButtonStyle.gray, emoji="⚔️")
    async def cancel_abandon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="⚔️ Mission Continues!",
            description="You decide to press on and complete the mission!",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

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
            value="• `/shinobios_mission` - Start an interactive battle mission\n• Interactive buttons for combat (Attack/Status/Objectives/Help)\n• `/mission_status` - Check mission progress\n• `/abandon_mission` - Leave current mission",
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
        
        # Start interactive mission battle
        await asyncio.sleep(2)
        await self._start_interactive_mission_battle(interaction, mission)
    
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

    async def _start_interactive_mission_battle(self, interaction: discord.Interaction, mission: ShinobiOSMission):
        """Start an interactive mission battle with Discord UI components."""
        try:
            # Create enhanced battle embed
            embed = self._create_interactive_mission_embed(mission)
            view = MissionBattleView(self, mission, interaction.user.id)
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error starting interactive mission: {str(e)}", ephemeral=True)

    def _create_interactive_mission_embed(self, mission: ShinobiOSMission) -> discord.Embed:
        """Create an enhanced mission battle embed for interactive UI."""
        if not mission.battle_state:
            return create_error_embed("Battle not initialized")
        
        embed = discord.Embed(
            title="⚔️ **MISSION BATTLE** ⚔️",
            description=f"**Mission:** {mission.title}\n**Environment:** {mission.battle_state.environment.name if mission.battle_state.environment else 'Unknown'}",
            color=discord.Color.red()
        )
        
        # Add participants with enhanced formatting
        players = mission.battle_state.get_players()
        enemies = mission.battle_state.get_enemies()
        
        if players:
            for i, player in enumerate(players):
                hp_percent = (player.stats.health / player.stats.max_health) * 100 if player.stats.max_health > 0 else 0
                chakra_percent = (player.stats.chakra / player.stats.max_chakra) * 100 if player.stats.max_chakra > 0 else 0
                
                embed.add_field(
                    name=f"👤 **{player.name}** (Player)",
                    value=f"**HP:** {player.stats.health}/{player.stats.max_health} ({hp_percent:.1f}%)\n"
                          f"**Chakra:** {player.stats.chakra}/{player.stats.max_chakra} ({chakra_percent:.1f}%)\n"
                          f"**Level:** {player.stats.level}",
                    inline=True
                )
        
        if enemies:
            alive_enemies = [e for e in enemies if e.stats.health > 0]
            for i, enemy in enumerate(alive_enemies[:3]):  # Show max 3 enemies
                hp_percent = (enemy.stats.health / enemy.stats.max_health) * 100 if enemy.stats.max_health > 0 else 0
                
                embed.add_field(
                    name=f"👹 **{enemy.name}** (Enemy {i+1})",
                    value=f"**HP:** {enemy.stats.health}/{enemy.stats.max_health} ({hp_percent:.1f}%)\n"
                          f"**Level:** {enemy.stats.level}",
                    inline=True
                )
            
            if len(alive_enemies) > 3:
                embed.add_field(
                    name="➕ More Enemies",
                    value=f"...and {len(alive_enemies) - 3} more enemies",
                    inline=True
                )
        
        # Add objectives
        if mission.battle_state.objectives:
            objectives_text = "\n".join([f"• {obj}" for obj in mission.battle_state.objectives])
            embed.add_field(name="🎯 Objectives", value=objectives_text, inline=False)
        
        # Add recent actions
        if mission.battle_state.battle_log:
            recent_actions = mission.battle_state.battle_log[-2:]
            action_text = "\n".join([
                f"**{action['actor']}** used {action['jutsu']} → {action['damage']} damage"
                for action in recent_actions
            ])
            embed.add_field(name="⚡ Recent Actions", value=action_text, inline=False)
        
        embed.set_footer(text="Use the buttons below to take action in battle!")
        
        return embed

    async def execute_mission_attack(self, interaction: discord.Interaction, mission: ShinobiOSMission, jutsu_name: str, user_id: int):
        """Execute a mission attack with interactive feedback."""
        try:
            user_id_str = str(user_id)
            
            # Get available enemies for auto-targeting
            enemies = mission.battle_state.get_enemies()
            alive_enemies = [e for e in enemies if e.stats.health > 0]
            
            if not alive_enemies:
                await interaction.followup.send("✅ No enemies remaining! Mission objectives may be complete.", ephemeral=True)
                return
            
            # Auto-target first alive enemy
            target_id = alive_enemies[0].user_id
            
            # Execute action
            result = await mission.execute_player_action(user_id_str, jutsu_name, target_id)
            
            if not result["success"]:
                await interaction.followup.send(f"❌ Attack failed: {result['error']}", ephemeral=True)
                return
            
            # Get action details
            action = result["action"]
            
            # Update mission embed
            embed = self._create_interactive_mission_embed(mission)
            
            # Add attack results to embed
            embed.add_field(
                name="💥 Your Attack",
                value=f"**{jutsu_name}** → **{action['target']}**\n"
                      f"Damage: {action['damage']} | Success: {'✅' if action['success'] else '❌'}",
                inline=False
            )
            
            view = MissionBattleView(self, mission, user_id)
            
            await interaction.followup.send(embed=embed, view=view)
            
            # Execute enemy turn after a delay
            await asyncio.sleep(1.5)
            await self._execute_enemy_turn(interaction, mission, user_id)
            
            # Check mission completion
            completion = result["completion_status"]
            if completion["completed"]:
                if completion["status"] == "success":
                    await self._handle_interactive_mission_success(interaction, mission)
                else:
                    await self._handle_interactive_mission_failure(interaction, mission)
                    
        except Exception as e:
            await interaction.followup.send(f"❌ Error during attack: {str(e)}", ephemeral=True)

    async def _execute_enemy_turn(self, interaction: discord.Interaction, mission: ShinobiOSMission, user_id: int):
        """Execute enemy turn in interactive mission."""
        try:
            enemy_actions = await mission.execute_enemy_turn()
            
            if enemy_actions:
                # Create enemy action embed
                embed = discord.Embed(
                    title="👹 **ENEMY TURN** 👹",
                    description="The enemies strike back!",
                    color=discord.Color.dark_red()
                )
                
                for i, action in enumerate(enemy_actions[:3]):  # Show max 3 actions
                    embed.add_field(
                        name=f"Attack {i+1}: {action['actor']}",
                        value=f"**{action['jutsu']}** → **{action['target']}**\n"
                              f"Damage: {action['damage']}",
                        inline=True
                    )
                
                await interaction.followup.send(embed=embed)
                
                # Send updated mission status after enemy turn
                await asyncio.sleep(1)
                updated_embed = self._create_interactive_mission_embed(mission)
                view = MissionBattleView(self, mission, user_id)
                
                await interaction.followup.send(embed=updated_embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error during enemy turn: {str(e)}", ephemeral=True)

    async def _handle_interactive_mission_success(self, interaction: discord.Interaction, mission: ShinobiOSMission):
        """Handle interactive mission success."""
        try:
            embed = discord.Embed(
                title="🏆 **MISSION COMPLETE!** 🏆",
                description="Excellent work! You have successfully completed the mission.",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🎉 Mission Success",
                value=f"**{mission.title}** has been completed!",
                inline=False
            )
            
            embed.add_field(
                name="💰 Rewards Earned",
                value=f"**Experience:** +{mission.reward.get('experience', 0)}\n"
                      f"**Currency:** +{mission.reward.get('currency', 0)} ryo",
                inline=False
            )
            
            embed.add_field(
                name="📊 Mission Stats",
                value=f"**Difficulty:** {mission.difficulty}-Rank\n"
                      f"**Environment:** {mission.battle_state.environment.name if mission.battle_state.environment else 'Unknown'}\n"
                      f"**Battle ID:** {mission.battle_id}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
            # Clean up mission
            self._cleanup_mission(mission.id)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error handling mission success: {str(e)}", ephemeral=True)

    async def _handle_interactive_mission_failure(self, interaction: discord.Interaction, mission: ShinobiOSMission):
        """Handle interactive mission failure."""
        try:
            embed = discord.Embed(
                title="💀 **MISSION FAILED** 💀",
                description="The mission has ended in failure...",
                color=discord.Color.dark_red()
            )
            
            embed.add_field(
                name="💔 Defeat",
                value="You have been defeated in battle. Better luck next time!",
                inline=False
            )
            
            embed.add_field(
                name="📊 Mission Info",
                value=f"**Mission:** {mission.title}\n"
                      f"**Difficulty:** {mission.difficulty}-Rank",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
            # Clean up mission
            self._cleanup_mission(mission.id)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error handling mission failure: {str(e)}", ephemeral=True)

    async def execute_mission_abandon(self, interaction: discord.Interaction, mission: ShinobiOSMission, user_id: int):
        """Handle mission abandonment."""
        try:
            embed = discord.Embed(
                title="🏃 **MISSION ABANDONED** 🏃",
                description=f"You have abandoned: **{mission.title}**",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="⚠️ Consequences",
                value="• No rewards earned\n• Mission progress lost\n• Return to base",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
            # Clean up mission
            self._cleanup_mission(mission.id)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error abandoning mission: {str(e)}", ephemeral=True)

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

    @app_commands.command(name="mission_status", description="Check current mission status and resume interactive battle")
    async def mission_status(self, interaction: discord.Interaction):
        """Check current mission status and resume interactive battle"""
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
        
        # Create interactive mission resume
        embed = self._create_interactive_mission_embed(mission)
        embed.title = "📊 **CURRENT MISSION STATUS** 📊"
        view = MissionBattleView(self, mission, interaction.user.id)
        
        await interaction.response.send_message(embed=embed, view=view)

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

    @commands.command(name="test_mission")
    @commands.has_permissions(administrator=True)
    async def test_mission(self, ctx: commands.Context):
        """Test command for interactive missions (admin only)."""
        try:
            user_id = str(ctx.author.id)
            
            # Check if user already has an active mission
            if user_id in self.player_missions:
                await ctx.send("❌ You already have an active mission! Use `/mission_status` to resume it.")
                return
            
            # Load character data
            character_data = self._load_character_data(user_id)
            if not character_data:
                await ctx.send("❌ You need to create a character first! Use `/create` command.")
                return
            
            # Create test mission
            mission = ShinobiOSMission(
                engine=self.engine,
                id=str(random.randint(10000, 99999)),
                title="🧪 TEST MISSION: Forest Combat Training",
                description="An interactive test mission in the forest environment",
                difficulty="C",
                village=character_data.get("village", "Unknown"),
                reward={"experience": 200, "currency": 100},
                duration=timedelta(hours=1)
            )
            
            # Initialize battle with test data
            players = [{
                "user_id": user_id,
                "name": character_data.get("name", ctx.author.display_name),
                "level": character_data.get("level", 1),
                "stats": character_data.get("stats", {})
            }]
            
            mission.initialize_battle(players, "forest")
            
            # Store mission
            self.active_missions[mission.id] = mission
            self.player_missions[user_id] = mission.id
            
            # Create opening embed
            embed = discord.Embed(
                title="🧪 **TEST MISSION STARTED** 🧪",
                description="**Mission:** Forest Combat Training (TEST)\n**Environment:** Forest\n**Difficulty:** C-Rank",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="🎯 Test Features",
                value="• Interactive Discord buttons\n• Real-time battle updates\n• Jutsu selection interface\n• Mission objectives tracking",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Test Note",
                value="This is a test mission for admins to verify the interactive mission system is working correctly.",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Start interactive mission battle
            await asyncio.sleep(2)
            
            # Create interaction-like object for testing
            class TestInteraction:
                def __init__(self, user):
                    self.user = user
                    
                async def followup_send(self, **kwargs):
                    await ctx.send(**kwargs)
            
            test_interaction = TestInteraction(ctx.author)
            await self._start_interactive_mission_battle(test_interaction, mission)
            
        except Exception as e:
            await ctx.send(f"❌ Error creating test mission: {str(e)}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MissionCommands(bot))
