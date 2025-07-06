"""
Boss Battle Commands - Solomon: The Burning Revenant
Ultimate boss battle system commands for Discord integration.
"""
import json
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class BossCommands(commands.Cog):
    """Commands for the ultimate boss battle system."""
    
    def __init__(self, bot):
        self.bot = bot
        self.boss_data_path = "data/characters/solomon.json"
        self.jutsu_data_path = "data/jutsu/solomon_jutsu.json"
        
    def load_boss_data(self) -> Dict[str, Any]:
        """Load Solomon's boss data."""
        try:
            with open(self.boss_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
            
    def load_jutsu_data(self) -> Dict[str, Any]:
        """Load Solomon's jutsu data."""
        try:
            with open(self.jutsu_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
            
    def load_character_data(self, user_id: int) -> Optional[Dict[str, Any]]:
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
            
    def save_character_data(self, character_data: Dict[str, Any]):
        """Save updated character data."""
        try:
            character_file = f"data/characters/{character_data['id']}.json"
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving character data: {e}")

    @app_commands.command(name="solomon", description="Challenge Solomon - The Burning Revenant (Ultimate Boss)")
    @app_commands.describe(
        action="What you want to do",
        jutsu="Jutsu to use in battle"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="challenge", value="challenge"),
        app_commands.Choice(name="attack", value="attack"),
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="flee", value="flee"),
        app_commands.Choice(name="info", value="info")
    ])
    async def solomon_command(self, interaction: discord.Interaction, action: str, jutsu: str = None):
        """Main command for Solomon boss battles."""
        await interaction.response.defer(thinking=True)
        
        if action == "info":
            await self.show_solomon_info(interaction)
            return
            
        # Load character data
        character_data = self.load_character_data(interaction.user.id)
        if not character_data:
            await interaction.followup.send("❌ You don't have a character! Use `/create` first.")
            return
            
        if action == "challenge":
            await self.start_solomon_battle(interaction, character_data)
        elif action == "attack":
            if not jutsu:
                await interaction.followup.send("❌ Please specify a jutsu to use!")
                return
            await self.attack_solomon(interaction, character_data, jutsu)
        elif action == "status":
            await self.show_battle_status(interaction, character_data)
        elif action == "flee":
            await self.flee_from_battle(interaction, character_data)
            
    async def show_solomon_info(self, interaction: discord.Interaction):
        """Show information about Solomon."""
        boss_data = self.load_boss_data()
        jutsu_data = self.load_jutsu_data()
        
        embed = discord.Embed(
            title="🔥 **SOLOMON - THE BURNING REVENANT** 🔥",
            description="**The Ultimate Being**\n\n"
                       "**Solomon** is the legendary Uchiha exile, perfect Jinchūriki of Son Gokū, "
                       "and master of the Eternal Mangekyō Sharingan. He represents the pinnacle "
                       "of power in the HCshinobi world.\n\n"
                       "**No boss is above this boss.**",
            color=0xFF0000
        )
        
        # Add stats
        embed.add_field(
            name="📊 **Stats**",
            value=f"**Level:** {boss_data.get('level', 70)}\n"
                  f"**HP:** {boss_data.get('hp', 1500)}/{boss_data.get('max_hp', 1500)}\n"
                  f"**Chakra:** {boss_data.get('chakra', 1000)}/{boss_data.get('max_chakra', 1000)}\n"
                  f"**Stamina:** {boss_data.get('stamina', 500)}/{boss_data.get('max_stamina', 500)}",
            inline=True
        )
        
        # Add abilities
        embed.add_field(
            name="⚡ **Abilities**",
            value=f"**Kekkei Genkai:** {', '.join(boss_data.get('kekkei_genkai', []))}\n"
                  f"**Sage Mode:** {boss_data.get('sage_mode', 'Ōkami Sage Mode')}\n"
                  f"**Jinchūriki:** {boss_data.get('jinchuriki', 'Son Gokū (Four-Tails)')}",
            inline=True
        )
        
        # Add requirements
        requirements = boss_data.get("boss_requirements", {})
        embed.add_field(
            name="🎯 **Requirements**",
            value=f"**Min Level:** {requirements.get('min_level', 50)}\n"
                  f"**Achievements:** {', '.join(requirements.get('required_achievements', []))}\n"
                  f"**Cooldown:** {requirements.get('cooldown_hours', 168)} hours",
            inline=False
        )
        
        # Add phases
        phases = boss_data.get("boss_phases", [])
        phase_text = ""
        for i, phase in enumerate(phases, 1):
            phase_text += f"**Phase {i}:** {phase.get('name', 'Unknown')}\n"
            phase_text += f"*{phase.get('description', '')}*\n\n"
            
        embed.add_field(name="🔥 **Battle Phases**", value=phase_text, inline=False)
        
        # Add rewards
        rewards = boss_data.get("boss_rewards", {})
        embed.add_field(
            name="🏆 **Rewards**",
            value=f"**EXP:** {rewards.get('exp', 10000)}\n"
                  f"**Ryo:** {rewards.get('ryo', 50000)}\n"
                  f"**Tokens:** {rewards.get('tokens', 100)}\n"
                  f"**Titles:** {', '.join(rewards.get('titles', []))}",
            inline=True
        )
        
        embed.set_footer(text="Use /solomon challenge to begin the ultimate battle!")
        
        await interaction.followup.send(embed=embed)
        
    async def start_solomon_battle(self, interaction: discord.Interaction, character_data: Dict[str, Any]):
        """Start a battle with Solomon."""
        boss_data = self.load_boss_data()
        
        # Check requirements
        requirements = boss_data.get("boss_requirements", {})
        min_level = requirements.get("min_level", 50)
        
        if character_data.get("level", 0) < min_level:
            embed = discord.Embed(
                title="❌ **INSUFFICIENT POWER** ❌",
                description=f"**Solomon:** *'You are not yet ready to face the ultimate being.'*\n\n"
                           f"You must be at least **level {min_level}** to challenge Solomon.\n"
                           f"Your current level: **{character_data.get('level', 0)}**",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)
            return
            
        # Check cooldown
        cooldown_hours = requirements.get("cooldown_hours", 168)
        # This would need to be stored in a database or file for persistence
        # For now, we'll skip the cooldown check
        
        # Initialize battle
        battle_data = {
            "user_id": interaction.user.id,
            "character": character_data.copy(),
            "boss": boss_data.copy(),
            "current_phase": 0,
            "turn": 1,
            "battle_log": [],
            "started_at": datetime.now().isoformat()
        }
        
        # Store battle data (in a real implementation, this would be in a database)
        # For now, we'll create a simple file-based system
        battle_file = f"data/battles/solomon_{interaction.user.id}.json"
        try:
            with open(battle_file, 'w', encoding='utf-8') as f:
                json.dump(battle_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving battle data: {e}")
            
        # Create battle embed
        embed = self.create_battle_embed(battle_data, "battle_start")
        await interaction.followup.send(embed=embed)
        
    def create_battle_embed(self, battle_data: Dict[str, Any], embed_type: str) -> discord.Embed:
        """Create battle embed based on type."""
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        if embed_type == "battle_start":
            embed = discord.Embed(
                title="🔥 **SOLOMON - THE BURNING REVENANT** 🔥",
                description="**The Ultimate Being has appeared!**\n\n"
                           "**Solomon:** *'You dare challenge the Burning Revenant? "
                           "Let me show you the power of the ultimate being!'*\n\n"
                           "**Phase 1: The Crimson Shadow**\n"
                           "Solomon begins with Sharingan analysis and basic Katon techniques",
                color=0xFF0000
            )
        elif embed_type == "battle_turn":
            embed = discord.Embed(
                title=f"⚔️ **BATTLE TURN {battle_data['turn']}** ⚔️",
                description="**The battle rages on!**",
                color=0xFF6600
            )
        else:
            embed = discord.Embed(title="Battle Status", color=0x0099FF)
            
        # Add character stats
        char_hp_percent = (character["hp"] / character["max_hp"]) * 100
        boss_hp_percent = (boss["hp"] / boss["max_hp"]) * 100
        
        embed.add_field(
            name=f"👤 **{character['name']}**",
            value=f"**HP:** {character['hp']}/{character['max_hp']} ({char_hp_percent:.1f}%)\n"
                  f"**Chakra:** {character['chakra']}/{character['max_chakra']}\n"
                  f"**Stamina:** {character['stamina']}/{character['max_stamina']}",
            inline=True
        )
        
        embed.add_field(
            name="🔥 **SOLOMON** 🔥",
            value=f"**HP:** {boss['hp']}/{boss['max_hp']} ({boss_hp_percent:.1f}%)\n"
                  f"**Phase:** Phase 1: The Crimson Shadow\n"
                  f"**Special:** Sharingan Analysis, Chakra Absorption",
            inline=True
        )
        
        # Add battle log
        if battle_data.get("battle_log"):
            log_text = "\n".join(battle_data["battle_log"][-5:])  # Last 5 entries
            embed.add_field(name="📜 **Battle Log**", value=log_text, inline=False)
            
        embed.set_footer(text="Use /solomon attack <jutsu> to attack Solomon!")
        
        return embed
        
    async def attack_solomon(self, interaction: discord.Interaction, character_data: Dict[str, Any], jutsu_name: str):
        """Process player's attack against Solomon."""
        # Load battle data
        battle_file = f"data/battles/solomon_{interaction.user.id}.json"
        try:
            with open(battle_file, 'r', encoding='utf-8') as f:
                battle_data = json.load(f)
        except FileNotFoundError:
            await interaction.followup.send("❌ You are not in a battle with Solomon!")
            return
            
        # Check if character has the jutsu
        if jutsu_name not in character_data.get("jutsu", []):
            await interaction.followup.send(f"❌ You don't know the jutsu **{jutsu_name}**!")
            return
            
        # Calculate player damage (simplified)
        base_damage = 50 + (character_data.get("ninjutsu", 0) // 10)
        damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
        
        # Apply damage to boss
        battle_data["boss"]["hp"] = max(0, battle_data["boss"]["hp"] - damage)
        battle_data["battle_log"].append(f"⚔️ **{character_data['name']}** uses **{jutsu_name}** - **{damage} damage!**")
        
        # Check if boss is defeated
        if battle_data["boss"]["hp"] <= 0:
            await self.end_battle(interaction, battle_data, "victory")
            return
            
        # Process boss turn
        battle_data = await self.process_boss_turn(battle_data)
        
        # Check if player is defeated
        if battle_data["character"]["hp"] <= 0:
            await self.end_battle(interaction, battle_data, "defeat")
            return
            
        # Update battle
        battle_data["turn"] += 1
        
        # Save battle data
        try:
            with open(battle_file, 'w', encoding='utf-8') as f:
                json.dump(battle_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving battle data: {e}")
            
        # Send updated battle embed
        embed = self.create_battle_embed(battle_data, "battle_turn")
        await interaction.followup.send(embed=embed)
        
    async def process_boss_turn(self, battle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Solomon's turn in the battle."""
        import random
        
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        # Get current phase
        hp_percentage = boss["hp"] / boss["max_hp"]
        current_phase = self.get_current_phase(hp_percentage)
        
        # Get boss jutsu
        jutsu_pool = current_phase.get("jutsu_pool", ["Katon: Gōka Messhitsu"])
        jutsu_name = random.choice(jutsu_pool)
        
        # Calculate boss damage
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
                
        return battle_data
        
    def get_current_phase(self, hp_percentage: float) -> Dict[str, Any]:
        """Get the current boss phase based on HP percentage."""
        boss_data = self.load_boss_data()
        phases = boss_data.get("boss_phases", [])
        
        for phase in phases:
            if hp_percentage >= phase.get("hp_threshold", 1.0):
                return phase
        return phases[-1] if phases else {}
        
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
        
    async def end_battle(self, interaction: discord.Interaction, battle_data: Dict[str, Any], result: str):
        """End the boss battle and handle rewards."""
        import os
        
        user_id = interaction.user.id
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        # Remove battle file
        battle_file = f"data/battles/solomon_{user_id}.json"
        try:
            os.remove(battle_file)
        except FileNotFoundError:
            pass
            
        if result == "victory":
            # Grant rewards
            boss_data = self.load_boss_data()
            rewards = boss_data.get("boss_rewards", {})
            
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
            self.save_character_data(character)
            
            # Create victory embed
            embed = discord.Embed(
                title="🏆 **VICTORY AGAINST SOLOMON!** 🏆",
                description="**You have defeated the Ultimate Being!**\n\n"
                           "**Solomon:** *'Impossible... You have proven yourself worthy. "
                           "You are truly the equal of the ultimate being.'*\n\n"
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
                           "**Solomon:** *'You are not yet ready to face the ultimate being. "
                           "Train harder, grow stronger, and perhaps one day you will be worthy.'*\n\n"
                           "**Try again when you are stronger!**",
                color=0xFF0000
            )
            
        await interaction.followup.send(embed=embed)
        
    async def show_battle_status(self, interaction: discord.Interaction, character_data: Dict[str, Any]):
        """Show current battle status."""
        battle_file = f"data/battles/solomon_{interaction.user.id}.json"
        try:
            with open(battle_file, 'r', encoding='utf-8') as f:
                battle_data = json.load(f)
        except FileNotFoundError:
            await interaction.followup.send("❌ You are not in a battle with Solomon!")
            return
            
        embed = self.create_battle_embed(battle_data, "battle_turn")
        await interaction.followup.send(embed=embed)
        
    async def flee_from_battle(self, interaction: discord.Interaction, character_data: Dict[str, Any]):
        """Flee from the battle."""
        import os
        
        battle_file = f"data/battles/solomon_{interaction.user.id}.json"
        try:
            os.remove(battle_file)
        except FileNotFoundError:
            await interaction.followup.send("❌ You are not in a battle with Solomon!")
            return
            
        embed = discord.Embed(
            title="🏃 **FLED FROM BATTLE** 🏃",
            description="**You have fled from Solomon's wrath...**\n\n"
                       "**Solomon:** *'Cowardice will not save you forever. "
                       "The ultimate being will always be waiting.'*",
            color=0xFF6600
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    """Setup the boss battle commands."""
    await bot.add_cog(BossCommands(bot)) 