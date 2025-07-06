"""
Ultimate Boss Battle System - Solomon: The Burning Revenant
The pinnacle of combat challenges in the HCshinobi world.
"""
import json
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import discord
from discord import app_commands
from discord.ext import commands

class BossBattleSystem:
    """Ultimate boss battle system for legendary encounters."""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_boss_battles = {}
        self.boss_cooldowns = {}
        self.boss_data_path = "data/characters/solomon.json"
        self.boss_data = self.load_boss_data()
        
    def load_boss_data(self) -> Dict[str, Any]:
        """Load boss character data."""
        try:
            with open(self.boss_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
            
    def save_boss_data(self):
        """Save boss character data."""
        with open(self.boss_data_path, 'w', encoding='utf-8') as f:
            json.dump(self.boss_data, f, indent=4, ensure_ascii=False)
            
    def get_current_phase(self, boss_hp_percentage: float) -> Dict[str, Any]:
        """Get the current boss phase based on HP percentage."""
        for phase in self.boss_data.get("boss_phases", []):
            if boss_hp_percentage >= phase["hp_threshold"]:
                return phase
        return self.boss_data.get("boss_phases", [])[-1] if self.boss_data.get("boss_phases") else {}
        
    def calculate_boss_damage(self, jutsu_name: str, phase: Dict[str, Any]) -> int:
        """Calculate boss damage based on jutsu and current phase."""
        base_damage = {
            "Katon: Gōka Messhitsu": 80,
            "Katon: Gōryūka no Jutsu": 100,
            "Sharingan Genjutsu": 60,
            "Adamantine Chakra-Forged Chains": 90,
            "Amaterasu": 150,
            "Kamui Phase": 0,  # Dodge
            "Yōton: Maguma Hōkai": 120,
            "Yōton: Ryūsei no Jutsu": 140,
            "Susanoo: Ōkami no Yōsei": 200,
            "Yōton: Enkō no Ōkami": 180,
            "Kōkō no Kusari": 160,
            "Eclipse Fang Severance": 250,
            "Ōkami no Yōsei Susanoo: Final Incarnation": 300,
            "Yōton: Enkō no Ōkami: Pack Release": 220,
            "Summoning: Wolves of Kiba no Tōdai": 280
        }
        
        damage = base_damage.get(jutsu_name, 100)
        
        # Phase multipliers
        phase_multipliers = {
            "Phase 1: The Crimson Shadow": 1.0,
            "Phase 2: The Burning Revenant": 1.3,
            "Phase 3: The Exiled Flame": 1.6,
            "Phase 4: The Ultimate Being": 2.0
        }
        
        multiplier = phase_multipliers.get(phase.get("name", ""), 1.0)
        return int(damage * multiplier)
        
    def get_boss_jutsu(self, phase: Dict[str, Any]) -> str:
        """Get a random jutsu from the current phase's jutsu pool."""
        jutsu_pool = phase.get("jutsu_pool", [])
        if not jutsu_pool:
            return "Basic Attack"
        return random.choice(jutsu_pool)
        
    def check_boss_requirements(self, character_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if character meets boss battle requirements."""
        requirements = self.boss_data.get("boss_requirements", {})
        
        # Level requirement
        min_level = requirements.get("min_level", 50)
        if character_data.get("level", 0) < min_level:
            return False, f"You must be at least level {min_level} to challenge Solomon."
            
        # Achievement requirements
        required_achievements = requirements.get("required_achievements", [])
        character_achievements = character_data.get("achievements", [])
        for achievement in required_achievements:
            if achievement not in character_achievements:
                return False, f"You need the '{achievement}' achievement to challenge Solomon."
                
        # Cooldown check
        user_id = str(character_data.get("id", ""))
        cooldown_hours = requirements.get("cooldown_hours", 168)
        last_battle = self.boss_cooldowns.get(user_id)
        
        if last_battle:
            time_since_battle = datetime.now() - last_battle
            if time_since_battle < timedelta(hours=cooldown_hours):
                remaining_time = timedelta(hours=cooldown_hours) - time_since_battle
                return False, f"Solomon is recovering. You can challenge him again in {remaining_time.days}d {remaining_time.seconds//3600}h."
                
        return True, "Requirements met."
        
    async def start_boss_battle(self, interaction: discord.Interaction, character_data: Dict[str, Any]) -> bool:
        """Start a boss battle with Solomon."""
        user_id = str(character_data.get("id", ""))
        
        # Check if already in battle
        if user_id in self.active_boss_battles:
            await interaction.followup.send("❌ You are already in a battle with Solomon!")
            return False
            
        # Check requirements
        can_battle, message = self.check_boss_requirements(character_data)
        if not can_battle:
            await interaction.followup.send(f"❌ {message}")
            return False
            
        # Initialize battle
        battle_data = {
            "user_id": user_id,
            "character": character_data.copy(),
            "boss": self.boss_data.copy(),
            "current_phase": 0,
            "turn": 1,
            "battle_log": [],
            "started_at": datetime.now()
        }
        
        self.active_boss_battles[user_id] = battle_data
        
        # Create battle embed
        embed = self.create_battle_embed(battle_data, "battle_start")
        await interaction.followup.send(embed=embed)
        
        return True
        
    def create_battle_embed(self, battle_data: Dict[str, Any], embed_type: str) -> discord.Embed:
        """Create battle embed based on type."""
        character = battle_data["character"]
        boss = battle_data["boss"]
        current_phase = self.get_current_phase(boss["hp"] / boss["max_hp"])
        
        if embed_type == "battle_start":
            embed = discord.Embed(
                title="🔥 **SOLOMON - THE BURNING REVENANT** 🔥",
                description="**The Ultimate Being has appeared!**\n\n"
                           "**Solomon** - The legendary Uchiha exile, perfect Jinchūriki of Son Gokū, "
                           "and master of the Eternal Mangekyō Sharingan stands before you.\n\n"
                           "**Current Phase:** " + current_phase.get("name", "Unknown") + "\n"
                           "**Phase Description:** " + current_phase.get("description", ""),
                color=0xFF0000
            )
            
        elif embed_type == "battle_turn":
            embed = discord.Embed(
                title="⚔️ **BATTLE TURN " + str(battle_data["turn"]) + "** ⚔️",
                description="**The battle rages on!**",
                color=0xFF6600
            )
            
        elif embed_type == "battle_end":
            embed = discord.Embed(
                title="🏁 **BATTLE ENDED** 🏁",
                description="**The ultimate confrontation has concluded!**",
                color=0x00FF00
            )
            
        else:
            embed = discord.Embed(title="Battle Status", color=0x0099FF)
            
        # Add character stats
        char_hp_percent = (character["hp"] / character["max_hp"]) * 100
        boss_hp_percent = (boss["hp"] / boss["max_hp"]) * 100
        
        embed.add_field(
            name="👤 **" + character["name"] + "**",
            value=f"**HP:** {character['hp']}/{character['max_hp']} ({char_hp_percent:.1f}%)\n"
                  f"**Chakra:** {character['chakra']}/{character['max_chakra']}\n"
                  f"**Stamina:** {character['stamina']}/{character['max_stamina']}",
            inline=True
        )
        
        embed.add_field(
            name="🔥 **SOLOMON** 🔥",
            value=f"**HP:** {boss['hp']}/{boss['max_hp']} ({boss_hp_percent:.1f}%)\n"
                  f"**Phase:** {current_phase.get('name', 'Unknown')}\n"
                  f"**Special:** {', '.join(current_phase.get('special_abilities', []))}",
            inline=True
        )
        
        # Add battle log
        if battle_data.get("battle_log"):
            log_text = "\n".join(battle_data["battle_log"][-5:])  # Last 5 entries
            embed.add_field(name="📜 **Battle Log**", value=log_text, inline=False)
            
        embed.set_footer(text="Use /boss attack <jutsu> to attack Solomon!")
        
        return embed
        
    async def process_boss_turn(self, battle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Solomon's turn in the battle."""
        character = battle_data["character"]
        boss = battle_data["boss"]
        current_phase = self.get_current_phase(boss["hp"] / boss["max_hp"])
        
        # Get boss jutsu
        jutsu_name = self.get_boss_jutsu(current_phase)
        damage = self.calculate_boss_damage(jutsu_name, current_phase)
        
        # Special phase abilities
        if "Kamui Phase" in jutsu_name:
            battle_data["battle_log"].append(f"🔥 **Solomon** uses **{jutsu_name}** - **DODGED!**")
            return battle_data
            
        # Apply damage
        character["hp"] = max(0, character["hp"] - damage)
        battle_data["battle_log"].append(f"🔥 **Solomon** uses **{jutsu_name}** - **{damage} damage!**")
        
        # Phase transition check
        new_phase = self.get_current_phase(boss["hp"] / boss["max_hp"])
        if new_phase != current_phase:
            battle_data["battle_log"].append(f"🔥 **PHASE TRANSITION:** {new_phase.get('name', 'Unknown')}")
            battle_data["battle_log"].append(f"🔥 **{new_phase.get('description', '')}**")
            
        # Boss regeneration
        if boss["hp"] < boss["max_hp"]:
            regen = int(boss["max_hp"] * 0.02)  # 2% regen per turn
            boss["hp"] = min(boss["max_hp"], boss["hp"] + regen)
            if regen > 0:
                battle_data["battle_log"].append(f"🔥 **Solomon** regenerates **{regen} HP**")
                
        battle_data["turn"] += 1
        return battle_data
        
    async def process_player_attack(self, interaction: discord.Interaction, jutsu_name: str) -> bool:
        """Process player's attack against Solomon."""
        user_id = str(interaction.user.id)
        
        if user_id not in self.active_boss_battles:
            await interaction.followup.send("❌ You are not in a boss battle!")
            return False
            
        battle_data = self.active_boss_battles[user_id]
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        # Check if character has the jutsu
        if jutsu_name not in character.get("jutsu", []):
            await interaction.followup.send(f"❌ You don't know the jutsu **{jutsu_name}**!")
            return False
            
        # Calculate player damage (simplified)
        base_damage = 50 + (character.get("ninjutsu", 0) // 10)
        damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
        
        # Apply damage to boss
        boss["hp"] = max(0, boss["hp"] - damage)
        battle_data["battle_log"].append(f"⚔️ **{character['name']}** uses **{jutsu_name}** - **{damage} damage!**")
        
        # Check if boss is defeated
        if boss["hp"] <= 0:
            await self.end_boss_battle(interaction, battle_data, "victory")
            return True
            
        # Process boss turn
        battle_data = await self.process_boss_turn(battle_data)
        
        # Check if player is defeated
        if character["hp"] <= 0:
            await self.end_boss_battle(interaction, battle_data, "defeat")
            return True
            
        # Update battle
        self.active_boss_battles[user_id] = battle_data
        
        # Send updated battle embed
        embed = self.create_battle_embed(battle_data, "battle_turn")
        await interaction.followup.send(embed=embed)
        
        return True
        
    async def end_boss_battle(self, interaction: discord.Interaction, battle_data: Dict[str, Any], result: str):
        """End the boss battle and handle rewards."""
        user_id = battle_data["user_id"]
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        # Remove from active battles
        self.active_boss_battles.pop(user_id, None)
        
        # Set cooldown
        self.boss_cooldowns[user_id] = datetime.now()
        
        if result == "victory":
            # Grant rewards
            rewards = self.boss_data.get("boss_rewards", {})
            
            # Update character stats
            character["exp"] += rewards.get("exp", 10000)
            character["ryo"] += rewards.get("ryo", 50000)
            
            # Add achievements
            achievements = character.get("achievements", [])
            for achievement in rewards.get("achievements", []):
                if achievement not in achievements:
                    achievements.append(achievement)
            character["achievements"] = achievements
            
            # Add titles
            titles = character.get("titles", [])
            for title in rewards.get("titles", []):
                if title not in titles:
                    titles.append(title)
            character["titles"] = titles
            
            # Save character data
            await self.save_character_data(character)
            
            # Create victory embed
            embed = discord.Embed(
                title="🏆 **VICTORY AGAINST SOLOMON!** 🏆",
                description="**You have defeated the Ultimate Being!**\n\n"
                           "**Rewards Earned:**\n"
                           f"💰 **{rewards.get('exp', 10000)} EXP**\n"
                           f"🪙 **{rewards.get('ryo', 50000)} Ryo**\n"
                           f"🏅 **Achievements:** {', '.join(rewards.get('achievements', []))}\n"
                           f"👑 **Titles:** {', '.join(rewards.get('titles', []))}",
                color=0xFFD700
            )
            
        else:  # defeat
            embed = discord.Embed(
                title="💀 **DEFEATED BY SOLOMON** 💀",
                description="**The Burning Revenant has proven too powerful...**\n\n"
                           "**Solomon:** *'You are not yet ready to face the ultimate being.'*\n\n"
                           "**Try again when you are stronger!**",
                color=0xFF0000
            )
            
        await interaction.followup.send(embed=embed)
        
    async def save_character_data(self, character_data: Dict[str, Any]):
        """Save updated character data."""
        try:
            character_file = f"data/characters/{character_data['id']}.json"
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving character data: {e}")

class BossBattleCommands(commands.Cog):
    """Commands for the ultimate boss battle system."""
    
    def __init__(self, bot):
        self.bot = bot
        self.boss_system = BossBattleSystem(bot)
        
    @app_commands.command(name="solomon", description="Challenge Solomon - The Burning Revenant (Ultimate Boss)")
    @app_commands.describe(
        action="What you want to do",
        jutsu="Jutsu to use in battle"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="challenge", value="challenge"),
        app_commands.Choice(name="attack", value="attack"),
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="flee", value="flee")
    ])
    async def solomon_command(self, interaction: discord.Interaction, action: str, jutsu: str = None):
        """Main command for Solomon boss battles."""
        await interaction.response.defer(thinking=True)
        
        # Load character data
        character_data = await self.load_character_data(interaction.user.id)
        if not character_data:
            await interaction.followup.send("❌ You don't have a character! Use `/create` first.")
            return
            
        if action == "challenge":
            await self.boss_system.start_boss_battle(interaction, character_data)
            
        elif action == "attack":
            if not jutsu:
                await interaction.followup.send("❌ Please specify a jutsu to use!")
                return
            await self.boss_system.process_player_attack(interaction, jutsu)
            
        elif action == "status":
            user_id = str(interaction.user.id)
            if user_id in self.boss_system.active_boss_battles:
                battle_data = self.boss_system.active_boss_battles[user_id]
                embed = self.boss_system.create_battle_embed(battle_data, "battle_turn")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ You are not in a boss battle!")
                
        elif action == "flee":
            user_id = str(interaction.user.id)
            if user_id in self.boss_system.active_boss_battles:
                self.boss_system.active_boss_battles.pop(user_id, None)
                embed = discord.Embed(
                    title="🏃 **FLED FROM BATTLE** 🏃",
                    description="**You have fled from Solomon's wrath...**\n\n"
                               "**Solomon:** *'Cowardice will not save you forever.'*",
                    color=0xFF6600
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ You are not in a boss battle!")
                
    async def load_character_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Load character data for a user."""
        try:
            character_file = f"data/characters/{user_id}.json"
            with open(character_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading character data: {e}")
            return None

async def setup(bot):
    """Setup the boss battle system."""
    await bot.add_cog(BossBattleCommands(bot)) 