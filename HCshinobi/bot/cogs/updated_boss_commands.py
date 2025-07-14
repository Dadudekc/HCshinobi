"""
Updated Boss Battle Commands - Solomon Uchiha: The Perfect Jinchūriki
Ultimate boss battle system with new mechanics from character sheet.
"""
import json
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import random
import os

def roll_d20(modifier=0):
    roll = random.randint(1, 20)
    total = roll + modifier
    crit = None
    if roll == 20:
        crit = 'success'
    elif roll == 1:
        crit = 'failure'
    return {'roll': roll, 'modifier': modifier, 'total': total, 'crit': crit}

# In attack and defense logic, use roll_d20 and display results in embeds/logs.
# For player saving throws, prompt the player with a Discord button to roll (or auto-roll for them), then show the result.
# Example usage in attack:
#   result = roll_d20(player_dex_mod)
#   log = f"You attack! (Roll: {result['roll']} + {result['modifier']} = {result['total']})"
#   if result['crit'] == 'success': log += ' CRITICAL HIT!'
#   elif result['crit'] == 'failure': log += ' CRITICAL FAILURE!'
#   ...
#   Show log in Discord embed.
#
# Repeat for boss attacks and all skill checks/saves.

class UpdatedSolomonBattleView(discord.ui.View):
    """Interactive view for updated Solomon battles with new mechanics."""
    
    def __init__(self, cog, battle_data: Dict[str, Any]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.battle_data = battle_data
        self.user_id = battle_data["user_id"]
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the battle participant can use buttons."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This is not your battle!", ephemeral=True
            )
            return False
        return True
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Get character's jutsu for selection
        character = self.battle_data["character"]
        jutsu_list = character.get("jutsu", ["Basic Attack"])
        
        if not jutsu_list:
            jutsu_list = ["Basic Attack", "Punch", "Kick"]
        
        # Create jutsu selection view
        jutsu_view = UpdatedJutsuSelectionView(self.cog, self.battle_data, jutsu_list)
        
        embed = discord.Embed(
            title="🎯 Select Your Jutsu",
            description="Choose which jutsu to use against Solomon:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=jutsu_view, ephemeral=True)
    
    @discord.ui.button(label="🔄 Transform", style=discord.ButtonStyle.green, emoji="🔄")
    async def transform_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Show transformation options
        transform_view = TransformationSelectionView(self.cog, self.battle_data)
        
        embed = discord.Embed(
            title="🔄 Solomon's Transformations",
            description="Solomon can activate various transformation modes:",
            color=discord.Color.purple()
        )
        
        await interaction.followup.send(embed=embed, view=transform_view, ephemeral=True)
    
    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.gray, emoji="📊")
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        character = self.battle_data["character"]
        boss = self.battle_data["boss"]
        
        # Calculate health percentages
        char_hp_percent = (character["hp"] / character["max_hp"]) * 100
        boss_hp_percent = (boss["hp"] / boss["max_hp"]) * 100
        
        embed = discord.Embed(
            title="📊 Battle Status",
            description=f"**Turn {self.battle_data['turn']}** | **Phase {self.battle_data['current_phase'] + 1}**",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name=f"👤 {character['name']}",
            value=f"**HP:** {character['hp']}/{character['max_hp']} ({char_hp_percent:.1f}%)\n"
                  f"**Chakra:** {character['chakra']}/{character['max_chakra']}\n"
                  f"**Stamina:** {character['stamina']}/{character['max_stamina']}",
            inline=True
        )
        
        # Show Solomon's current state
        active_transformations = self.battle_data.get("active_transformations", [])
        transform_text = ", ".join(active_transformations) if active_transformations else "None"
        
        embed.add_field(
            name="🔥 Solomon Uchiha",
            value=f"**HP:** {boss['hp']}/{boss['max_hp']} ({boss_hp_percent:.1f}%)\n"
                  f"**Chakra:** {boss['chakra']}/{boss['max_chakra']}\n"
                  f"**Transformations:** {transform_text}",
            inline=True
        )
        
        # Show recent battle log
        recent_log = self.battle_data.get("battle_log", [])[-3:]  # Last 3 entries
        if recent_log:
            log_text = "\n".join(recent_log)
            embed.add_field(name="⚡ Recent Actions", value=log_text, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🏃 Flee", style=discord.ButtonStyle.gray, emoji="🏃")
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Create confirmation view
        confirm_view = FleeConfirmationView(self.cog, self.battle_data)
        
        embed = discord.Embed(
            title="🏃 Flee from Battle?",
            description="**Solomon:** *'Running away already? How disappointing...'*\n\n"
                       "Are you sure you want to flee? You'll lose the battle and take damage.",
            color=discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, view=confirm_view, ephemeral=True)

class UpdatedJutsuSelectionView(discord.ui.View):
    """View for selecting jutsu during updated battle."""
    
    def __init__(self, cog, battle_data: Dict[str, Any], jutsu_list: List[str]):
        super().__init__(timeout=60)
        self.cog = cog
        self.battle_data = battle_data
        self.jutsu_list = jutsu_list
        
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
        
        # Execute the attack
        await self.cog.execute_updated_attack(interaction, self.battle_data, selected_jutsu)

class TransformationSelectionView(discord.ui.View):
    """View for selecting Solomon's transformation modes."""
    
    def __init__(self, cog, battle_data: Dict[str, Any]):
        super().__init__(timeout=60)
        self.cog = cog
        self.battle_data = battle_data
        
        # Add transformation buttons
        transformations = [
            ("Ōkami Sage Mode", "Sage Mode", discord.ButtonStyle.green),
            ("Partial Tailed Beast Cloak", "Partial Cloak", discord.ButtonStyle.orange),
            ("Full Tailed Beast Cloak", "Full Cloak", discord.ButtonStyle.red),
            ("Susanoo", "Susanoo", discord.ButtonStyle.purple),
            ("Fusion Form", "Fusion", discord.ButtonStyle.danger)
        ]
        
        for name, label, style in transformations:
            button = discord.ui.Button(
                label=label,
                style=style,
                custom_id=f"transform_{name}"
            )
            button.callback = self.transform_callback
            self.add_item(button)
    
    async def transform_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get the selected transformation
        button_id = interaction.data['custom_id']
        transform_name = button_id.split('_', 1)[1]
        
        # Execute the transformation
        await self.cog.execute_transformation(interaction, self.battle_data, transform_name)

class FleeConfirmationView(discord.ui.View):
    """View for confirming flee action."""
    
    def __init__(self, cog, battle_data: Dict[str, Any]):
        super().__init__(timeout=30)
        self.cog = cog
        self.battle_data = battle_data
    
    @discord.ui.button(label="Yes, Flee", style=discord.ButtonStyle.danger, emoji="🏃")
    async def confirm_flee(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.execute_flee(interaction, self.battle_data)
    
    @discord.ui.button(label="No, Stay", style=discord.ButtonStyle.gray, emoji="⚔️")
    async def cancel_flee(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="⚔️ Back to Battle!",
            description="**Solomon:** *'Good, show me your true power!'*",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class UpdatedBossCommands(commands.Cog):
    """Updated commands for Solomon boss battle system with new mechanics."""
    
    def __init__(self, bot):
        self.bot = bot
        self.boss_data_path = "data/characters/solomon.json"
        self.jutsu_data_path = "data/jutsu/solomon_jutsu.json"
        self.active_boss_battles: Dict[str, Dict[str, Any]] = {}
        
    def load_boss_data(self) -> Dict[str, Any]:
        """Load Solomon's updated boss data."""
        try:
            with open(self.boss_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "id": "solomon",
                "name": "Solomon Uchiha",
                "level": 20,
                "hp": 200,
                "max_hp": 200,
                "chakra": 44,
                "max_chakra": 44,
                "stamina": 100,
                "max_stamina": 100,
                "boss_requirements": {
                    "min_level": 15,
                    "required_achievements": ["Master of Elements", "Battle Hardened"],
                    "cooldown_hours": 168
                }
            }
    
    def load_jutsu_data(self) -> Dict[str, Any]:
        """Load Solomon's jutsu data."""
        try:
            with open(self.jutsu_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"solomon_jutsu": {}}
    
    def load_character_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Load character data for the user."""
        try:
            char_file = f"data/characters/{user_id}.json"
            with open(char_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def save_character_data(self, user_id: int, character_data: Dict[str, Any]):
        """Save character data."""
        char_file = f"data/characters/{user_id}.json"
        with open(char_file, 'w', encoding='utf-8') as f:
            json.dump(character_data, f, indent=4, ensure_ascii=False)
    
    @app_commands.command(name="solomon_updated", description="Challenge Solomon Uchiha - The Perfect Jinchūriki (Updated Boss)")
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
    async def solomon_updated_command(self, interaction: discord.Interaction, action: str, jutsu: str = None):
        """Main command for updated Solomon boss battles."""
        await interaction.response.defer(thinking=True)
        
        if action == "info":
            await self.show_updated_solomon_info(interaction)
            return
            
        # Load character data
        character_data = self.load_character_data(interaction.user.id)
        if not character_data:
            await interaction.followup.send("❌ You don't have a character! Use `/create` first.")
            return
            
        if action == "challenge":
            await self.start_updated_solomon_battle(interaction, character_data)
        elif action == "attack":
            if not jutsu:
                await interaction.followup.send("❌ Please specify a jutsu to use!")
                return
            await self.attack_updated_solomon(interaction, character_data, jutsu)
        elif action == "status":
            await self.show_updated_battle_status(interaction, character_data)
        elif action == "flee":
            await self.flee_from_updated_battle(interaction, character_data)
    
    async def show_updated_solomon_info(self, interaction: discord.Interaction):
        """Show detailed information about updated Solomon."""
        boss_data = self.load_boss_data()
        
        embed = discord.Embed(
            title="🔥 **SOLOMON UCHIHA** 🔥",
            description="**The Perfect Jinchūriki** | **Level 20**\n\n"
                       "**Solomon:** *'I am the ultimate being. Face me if you dare.'*",
            color=0xFF0000
        )
        
        # Basic stats
        embed.add_field(
            name="📊 **Stats**",
            value=f"**HP:** {boss_data.get('hp', 200)}/{boss_data.get('max_hp', 200)}\n"
                  f"**Chakra:** {boss_data.get('chakra', 44)}/{boss_data.get('max_chakra', 44)}\n"
                  f"**Stamina:** {boss_data.get('stamina', 100)}/{boss_data.get('max_stamina', 100)}\n"
                  f"**Level:** {boss_data.get('level', 20)}",
            inline=True
        )
        
        # Abilities
        ability_scores = boss_data.get("ability_scores", {})
        if ability_scores:
            embed.add_field(
                name="⚡ **Ability Scores**",
                value=f"**STR:** {ability_scores.get('strength', 16)} (+{ability_scores.get('strength', 16)-10})\n"
                      f"**DEX:** {ability_scores.get('dexterity', 20)} (+{ability_scores.get('dexterity', 20)-10})\n"
                      f"**CON:** {ability_scores.get('constitution', 18)} (+{ability_scores.get('constitution', 18)-10})\n"
                      f"**WIS:** {ability_scores.get('wisdom', 20)} (+{ability_scores.get('wisdom', 20)-10})",
                inline=True
            )
        
        # Transformation modes
        transform_modes = boss_data.get("transformation_modes", {})
        if transform_modes:
            transform_text = "\n".join([f"• {mode['name']} ({mode['chakra_cost']} chakra)" 
                                       for mode in transform_modes.values()])
            embed.add_field(
                name="🔄 **Transformation Modes**",
                value=transform_text,
                inline=False
            )
        
        # Requirements
        requirements = boss_data.get("boss_requirements", {})
        embed.add_field(
            name="🎯 **Requirements**",
            value=f"**Min Level:** {requirements.get('min_level', 15)}\n"
                  f"**Achievements:** {', '.join(requirements.get('required_achievements', []))}\n"
                  f"**Cooldown:** {requirements.get('cooldown_hours', 168)} hours",
            inline=False
        )
        
        embed.set_footer(text="Use /solomon_updated challenge to face the ultimate being!")
        
        await interaction.followup.send(embed=embed)
    
    async def start_updated_solomon_battle(self, interaction: discord.Interaction, character_data: Dict[str, Any]):
        """Start an updated battle with Solomon."""
        boss_data = self.load_boss_data()
        
        # Check requirements
        requirements = boss_data.get("boss_requirements", {})
        min_level = requirements.get("min_level", 15)
        required_achievements = requirements.get("required_achievements", [])
        
        # Level check
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
        
        # Achievement check
        for ach in required_achievements:
            if ach not in character_data.get("achievements", []):
                embed = discord.Embed(
                    title="❌ **INSUFFICIENT POWER** ❌",
                    description=f"**Solomon:** *'You are not yet ready to face the ultimate being.'*\n\n"
                               f"You must have the achievement: **{ach}**",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed)
                return
        
        # Check if already in battle
        user_id = str(interaction.user.id)
        if user_id in self.active_boss_battles:
            embed = discord.Embed(
                title="❌ **ALREADY IN BATTLE** ❌",
                description="You are already in a battle with Solomon!",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Initialize battle with updated stats
        boss_stats = {
            "id": boss_data.get("id", "solomon"),
            "name": boss_data.get("name", "Solomon Uchiha"),
            "hp": boss_data.get("hp", 200),
            "max_hp": boss_data.get("max_hp", 200),
            "chakra": boss_data.get("chakra", 44),
            "max_chakra": boss_data.get("max_chakra", 44),
            "stamina": boss_data.get("stamina", 100),
            "max_stamina": boss_data.get("max_stamina", 100),
            "level": boss_data.get("level", 20)
        }
        
        battle_data = {
            "user_id": interaction.user.id,
            "character": character_data.copy(),
            "boss": boss_stats,
            "current_phase": 0,
            "turn": 1,
            "battle_log": [],
            "started_at": datetime.now().isoformat(),
            "active_transformations": [],
            "boss_chakra_used": 0
        }
        
        # Store battle in memory
        self.active_boss_battles[user_id] = battle_data
        
        # Create battle embed and view
        embed = self.create_updated_battle_embed(battle_data)
        view = UpdatedSolomonBattleView(self, battle_data)
        
        await interaction.followup.send(embed=embed, view=view)
    
    def create_updated_battle_embed(self, battle_data: Dict[str, Any]) -> discord.Embed:
        """Create an updated battle embed."""
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        char_hp_percent = (character["hp"] / character["max_hp"]) * 100
        boss_hp_percent = (boss["hp"] / boss["max_hp"]) * 100
        
        # Get current phase info
        phase_names = ["The Crimson Shadow", "The Burning Revenant", "The Exiled Flame", "The Ultimate Being"]
        current_phase = battle_data["current_phase"]
        phase_name = phase_names[current_phase] if current_phase < len(phase_names) else "Unknown"
        
        embed = discord.Embed(
            title="🔥 **SOLOMON UCHIHA - THE PERFECT JINCHŪRIKI** 🔥",
            description=f"**The Ultimate Being** | **Turn {battle_data['turn']}**\n"
                       f"**Phase {current_phase + 1}: {phase_name}**\n\n"
                       f"**Solomon:** *'Show me your true power!'*",
            color=0xFF0000
        )
        
        # Character stats
        embed.add_field(
            name=f"👤 **{character['name']}**",
            value=f"**HP:** {character['hp']}/{character['max_hp']} ({char_hp_percent:.1f}%)\n"
                  f"**Chakra:** {character['chakra']}/{character['max_chakra']}\n"
                  f"**Stamina:** {character['stamina']}/{character['max_stamina']}",
            inline=True
        )
        
        # Solomon stats with transformations
        active_transformations = battle_data.get("active_transformations", [])
        transform_text = ", ".join(active_transformations) if active_transformations else "None"
        
        embed.add_field(
            name="🔥 **SOLOMON UCHIHA**",
            value=f"**HP:** {boss['hp']}/{boss['max_hp']} ({boss_hp_percent:.1f}%)\n"
                  f"**Chakra:** {boss['chakra']}/{boss['max_chakra']}\n"
                  f"**Transformations:** {transform_text}",
            inline=True
        )
        
        # Add battle log
        if battle_data.get("battle_log"):
            log_text = "\n".join(battle_data["battle_log"][-5:])  # Last 5 entries
            embed.add_field(name="📜 **Battle Log**", value=log_text, inline=False)
            
        embed.set_footer(text="Use the buttons below to interact with the battle!")
        
        return embed
    
    async def execute_updated_attack(self, interaction: discord.Interaction, battle_data: Dict[str, Any], jutsu_name: str):
        """Execute a player attack with d20 mechanics."""
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        # Check if character has the jutsu
        if jutsu_name not in character.get("jutsu", []):
            await interaction.followup.send(f"❌ You don't know the jutsu **{jutsu_name}**!", ephemeral=True)
            return
        
        # Determine attack stat (default DEX, can be customized per jutsu)
        stat_mod = character.get("dexterity", 0) // 2 - 5  # DEX mod
        ac = boss.get("ac", 15)
        attack_result = roll_d20(stat_mod)
        log = f"⚔️ **{character['name']}** uses **{jutsu_name}**! (Roll: {attack_result['roll']} + {attack_result['modifier']} = {attack_result['total']} vs AC {ac})"
        
        # Crit/fail logic
        if attack_result['crit'] == 'success':
            log += " — **CRITICAL HIT!**"
        elif attack_result['crit'] == 'failure':
            log += " — **CRITICAL FAILURE!**"
        
        # Hit/miss logic
        if attack_result['crit'] == 'failure' or attack_result['total'] < ac:
            log += " — Misses!"
            battle_data["battle_log"].append(log)
        else:
            # Calculate damage (crit = double damage)
            base_damage = 20 + (character.get("ninjutsu", 0) // 5)
            damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
            if attack_result['crit'] == 'success':
                damage *= 2
            boss["hp"] = max(0, boss["hp"] - damage)
            log += f" — **Hits for {damage} damage!**"
            battle_data["battle_log"].append(log)
        
        # Check if boss is defeated
        if boss["hp"] <= 0:
            await self.handle_updated_victory(interaction, battle_data)
            return
        
        # Process boss turn with new mechanics
        battle_data = await self.process_updated_boss_turn(interaction, battle_data)
        
        # Check if player is defeated
        if character["hp"] <= 0:
            await self.handle_updated_defeat(interaction, battle_data)
            return
        
        # Update battle
        battle_data["turn"] += 1
        
        # Update battle in memory
        user_id = str(interaction.user.id)
        self.active_boss_battles[user_id] = battle_data
        
        # Send updated embed
        embed = self.create_updated_battle_embed(battle_data)
        view = UpdatedSolomonBattleView(self, battle_data)
        
        await interaction.followup.send(embed=embed, view=view)

    async def process_updated_boss_turn(self, interaction, battle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Solomon's turn with d20 mechanics."""
        character = battle_data["character"]
        boss = battle_data["boss"]
        
        # Get current phase
        hp_percentage = boss["hp"] / boss["max_hp"]
        current_phase = self.get_updated_phase(hp_percentage)
        
        # Check if Solomon should transform
        if self.should_transform(battle_data, current_phase):
            transform_mode = self.select_transformation(battle_data, current_phase)
            if transform_mode and boss["chakra"] >= transform_mode["chakra_cost"]:
                battle_data = self.activate_transformation(battle_data, transform_mode)
        
        # Get boss jutsu based on current phase and transformations
        jutsu_pool = current_phase.get("jutsu_pool", ["Fire Release: Great Fireball Jutsu"])
        jutsu_name = random.choice(jutsu_pool)
        
        # Boss attack roll (default DEX, can be customized per jutsu)
        boss_stat_mod = boss.get("dexterity", 0) // 2 - 5
        player_ac = character.get("ac", 15)
        attack_result = roll_d20(boss_stat_mod)
        log = f"🔥 **Solomon** uses **{jutsu_name}**! (Roll: {attack_result['roll']} + {attack_result['modifier']} = {attack_result['total']} vs AC {player_ac})"
        
        # Crit/fail logic
        if attack_result['crit'] == 'success':
            log += " — **CRITICAL HIT!**"
        elif attack_result['crit'] == 'failure':
            log += " — **CRITICAL FAILURE!**"
        
        # Hit/miss logic
        if attack_result['crit'] == 'failure' or attack_result['total'] < player_ac:
            log += " — Misses!"
            battle_data["battle_log"].append(log)
        else:
            # Check if jutsu requires a saving throw
            jutsu_data = self.load_jutsu_data().get("solomon_jutsu", {})
            jutsu_info = jutsu_data.get(jutsu_name.replace(" ", "_"), {})
            save_dc = jutsu_info.get("save_dc")
            save_type = jutsu_info.get("save_type")
            if save_dc and save_type:
                # Prompt player for saving throw (auto-roll for now)
                player_mod = character.get(save_type.lower(), 0) // 2 - 5
                save_result = roll_d20(player_mod)
                save_log = f"🛡️ **Saving Throw:** {save_type.upper()} (Roll: {save_result['roll']} + {save_result['modifier']} = {save_result['total']} vs DC {save_dc})"
                if save_result['crit'] == 'success':
                    save_log += " — **CRITICAL SUCCESS!**"
                elif save_result['crit'] == 'failure':
                    save_log += " — **CRITICAL FAILURE!**"
                if save_result['total'] >= save_dc and save_result['crit'] != 'failure':
                    save_log += " — Success!"
                    log += " — Player saves!"
                else:
                    # Full damage
                    base_damage = jutsu_info.get("damage", 50)
                    damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
                    if attack_result['crit'] == 'success':
                        damage *= 2
                    character["hp"] = max(0, character["hp"] - damage)
                    log += f" — **Hits for {damage} damage!**"
                battle_data["battle_log"].append(log)
                battle_data["battle_log"].append(save_log)
            else:
                # No save, just damage
                base_damage = jutsu_info.get("damage", 50)
                damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
                if attack_result['crit'] == 'success':
                    damage *= 2
                character["hp"] = max(0, character["hp"] - damage)
                log += f" — **Hits for {damage} damage!**"
                battle_data["battle_log"].append(log)
        
        # Phase transition check
        new_phase = self.get_updated_phase(boss["hp"] / boss["max_hp"])
        if new_phase != current_phase:
            battle_data["current_phase"] = self.get_phase_index(new_phase)
            battle_data["battle_log"].append(f"🔥 **Solomon enters Phase {battle_data['current_phase'] + 1}!**")
        
        return battle_data
    
    def get_updated_phase(self, hp_percentage: float) -> Dict[str, Any]:
        """Get the current battle phase based on HP percentage."""
        boss_data = self.load_boss_data()
        phases = boss_data.get("boss_phases", [])
        
        for phase in phases:
            if hp_percentage >= phase.get("hp_threshold", 1.0):
                return phase
        
        return phases[-1] if phases else {}
    
    def get_phase_index(self, phase: Dict[str, Any]) -> int:
        """Get the index of a phase."""
        boss_data = self.load_boss_data()
        phases = boss_data.get("boss_phases", [])
        
        for i, p in enumerate(phases):
            if p.get("name") == phase.get("name"):
                return i
        
        return 0
    
    def should_transform(self, battle_data: Dict[str, Any], current_phase: Dict[str, Any]) -> bool:
        """Determine if Solomon should transform."""
        active_transformations = battle_data.get("active_transformations", [])
        available_transformations = current_phase.get("transformation_modes", [])
        
        # Don't transform if already in a transformation
        if active_transformations:
            return False
        
        # Transform based on phase and random chance
        phase_index = self.get_phase_index(current_phase)
        transform_chance = (phase_index + 1) * 0.2  # 20%, 40%, 60%, 80%
        
        return random.random() < transform_chance
    
    def select_transformation(self, battle_data: Dict[str, Any], current_phase: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select which transformation to activate."""
        boss_data = self.load_boss_data()
        transform_modes = boss_data.get("transformation_modes", {})
        available_transformations = current_phase.get("transformation_modes", [])
        
        # Filter available transformations
        available_modes = []
        for transform_name in available_transformations:
            if transform_name in transform_modes:
                available_modes.append(transform_modes[transform_name])
        
        if not available_modes:
            return None
        
        # Select based on phase (higher phases get stronger transformations)
        phase_index = self.get_phase_index(current_phase)
        if phase_index >= 3:  # Phase 4
            return transform_modes.get("fusion_form")
        elif phase_index >= 2:  # Phase 3
            return transform_modes.get("susanoo")
        elif phase_index >= 1:  # Phase 2
            return transform_modes.get("partial_tailed_beast_cloak")
        else:  # Phase 1
            return transform_modes.get("okami_sage_mode")
    
    def activate_transformation(self, battle_data: Dict[str, Any], transform_mode: Dict[str, Any]) -> Dict[str, Any]:
        """Activate a transformation mode."""
        boss = battle_data["boss"]
        transform_name = transform_mode.get("name", "Unknown Transformation")
        
        # Deduct chakra cost
        chakra_cost = transform_mode.get("chakra_cost", 0)
        boss["chakra"] = max(0, boss["chakra"] - chakra_cost)
        
        # Add to active transformations
        active_transformations = battle_data.get("active_transformations", [])
        active_transformations.append(transform_name)
        battle_data["active_transformations"] = active_transformations
        
        # Add to battle log
        battle_data["battle_log"].append(f"🔄 **Solomon activates {transform_name}!**")
        
        return battle_data
    
    def calculate_updated_boss_damage(self, jutsu_name: str, phase: Dict[str, Any], battle_data: Dict[str, Any]) -> int:
        """Calculate boss damage with updated mechanics."""
        jutsu_data = self.load_jutsu_data()
        jutsu_info = jutsu_data.get("solomon_jutsu", {}).get(jutsu_name.replace(" ", "_"), {})
        
        # Base damage from jutsu
        base_damage = jutsu_info.get("damage", 50)
        
        # Apply phase multiplier
        damage_multiplier = phase.get("damage_multiplier", 1.0)
        base_damage *= damage_multiplier
        
        # Apply transformation bonuses
        active_transformations = battle_data.get("active_transformations", [])
        for transform_name in active_transformations:
            if "Sage Mode" in transform_name:
                base_damage *= 1.2
            elif "Tailed Beast Cloak" in transform_name:
                base_damage *= 1.5
            elif "Susanoo" in transform_name:
                base_damage *= 2.0
            elif "Fusion" in transform_name:
                base_damage *= 2.5
        
        # Add random variation
        damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
        
        return max(10, damage)  # Minimum 10 damage
    
    async def execute_transformation(self, interaction: discord.Interaction, battle_data: Dict[str, Any], transform_name: str):
        """Execute a transformation for Solomon."""
        boss_data = self.load_boss_data()
        transform_modes = boss_data.get("transformation_modes", {})
        
        # Find the transformation
        transform_mode = None
        for key, mode in transform_modes.items():
            if transform_name in mode.get("name", ""):
                transform_mode = mode
                break
        
        if not transform_mode:
            await interaction.followup.send("❌ Invalid transformation!", ephemeral=True)
            return
        
        # Check if already in this transformation
        active_transformations = battle_data.get("active_transformations", [])
        if transform_name in active_transformations:
            await interaction.followup.send("❌ Already in this transformation!", ephemeral=True)
            return
        
        # Check chakra cost
        boss = battle_data["boss"]
        chakra_cost = transform_mode.get("chakra_cost", 0)
        if boss["chakra"] < chakra_cost:
            await interaction.followup.send("❌ Not enough chakra for this transformation!", ephemeral=True)
            return
        
        # Activate transformation
        battle_data = self.activate_transformation(battle_data, transform_mode)
        
        # Update battle in memory
        user_id = str(interaction.user.id)
        self.active_boss_battles[user_id] = battle_data
        
        # Send updated embed
        embed = self.create_updated_battle_embed(battle_data)
        view = UpdatedSolomonBattleView(self, battle_data)
        
        await interaction.followup.send(embed=embed, view=view)
    
    async def handle_updated_victory(self, interaction: discord.Interaction, battle_data: Dict[str, Any]):
        """Handle victory in updated battle."""
        character = battle_data["character"]
        boss_data = self.load_boss_data()
        rewards = boss_data.get("boss_rewards", {})
        
        # Give rewards
        character["exp"] = character.get("exp", 0) + rewards.get("exp", 10000)
        character["ryo"] = character.get("ryo", 0) + rewards.get("ryo", 50000)
        character["tokens"] = character.get("tokens", 0) + rewards.get("tokens", 100)
        
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
        self.save_character_data(interaction.user.id, character)
        
        # Remove from active battles
        user_id = str(interaction.user.id)
        self.active_boss_battles.pop(user_id, None)
        
        from HCshinobi.core.battle_log_templates import ModernBattleLogger
        
        battle_logger = ModernBattleLogger()
        battle_summary = battle_logger.format_modern_battle_summary(
            mission_name="Solomon Uchiha Boss Battle",
            winner=character['name'],
            loser="Solomon Uchiha - The Perfect Jinchūriki",
            turn=battle_data.get('turn', 1),
            actions=[{"type": "attack", "actor": character['name'], "jutsu": "Final Strike", "damage": 0}]
        )
        
        # Add Solomon-specific dialogue and rewards
        battle_summary += f"\n\n**Solomon:** *'Impressive... You have proven yourself worthy.'*\n\n"
        battle_summary += f"**Rewards Earned:**\n"
        battle_summary += f"• **EXP:** +{rewards.get('exp', 10000)}\n"
        battle_summary += f"• **Ryo:** +{rewards.get('ryo', 50000)}\n"
        battle_summary += f"• **Tokens:** +{rewards.get('tokens', 100)}\n"
        battle_summary += f"• **Achievements:** {', '.join(rewards.get('achievements', []))}\n"
        battle_summary += f"• **Titles:** {', '.join(rewards.get('titles', []))}"
        
        embed = discord.Embed(
            title="🏆 **VICTORY OVER SOLOMON UCHIHA!** 🏆",
            description=battle_summary,
            color=0x00FF00
        )
        
        embed.set_footer(text="You have become a legend!")
        
        await interaction.followup.send(embed=embed)
    
    async def handle_updated_defeat(self, interaction: discord.Interaction, battle_data: Dict[str, Any]):
        """Handle defeat in updated battle."""
        character = battle_data["character"]
        
        # Remove from active battles
        user_id = str(interaction.user.id)
        self.active_boss_battles.pop(user_id, None)
        
        # Create defeat embed
        embed = discord.Embed(
            title="💀 **DEFEATED BY SOLOMON UCHIHA** 💀",
            description=f"**{character['name']}** has been defeated by the Perfect Jinchūriki!\n\n"
                       f"**Solomon:** *'You are not yet ready. Train harder and return when you are stronger.'*\n\n"
                       f"**Solomon's parting words:** *'The path to true power is not easy. Learn from this defeat.'*",
            color=0xFF0000
        )
        
        embed.set_footer(text="You can challenge Solomon again in 7 days.")
        
        await interaction.followup.send(embed=embed)
    
    async def show_updated_battle_status(self, interaction: discord.Interaction, character_data: Dict[str, Any]):
        """Show updated battle status."""
        user_id = str(interaction.user.id)
        if user_id in self.active_boss_battles:
            battle_data = self.active_boss_battles[user_id]
            embed = self.create_updated_battle_embed(battle_data)
            view = UpdatedSolomonBattleView(self, battle_data)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send("❌ You are not in a boss battle!")
    
    async def flee_from_updated_battle(self, interaction: discord.Interaction, character_data: Dict[str, Any]):
        """Flee from updated battle."""
        user_id = str(interaction.user.id)
        if user_id in self.active_boss_battles:
            self.active_boss_battles.pop(user_id, None)
            embed = discord.Embed(
                title="🏃 **FLED FROM BATTLE** 🏃",
                description="**You have fled from Solomon's wrath...**\n\n"
                           "**Solomon:** *'Cowardice will not save you forever.'*",
                color=0xFF6600
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ You are not in a boss battle!")
    
    async def execute_flee(self, interaction: discord.Interaction, battle_data: Dict[str, Any]):
        """Execute flee action."""
        user_id = str(interaction.user.id)
        self.active_boss_battles.pop(user_id, None)
        
        embed = discord.Embed(
            title="🏃 **FLED FROM BATTLE** 🏃",
            description="**You have fled from Solomon's wrath...**\n\n"
                       "**Solomon:** *'Cowardice will not save you forever.'*",
            color=0xFF6600
        )
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    """Setup function for the updated boss commands cog."""
    await bot.add_cog(UpdatedBossCommands(bot)) 