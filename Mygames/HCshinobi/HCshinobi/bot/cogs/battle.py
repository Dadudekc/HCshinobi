#!/usr/bin/env python
"""
Discord Cog for handling battle commands and interactions.

This cog provides commands to initiate battles and interact with the ongoing battle state.
It creates embeds representing the current battle state and a set of UI buttons for player actions.
Dependencies (BattleManager, etc.) are injected via the bot instance.
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, button
import logging
from typing import Optional, List

# Import core battle components via dependency injection.
try:
    from ...core.battle_manager import BattleManager, BattleState, BattleParticipant, BattleManagerError
except ImportError as e:
    logging.error(f"Error importing BattleManager components: {e}")
    raise

logger = logging.getLogger(__name__)

# --- Helper Functions --- 
def create_battle_embed(battle_state: BattleState) -> discord.Embed:
    """
    Create a Discord embed representing the current battle state.
    
    Args:
        battle_state (BattleState): The state of the battle.
    
    Returns:
        discord.Embed: The constructed embed.
    """
    player = battle_state.player
    opponent = battle_state.opponent
    turn_indicator = "Opponent's Turn" if battle_state.is_ai_turn else "Your Turn"
    embed_color = discord.Color.dark_grey() if battle_state.is_ai_turn else discord.Color.blue()

    embed = discord.Embed(
        title=f"⚔️ Battle: {player.character_id} vs {opponent.character_id} ⚔️",
        description=f"**Turn {battle_state.turn_number}** - {turn_indicator}\n\n*{battle_state.last_action_description}*",
        color=embed_color
    )
    
    player_status = (
        f"❤️ HP: {player.current_hp}/{player.max_hp}\n"
        f"⚡ Chakra: {player.current_chakra}/{player.max_chakra}\n"
        f"✨ Status: {', '.join(player.status_effects) or 'Normal'}"
    )
    embed.add_field(name=f"__**{player.character_id}**__ (Player)", value=player_status, inline=True)
    
    opponent_status = (
        f"❤️ HP: {opponent.current_hp}/{opponent.max_hp}\n"
        f"⚡ Chakra: {opponent.current_chakra}/{opponent.max_chakra}\n"
        f"✨ Status: {', '.join(opponent.status_effects) or 'Normal'}"
    )
    embed.add_field(name=f"__**{opponent.character_id}**__ (Opponent)", value=opponent_status, inline=True)
    
    embed.set_footer(text=f"Battle ID: {battle_state.battle_id}")
    return embed

# --- Action Buttons View --- 
class BattleActionView(View):
    """
    A Discord UI View containing buttons for player actions during battle.
    
    Attributes:
        battle_id (str): The unique identifier for the battle.
        battle_manager (BattleManager): The battle manager handling battle logic.
        _interaction (Optional[discord.Interaction]): The interaction used for updates.
        _message (Optional[discord.Message]): The original message to update.
    """
    def __init__(self, battle_id: str, battle_manager: BattleManager):
        super().__init__(timeout=180)  # View times out after 180 seconds
        self.battle_id = battle_id
        self.battle_manager = battle_manager
        self._interaction: Optional[discord.Interaction] = None
        self._message: Optional[discord.Message] = None

    async def update_view(self, interaction: discord.Interaction, battle_state: BattleState) -> None:
        """
        Updates the battle message embed and view based on the latest battle state.
        
        Args:
            interaction (discord.Interaction): The interaction triggering the update.
            battle_state (BattleState): The current battle state.
        """
        embed = create_battle_embed(battle_state)
        # If the original message isn't stored, attempt to fetch it.
        if not self._message:
            try:
                if battle_state.message_id:
                    channel = interaction.channel
                    self._message = await channel.fetch_message(battle_state.message_id)
            except (discord.NotFound, discord.Forbidden) as e:
                logger.error(f"[View {self.battle_id}] Failed to fetch battle message: {e}")
                await interaction.followup.send("Error: Could not update battle display.", ephemeral=True)
                self.stop()
                return
            except Exception as e:
                logger.exception(f"[View {self.battle_id}] Error fetching message: {e}")
                self.stop()
                return
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.InteractionResponded:
            if self._message:
                await self._message.edit(embed=embed, view=self)
            else:
                logger.error(f"[View {self.battle_id}] Could not edit message; no message object available.")

    async def handle_action(self, interaction: discord.Interaction, action_name: str) -> None:
        """
        Handles button press events and processes the corresponding battle action.
        
        Args:
            interaction (discord.Interaction): The interaction from the button press.
            action_name (str): The name of the action (e.g., "attack", "pass").
        """
        # TODO: Implement user verification (only allow the battle initiator to interact)
        battle_state = self.battle_manager.get_battle_state(self.battle_id)
        if not battle_state:
            await interaction.response.send_message("This battle no longer exists.", ephemeral=True)
            self.stop()
            return

        if battle_state.is_ai_turn:
            await interaction.response.send_message("Please wait for your turn.", ephemeral=True)
            return

        try:
            logger.debug(f"[View {self.battle_id}] Action '{action_name}' triggered by {interaction.user}.")
            updated_state = await self.battle_manager.process_player_action(self.battle_id, action_name)
            await self.update_view(interaction, updated_state)
            if updated_state.player.current_hp <= 0:
                logger.info(f"[View {self.battle_id}] Player defeated. Stopping view.")
                self.stop()
                final_embed = create_battle_embed(updated_state)
                final_embed.description = f"**DEFEAT!** {updated_state.last_action_description}"
                final_embed.color = discord.Color.dark_grey()
                await interaction.edit_original_response(embed=final_embed, view=None)
        except BattleManagerError as e:
            logger.error(f"[View {self.battle_id}] Error processing action '{action_name}': {e}")
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
        except Exception as e:
            logger.exception(f"[View {self.battle_id}] Unexpected error handling action '{action_name}': {e}")
            await interaction.response.send_message("An unexpected error occurred.", ephemeral=True)

    @button(label="Attack", style=discord.ButtonStyle.primary, custom_id="battle_attack")
    async def attack_button(self, interaction: discord.Interaction, button: Button) -> None:
        await self.handle_action(interaction, "attack")
        
    @button(label="Pass", style=discord.ButtonStyle.secondary, custom_id="battle_pass")
    async def pass_button(self, interaction: discord.Interaction, button: Button) -> None:
        await self.handle_action(interaction, "pass")
        
    # Additional buttons (e.g., Defend, Use Skill) can be added similarly.

    async def on_timeout(self) -> None:
        logger.info(f"[View {self.battle_id}] Battle view timed out.")
        if self._message:
            try:
                await self._message.edit(content=f"Battle ({self.battle_id}) timed out.", embed=None, view=None)
            except discord.NotFound:
                logger.warning(f"[View {self.battle_id}] Could not edit message on timeout (not found).")
            except Exception as e:
                logger.error(f"[View {self.battle_id}] Error editing timed-out message: {e}")
        # Optionally signal battle end to the battle manager.

# --- Cog Definition ---
class BattleCommands(commands.Cog):
    """Cog for initiating and managing battles."""
    def __init__(self, bot: "HCShinobiBot"):
        self.bot = bot
        self.battle_manager: BattleManager = bot.battle_manager

    @app_commands.command(name="challenge", description="Challenge an opponent to a battle.")
    @app_commands.describe(
        your_character="Your character file name (e.g., Cap, Chen).",
        opponent="Opponent character file name (default: Solomon)."
    )
    async def challenge(
        self,
        interaction: discord.Interaction,
        your_character: str,
        opponent: str = "Solomon"
    ) -> None:
        """
        Initiates a battle simulation between two characters.
        Prevents using Solomon as your own character and disallows self-challenge.
        """
        await interaction.response.defer(ephemeral=True)
        logger.info(f"{interaction.user.name} initiated challenge: {your_character} vs {opponent}")

        # Use the battle manager to start the battle
        result = await self.bot.battle_manager.start_battle(
            channel_id=interaction.channel_id,
            player1_name=your_character,
            player2_name=opponent
        )

        if "error" in result:
            await interaction.followup.send(result["error"], ephemeral=True)
            return

        # Send confirmation and potentially the initial battle state
        battle_state = result.get("state")
        if battle_state:
            embed = create_battle_embed(battle_state)
            view = BattleActionView(result["battle_id"], self.bot.battle_manager)
            await interaction.followup.send(
                f"⚔️ Battle initiated between {your_character} and {opponent}! Battle ID: {result['battle_id']}",
                embed=embed,
                view=view,
                ephemeral=False # Make battle initiation public?
            )
            # Store the view message ID if needed for later updates
            # message = await interaction.original_response()
            # self.bot.battle_manager.set_battle_message_id(result["battle_id"], message.id)
        else:
            # Fallback message if state isn't immediately available
            await interaction.followup.send(f"Challenge initiated! Battle ID: {result['battle_id']}", ephemeral=True)

async def setup(bot: "HCShinobiBot") -> None:
    """Registers the BattleCommands cog with the bot."""
    if not hasattr(bot, 'battle_manager'):
        logger.error("BattleManager not found on bot. Battle Cog cannot be loaded.")
        raise AttributeError("Missing BattleManager on bot.")
    await bot.add_cog(BattleCommands(bot))
    logger.info("BattleCommands Cog loaded and added to bot.")
