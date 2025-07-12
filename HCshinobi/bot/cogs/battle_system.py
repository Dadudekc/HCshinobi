"""
Interactive PvP Battle System for HCShinobi Bot

This module provides a comprehensive Player vs Player battle system similar to the Solomon interactive battles.

Features:
- Challenge system: Players can challenge each other with /challenge @user
- Interactive Discord UI: Discord buttons for Attack, Status, Forfeit, and Info
- Turn-based combat: Players take turns attacking each other
- Jutsu selection: Players choose from their available jutsu
- Real-time battle updates: Battle embeds update with each action
- Battle management: View active battles, resume battles, forfeit options
- Testing support: Admin test command for testing the PvP system

Commands:
- /challenge @user - Challenge another player to PvP battle
- /pvp_battles - View all active PvP battles
- /resume_pvp [battle_id] - Resume an active PvP battle
- /battle_status [battle_id] - View battle status (supports both PvP and other battles)
- !test_pvp - Admin command to test PvP system against a bot

The system integrates with the existing character system and provides
a seamless interactive experience through Discord's UI components.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any, List
import random
import asyncio

from ...utils.embeds import create_error_embed
from ...utils.battle_ui import render_battle_view
from ...core.battle.state import BattleState, BattleParticipant
from ...core.character import Character


class PvPBattleView(discord.ui.View):
    """Interactive view for PvP battles with buttons."""
    
    def __init__(self, cog, battle_data: Dict[str, Any]):
        super().__init__(timeout=600)  # 10 minute timeout for PvP
        self.cog = cog
        self.battle_data = battle_data
        self.current_turn_user_id = battle_data["current_turn_user_id"]
        self.challenger_id = battle_data["challenger_id"]
        self.opponent_id = battle_data["opponent_id"]
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the current turn player can use buttons."""
        if interaction.user.id != self.current_turn_user_id:
            if interaction.user.id in [self.challenger_id, self.opponent_id]:
                await interaction.response.send_message(
                    "⏳ It's not your turn! Wait for your opponent to act.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ This is not your battle!", ephemeral=True
                )
            return False
        return True
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.red, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Get current player's character
        if interaction.user.id == self.challenger_id:
            character = self.battle_data["challenger"]
        else:
            character = self.battle_data["opponent"]
        
        jutsu_list = character.get("jutsu", ["Basic Attack", "Punch", "Kick"])
        
        # Create jutsu selection view
        jutsu_view = PvPJutsuSelectionView(self.cog, self.battle_data, jutsu_list, interaction.user.id)
        
        embed = discord.Embed(
            title="🎯 Select Your Jutsu",
            description="Choose which jutsu to use against your opponent:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=jutsu_view, ephemeral=True)
    
    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.gray, emoji="📊")
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        challenger = self.battle_data["challenger"]
        opponent = self.battle_data["opponent"]
        
        # Calculate health percentages
        challenger_hp_percent = (challenger["hp"] / challenger["max_hp"]) * 100
        opponent_hp_percent = (opponent["hp"] / opponent["max_hp"]) * 100
        
        embed = discord.Embed(
            title="📊 Battle Status",
            description=f"**Turn {self.battle_data['turn']}** | **PvP Battle**",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name=f"👤 {challenger['name']} (Challenger)",
            value=f"**HP:** {challenger['hp']}/{challenger['max_hp']} ({challenger_hp_percent:.1f}%)\n"
                  f"**Chakra:** {challenger['chakra']}/{challenger['max_chakra']}\n"
                  f"**Stamina:** {challenger['stamina']}/{challenger['max_stamina']}",
            inline=True
        )
        
        embed.add_field(
            name=f"🎯 {opponent['name']} (Opponent)",
            value=f"**HP:** {opponent['hp']}/{opponent['max_hp']} ({opponent_hp_percent:.1f}%)\n"
                  f"**Chakra:** {opponent['chakra']}/{opponent['max_chakra']}\n"
                  f"**Stamina:** {opponent['stamina']}/{opponent['max_stamina']}",
            inline=True
        )
        
        # Show whose turn it is
        current_player_name = challenger["name"] if self.current_turn_user_id == self.challenger_id else opponent["name"]
        embed.add_field(
            name="⏰ Current Turn",
            value=f"**{current_player_name}**",
            inline=False
        )
        
        # Show recent battle log
        recent_log = self.battle_data.get("battle_log", [])[-3:]  # Last 3 entries
        if recent_log:
            log_text = "\n".join(recent_log)
            embed.add_field(name="⚡ Recent Actions", value=log_text, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🏃 Forfeit", style=discord.ButtonStyle.gray, emoji="🏃")
    async def forfeit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Create confirmation view
        confirm_view = PvPForfeitConfirmationView(self.cog, self.battle_data, interaction.user.id)
        
        embed = discord.Embed(
            title="🏃 Forfeit Battle?",
            description="Are you sure you want to forfeit? You'll lose the battle and your opponent will be declared the winner.",
            color=discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, view=confirm_view, ephemeral=True)
    
    @discord.ui.button(label="ℹ️ Info", style=discord.ButtonStyle.gray, emoji="ℹ️")
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="ℹ️ PvP Battle Info",
            description="**How PvP Battles Work:**",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Turn-Based Combat",
            value="• Players take turns attacking each other\n• Only the current turn player can act\n• Use jutsu to deal damage",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ Battle Actions",
            value="• **Attack:** Choose a jutsu to attack your opponent\n• **Status:** View current battle statistics\n• **Forfeit:** Give up and end the battle",
            inline=False
        )
        
        embed.add_field(
            name="🏆 Victory Conditions",
            value="• Reduce opponent's HP to 0\n• Opponent forfeits\n• Battle timeout (10 minutes)",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class PvPJutsuSelectionView(discord.ui.View):
    """View for selecting jutsu during PvP battle."""
    
    def __init__(self, cog, battle_data: Dict[str, Any], jutsu_list: List[str], user_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.battle_data = battle_data
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
        
        # Execute the attack
        await self.cog.execute_pvp_attack(interaction, self.battle_data, selected_jutsu, self.user_id)


class PvPForfeitConfirmationView(discord.ui.View):
    """View for confirming forfeit action."""
    
    def __init__(self, cog, battle_data: Dict[str, Any], user_id: int):
        super().__init__(timeout=30)
        self.cog = cog
        self.battle_data = battle_data
        self.user_id = user_id
    
    @discord.ui.button(label="Yes, Forfeit", style=discord.ButtonStyle.danger, emoji="🏃")
    async def confirm_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog.execute_pvp_forfeit(interaction, self.battle_data, self.user_id)
    
    @discord.ui.button(label="No, Continue Fighting", style=discord.ButtonStyle.gray, emoji="⚔️")
    async def cancel_forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="⚔️ Back to Battle!",
            description="The fight continues! Show your opponent what you're made of!",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class BattleSystemCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, services=None) -> None:
        self.bot = bot
        self.services = services
        self.active_pvp_battles: Dict[str, Dict[str, Any]] = {}  # Store active PvP battles

    @app_commands.command(name="challenge", description="Challenge another player to battle")
    async def challenge(self, interaction: discord.Interaction, opponent: discord.User) -> None:
        """Challenge another player to a battle."""
        try:
            if opponent.id == interaction.user.id:
                await interaction.response.send_message(
                    embed=create_error_embed("You can't challenge yourself to battle!"),
                    ephemeral=True
                )
                return

            if opponent.bot:
                await interaction.response.send_message(
                    embed=create_error_embed("You can't challenge bots to battle!"),
                    ephemeral=True
                )
                return

            # Check if services are available
            if not hasattr(self.bot, 'services'):
                await interaction.response.send_message(
                    embed=create_error_embed("Battle system not available."),
                    ephemeral=True
                )
                return

            # Load characters
            challenger_char = await self._get_character(interaction.user.id)
            opponent_char = await self._get_character(opponent.id)

            if not challenger_char:
                await interaction.response.send_message(
                    embed=create_error_embed("You need to create a character first!"),
                    ephemeral=True
                )
                return

            if not opponent_char:
                await interaction.response.send_message(
                    embed=create_error_embed(f"{opponent.display_name} doesn't have a character yet!"),
                    ephemeral=True
                )
                return

            # Create battle participants
            challenger_participant = BattleParticipant.from_character(challenger_char)
            opponent_participant = BattleParticipant.from_character(opponent_char)

            # Create battle state
            battle_state = BattleState(
                attacker=challenger_participant,
                defender=opponent_participant,
                current_turn_player_id=str(interaction.user.id)
            )

            # Store battle in persistence (if available)
            if hasattr(self.bot.services, 'battle_persistence'):
                await self.bot.services.battle_persistence.store_active_battle(battle_state.id, battle_state)

            embed = discord.Embed(
                title="⚔️ Battle Challenge!",
                description=f"{interaction.user.mention} challenges {opponent.mention} to battle!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Challenger",
                value=f"{challenger_char.name} (Level {challenger_char.level})\nHP: {challenger_char.hp}",
                inline=True
            )
            embed.add_field(
                name="Opponent",
                value=f"{opponent_char.name} (Level {opponent_char.level})\nHP: {opponent_char.hp}",
                inline=True
            )
            embed.add_field(
                name="Battle ID",
                value=battle_state.id[:8],
                inline=False
            )

            # Create PvP battle data for interactive system
            battle_id = f"pvp_{interaction.user.id}_{opponent.id}_{len(self.active_pvp_battles)}"
            
            view = BattleAcceptView(self, battle_id, challenger_char, opponent_char, opponent.id)
            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error creating battle challenge: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="battle_status", description="View current battle status")
    async def battle_status(self, interaction: discord.Interaction, battle_id: Optional[str] = None) -> None:
        """View the status of a battle."""
        try:
            # Check PvP battles first
            user_pvp_battle = None
            pvp_battle_id = None
            
            if not battle_id:
                # Find user's active PvP battle
                for bid, battle_data in self.active_pvp_battles.items():
                    if (interaction.user.id == battle_data["challenger_id"] or 
                        interaction.user.id == battle_data["opponent_id"]):
                        user_pvp_battle = battle_data
                        pvp_battle_id = bid
                        break
            else:
                user_pvp_battle = self.active_pvp_battles.get(battle_id)
                pvp_battle_id = battle_id

            if user_pvp_battle:
                # Show PvP battle status
                embed = self.create_pvp_battle_embed(user_pvp_battle)
                embed.title = "📊 PvP Battle Status"
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Fall back to original battle system
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'battle_persistence'):
                await interaction.response.send_message(
                    embed=create_error_embed("No active battles found."),
                    ephemeral=True
                )
                return

            # If no battle_id provided, find user's active battle
            if not battle_id:
                active_battles = self.bot.services.battle_persistence.active_battles
                user_battle = None
                for bid, battle in active_battles.items():
                    if (battle.attacker.character.id == interaction.user.id or 
                        battle.defender.character.id == interaction.user.id):
                        user_battle = battle
                        battle_id = bid
                        break
                
                if not user_battle:
                    await interaction.response.send_message(
                        embed=create_error_embed("You're not in any active battles."),
                        ephemeral=True
                    )
                    return
            else:
                user_battle = self.bot.services.battle_persistence.active_battles.get(battle_id)
                if not user_battle:
                    await interaction.response.send_message(
                        embed=create_error_embed("Battle not found."),
                        ephemeral=True
                    )
                    return

            embed = discord.Embed(
                title="⚔️ Battle Status",
                description=f"Battle ID: {battle_id[:8]}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Attacker",
                value=f"{user_battle.attacker.character.name}\nHP: {user_battle.attacker.current_hp}/{user_battle.attacker.character.hp}",
                inline=True
            )
            embed.add_field(
                name="Defender", 
                value=f"{user_battle.defender.character.name}\nHP: {user_battle.defender.current_hp}/{user_battle.defender.character.hp}",
                inline=True
            )
            embed.add_field(
                name="Turn",
                value=f"Turn {user_battle.turn_number}",
                inline=True
            )
            
            current_player = "Attacker" if user_battle.current_turn_player_id == str(user_battle.attacker.character.id) else "Defender"
            embed.add_field(
                name="Current Turn",
                value=current_player,
                inline=True
            )

            if user_battle.battle_log:
                recent_log = "\n".join(user_battle.battle_log[-3:])  # Show last 3 actions
                embed.add_field(
                    name="Recent Actions",
                    value=recent_log,
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error viewing battle status: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="pvp_battles", description="View all active PvP battles")
    async def pvp_battles(self, interaction: discord.Interaction) -> None:
        """View all active PvP battles."""
        try:
            if not self.active_pvp_battles:
                embed = discord.Embed(
                    title="⚔️ Active PvP Battles",
                    description="No PvP battles are currently active.",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="⚔️ Active PvP Battles",
                description=f"There are currently **{len(self.active_pvp_battles)}** active PvP battles:",
                color=discord.Color.blue()
            )

            for battle_id, battle_data in self.active_pvp_battles.items():
                challenger = battle_data["challenger"]
                opponent = battle_data["opponent"]
                current_turn = challenger["name"] if battle_data["current_turn_user_id"] == challenger["id"] else opponent["name"]
                
                embed.add_field(
                    name=f"Battle {battle_id[:8]}",
                    value=f"**{challenger['name']}** vs **{opponent['name']}**\n"
                          f"Turn: {battle_data['turn']} | Current: {current_turn}\n"
                          f"HP: {challenger['hp']}/{challenger['max_hp']} | {opponent['hp']}/{opponent['max_hp']}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error viewing PvP battles: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="resume_pvp", description="Resume an active PvP battle")
    @app_commands.describe(battle_id="The battle ID to resume (optional - finds your active battle if not provided)")
    async def resume_pvp(self, interaction: discord.Interaction, battle_id: Optional[str] = None) -> None:
        """Resume an active PvP battle."""
        try:
            user_battle = None
            found_battle_id = None

            if battle_id:
                # Use provided battle ID
                user_battle = self.active_pvp_battles.get(battle_id)
                found_battle_id = battle_id
            else:
                # Find user's active battle
                for bid, battle_data in self.active_pvp_battles.items():
                    if (interaction.user.id == battle_data["challenger_id"] or 
                        interaction.user.id == battle_data["opponent_id"]):
                        user_battle = battle_data
                        found_battle_id = bid
                        break

            if not user_battle:
                await interaction.response.send_message(
                    embed=create_error_embed("No active PvP battle found."),
                    ephemeral=True
                )
                return

            # Create battle embed and view
            embed = self.create_pvp_battle_embed(user_battle)
            view = PvPBattleView(self, user_battle)

            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error resuming PvP battle: {str(e)}"),
                ephemeral=True
            )

    async def _get_character(self, user_id: int) -> Optional[Character]:
        """Helper method to get a character."""
        try:
            # Try to use the character system from bot services
            if hasattr(self.bot, 'services') and hasattr(self.bot.services, 'character_system'):
                return await self.bot.services.character_system.get_character(user_id)
            
            # Fallback: direct character system access 
            from ...core.character_system import CharacterSystem
            char_system = CharacterSystem()
            return await char_system.get_character(user_id)
        except Exception as e:
            print(f"Error getting character for user {user_id}: {e}")
            return None

    @commands.command(name="test_pvp")
    @commands.has_permissions(administrator=True)
    async def test_pvp(self, ctx: commands.Context):
        """Test command for PvP battles (admin only)."""
        try:
            # Get current user's character
            character = await self._get_character(ctx.author.id)
            if not character:
                await ctx.send("❌ You need to create a character first! Use `/create` command.")
                return

            # Create a test opponent character (simulate another player)
            test_opponent = Character(
                id="test_bot",
                name="Test Ninja",
                clan="Testing Clan",
                level=30,
                hp=300,
                max_hp=300,
                chakra=200,
                max_chakra=200,
                stamina=150,
                max_stamina=150,
                jutsu=["Test Jutsu", "Basic Attack", "Power Strike"]
            )

            # Create PvP battle data
            battle_id = f"test_pvp_{ctx.author.id}_{len(self.active_pvp_battles)}"
            battle_data = {
                "battle_id": battle_id,
                "challenger_id": int(character.id),
                "opponent_id": "test_bot",
                "current_turn_user_id": int(character.id),  # Player goes first
                "turn": 1,
                "challenger": {
                    "id": character.id,
                    "name": character.name,
                    "hp": character.hp,
                    "max_hp": character.max_hp,
                    "chakra": character.chakra,
                    "max_chakra": character.max_chakra,
                    "stamina": character.stamina,
                    "max_stamina": character.max_stamina,
                    "jutsu": character.jutsu,
                    "level": character.level
                },
                "opponent": {
                    "id": test_opponent.id,
                    "name": test_opponent.name,
                    "hp": test_opponent.hp,
                    "max_hp": test_opponent.max_hp,
                    "chakra": test_opponent.chakra,
                    "max_chakra": test_opponent.max_chakra,
                    "stamina": test_opponent.stamina,
                    "max_stamina": test_opponent.max_stamina,
                    "jutsu": test_opponent.jutsu,
                    "level": test_opponent.level
                },
                "battle_log": [
                    f"🧪 **TEST BATTLE INITIATED**",
                    f"⚔️ {character.name} vs {test_opponent.name}",
                    f"🎯 {character.name}'s turn to act!"
                ]
            }

            # Store active battle
            self.active_pvp_battles[battle_id] = battle_data

            # Create battle embed and view
            embed = self.create_pvp_battle_embed(battle_data)
            embed.title = "🧪 **TEST PVP BATTLE** 🧪"
            embed.description = f"**Testing PvP System** | **{character.name} vs {test_opponent.name}**"
            embed.set_footer(text="This is a test battle against a bot opponent!")
            
            view = PvPBattleView(self, battle_data)

            await ctx.send(embed=embed, view=view)

        except Exception as e:
            await ctx.send(f"❌ Error creating test PvP battle: {str(e)}")

    async def start_interactive_pvp_battle(self, interaction: discord.Interaction, battle_id: str, challenger_char, opponent_char):
        """Start an interactive PvP battle."""
        try:
            # Create battle data
            battle_data = {
                "battle_id": battle_id,
                "challenger_id": challenger_char.id,
                "opponent_id": opponent_char.id,
                "current_turn_user_id": challenger_char.id,  # Challenger goes first
                "turn": 1,
                "challenger": {
                    "id": challenger_char.id,
                    "name": challenger_char.name,
                    "hp": challenger_char.hp,
                    "max_hp": challenger_char.max_hp,
                    "chakra": challenger_char.chakra,
                    "max_chakra": challenger_char.max_chakra,
                    "stamina": challenger_char.stamina,
                    "max_stamina": challenger_char.max_stamina,
                    "jutsu": challenger_char.jutsu,
                    "level": challenger_char.level
                },
                "opponent": {
                    "id": opponent_char.id,
                    "name": opponent_char.name,
                    "hp": opponent_char.hp,
                    "max_hp": opponent_char.max_hp,
                    "chakra": opponent_char.chakra,
                    "max_chakra": opponent_char.max_chakra,
                    "stamina": opponent_char.stamina,
                    "max_stamina": opponent_char.max_stamina,
                    "jutsu": opponent_char.jutsu,
                    "level": opponent_char.level
                },
                "battle_log": [
                    f"⚔️ {challenger_char.name} challenges {opponent_char.name} to battle!",
                    f"🎯 {challenger_char.name}'s turn to act!"
                ]
            }

            # Store active battle
            self.active_pvp_battles[battle_id] = battle_data

            # Create battle embed and view
            embed = self.create_pvp_battle_embed(battle_data)
            view = PvPBattleView(self, battle_data)

            # Send the interactive battle interface
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(f"❌ Error starting battle: {str(e)}", ephemeral=True)

    def create_pvp_battle_embed(self, battle_data: Dict[str, Any]) -> discord.Embed:
        """Create a PvP battle embed."""
        challenger = battle_data["challenger"]
        opponent = battle_data["opponent"]
        
        challenger_hp_percent = (challenger["hp"] / challenger["max_hp"]) * 100
        opponent_hp_percent = (opponent["hp"] / opponent["max_hp"]) * 100
        
        embed = discord.Embed(
            title="⚔️ **PVP BATTLE** ⚔️",
            description=f"**Turn {battle_data['turn']}** | **{challenger['name']} vs {opponent['name']}**",
            color=discord.Color.red()
        )
        
        # Challenger stats
        embed.add_field(
            name=f"👤 **{challenger['name']}** (Challenger)",
            value=f"**HP:** {challenger['hp']}/{challenger['max_hp']} ({challenger_hp_percent:.1f}%)\n"
                  f"**Chakra:** {challenger['chakra']}/{challenger['max_chakra']}\n"
                  f"**Level:** {challenger['level']}",
            inline=True
        )
        
        # Opponent stats
        embed.add_field(
            name=f"🎯 **{opponent['name']}** (Opponent)",
            value=f"**HP:** {opponent['hp']}/{opponent['max_hp']} ({opponent_hp_percent:.1f}%)\n"
                  f"**Chakra:** {opponent['chakra']}/{opponent['max_chakra']}\n"
                  f"**Level:** {opponent['level']}",
            inline=True
        )
        
        # Current turn indicator
        current_player_name = challenger["name"] if battle_data["current_turn_user_id"] == challenger["id"] else opponent["name"]
        embed.add_field(
            name="⏰ Current Turn",
            value=f"**{current_player_name}**",
            inline=False
        )
        
        # Battle log
        recent_log = battle_data.get("battle_log", [])[-2:]  # Last 2 entries
        if recent_log:
            log_text = "\n".join(recent_log)
            embed.add_field(name="⚡ Recent Actions", value=log_text, inline=False)
        
        embed.set_footer(text="Use the buttons below to take action in battle!")
        
        return embed

    async def execute_pvp_attack(self, interaction: discord.Interaction, battle_data: Dict[str, Any], jutsu_name: str, attacker_id: int):
        """Execute a PvP attack."""
        try:
            # Determine attacker and defender
            if attacker_id == battle_data["challenger_id"]:
                attacker = battle_data["challenger"]
                defender = battle_data["opponent"]
                attacker_name = "challenger"
                defender_name = "opponent"
            else:
                attacker = battle_data["opponent"]
                defender = battle_data["challenger"]
                attacker_name = "opponent"
                defender_name = "challenger"
            
            # Calculate damage
            base_damage = random.randint(20, 80)
            level_bonus = attacker["level"] * 2
            jutsu_multiplier = self.get_pvp_jutsu_multiplier(jutsu_name)
            
            total_damage = int((base_damage + level_bonus) * jutsu_multiplier)
            
            # Apply damage
            defender["hp"] = max(0, defender["hp"] - total_damage)
            
            # Update battle log
            battle_data["battle_log"].append(f"💥 {attacker['name']} used {jutsu_name} for {total_damage} damage!")
            
            # Check for victory
            if defender["hp"] <= 0:
                await self.handle_pvp_victory(interaction, battle_data, attacker_id)
                return
            
            # Switch turns
            if battle_data["current_turn_user_id"] == battle_data["challenger_id"]:
                battle_data["current_turn_user_id"] = battle_data["opponent_id"]
                next_player = battle_data["opponent"]["name"]
            else:
                battle_data["current_turn_user_id"] = battle_data["challenger_id"]
                next_player = battle_data["challenger"]["name"]
            
            battle_data["turn"] += 1
            battle_data["battle_log"].append(f"🎯 {next_player}'s turn!")
            
            # Check if next turn is a bot (for testing)
            if battle_data["current_turn_user_id"] == "test_bot":
                # Auto-play bot turn after a short delay
                await asyncio.sleep(2)
                await self._execute_bot_turn(interaction, battle_data)
                return
            
            # Update battle display
            embed = self.create_pvp_battle_embed(battle_data)
            view = PvPBattleView(self, battle_data)
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error during attack: {str(e)}", ephemeral=True)

    def get_pvp_jutsu_multiplier(self, jutsu_name: str) -> float:
        """Get damage multiplier for PvP jutsu."""
        jutsu_multipliers = {
            "Rasengan": 1.4,
            "Chidori": 1.3,
            "Great Fireball Jutsu": 1.2,
            "Dragon Flame Jutsu": 1.15,
            "Shadow Clone Jutsu": 1.1,
            "Fireball Jutsu": 1.0,
            "Basic Attack": 0.8,
            "Punch": 0.7,
            "Kick": 0.7
        }
        return jutsu_multipliers.get(jutsu_name, 1.0)

    async def handle_pvp_victory(self, interaction: discord.Interaction, battle_data: Dict[str, Any], winner_id: int):
        """Handle PvP battle victory."""
        try:
            # Determine winner and loser
            if winner_id == battle_data["challenger_id"]:
                winner = battle_data["challenger"]
                loser = battle_data["opponent"]
            else:
                winner = battle_data["opponent"]
                loser = battle_data["challenger"]
            
            # Create victory embed
            embed = discord.Embed(
                title="🏆 **VICTORY!** 🏆",
                description=f"**{winner['name']}** has defeated **{loser['name']}** in epic combat!",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🏆 Winner",
                value=f"**{winner['name']}**\nHP Remaining: {winner['hp']}/{winner['max_hp']}",
                inline=True
            )
            
            embed.add_field(
                name="💀 Defeated",
                value=f"**{loser['name']}**\nHP: 0/{loser['max_hp']}",
                inline=True
            )
            
            embed.add_field(
                name="📊 Battle Stats",
                value=f"**Duration:** {battle_data['turn']} turns\n**Battle ID:** {battle_data['battle_id'][:8]}",
                inline=False
            )
            
            # Remove from active battles
            if battle_data["battle_id"] in self.active_pvp_battles:
                del self.active_pvp_battles[battle_data["battle_id"]]
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error handling victory: {str(e)}", ephemeral=True)

    async def execute_pvp_forfeit(self, interaction: discord.Interaction, battle_data: Dict[str, Any], forfeiting_user_id: int):
        """Handle PvP battle forfeit."""
        try:
            # Determine who forfeited and who wins
            if forfeiting_user_id == battle_data["challenger_id"]:
                forfeiter = battle_data["challenger"]
                winner = battle_data["opponent"]
            else:
                forfeiter = battle_data["opponent"]
                winner = battle_data["challenger"]
            
            # Create forfeit embed
            embed = discord.Embed(
                title="🏃 **BATTLE FORFEITED** 🏃",
                description=f"**{forfeiter['name']}** has forfeited the battle!",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="🏆 Winner by Forfeit",
                value=f"**{winner['name']}**",
                inline=True
            )
            
            embed.add_field(
                name="🏃 Forfeited",
                value=f"**{forfeiter['name']}**",
                inline=True
            )
            
            embed.add_field(
                name="📊 Battle Stats",
                value=f"**Duration:** {battle_data['turn']} turns\n**Battle ID:** {battle_data['battle_id'][:8]}",
                inline=False
            )
            
            # Remove from active battles
            if battle_data["battle_id"] in self.active_pvp_battles:
                del self.active_pvp_battles[battle_data["battle_id"]]
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error handling forfeit: {str(e)}", ephemeral=True)

    async def _execute_bot_turn(self, interaction: discord.Interaction, battle_data: Dict[str, Any]):
        """Execute an automatic bot turn for testing."""
        try:
            # Bot is the opponent
            bot_character = battle_data["opponent"]
            player_character = battle_data["challenger"]
            
            # Choose a random jutsu for the bot
            bot_jutsu = random.choice(bot_character["jutsu"])
            
            # Calculate bot damage
            base_damage = random.randint(15, 60)  # Slightly weaker than player
            level_bonus = bot_character["level"] * 1.5
            jutsu_multiplier = self.get_pvp_jutsu_multiplier(bot_jutsu)
            
            total_damage = int((base_damage + level_bonus) * jutsu_multiplier)
            
            # Apply damage to player
            player_character["hp"] = max(0, player_character["hp"] - total_damage)
            
            # Update battle log
            battle_data["battle_log"].append(f"🤖 {bot_character['name']} used {bot_jutsu} for {total_damage} damage!")
            
            # Check if player is defeated
            if player_character["hp"] <= 0:
                await self.handle_pvp_victory(interaction, battle_data, "test_bot")
                return
            
            # Switch back to player
            battle_data["current_turn_user_id"] = battle_data["challenger_id"]
            battle_data["turn"] += 1
            battle_data["battle_log"].append(f"🎯 {player_character['name']}'s turn!")
            
            # Update battle display
            embed = self.create_pvp_battle_embed(battle_data)
            view = PvPBattleView(self, battle_data)
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error during bot turn: {str(e)}", ephemeral=True)


class BattleAcceptView(discord.ui.View):
    """View for accepting battle challenges."""
    
    def __init__(self, cog, battle_id: str, challenger_char, opponent_char, opponent_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.battle_id = battle_id
        self.challenger_char = challenger_char
        self.opponent_char = opponent_char
        self.opponent_id = opponent_id

    @discord.ui.button(label="Accept Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Only the challenged player can accept this battle!",
                ephemeral=True
            )
            return

        # Start interactive PvP battle
        await self.cog.start_interactive_pvp_battle(interaction, self.battle_id, self.challenger_char, self.opponent_char)

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Decline Battle", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Only the challenged player can decline this battle!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="❌ Battle Declined",
            description=f"{interaction.user.display_name} declined the battle challenge.",
            color=discord.Color.red()
        )

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BattleSystemCommands(bot))
