"""
Battle UI Components - Provides interactive UI elements for battles

This module contains reusable battle interface components including:
- Battle view with buttons for attacks, defense, and jutsu
- Battle log display
- Visual HP bars
- Turn management
"""

import discord
import logging
import random
from typing import Dict, Optional, List, Any, Union, Callable, Awaitable, Tuple
import asyncio

from ..core.character import Character

logger = logging.getLogger(__name__)

class BattleActionButton(discord.ui.Button):
    """Button for battle actions like attack, defend, etc."""
    
    def __init__(self, action_type: str, label: str, style: discord.ButtonStyle, emoji: str = None):
        super().__init__(
            label=label, 
            style=style,
            emoji=emoji,
            custom_id=f"battle_action_{action_type}"
        )
        self.action_type = action_type
    
    async def callback(self, interaction: discord.Interaction):
        view: 'BattleViewBase' = self.view
        await view.handle_action(interaction, self.action_type)


class JutsuSelectMenu(discord.ui.Select):
    """Dropdown menu for selecting jutsu to use in battle."""
    
    def __init__(self, jutsu_list: List[str]):
        options = [
            discord.SelectOption(
                label=jutsu_name[:25],  # Discord limits option label length
                value=jutsu_name
            ) for jutsu_name in jutsu_list[:25]  # Max 25 options in a select
        ]
        
        super().__init__(
            placeholder="Select a jutsu to use...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="battle_jutsu_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        view: 'BattleViewBase' = self.view
        await view.handle_jutsu_selection(interaction, self.values[0])


class BattleViewBase(discord.ui.View):
    """Base interactive battle interface with common functionality."""
    
    def __init__(self, timeout: int = 180):
        super().__init__(timeout=timeout)  # 3 minute default timeout
        self.message = None
        self.battle_log = []
        self.winner = None
    
    def add_to_log(self, message: str):
        """Add a message to the battle log."""
        self.battle_log.append(message)
        # Keep log size reasonable
        if len(self.battle_log) > 10:
            self.battle_log = self.battle_log[-10:]
    
    async def handle_action(self, interaction: discord.Interaction, action_type: str):
        """Handle player action selection - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement handle_action")
        
    async def handle_jutsu_selection(self, interaction: discord.Interaction, jutsu_name: str):
        """Handle jutsu selection from dropdown - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement handle_jutsu_selection")
    
    async def update_battle_view(self, interaction: discord.Interaction):
        """Update the battle message with current state."""
        embed = self.create_battle_embed()
        
        # If battle ended, disable the view
        if self.winner:
            for item in self.children:
                item.disabled = True
        
        try:
            if self.message:
                await self.message.edit(embed=embed, view=self)
            else:
                # This is the first update, store the message
                await interaction.followup.send(embed=embed, view=self)
                self.message = await interaction.original_response()
        except Exception as e:
            logger.error(f"Error updating battle view: {e}", exc_info=True)
    
    def create_battle_embed(self) -> discord.Embed:
        """Create embed showing current battle state - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement create_battle_embed")
    
    async def on_timeout(self):
        """Handle view timeout."""
        if self.message:
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            try:
                await self.message.edit(view=self)
            except:
                pass


class SimpleBattleView(BattleViewBase):
    """
    Interactive battle interface with buttons for actions.
    This version is simplified and doesn't require a full battle system.
    """
    
    def __init__(
        self, 
        player: Character, 
        opponent: Character,
        on_battle_end: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
    ):
        super().__init__(timeout=180)  # 3 minute timeout
        self.player = player
        self.player_hp = player.hp
        self.opponent = opponent
        self.opponent_hp = opponent.hp
        self.turn_count = 1
        self.on_battle_end = on_battle_end  # Callback when battle ends
        self.defending = False
        self.battle_data = {}  # Store additional battle data
        
        # Add action buttons
        self.add_item(BattleActionButton(
            action_type="attack",
            label="Attack",
            style=discord.ButtonStyle.danger,
            emoji="⚔️"
        ))
        self.add_item(BattleActionButton(
            action_type="defend",
            label="Defend",
            style=discord.ButtonStyle.primary,
            emoji="🛡️"
        ))
        
        # Add jutsu button or select menu if player has jutsu
        if player.jutsu and len(player.jutsu) > 0:
            if len(player.jutsu) <= 5:  # If few jutsu, use buttons
                for jutsu_name in player.jutsu[:5]:  # Limit to 5 buttons
                    self.add_item(BattleActionButton(
                        action_type=f"jutsu_{jutsu_name}",
                        label=jutsu_name[:20],  # Keep label short
                        style=discord.ButtonStyle.success,
                        emoji="✨"
                    ))
            else:  # If many jutsu, use a select menu
                self.add_item(JutsuSelectMenu(player.jutsu))
        
        # Add additional buttons
        self.add_item(BattleActionButton(
            action_type="flee",
            label="Flee",
            style=discord.ButtonStyle.secondary,
            emoji="🏃"
        ))
    
    def create_battle_embed(self) -> discord.Embed:
        """Create embed showing current battle state."""
        # Determine embed color based on situation
        if self.winner:
            color = discord.Color.green() if self.winner == self.player.id else discord.Color.red()
        else:
            color = discord.Color.gold()
        
        # Create the base embed
        embed = discord.Embed(
            title=f"⚔️ Battle: {self.player.name} vs {self.opponent.name}",
            description=f"Turn {self.turn_count}" if not self.winner else "Battle Complete!",
            color=color
        )
        
        # Calculate HP percentage and create HP bars
        player_hp_percent = max(0, min(1, self.player_hp / self.player.hp))
        player_hp_bar = "█" * int(player_hp_percent * 10) + "░" * (10 - int(player_hp_percent * 10))
        
        opponent_hp_percent = max(0, min(1, self.opponent_hp / self.opponent.hp))
        opponent_hp_bar = "█" * int(opponent_hp_percent * 10) + "░" * (10 - int(opponent_hp_percent * 10))
        
        # Add player and opponent fields
        embed.add_field(
            name=f"{self.player.name} (You)",
            value=f"HP: {self.player_hp}/{self.player.hp} [{player_hp_bar}]\nChakra: {self.player.chakra}\nRank: {self.player.rank}",
            inline=True
        )
        
        embed.add_field(
            name=f"{self.opponent.name}",
            value=f"HP: {self.opponent_hp}/{self.opponent.hp} [{opponent_hp_bar}]\nChakra: {self.opponent.chakra}\nRank: {self.opponent.rank}",
            inline=True
        )
        
        # Add battle log field
        if self.battle_log:
            log_text = "\n".join(self.battle_log[-5:])  # Show last 5 log entries
            embed.add_field(
                name="Battle Log",
                value=f"```\n{log_text}\n```",
                inline=False
            )
        
        # Add footer with battle stats
        embed.set_footer(text=f"Battle | Turn {self.turn_count}")
        return embed
    
    async def handle_action(self, interaction: discord.Interaction, action_type: str):
        """Handle player action selection."""
        # Make sure only the player can interact
        if str(interaction.user.id) != self.player.id:
            await interaction.response.send_message("This is not your battle!", ephemeral=True)
            return
        
        # Process different action types
        if action_type == "attack":
            await self.process_attack(interaction)
        elif action_type == "defend":
            await self.process_defend(interaction)
        elif action_type == "flee":
            await self.process_flee(interaction)
        elif action_type.startswith("jutsu_"):
            jutsu_name = action_type.replace("jutsu_", "")
            await self.process_jutsu(interaction, jutsu_name)
        else:
            await interaction.response.send_message("Unknown action type", ephemeral=True)
    
    async def handle_jutsu_selection(self, interaction: discord.Interaction, jutsu_name: str):
        """Handle jutsu selection from dropdown."""
        await self.process_jutsu(interaction, jutsu_name)
    
    async def process_attack(self, interaction: discord.Interaction):
        """Process basic attack action."""
        await interaction.response.defer()
        
        # Calculate damage (basic formula - can be enhanced)
        base_damage = self.player.strength // 2
        variation = random.randint(-2, 2)
        damage = max(1, base_damage + variation)
        
        # Update opponent HP
        self.opponent_hp = max(0, self.opponent_hp - damage)
        
        # Add to battle log
        self.add_to_log(f"{self.player.name} attacks for {damage} damage!")
        
        # Check if battle is over
        if self.opponent_hp <= 0:
            await self.end_battle(self.player.id)
        else:
            # Process opponent's turn
            await self.opponent_turn()
        
        # Update the battle view
        await self.update_battle_view(interaction)
    
    async def process_defend(self, interaction: discord.Interaction):
        """Process defend action."""
        await interaction.response.defer()
        
        # Defending reduces damage on next opponent turn
        self.defending = True
        self.add_to_log(f"{self.player.name} takes a defensive stance!")
        
        # Process opponent's turn
        await self.opponent_turn()
        
        # Update the battle view
        await self.update_battle_view(interaction)
    
    async def process_jutsu(self, interaction: discord.Interaction, jutsu_name: str):
        """Process jutsu use action."""
        await interaction.response.defer()
        
        # Simple implementation - more complex jutsu system would be implemented here
        base_damage = self.player.ninjutsu // 2 + 2
        variation = random.randint(-1, 3)
        damage = max(1, base_damage + variation)
        
        # Update opponent HP
        self.opponent_hp = max(0, self.opponent_hp - damage)
        
        # Add to battle log
        self.add_to_log(f"{self.player.name} uses {jutsu_name} for {damage} damage!")
        
        # Check if battle is over
        if self.opponent_hp <= 0:
            await self.end_battle(self.player.id)
        else:
            # Process opponent's turn
            await self.opponent_turn()
        
        # Update the battle view
        await self.update_battle_view(interaction)
    
    async def process_flee(self, interaction: discord.Interaction):
        """Process flee action."""
        await interaction.response.defer()
        
        # Simple flee logic - 30% chance to succeed
        flee_success = random.random() < 0.3
        
        if flee_success:
            self.add_to_log(f"{self.player.name} successfully fled from battle!")
            await self.end_battle(None)  # No winner
        else:
            self.add_to_log(f"{self.player.name} tried to flee but failed!")
            # Process opponent's turn
            await self.opponent_turn()
        
        # Update the battle view
        await self.update_battle_view(interaction)
    
    async def opponent_turn(self):
        """Process opponent's turn."""
        # Skip if battle is already over
        if self.winner:
            return
            
        # Simple AI for opponent
        actions = ["attack", "jutsu"]
        action = random.choice(actions)
        
        damage_reduction = 0.5 if self.defending else 1.0
        self.defending = False  # Reset defending status
        
        if action == "attack":
            base_damage = self.opponent.strength // 2
            variation = random.randint(-2, 2)
            damage = max(1, int((base_damage + variation) * damage_reduction))
            
            # Update player HP
            self.player_hp = max(0, self.player_hp - damage)
            
            # Add to battle log
            self.add_to_log(f"{self.opponent.name} attacks for {damage} damage!")
        else:  # Use jutsu
            if self.opponent.jutsu:
                jutsu_name = random.choice(self.opponent.jutsu)
                base_damage = self.opponent.ninjutsu // 2 + 1
                variation = random.randint(-1, 3)
                damage = max(1, int((base_damage + variation) * damage_reduction))
                
                # Update player HP
                self.player_hp = max(0, self.player_hp - damage)
                
                # Add to battle log
                self.add_to_log(f"{self.opponent.name} uses {jutsu_name} for {damage} damage!")
            else:
                # Fallback to basic attack
                base_damage = self.opponent.strength // 2
                variation = random.randint(-2, 2)
                damage = max(1, int((base_damage + variation) * damage_reduction))
                
                # Update player HP
                self.player_hp = max(0, self.player_hp - damage)
                
                # Add to battle log
                self.add_to_log(f"{self.opponent.name} attacks for {damage} damage!")
        
        # Check if battle is over
        if self.player_hp <= 0:
            await self.end_battle(self.opponent.id)
        
        # Increment turn counter
        self.turn_count += 1
    
    async def end_battle(self, winner_id: Optional[str]):
        """End the battle and determine the result."""
        self.winner = winner_id
        
        if winner_id:
            if winner_id == self.player.id:
                self.add_to_log(f"{self.player.name} has defeated {self.opponent.name}!")
            else:
                self.add_to_log(f"{self.opponent.name} has defeated {self.player.name}!")
        else:
            self.add_to_log("The battle ended with no clear winner.")
            
        # Store battle results
        self.battle_data = {
            "winner_id": winner_id,
            "player_hp_remaining": self.player_hp,
            "opponent_hp_remaining": self.opponent_hp,
            "turns": self.turn_count,
            "battle_log": self.battle_log.copy()
        }
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
            
        # Call the battle end callback if provided
        if self.on_battle_end:
            try:
                await self.on_battle_end(winner_id, self.battle_data)
            except Exception as e:
                logger.error(f"Error in battle end callback: {e}", exc_info=True)


class BattleSystemView(BattleViewBase):
    """
    Battle view that integrates with the existing BattleSystem.
    This class adapts our interactive UI to work with the existing battle logic.
    """
    
    def __init__(
        self, 
        battle_id: str, 
        player: Character, 
        opponent: Character,
        battle_manager: Any,  # BattleManager
        battle_system: Any  # BattleSystem
    ):
        super().__init__(timeout=300)  # 5 minute timeout
        self.battle_id = battle_id
        self.player = player
        self.opponent = opponent
        self.battle_manager = battle_manager
        self.battle_system = battle_system
        
        # Add action buttons
        self.add_item(BattleActionButton(
            action_type="attack",
            label="Attack",
            style=discord.ButtonStyle.danger,
            emoji="⚔️"
        ))
        self.add_item(BattleActionButton(
            action_type="defend",
            label="Defend",
            style=discord.ButtonStyle.primary,
            emoji="🛡️"
        ))
        
        # Add jutsu button or select menu if player has jutsu
        if player.jutsu and len(player.jutsu) > 0:
            if len(player.jutsu) <= 5:  # If few jutsu, use buttons
                for jutsu_name in player.jutsu[:5]:  # Limit to 5 buttons
                    self.add_item(BattleActionButton(
                        action_type=f"jutsu_{jutsu_name}",
                        label=jutsu_name[:20],  # Keep label short
                        style=discord.ButtonStyle.success,
                        emoji="✨"
                    ))
            else:  # If many jutsu, use a select menu
                self.add_item(JutsuSelectMenu(player.jutsu))
        
        # Add flee button
        self.add_item(BattleActionButton(
            action_type="flee",
            label="Flee",
            style=discord.ButtonStyle.secondary,
            emoji="🏃"
        ))
        
        # Get initial battle state
        self.battle_state = self.battle_system.get_battle_state(self.battle_id)
        self.is_active = self.battle_state and self.battle_state.is_active
        
        # Update button states
        self.update_buttons()
        
    def update_buttons(self):
        """Disable buttons if battle is not active."""
        for item in self.children:
            item.disabled = not self.is_active
            
    def create_battle_embed(self) -> discord.Embed:
        """Create an embed showing current battle state."""
        # Get current battle state
        state = self.battle_system.get_battle_state(self.battle_id) or self.battle_state
        
        # Determine embed color and state
        if not state or not state.is_active:
            color = discord.Color.green()
            status = "Battle Complete!"
        else:
            color = discord.Color.gold()
            # Check if state has current_turn attribute, use turn_count or a default if not
            if hasattr(state, 'current_turn'):
                status = f"Turn: {state.current_turn}"
            elif hasattr(state, 'turn_count'):
                status = f"Turn: {state.turn_count}"
            else:
                # Get whose turn it is
                current_player_id = state.current_turn_player_id if hasattr(state, 'current_turn_player_id') else None
                if current_player_id:
                    # Show whose turn it is based on ID
                    if current_player_id == state.attacker.id:
                        status = f"Turn: {state.attacker.name}"
                    else:
                        status = f"Turn: {state.defender.name}"
                else:
                    # Fallback
                    status = "Battle In Progress"
            
        # Create base embed
        embed = discord.Embed(
            title=f"⚔️ Battle: {self.player.name} vs {self.opponent.name}",
            description=status,
            color=color
        )
        
        # Add player HP bars
        if state:
            attacker = state.attacker
            defender = state.defender
            
            # Create HP bars
            attacker_hp_percent = max(0, min(1, state.attacker_hp / attacker.hp))
            attacker_hp_bar = "█" * int(attacker_hp_percent * 10) + "░" * (10 - int(attacker_hp_percent * 10))
            
            defender_hp_percent = max(0, min(1, state.defender_hp / defender.hp))
            defender_hp_bar = "█" * int(defender_hp_percent * 10) + "░" * (10 - int(defender_hp_percent * 10))
            
            # Add fields for each player
            embed.add_field(
                name=f"{attacker.name}",
                value=f"HP: {state.attacker_hp}/{attacker.hp} [{attacker_hp_bar}]\n"
                      f"Chakra: {state.attacker_chakra}/{attacker.chakra}\n"
                      f"Rank: {attacker.rank}",
                inline=True
            )
            
            embed.add_field(
                name=f"{defender.name}",
                value=f"HP: {state.defender_hp}/{defender.hp} [{defender_hp_bar}]\n"
                      f"Chakra: {state.defender_chakra}/{defender.chakra}\n"
                      f"Rank: {defender.rank}",
                inline=True
            )
            
            # Add battle log
            if state.battle_log:
                log_text = "\n".join(state.battle_log[-5:])  # Last 5 log entries
                embed.add_field(
                    name="Battle Log",
                    value=f"```\n{log_text}\n```",
                    inline=False
                )
                
            # Show winner if battle is over
            if not state.is_active and state.winner_id:
                winner = attacker if state.winner_id == attacker.id else defender
                embed.add_field(
                    name="Result",
                    value=f"**{winner.name}** has won the battle!",
                    inline=False
                )
        
        return embed
        
    async def handle_action(self, interaction: discord.Interaction, action_type: str):
        """Handle a player action button press."""
        # Make sure it's the player's turn
        state = self.battle_system.get_battle_state(self.battle_id)
        if not state or not state.is_active:
            await interaction.response.send_message("This battle has already ended.", ephemeral=True)
            return
            
        current_turn_id = state.current_turn_player_id
        if str(interaction.user.id) != current_turn_id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
            
        # Process the action
        await interaction.response.defer()
        
        action_dict = {"type": "basic_attack"}  # Default action
        
        if action_type == "attack":
            action_dict = {"type": "basic_attack"}
        elif action_type == "defend":
            action_dict = {"type": "defend"}
        elif action_type == "flee":
            action_dict = {"type": "flee"}
        elif action_type.startswith("jutsu_"):
            jutsu_name = action_type.replace("jutsu_", "")
            action_dict = {"type": "jutsu", "jutsu_name": jutsu_name}
            
        # Submit the action to the battle system
        try:
            result = await self.battle_manager.process_player_action(
                str(interaction.user.id),
                action_dict,
                self.battle_id
            )
            
            # Update battle state
            updated_state = self.battle_system.get_battle_state(self.battle_id)
            if updated_state:
                self.battle_state = updated_state
                self.is_active = updated_state.is_active
                
            # Update view
            self.update_buttons()
            await self.update_battle_view(interaction)
            
            # Stop the view if battle ended
            if not self.is_active:
                self.stop()
                
        except Exception as e:
            logger.error(f"Error processing battle action: {e}", exc_info=True)
            await interaction.followup.send(f"Error processing your action: {str(e)}", ephemeral=True)
    
    async def handle_jutsu_selection(self, interaction: discord.Interaction, jutsu_name: str):
        """Handle jutsu selection from dropdown."""
        action_dict = {"type": "jutsu", "jutsu_name": jutsu_name}
        await self.handle_action(interaction, f"jutsu_{jutsu_name}") 