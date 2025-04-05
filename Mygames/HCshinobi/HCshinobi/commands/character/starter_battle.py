"""
Starter Battle Module - Handles the Academy Entrance Test Battle
"""

import asyncio
import discord
import logging
import random
from typing import Dict, Optional, Tuple, Any, List

from ...core.character import Character
from ...core.battle_system import BattleSystem
from ...core.loot_system import LootSystem
from ...core.battle_manager import BattleManager  # Add import for BattleManager

logger = logging.getLogger(__name__)

# --- Interactive Battle UI Components --- #

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
        view: BattleView = self.view
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
        view: BattleView = self.view
        await view.handle_jutsu_selection(interaction, self.values[0])


class BattleView(discord.ui.View):
    """Interactive battle interface with buttons for actions."""
    
    def __init__(self, battle: 'StarterBattle', player: Character, opponent: Character):
        super().__init__(timeout=180)  # 3 minute timeout
        self.battle = battle
        self.player = player
        self.player_hp = player.hp
        self.opponent = opponent
        self.opponent_hp = opponent.hp
        self.turn_count = 1
        self.battle_log = []
        self.message = None
        self.winner = None
        
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
    
    def add_to_log(self, message: str):
        """Add a message to the battle log."""
        self.battle_log.append(message)
        # Keep log size reasonable
        if len(self.battle_log) > 10:
            self.battle_log = self.battle_log[-10:]
    
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
        embed.set_footer(text=f"Academy Entrance Test | Turn {self.turn_count}")
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
        
        # For the academy test, always allow fleeing but count as a loss
        self.add_to_log(f"{self.player.name} attempts to flee from the battle!")
        self.add_to_log("You cannot run from the Academy Entrance Test!")
        
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
        
        damage_reduction = 0.5 if getattr(self, "defending", False) else 1.0
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
        
        # For the entrance test, make sure the player wins eventually
        if self.player_hp <= 5:
            # Make opponent weak
            self.add_to_log(f"{self.opponent.name} is looking tired!")
            self.opponent_hp = min(self.opponent_hp, 5)
        
        # Check if battle is over
        if self.player_hp <= 0:
            # For academy test, player's HP doesn't go below 1
            self.player_hp = 1
            self.add_to_log(f"{self.player.name} narrowly avoids defeat!")
        
        # Increment turn counter
        self.turn_count += 1
    
    async def end_battle(self, winner_id: str):
        """End the battle and determine the result."""
        self.winner = winner_id
        
        if winner_id == self.player.id:
            self.add_to_log(f"{self.player.name} has defeated {self.opponent.name}!")
        else:
            self.add_to_log(f"{self.opponent.name} has defeated {self.player.name}!")
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
    
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


class AcademyNPC:
    """Represents an NPC for the academy entrance battle."""
    
    def __init__(self, name: str, level: int = 1):
        """Initialize the Academy NPC."""
        self.id = f"npc_{name.lower().replace(' ', '_')}"
        self.name = name
        self.level = level
        
        # Base stats for an academy instructor
        self.hp = 50
        self.chakra = 40
        self.stamina = 40
        self.strength = 8
        self.speed = 8
        self.ninjutsu = 10
        self.taijutsu = 10
        self.genjutsu = 8
        self.intelligence = 12
        self.perception = 10
        self.willpower = 10
        self.chakra_control = 12
        
        # Required for battle system
        self.rank = "Chunin"
        self.clan = "Academy"
        self.specialization = "Ninjutsu"
        self.jutsu = ["Basic Strike", "Academy Test Jutsu"]
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.level = 5  # Academy instructor level
        self.wins_against_rank = {}
        
    def to_character(self) -> Character:
        """Convert NPC to Character object for battle system."""
        return Character(
            id=self.id,
            name=self.name,
            hp=self.hp,
            chakra=self.chakra,
            stamina=self.stamina,
            strength=self.strength,
            speed=self.speed,
            ninjutsu=self.ninjutsu,
            taijutsu=self.taijutsu,
            genjutsu=self.genjutsu,
            intelligence=self.intelligence,
            perception=self.perception,
            willpower=self.willpower,
            chakra_control=self.chakra_control,
            rank=self.rank,
            clan=self.clan,
            specialization=self.specialization,
            jutsu=self.jutsu,
            wins=self.wins,
            losses=self.losses,
            draws=self.draws,
            level=self.level,
            wins_against_rank=self.wins_against_rank
        )

