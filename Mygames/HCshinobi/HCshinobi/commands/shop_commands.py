"""Shop commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import app_commands, ui # Added ui for potential future use
import logging
import json
import os
from typing import Dict, Optional, List, Any, Union, Tuple
import random
from datetime import datetime, timedelta
from enum import Enum

from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.utils.embed_utils import get_rarity_color
from HCshinobi.core.character import Character # Import Character for type hinting
from HCshinobi.core.constants import ( # Import rank constants
    SHOP_ITEMS_FILE, 
    RANK_ORDER, 
    MAX_JUTSU_RANK_BY_CHAR_RANK,
    DATA_DIR, SHOPS_SUBDIR, # Import directory constants
    DEFAULT_SELL_MODIFIER,
    JUTSU_SHOP_STATE_FILE,
    EQUIPMENT_SHOP_FILE,
)
from HCshinobi.utils.file_io import load_json, save_json
# Assume JutsuShopSystem is injected or accessible via bot.services
from HCshinobi.core.jutsu_shop_system import JutsuShopSystem 
from HCshinobi.core.equipment_shop_system import EquipmentShopSystem # Import new system

# Define choices for the shop type parameter
class ShopType(Enum):
    ITEMS = "items"
    JUTSU = "jutsu"
    EQUIPMENT = "equipment"
    ALL = "all"

# Remove old path definition
# SHOP_DATA_PATH = os.path.join('data', 'shop', 'items.json')

class ShopCommands(commands.Cog):
    def __init__(self, bot: commands.Bot): # Removed explicit systems from signature
        """Initialize shop commands."""
        self.bot = bot
        # --- Get systems from other Cogs/Services --- #
        currency_cog = bot.get_cog('Currency') # Use the Cog name specified in currency_system.py
        if not currency_cog:
            raise RuntimeError("CurrencyCog not loaded, cannot initialize ShopCommands")
        self.currency_system: CurrencySystem = currency_cog.get_system()
        
        # Assuming other systems are still on bot.services or similar
        # If they become Cogs, get them like CurrencyCog
        self.character_system = getattr(bot.services, 'character_system', None)
        self.jutsu_shop_system = getattr(bot.services, 'jutsu_shop_system', None)
        self.equipment_shop_system = getattr(bot.services, 'equipment_shop_system', None)
        
        if not self.character_system or not self.jutsu_shop_system or not self.equipment_shop_system:
             # Log error or raise exception
             logging.error("ShopCommands initialized without one or more required systems (Character, JutsuShop, EquipmentShop).")
        # --- End Get systems --- #
        
        self.logger = logging.getLogger(__name__)
        self.item_shop_data = self._load_item_shop_data() # Keep this for consumables/misc

    def _load_item_shop_data(self) -> dict:
        """Loads shop items from the JSON file specified by constant."""
        # Construct the full path
        file_path = os.path.join(DATA_DIR, SHOPS_SUBDIR, SHOP_ITEMS_FILE)
        try:
            return load_json(file_path)
        except FileNotFoundError:
            self.logger.error(f"Shop items file not found at {file_path}")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading shop items from {file_path}: {e}")
            return {}

    @app_commands.command(name="shop", description="View items available for purchase in different shops")
    @app_commands.describe(shop_type="Which shop inventory to view initially?")
    @app_commands.choices(shop_type=[
        app_commands.Choice(name="All Shops", value=ShopType.ALL.value),
        app_commands.Choice(name="Consumables/Misc Items", value=ShopType.ITEMS.value),
        app_commands.Choice(name="Jutsu Scrolls", value=ShopType.JUTSU.value),
        app_commands.Choice(name="Ninja Equipment", value=ShopType.EQUIPMENT.value),
    ])
    async def shop(self, interaction: discord.Interaction, shop_type: Optional[str] = ShopType.ALL.value):
        """Display the interactive shop view."""
        # Defer first
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for shop view: {e}", exc_info=True)
            return # Cannot followup if defer failed

        try:
            # --- Get All Inventory Data --- # 
            # Consumables/Misc
            item_inventory = self.item_shop_data or {}
            # Jutsu
            jutsu_inventory_details = []
            if self.jutsu_shop_system:
                 await self.jutsu_shop_system.refresh_shop_if_needed() # Ensure it's fresh
                 jutsu_inventory_details = self.jutsu_shop_system.get_current_shop_inventory_details()
            else:
                 self.logger.warning("JutsuShopSystem not available for interactive shop.")
            # Equipment
            equipment_inventory = {}
            if self.equipment_shop_system:
                 equipment_inventory = self.equipment_shop_system.get_shop_inventory() or {}
            else:
                 self.logger.warning("EquipmentShopSystem not available for interactive shop.")
            # --- End Get Data --- #

            if not item_inventory and not jutsu_inventory_details and not equipment_inventory:
                 await interaction.followup.send("❌ All shops are currently empty or unavailable.", ephemeral=True)
                 return

            # --- Create and Send Interactive View --- #
            # Pass all necessary data/systems to the view
            view = ShopView(
                shop_commands=self, # Pass the cog instance
                item_inventory=item_inventory,
                jutsu_inventory=jutsu_inventory_details,
                equipment_inventory=equipment_inventory,
                initial_filter=shop_type # Start with the selected filter
            )
            
            # The view's refresh_page method will handle the initial followup
            await view.refresh_page(interaction)
            # --- End Send View --- #
            
        except Exception as e:
            self.logger.error(f"Error showing shop: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred displaying the shop. Please try again later.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending shop error followup: {http_err_fatal}", exc_info=True)

    # REMOVED /buy command - Interactive view handles buying consumables/misc
    # @app_commands.command(name="buy", description="Purchase an item from the shop by its ID")
    # @app_commands.describe(item_id="The ID of the item to purchase (see /shop)")
    # async def buy(self, interaction: discord.Interaction, item_id: str):
    #    ... (old implementation) ...

    # REMOVED /sell command - Selling logic needs rework for unified inventory
    # @app_commands.command(name="sell", description="Sell an item from your inventory")
    # @app_commands.describe(item_id="The ID of the item in your inventory to sell")
    # async def sell(self, interaction: discord.Interaction, item_id: str):
    #     ... (old implementation) ...

    # --- Refactored Internal Buy Logic --- #
    async def _buy_consumable_item(self, character_id: str, item_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """Internal logic to buy a consumable/misc item."""
        character = await self.character_system.get_character(character_id)
        if not character: return False, "Character not found.", None
        
        item_id_lower = item_id.lower()
        item_data = self.item_shop_data.get(item_id_lower)
        if not item_data: return False, f"Item ID '{item_id}' not found in shop.", None
            
        item_name = item_data.get('name', 'Unnamed Item')
        item_price = item_data.get('price', 0)
        
        if not self.currency_system.has_sufficient_funds(character_id, item_price):
            balance = self.currency_system.get_player_balance(character_id)
            return False, f"Insufficient Ryō. Cost: {item_price:,}, Your Balance: {balance:,}.\n", None

        # Add to inventory
        if not hasattr(character, 'inventory') or character.inventory is None:
            character.inventory = []
        character.inventory.append(item_id_lower)
        
        # Update the balance and save it immediately if possible
        if hasattr(self.currency_system, 'add_balance_and_save'):
            self.currency_system.add_balance_and_save(character_id, -item_price)
        else:
            # Fallback to old method + manual save
            self.currency_system.add_balance(character_id, -item_price)
            if hasattr(self.currency_system, 'save_currency_data'):
                self.currency_system.save_currency_data()
            
        save_success = await self.character_system.save_character(character)
        
        if not save_success:
            # Roll back the currency change if character save fails
            if hasattr(self.currency_system, 'add_balance_and_save'):
                self.currency_system.add_balance_and_save(character_id, item_price)
            else:
                self.currency_system.add_balance(character_id, item_price)
                if hasattr(self.currency_system, 'save_currency_data'):
                    self.currency_system.save_currency_data()
                
            try: character.inventory.remove(item_id_lower) # Rollback inventory
            except ValueError: pass
            return False, "Transaction failed! Could not save character changes.\n", None
            
        return True, f"Successfully bought **{item_name}** for {item_price:,} Ryō.\n", item_data

    async def _buy_jutsu_scroll(self, character_id: str, jutsu_name: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Process the purchase of a jutsu scroll.

        Returns:
            Tuple[bool, str, Optional[Dict]]: (Success status, Message, Item data if successful)
        """
        character = await self.character_system.get_character(character_id)
        if not character:
            return False, "You need a character first (use `/create`).\n", None

        # Initialize the jutsu shop if needed
        await self.jutsu_shop_system.refresh_shop_if_needed()
        
        current_shop_names = self.jutsu_shop_system.current_inventory_names
        if jutsu_name not in current_shop_names: 
             return False, f"'{jutsu_name}' is not currently available.\n", None

        jutsu_data = self.jutsu_shop_system.master_jutsu_data.get(jutsu_name)
        if not jutsu_data: 
             self.logger.error(f"Jutsu '{jutsu_name}' in shop but not master map!")
             return False, "Internal error retrieving Jutsu details.\n", None

        if jutsu_name in character.jutsu: 
             return False, f"You already know '{jutsu_name}'.\n", None

        # Rank Check (Improved error handling)
        player_rank = character.rank if hasattr(character, 'rank') and character.rank else "Academy Student"
        jutsu_rank = jutsu_data.get('rank', 'S') 
        max_purchasable_rank = MAX_JUTSU_RANK_BY_CHAR_RANK.get(player_rank, "E")
        
        try:
            # Enhanced error handling for rank checks
            if player_rank == "Academy Student":
                # Academy Students can't purchase jutsu
                return False, (f"⚠️ Rank Requirement Not Met: Academy Students cannot purchase jutsu.\n"
                              f"You need to graduate to Genin rank first."), None
                              
            # Make sure we have valid values for comparison
            if player_rank not in RANK_ORDER:
                self.logger.error(f"Unknown player rank '{player_rank}' not in RANK_ORDER")
                player_rank_index = 0  # Lowest rank as fallback
            else:
                player_rank_index = RANK_ORDER.index(player_rank)
                
            if jutsu_rank not in RANK_ORDER:
                self.logger.error(f"Unknown jutsu rank '{jutsu_rank}' not in RANK_ORDER")
                jutsu_rank_index = len(RANK_ORDER) - 1  # Highest rank as fallback
            else:
                jutsu_rank_index = RANK_ORDER.index(jutsu_rank)
                
            if max_purchasable_rank not in RANK_ORDER:
                self.logger.error(f"Unknown max purchasable rank '{max_purchasable_rank}' not in RANK_ORDER")
                max_purchasable_index = 0  # Lowest rank as fallback
            else:
                max_purchasable_index = RANK_ORDER.index(max_purchasable_rank)
            
            if jutsu_rank_index > max_purchasable_index:
                # Improved error message that clearly explains the rank requirement
                return False, (f"⚠️ Rank Requirement Not Met: Your rank ({player_rank}) is too low to learn this "
                               f"{jutsu_rank}-rank Jutsu.\nYou need to be at least {max_purchasable_rank} rank "
                               f"to purchase {jutsu_rank}-rank jutsu.\n"), None
        except Exception as e:
            self.logger.error(f"Error in rank check: Player='{player_rank}', Jutsu='{jutsu_rank}', Error: {e}")
            return False, f"You don't meet the requirements to purchase this jutsu (rank: {jutsu_rank}).\n", None

        cost = jutsu_data.get('shop_cost')
        if not isinstance(cost, int) or cost <= 0: 
             return False, f"'{jutsu_name}' cannot be purchased (invalid cost).\n", None
             
        if not self.currency_system.has_sufficient_funds(character_id, cost):
             balance = self.currency_system.get_player_balance(character_id)
             return False, f"Insufficient Ryō. Cost: {cost:,}, Your Balance: {balance:,}.\n", None

        learned_new_jutsu, progression_messages = await self.character_system.add_jutsu(character_id, jutsu_name)
        if not learned_new_jutsu:
            # Already knew it - should have been caught earlier, but handle defensively
            return False, f"You already know **{jutsu_name}**.\n", None # Indicate not purchased

        # Update and save the balance
        if hasattr(self.currency_system, 'add_balance_and_save'):
            self.currency_system.add_balance_and_save(character_id, -cost)
        else:
            # Fallback to old method + manual save
            self.currency_system.add_balance(character_id, -cost)
            if hasattr(self.currency_system, 'save_currency_data'):
                self.currency_system.save_currency_data()
        # Note: The character is already saved in add_jutsu
        
        success_message = f"Successfully learned **{jutsu_name}** for {cost:,} Ryō!\n"
        if progression_messages:
             success_message += "\n**Progression Updates:**\n" + "\n".join(progression_messages)
             
        return True, success_message, jutsu_data
    # --- End Refactored Logic --- #

    # --- Jutsu Shop Commands --- #
    jutsu_group = app_commands.Group(name="jutsu_shop", description="Commands related to the Jutsu scroll shop")

    # REMOVED /jutsu_shop shop command - use /shop with filter instead
    # @jutsu_group.command(name="shop", description="View the jutsu available in the Genin shop.")
    # async def view_jutsu_shop(self, interaction: discord.Interaction):
    #    ... (old implementation) ...

    # REMOVED /jutsu_shop buy command - Interactive view handles this
    # @jutsu_group.command(name="buy", description="Buy a Jutsu scroll from the shop")
    # @app_commands.describe(jutsu_name="The exact name of the Jutsu scroll to buy")
    # async def buy_jutsu_scroll_command(self, interaction: discord.Interaction, jutsu_name: str): 
    #     ... (old implementation) ...

    # --- Equipment Shop Commands --- #
    equipment_group = app_commands.Group(name="equipment", description="Commands related to the Ninja Equipment shop")

    # REMOVED /equipment shop command - use /shop with filter instead
    # @equipment_group.command(name="shop", description="Browse equipment available for purchase")
    # async def equipment_shop(self, interaction: discord.Interaction):
    #     ... (old implementation) ...

    # REMOVED /equipment buy command - Interactive view handles this
    # @equipment_group.command(name="buy", description="Buy a piece of equipment from the shop")
    # @app_commands.describe(equipment_id="The exact ID of the equipment to buy")
    # async def buy_equipment_item_command(self, interaction: discord.Interaction, equipment_id: str): 
    #    ... (old implementation) ...

    # REMOVED /equipment sell command - Selling logic needs rework for unified inventory
    # @equipment_group.command(name="sell", description="Sell a piece of equipment from your inventory")
    # @app_commands.describe(equipment_id="The exact ID of the equipment in your inventory to sell")
    # async def sell_equipment_item_command(self, interaction: discord.Interaction, equipment_id: str): 
    #     ... (old implementation) ...

    # --- Posting Logic --- #
    async def post_or_update_equipment_shop(self):
        """Posts the initial equipment shop embed or updates the existing one."""
        channel_id = self.equipment_shop_system.equipment_shop_channel_id
        message_id = self.equipment_shop_system.equipment_shop_message_id

        if not channel_id:
            self.logger.warning("Equipment shop channel ID not configured. Cannot post/update shop.")
            return

        channel = self.bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            self.logger.error(f"Could not find equipment shop channel with ID: {channel_id}")
            return

        # --- Create Embed --- # 
        # (Adapted from /equipment shop command, could be refactored into a helper)
        try:
            inventory = self.equipment_shop_system.get_shop_inventory()
            embed = discord.Embed(
                title="🛠️ Ninja Equipment Shop - Available Gear 🛠️",
                description="High-quality tools and armor. Use `/equipment buy <ID>` to purchase.",
                color=discord.Color.orange()
            )
            if not inventory:
                 embed.description = "The Equipment Shop is currently empty or restocking."
            else:
                sorted_items = sorted(inventory.items(), key=lambda item: item[1].get('price', 0))
                shop_text = ""
                for item_id, item_data in sorted_items:
                    name = item_data.get('name', item_id)
                    price = item_data.get('price', 'N/A')
                    rarity = item_data.get('rarity', 'Common')
                    desc = item_data.get('description', 'No description.')
                    stats = item_data.get('stats', {})
                    slot = item_data.get('slot', 'Misc')
                    
                    item_line = f"• **{name}** (`{item_id}`) - {price:,} Ryō\n"
                    item_line += f"  *{rarity.title()}* | Slot: {slot}\n"
                    if stats:
                        stats_text = ", ".join([f"{k.replace('_', ' ').title()}: +{v}" for k, v in stats.items()])
                        item_line += f"  Stats: {stats_text}\n"
                    # item_line += f"  *{desc}*\n"
                    shop_text += item_line + "\n"
                embed.description += "\n\n" + shop_text.strip()
            
            embed.set_footer(text="Prices and availability subject to change.")
            embed.timestamp = discord.utils.utcnow()
        except Exception as e:
             self.logger.error(f"Failed to create equipment shop embed: {e}", exc_info=True)
             return # Don't proceed if embed creation fails
        # --- End Create Embed --- #

        # --- Post or Edit Logic --- #
        message = None
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(content=None, embed=embed) # Edit existing
                self.logger.info(f"Updated equipment shop message in channel {channel_id}")
            except discord.NotFound:
                self.logger.warning(f"Previous equipment shop message {message_id} not found. Posting a new one.")
                message = None # Force sending new message
            except discord.Forbidden:
                self.logger.error(f"Missing permissions to edit message {message_id} in channel {channel_id}.")
                message = None # Try sending new message?
            except Exception as e:
                self.logger.error(f"Failed to edit equipment shop message {message_id}: {e}", exc_info=True)
                message = None # Try sending new message
        
        if not message:
            try:
                new_message = await channel.send(embed=embed)
                self.equipment_shop_system.set_shop_message_id(new_message.id) # Save new ID
                self.logger.info(f"Posted new equipment shop message to channel {channel_id} (ID: {new_message.id})")
            except discord.Forbidden:
                 self.logger.error(f"Missing permissions to send messages in channel {channel_id}.")
            except Exception as e:
                 self.logger.error(f"Failed to send new equipment shop message to {channel_id}: {e}", exc_info=True)
        # --- End Post or Edit --- #

