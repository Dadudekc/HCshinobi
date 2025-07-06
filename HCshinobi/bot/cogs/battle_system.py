import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from ...utils.embeds import create_error_embed
from ...utils.battle_ui import render_battle_view
from ...core.battle.state import BattleState, BattleParticipant
from ...core.character import Character


class BattleSystemCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, services=None) -> None:
        self.bot = bot
        self.services = services

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

            view = BattleAcceptView(battle_state, opponent.id)
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
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'battle_persistence'):
                await interaction.response.send_message(
                    embed=create_error_embed("Battle system not available."),
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

    async def _get_character(self, user_id: int) -> Optional[Character]:
        """Helper method to get a character."""
        if hasattr(self.bot.services, 'character_system'):
            return await self.bot.services.character_system.get_character(user_id)
        return None


class BattleAcceptView(discord.ui.View):
    """View for accepting battle challenges."""
    
    def __init__(self, battle_state: BattleState, opponent_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.battle_state = battle_state
        self.opponent_id = opponent_id

    @discord.ui.button(label="Accept Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message(
                "Only the challenged player can accept this battle!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚔️ Battle Accepted!",
            description=f"The battle between {self.battle_state.attacker.character.name} and {self.battle_state.defender.character.name} begins!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Current Turn",
            value=f"{self.battle_state.attacker.character.name}",
            inline=True
        )
        embed.add_field(
            name="Battle Commands",
            value="Use `/attack` to attack your opponent!",
            inline=False
        )

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

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