class AcademyLoot:
    """Handles the loot drops for academy entrance battles."""
    
    # Define loot tables with weighted probabilities
    LOOT_TABLES = {
        "win": {
            "Common": {
                "weight": 60,
                "items": [
                    {"name": "Academy Uniform", "type": "equipment", "chance": 50},
                    {"name": "Basic Kunai Set", "type": "equipment", "chance": 70},
                    {"name": "Ninja Headband", "type": "equipment", "chance": 100},
                    {"name": "Academy Textbook", "type": "item", "chance": 80},
                    {"name": "Practice Shuriken", "type": "item", "chance": 90}
                ],
                "ryo_range": (100, 200),
                "color": 0x969696  # Gray
            },
            "Uncommon": {
                "weight": 25,
                "items": [
                    {"name": "Quality Kunai Set", "type": "equipment", "chance": 60},
                    {"name": "Starter Chakra Scroll", "type": "jutsu", "chance": 70},
                    {"name": "Training Weights", "type": "equipment", "chance": 50},
                    {"name": "Chakra Paper", "type": "item", "chance": 80}
                ],
                "ryo_range": (200, 350),
                "color": 0x1E88E5  # Blue
            },
            "Rare": {
                "weight": 10,
                "items": [
                    {"name": "Elite Headband", "type": "equipment", "chance": 40},
                    {"name": "Basic Nature Scroll", "type": "jutsu", "chance": 60},
                    {"name": "Academy Top Student Badge", "type": "item", "chance": 50}
                ],
                "ryo_range": (350, 500),
                "color": 0x9C27B0  # Purple
            },
            "Epic": {
                "weight": 4,
                "items": [
                    {"name": "Chakra Enhancing Gloves", "type": "equipment", "chance": 30},
                    {"name": "Advanced Training Manual", "type": "jutsu", "chance": 40},
                    {"name": "Academy Excellence Medal", "type": "item", "chance": 35}
                ],
                "ryo_range": (500, 800),
                "color": 0xFF9800  # Orange
            },
            "Legendary": {
                "weight": 1,
                "items": [
                    {"name": "Hokage's Recognition Letter", "type": "item", "chance": 20},
                    {"name": "Academy Prodigy Title", "type": "title", "chance": 100},
                    {"name": "First Rank Jutsu", "type": "jutsu", "chance": 30}
                ],
                "ryo_range": (800, 1500),
                "color": 0xFFD700  # Gold
            }
        },
        "lose": {
            "Common": {
                "weight": 90,
                "items": [
                    {"name": "Practice Bandages", "type": "item", "chance": 80},
                    {"name": "Training Notes", "type": "item", "chance": 70}
                ],
                "ryo_range": (25, 50),
                "color": 0x969696  # Gray
            },
            "Uncommon": {
                "weight": 10,
                "items": [
                    {"name": "Second Chance Token", "type": "item", "chance": 50},
                    {"name": "Encouragement Letter", "type": "item", "chance": 60}
                ],
                "ryo_range": (50, 100),
                "color": 0x1E88E5  # Blue
            }
        }
    }
    
    @staticmethod
    def roll_loot(outcome: str = "win") -> Dict:
        """
        Roll for loot based on battle outcome.
        
        Args:
            outcome: "win" or "lose" to determine loot table
            
        Returns:
            Dict containing loot information
        """
        # Get appropriate loot table
        loot_table = AcademyLoot.LOOT_TABLES.get(outcome, AcademyLoot.LOOT_TABLES["lose"])
        
        # Roll for rarity
        total_weight = sum(rarity["weight"] for rarity in loot_table.values())
        roll = random.randint(1, total_weight)
        
        current_weight = 0
        selected_rarity = None
        for rarity, info in loot_table.items():
            current_weight += info["weight"]
            if roll <= current_weight:
                selected_rarity = rarity
                break
                
        if not selected_rarity:
            selected_rarity = list(loot_table.keys())[0]  # Default to first rarity
            
        # Get rarity info
        rarity_info = loot_table[selected_rarity]
        
        # Roll for ryo amount
        ryo_min, ryo_max = rarity_info["ryo_range"]
        ryo_amount = random.randint(ryo_min, ryo_max)
        
        # Roll for items
        items = []
        for item in rarity_info["items"]:
            if random.randint(1, 100) <= item["chance"]:
                items.append(item)
        
        # Create loot data
        loot_data = {
            "rarity": selected_rarity,
            "color": rarity_info["color"],
            "ryo": ryo_amount,
            "items": items
        }
        
        return loot_data