# Add the ShopView classes after the ShopCommands class but before any command method
class ShopItemButton(ui.Button):
    """Button for purchasing a specific item from the shop"""
    def __init__(self, item_id: str, item_name: str, price: int, item_type: str, shop_view: 'ShopView', disabled: bool = False, requirements_met: bool = True):
        # Set appropriate label and style based on requirements
        if requirements_met:
            label = f"Buy {item_name} ({price:,} Ryō)"
            style = discord.ButtonStyle.primary
        else:
            label = f"⚠️ {item_name} (Rank too low)"
            style = discord.ButtonStyle.secondary
            
        super().__init__(
            label=label,
            style=style,
            custom_id=f"shop_buy_{item_type}_{item_id}", # Include type in custom_id for safety
            disabled=disabled
        )
        self.item_id = item_id # This could be item ID or Jutsu name
        self.item_name = item_name
        self.price = price
        self.item_type = item_type # Store the type ('items', 'jutsu', 'equipment')
        self.shop_view = shop_view
        self.requirements_met = requirements_met
        
    async def callback(self, interaction: discord.Interaction):
        # Defer response to prevent timeout
        await interaction.response.defer(ephemeral=True)
        
        # Get shop commands instance from view
        shop_commands = self.shop_view.shop_commands
        character_id = str(interaction.user.id)
        
        success = False
        message = "An unknown error occurred."
        item_data = None # For embed later
        
        try:
            # --- Call appropriate buy logic based on type --- #
            if self.item_type == ShopType.ITEMS.value:
                # Call logic similar to the old /buy command
                success, message, item_data = await shop_commands._buy_consumable_item(character_id, self.item_id)
            elif self.item_type == ShopType.JUTSU.value:
                # Call logic similar to the old /buy_jutsu command
                success, message, item_data = await shop_commands._buy_jutsu_scroll(character_id, self.item_name) # Jutsu uses name
            elif self.item_type == ShopType.EQUIPMENT.value:
                # Call the equipment shop system's buy method
                success, message, item_data = await shop_commands.equipment_shop_system.buy_equipment(character_id, self.item_id)
            else:
                message = "Unknown item type in shop button."
            # --- End Buy Logic --- #

            if success:
                current_balance = shop_commands.currency_system.get_player_balance(character_id)
                embed = discord.Embed(
                    title=f"✅ {self.item_type.title()} Purchased!",
                    description=message,
                    color=discord.Color.green()
                )
                # Add details based on type
                if self.item_type == ShopType.ITEMS.value and item_data:
                     embed.set_footer(text=f"Item ID: {self.item_id} added to inventory. Balance: {current_balance:,} Ryō.")
                elif self.item_type == ShopType.JUTSU.value and item_data:
                     embed.set_footer(text=f"Learned {self.item_name}. Balance: {current_balance:,} Ryō.")
                elif self.item_type == ShopType.EQUIPMENT.value and item_data:
                     embed.set_footer(text=f"Equipment ID: {self.item_id} added. Balance: {current_balance:,} Ryō.")
                else:
                     embed.set_footer(text=f"Your new balance: {current_balance:,} Ryō.")
                     
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Refresh the shop view with potentially updated inventory/balance?
                # Re-fetching all data might be slow, maybe just re-build page?
                # Let's skip auto-refresh for now to avoid complexity.
                # await self.shop_view.refresh_page(interaction)
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
             shop_commands.logger.error(f"Error processing shop buy button (Type: {self.item_type}, ID: {self.item_id}): {e}", exc_info=True)
             await interaction.followup.send("❌ An internal error occurred during purchase.", ephemeral=True)

class ShopFilterSelect(ui.Select):
    """Dropdown for filtering shop items by type"""
    def __init__(self, shop_view: 'ShopView', types: List[str]):
        options = [
            discord.SelectOption(label="All Items", value=ShopType.ALL.value, description="View all items in the shop"),
        ]
        
        # Add specific types (Items, Jutsu, Equipment)
        type_map = {
            ShopType.ITEMS.value: "Consumables/Misc Items",
            ShopType.JUTSU.value: "Jutsu Scrolls",
            ShopType.EQUIPMENT.value: "Ninja Equipment",
        }
        
        for type_value in types:
            if type_value == ShopType.ALL.value: continue # Skip adding 'all' again
            label = type_map.get(type_value, type_value.title()) # Get friendly label
            options.append(
                discord.SelectOption(
                    label=label, 
                    value=type_value,
                    description=f"View only {label}"
                )
            )
            
        super().__init__(
            placeholder="Filter items by type...",
            options=options,
            custom_id="shop_filter"
        )
        self.shop_view = shop_view
        
    async def callback(self, interaction: discord.Interaction):
        # Update the filter and refresh the view
        self.shop_view.current_filter = self.values[0]
        self.shop_view.current_page = 0  # Reset to first page when changing filters
        
        await self.shop_view.refresh_page(interaction)