class StarterBattle:
    """
    Manages the academy entrance battle that happens after character creation.
    """
    
    def __init__(
        self, 
        battle_system: Any,  # Change type hint to Any to accept either BattleSystem or BattleManager
        character_system: Any, 
        currency_system: Any,
        loot_system: LootSystem
    ):
        """Initialize the starter battle system."""
        # Determine what type of battle system we have
        self.is_battle_manager = isinstance(battle_system, BattleManager)
        self.battle_system = battle_system
        self.character_system = character_system
        self.currency_system = currency_system
        self.loot_system = loot_system
        self.logger = logging.getLogger(__name__)
        
        # Create instructor NPCs
        self.instructors = [
            AcademyNPC("Instructor Hiroshi"),
            AcademyNPC("Instructor Ayame"),
            AcademyNPC("Instructor Takeshi")
        ]
    
    async def start_entrance_battle(self, interaction: discord.Interaction, character: Character) -> bool:
        """
        Start the academy entrance battle for a new character.
        
        Args:
            interaction: The Discord interaction
            character: The player's character
            
        Returns:
            True if the battle was initiated successfully
        """
        # Select a random instructor
        instructor = random.choice(self.instructors)
        instructor_char = instructor.to_character()
        
        # Ensure the instructor is temporarily registered in the character system
        # This is necessary for the battle system to retrieve the character
        if hasattr(self.character_system, 'characters'):
            self.character_system.characters[instructor_char.id] = instructor_char
            self.logger.info(f"Registered instructor {instructor_char.name} ({instructor_char.id}) temporarily in character system")
        
        # Create an embed for the battle intro
        embed = discord.Embed(
            title="🏫 Academy Entrance Test",
            description=f"Welcome, {character.name}! To enter the Ninja Academy, you must first demonstrate your skills in battle against {instructor_char.name}.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Your Opponent", value=f"{instructor_char.name} (Rank: {instructor_char.rank})", inline=False)
        embed.add_field(name="Instructions", value="Show your skills in battle! Use attacks and jutsu to defeat your opponent. This is a test, so don't worry about losing.", inline=False)
        
        # Send the intro message
        await interaction.followup.send(embed=embed)
        await asyncio.sleep(2)  # Brief pause for dramatic effect
        
        # Instead of starting a real battle system battle, use our interactive battle
        battle_view = BattleView(self, character, instructor_char)
        message = await interaction.followup.send(embed=battle_view.create_battle_embed(), view=battle_view)
        battle_view.message = message
        
        # Wait for battle to complete
        await battle_view.wait()
        
        # Check the result - for academy test, player always wins
        if not battle_view.winner:
            # If timeout occurred, set player as winner
            battle_view.winner = character.id
            battle_view.add_to_log(f"{character.name} passes the test by determination!")
            
            # Update the view one last time
            for item in battle_view.children:
                item.disabled = True
            
            await battle_view.message.edit(embed=battle_view.create_battle_embed(), view=battle_view)
        
        # Battle completed message
        battle_end_embed = discord.Embed(
            title="🏆 Battle Complete!",
            description=f"Congratulations! You've demonstrated your skills and defeated {instructor_char.name}!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=battle_end_embed)
        
        # Generate loot
        loot_data = AcademyLoot.roll_loot("win")
        
        # Create loot embed
        loot_embed = discord.Embed(
            title=f"🎁 {loot_data['rarity']} Reward!",
            description=f"For passing your entrance test, you've earned:",
            color=loot_data['color']
        )
        
        # Add ryo reward
        loot_embed.add_field(name="Ryō", value=f"{loot_data['ryo']:,}", inline=False)
        
        # Add items if any
        if loot_data['items']:
            items_text = "\n".join([f"• {item['name']}" for item in loot_data['items']])
            loot_embed.add_field(name="Items", value=items_text, inline=False)
            
            # Process items (would normally be added to inventory)
            # Here we'll just acknowledge it
            loot_embed.add_field(
                name="Note", 
                value="These items will be available once the inventory system is fully implemented.", 
                inline=False
            )
        
        # Add ryo to player's balance
        if hasattr(self.currency_system, 'add_balance_and_save'):
            self.currency_system.add_balance_and_save(character.id, loot_data['ryo'])
            self.logger.info(f"Added {loot_data['ryo']} Ryō to player {character.id} using add_balance_and_save")
        else:
            # Fall back to old method
            try:
                if hasattr(self.currency_system, 'add_ryo'):
                    self.currency_system.add_ryo(character.id, loot_data['ryo'])
                    self.logger.info(f"Added {loot_data['ryo']} Ryō to player {character.id} using add_ryo")
                else:
                    self.currency_system.add_to_balance(character.id, loot_data['ryo'])
                    self.logger.info(f"Added {loot_data['ryo']} Ryō to player {character.id} using add_to_balance")
                
                # Save currency data manually if needed
                if hasattr(self.currency_system, 'save_currency_data'):
                    self.currency_system.save_currency_data()
            except Exception as e:
                self.logger.error(f"Error adding loot reward to player {character.id}: {e}")
        
        # Send the loot embed
        await interaction.followup.send(embed=loot_embed)
        
        # End the battle in the battle system if needed
        try:
            # Sort IDs to match how battle_id is created in the battle system
            player_ids = sorted([character.id, instructor_char.id])
            battle_id = f"{player_ids[0]}_{player_ids[1]}"
            self.logger.info(f"Ending battle {battle_id} with winner {character.id}")
            
            # Check which type of battle system we have and call appropriate method
            if self.is_battle_manager:
                # If it's a BattleManager object
                if hasattr(self.battle_system, 'end_battle_session'):
                    await self.battle_system.end_battle_session(
                        battle_id, 
                        winner_id=character.id,
                        reason="Academy Entrance Test Completed"
                    )
                    self.logger.info(f"Successfully ended battle {battle_id} using end_battle_session on BattleManager")
                else:
                    self.logger.warning(f"Could not end battle {battle_id} - BattleManager has no end_battle_session method")
            else:
                # If it's a BattleSystem object
                if hasattr(self.battle_system, 'end_battle'):
                    await self.battle_system.end_battle(
                        battle_id, 
                        winner_id=character.id,
                        reason="Academy Entrance Test Completed"
                    )
                    self.logger.info(f"Successfully ended battle {battle_id} using end_battle on BattleSystem")
                else:
                    self.logger.warning(f"Could not end battle {battle_id} - battle system {type(self.battle_system).__name__} has no end_battle method")
        except Exception as e:
            self.logger.error(f"Error ending battle: {e}", exc_info=True)
            # Continue anyway - this is just cleanup
        
        # Update character's rank to Academy Student if it isn't already
        if character.rank != "Academy Student":
            character.rank = "Academy Student"
            await self.character_system.save_character(character)
        
        return True 