class ShopView(ui.View):
    """Interactive view for the shop system with filtering"""
    def __init__(self, 
                 shop_commands: 'ShopCommands', 
                 item_inventory: Dict[str, Dict[str, Any]], 
                 jutsu_inventory: List[Dict[str, Any]], 
                 equipment_inventory: Dict[str, Dict[str, Any]], 
                 initial_filter: str = ShopType.ALL.value,
                 timeout: float = 180):
        super().__init__(timeout=timeout)
        self.shop_commands = shop_commands
        # Store individual inventories
        self.item_inventory = item_inventory
        self.jutsu_inventory = jutsu_inventory
        self.equipment_inventory = equipment_inventory
        
        self.items_per_page = 5
        self.current_page = 0
        self.current_filter = initial_filter # Use initial_filter
        self.message = None
        
        # Player data - will be set during refresh_page
        self.player_id = None
        self.player_rank = "Academy Student"
        self.character = None
        
        # Add filter dropdown with combined types
        filter_options = [ShopType.ALL.value, ShopType.ITEMS.value, ShopType.JUTSU.value, ShopType.EQUIPMENT.value]
        self.add_item(ShopFilterSelect(self, filter_options))
        
        # Build initial page
        # Note: Initial build will be without player data - actual filtering happens in refresh_page
        self.build_page() 
        
    async def check_player_eligibility(self, interaction: discord.Interaction):
        """Fetch player data to check eligibility for items"""
        self.player_id = str(interaction.user.id)
        try:
            self.character = await self.shop_commands.character_system.get_character(self.player_id)
            if self.character and hasattr(self.character, 'rank') and self.character.rank:
                self.player_rank = self.character.rank
            else:
                self.player_rank = "Academy Student" # Default rank
        except Exception as e:
            self.shop_commands.logger.error(f"Error fetching character for eligibility check: {e}")
            self.player_rank = "Academy Student" # Default on error
    
    def can_player_use_jutsu(self, jutsu_data: Dict[str, Any]) -> bool:
        """Check if the player meets the rank requirement for a jutsu"""
        if not self.character or not hasattr(self, 'player_rank'):
            return False
        
        # Academy Students can't use jutsu
        if self.player_rank == "Academy Student":
            return False
            
        jutsu_rank = jutsu_data.get('rank', 'S')
        max_purchasable_rank = MAX_JUTSU_RANK_BY_CHAR_RANK.get(self.player_rank, "E")
        
        try:
            # Make sure we have valid values for comparison
            if self.player_rank not in RANK_ORDER:
                self.shop_commands.logger.error(f"Unknown player rank '{self.player_rank}' not in RANK_ORDER")
                return False
                
            if jutsu_rank not in RANK_ORDER:
                self.shop_commands.logger.error(f"Unknown jutsu rank '{jutsu_rank}' not in RANK_ORDER")
                return False
                
            if max_purchasable_rank not in RANK_ORDER:
                self.shop_commands.logger.error(f"Unknown max purchasable rank '{max_purchasable_rank}' not in RANK_ORDER")
                return False
        
            jutsu_rank_index = RANK_ORDER.index(jutsu_rank)
            max_purchasable_index = RANK_ORDER.index(max_purchasable_rank)
            return jutsu_rank_index <= max_purchasable_index
        except Exception as e:
            # On error, be restrictive for safety
            self.shop_commands.logger.error(f"Rank check error: Player={self.player_rank}, Jutsu={jutsu_rank}, Error: {e}")
            return False
        
    def build_page(self):
        """Build the current page of shop items with buttons"""
        # Clear existing item buttons (not navigation or filter)
        buttons_to_remove = [item for item in self.children if isinstance(item, ShopItemButton)]
        for button in buttons_to_remove:
            self.remove_item(button)
            
        # --- Get All Items Combined and Filtered --- #
        all_items_combined = []
        
        # Add Items (Consumables/Misc)
        if self.current_filter == ShopType.ALL.value or self.current_filter == ShopType.ITEMS.value:
            for item_id, item_data in self.item_inventory.items():
                item_data['id'] = item_id
                item_data['shop_item_type'] = ShopType.ITEMS.value # Add type marker
                all_items_combined.append(item_data)
                
        # Add Jutsu Scrolls
        if self.current_filter == ShopType.ALL.value or self.current_filter == ShopType.JUTSU.value:
            for jutsu_data in self.jutsu_inventory:
                # Need price from master list or shop system?
                # Assuming price is in the details from get_current_shop_inventory_details
                # We need a unique ID - use the name for now
                jutsu_data['id'] = jutsu_data.get('name')
                jutsu_data['shop_item_type'] = ShopType.JUTSU.value # Add type marker
                
                # Check if player meets rank requirements
                meets_requirements = self.can_player_use_jutsu(jutsu_data)
                jutsu_data['meets_requirements'] = meets_requirements
                
                all_items_combined.append(jutsu_data)
                 
        # Add Equipment
        if self.current_filter == ShopType.ALL.value or self.current_filter == ShopType.EQUIPMENT.value:
            for equip_id, equip_data in self.equipment_inventory.items():
                equip_data['id'] = equip_id
                equip_data['shop_item_type'] = ShopType.EQUIPMENT.value # Add type marker
                all_items_combined.append(equip_data)
        # --- End Combining Items --- #
                
        # Sort items (e.g., by name or price)
        # Sorting is complex with different types; let's sort by name for now
        all_items_combined.sort(key=lambda x: x.get('name', ''))
        
        # Calculate pagination
        total_items = len(all_items_combined)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        
        # Ensure current page is valid
        self.current_page = max(0, min(self.current_page, total_pages - 1))
        
        # Get items for current page
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)
        page_items = all_items_combined[start_idx:end_idx]
        
        # Add buttons for each item
        for item in page_items:
            # Need to adapt button creation based on item type
            item_type = item.get('shop_item_type')
            item_id_or_name = item.get('id') # Jutsu uses name as ID here
            item_name = item.get('name', 'Unknown Item')
            price = item.get('price') or item.get('shop_cost') or 0 # Handle different price keys
            
            if item_id_or_name:
                # For jutsu scrolls, check rank requirements and modify button accordingly
                if item_type == ShopType.JUTSU.value:
                    meets_requirements = item.get('meets_requirements', True)
                    # Still add button but disable it if requirements not met
                    button = ShopItemButton(
                        item_id=item_id_or_name,
                        item_name=item_name,
                        price=price,
                        item_type=item_type,
                        shop_view=self,
                        disabled=not meets_requirements,
                        requirements_met=meets_requirements
                    )
                else:
                    button = ShopItemButton(
                        item_id=item_id_or_name,
                        item_name=item_name,
                        price=price,
                        item_type=item_type,
                        shop_view=self
                    )
                self.add_item(button)
            
        # Update navigation buttons
        self.update_navigation(total_pages)
    
    def update_navigation(self, total_pages: int):
        """Update navigation buttons based on current page and total pages"""
        # Remove existing navigation buttons
        nav_buttons = [item for item in self.children 
                      if isinstance(item, ui.Button) and item.custom_id in ["prev_page", "next_page"]]
        for button in nav_buttons:
            self.remove_item(button)
            
        # Add navigation buttons if needed
        if total_pages > 1:
            # Previous page button
            prev_button = ui.Button(
                label="◀️ Previous",
                style=discord.ButtonStyle.secondary,
                custom_id="prev_page",
                disabled=self.current_page == 0
            )
            prev_button.callback = self.prev_page_callback
            self.add_item(prev_button)
            
            # Next page button
            next_button = ui.Button(
                label="Next ▶️",
                style=discord.ButtonStyle.secondary,
                custom_id="next_page",
                disabled=self.current_page == total_pages - 1
            )
            next_button.callback = self.next_page_callback
            self.add_item(next_button)
    
    async def prev_page_callback(self, interaction: discord.Interaction):
        """Handle previous page button press"""
        self.current_page = max(0, self.current_page - 1)
        await self.refresh_page(interaction)
        
    async def next_page_callback(self, interaction: discord.Interaction):
        """Handle next page button press"""
        self.current_page += 1
        await self.refresh_page(interaction)
    
    async def refresh_page(self, interaction: discord.Interaction):
        """Refresh the shop view with updated content"""
        # Fetch player data for eligibility checks
        await self.check_player_eligibility(interaction)
        
        # Rebuild the page with eligibility data
        self.build_page()
        
        # Create the updated embed based on current filtration
        embed = self.create_embed()
        
        # Update the message
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.edit_original_response(embed=embed, view=self)
    
    def create_embed(self) -> discord.Embed:
        """Create the shop embed based on current filter and page"""
        filter_name = "All Items" if self.current_filter == ShopType.ALL.value else f"{self.current_filter.title()}s"
        
        embed = discord.Embed(
            title="⚔️ Ninja Shop",
            description=f"Showing {filter_name}. Click an item button to purchase it!",
            color=discord.Color.dark_grey()
        )
        
        # Add player rank information if available
        if hasattr(self, 'player_rank') and self.player_rank:
            embed.description += f"\nYour current rank: **{self.player_rank}**"
        
        if self.current_filter == ShopType.JUTSU.value or self.current_filter == ShopType.ALL.value:
            max_rank = MAX_JUTSU_RANK_BY_CHAR_RANK.get(self.player_rank, "E")
            embed.description += f"\n*Note: Your rank allows you to learn jutsu up to rank **{max_rank}**.*"
        
        # Get filtered items for this view
        # We need to handle this more dynamically now with multiple item types
        filtered_items = []
        
        # For each button in the view, we need to gather details for the embed
        for item in self.children:
            if isinstance(item, ShopItemButton):
                # Need to access item details from their original inventories
                if item.item_type == ShopType.ITEMS.value:
                    item_data = self.item_inventory.get(item.item_id, {})
                    item_data['id'] = item.item_id
                    item_data['price'] = item.price
                    item_data['shop_item_type'] = item.item_type
                    item_data['meets_requirements'] = True  # Items always meet requirements
                    filtered_items.append(item_data)
                    
                elif item.item_type == ShopType.JUTSU.value:
                    # Find the matching jutsu data
                    for jutsu in self.jutsu_inventory:
                        if jutsu.get('name') == item.item_name:
                            # Include requirements information
                            jutsu['meets_requirements'] = item.requirements_met
                            filtered_items.append(jutsu)
                            break
                            
                elif item.item_type == ShopType.EQUIPMENT.value:
                    # Find the matching equipment data
                    equip_data = self.equipment_inventory.get(item.item_id, {})
                    equip_data['id'] = item.item_id
                    equip_data['price'] = item.price
                    equip_data['shop_item_type'] = item.item_type
                    filtered_items.append(equip_data)
        
        # Add each item to the embed with appropriate formatting
        for item in filtered_items:
            item_type = item.get('shop_item_type')
            name = item.get('name', 'Unknown Item')
            price = item.get('price') or item.get('shop_cost', 0)
            field_value = ""
            
            if item_type == ShopType.JUTSU.value:
                rank = item.get('rank', 'E')
                description = item.get('description', 'No description available')
                meets_requirements = item.get('meets_requirements', True)
                
                # Format jutsu information
                field_name = f"{name} - {price:,} Ryō - Rank {rank}"
                if not meets_requirements:
                    field_name = f"⚠️ {field_name} (Rank Requirement Not Met)"
                    field_value = f"*{description}*\n⚠️ **Your rank is too low to learn this jutsu.**\n"
                else:
                    field_value = f"*{description}*\n"
                    
                # Add element if available
                if 'element' in item:
                    field_value += f"Element: {item['element']}\n"
                    
            elif item_type == ShopType.ITEMS.value:
                # Format item information
                description = item.get('description', 'No description available')
                field_name = f"{name} - {price:,} Ryō"
                field_value = f"*{description}*\n"
                
            elif item_type == ShopType.EQUIPMENT.value:
                # Format equipment information
                rarity = item.get('rarity', 'common')
                description = item.get('description', 'No description available')
                field_name = f"{name} - {price:,} Ryō"
                field_value = f"*{rarity.title()}* - {description}\n"
                
                # Add stats if available
                if "stats" in item and isinstance(item["stats"], dict):
                    stats_text = ", ".join(f"{k.replace('_', ' ').title()}: +{v}" for k, v in item["stats"].items())
                    field_value += f"*Stats:* {stats_text}\n"
                    
                # Add required rank if available
                if "required_rank" in item:
                    field_value += f"*Rank Required:* {item['required_rank']}\n"
            
            # Add the field for this item
            embed.add_field(name=field_name, value=field_value, inline=False)
            
        # Add pagination footer if needed
        # We'd need to calculate total pages some other way, but let's skip for brevity
        
        return embed
    
    async def on_timeout(self):
        """Handle view timeout"""
        if self.message:
            try:
                await self.message.edit(content="Shop session has timed out. Use `/shop` to start a new session.", view=None)
            except (discord.NotFound, discord.HTTPException):
                pass

async def setup(bot: commands.Bot):
    """Setup function to add the ShopCommands cog to the bot."""
    # Dependencies (like CurrencyCog, CharacterSystem, etc.) should be loaded *before* this Cog
    await bot.add_cog(ShopCommands(bot)) 