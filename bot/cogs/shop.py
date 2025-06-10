"""Shop commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
from discord import app_commands, ui
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
from HCshinobi.core.character import Character
from HCshinobi.core.constants import (
    SHOP_ITEMS_FILE, 
    RANK_ORDER, 
    MAX_JUTSU_RANK_BY_CHAR_RANK,
    DATA_DIR, SHOPS_SUBDIR,
    DEFAULT_SELL_MODIFIER,
    JUTSU_SHOP_STATE_FILE,
    EQUIPMENT_SHOP_FILE,
)
from HCshinobi.utils.file_io import load_json, save_json
from HCshinobi.core.jutsu_shop_system import JutsuShopSystem
from HCshinobi.core.equipment_shop_system import EquipmentShopSystem

# Define choices for the shop type parameter
class ShopType(Enum):
    ITEMS = "items"
    JUTSU = "jutsu"
    EQUIPMENT = "equipment"
    ALL = "all"

class ShopCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        """Initialize shop commands."""
        self.bot = bot
        # Get specific systems from bot services
        self.jutsu_shop_system = bot.services.jutsu_shop_system
        self.equipment_shop_system = bot.services.equipment_shop_system
        self.character_system = bot.services.character_system
        self.currency_system = bot.services.currency_system
        
        if not all([self.jutsu_shop_system, self.equipment_shop_system, self.character_system, self.currency_system]):
            logging.error("ShopCommands initialized without one or more required systems")
            
        self.logger = logging.getLogger(__name__)
        self.item_shop_data = self._load_item_shop_data()

    def _load_item_shop_data(self) -> dict:
        """Loads shop items from the JSON file specified by constant."""
        file_path = os.path.join(DATA_DIR, SHOPS_SUBDIR, SHOP_ITEMS_FILE)
        try:
            return load_json(file_path)
        except FileNotFoundError:
            self.logger.error(f"Shop items file not found at {file_path}")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading shop items from {file_path}: {e}")
            return {}

    @app_commands.command(name="view", description="View items available for purchase in different shops")
    @app_commands.describe(shop_type="Which shop inventory to view initially?")
    @app_commands.choices(shop_type=[
        app_commands.Choice(name="All Shops", value=ShopType.ALL.value),
        app_commands.Choice(name="Consumables/Misc Items", value=ShopType.ITEMS.value),
        app_commands.Choice(name="Jutsu Scrolls", value=ShopType.JUTSU.value),
        app_commands.Choice(name="Ninja Equipment", value=ShopType.EQUIPMENT.value),
    ])
    async def view_shop(self, interaction: discord.Interaction, shop_type: Optional[str] = ShopType.ALL.value):
        """Display the interactive shop view."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for shop view: {e}", exc_info=True)
            return

        try:
            # Get all inventory data
            item_inventory = self.item_shop_data or {}
            jutsu_inventory_details = []
            if self.jutsu_shop_system:
                await self.jutsu_shop_system.refresh_shop_if_needed()
                jutsu_inventory_details = self.jutsu_shop_system.get_current_shop_inventory_details()
            else:
                self.logger.warning("JutsuShopSystem not available for interactive shop.")
                
            equipment_inventory = {}
            if self.equipment_shop_system:
                equipment_inventory = self.equipment_shop_system.get_shop_inventory() or {}
            else:
                self.logger.warning("EquipmentShopSystem not available for interactive shop.")

            if not item_inventory and not jutsu_inventory_details and not equipment_inventory:
                await interaction.followup.send("❌ All shops are currently empty or unavailable.", ephemeral=True)
                return

            # Create and send interactive view
            view = ShopView(
                shop_commands=self,
                item_inventory=item_inventory,
                jutsu_inventory=jutsu_inventory_details,
                equipment_inventory=equipment_inventory,
                initial_filter=shop_type
            )
            
            await view.refresh_page(interaction)
            
        except Exception as e:
            self.logger.error(f"Error showing shop: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred displaying the shop. Please try again later.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending shop error followup: {http_err_fatal}", exc_info=True)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    async def buy_item(self, interaction: discord.Interaction, item_id: str):
        """Buy an item from the shop."""
        # DEPRECATED - Use the interactive /view command instead
        await interaction.response.send_message("Please use the `/view` command to browse and buy items interactively.", ephemeral=True)

    @app_commands.command(name="sell", description="Sell an item from your inventory")
    @app_commands.describe(item_id="The ID of the item to sell (e.g., 'kunai', 'basic_healing_salve')")
    async def sell_item(self, interaction: discord.Interaction, item_id: str):
        """Sell an item from your inventory to the shop."""
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            self.logger.error(f"Error deferring interaction for sell: {e}", exc_info=True)
            return
            
        user_id = str(interaction.user.id)
        character = await self.character_system.get_character(user_id)
        if not character:
            await interaction.followup.send("❌ You need a character to sell items.", ephemeral=True)
            return
            
        if not hasattr(character, 'inventory') or not character.inventory:
             await interaction.followup.send("❌ Your inventory is empty.", ephemeral=True)
             return
             
        item_id_lower = item_id.lower()
        
        # Check if item is in inventory
        if item_id_lower not in character.inventory:
            await interaction.followup.send(f"❌ You do not have '{item_id}' in your inventory.", ephemeral=True)
            return
            
        # Get item definition to find its base price
        # Need to check both item_shop_data and equipment_shop_data
        item_def = None
        if item_id_lower in self.item_shop_data:
             item_def = self.item_shop_data[item_id_lower]
        elif self.equipment_shop_system:
             equipment_inventory = self.equipment_shop_system.get_shop_inventory() or {}
             if item_id_lower in equipment_inventory:
                  item_def = equipment_inventory[item_id_lower]
        
        if not item_def or not isinstance(item_def.get('price'), int) or item_def['price'] <= 0:
            self.logger.warning(f"Could not find valid price for item '{item_id_lower}' during sell attempt by {user_id}.")
            # Decide if unsellable or default value? For now, make unsellable.
            await interaction.followup.send(f"❌ Item '{item_id}' cannot be sold (price not found or invalid).", ephemeral=True)
            return
            
        item_name = item_def.get('name', item_id)
        base_price = item_def['price']
        sell_price = int(base_price * DEFAULT_SELL_MODIFIER)
        
        if sell_price <= 0:
             await interaction.followup.send(f"❌ Item '{item_name}' has no sell value.", ephemeral=True)
             return
             
        # Perform the transaction
        try:
            # 1. Remove item from inventory
            # Ensure inventory is a list and remove the item
            if not isinstance(character.inventory, list):
                 self.logger.error(f"Sell Error: Character {user_id} inventory is not a list.")
                 await interaction.followup.send(f"❌ Internal error: Inventory format incorrect.", ephemeral=True)
                 return
            try:
                character.inventory.remove(item_id_lower)
            except ValueError:
                 # This check should ideally be redundant if has_item check passed,
                 # but good for robustness.
                 self.logger.warning(f"Sell Error: Item {item_id_lower} not found in inventory for {user_id} despite initial check.")
                 await interaction.followup.send(f"❌ Error: Could not find '{item_name}' in your inventory.", ephemeral=True)
                 return
            
            # 2. Add currency using the consistent method
            currency_added = self.currency_system.add_balance_and_save(user_id, sell_price)
            if not currency_added:
                 # Failed to add currency, roll back inventory
                 self.logger.error(f"Sell Error: Failed to add currency {sell_price} for {user_id}. Rolling back inventory.")
                 character.inventory.append(item_id_lower) # Add item back
                 await interaction.followup.send("❌ Transaction failed! Could not update balance.", ephemeral=True)
                 return
            
            # 3. Save character state
            save_success = await self.character_system.save_character(character)
            
            if not save_success:
                # Attempt rollback
                self.logger.error(f"Failed to save character {user_id} after selling {item_id_lower}. Attempting rollback.")
                # Rollback inventory
                character.inventory.append(item_id_lower) # Add item back
                # Rollback currency
                currency_rolled_back = self.currency_system.add_balance_and_save(user_id, -sell_price)
                if not currency_rolled_back:
                     self.logger.error(f"CRITICAL: Failed to rollback currency for {user_id} after failed sell save.")
                     # Consider how to handle this critical state - manual intervention likely needed
                     
                await interaction.followup.send("❌ Transaction failed! Could not save character changes after selling.", ephemeral=True)
                return
                
            # Success message
            balance = self.currency_system.get_player_balance(user_id) # Get updated balance
            embed = discord.Embed(
                title="💰 Item Sold",
                description=f"Successfully sold **{item_name}** for **{sell_price:,}** Ryō!",
                color=discord.Color.green()
            )
            embed.add_field(name="Item", value=item_name, inline=True)
            embed.add_field(name="Sell Price", value=f"{sell_price:,} Ryō", inline=True)
            embed.add_field(name="New Balance", value=f"{balance:,} Ryō", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except ValueError:
            # This shouldn't happen if initial check passed, but handle defensively
            self.logger.warning(f"Item '{item_id_lower}' disappeared from inventory during sell for {user_id}.")
            await interaction.followup.send(f"❌ Error: Could not find '{item_name}' in your inventory to sell.", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error during sell transaction for {user_id}, item {item_id_lower}: {e}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred during the sell transaction.", ephemeral=True)

    # --- Autocomplete for sell --- #
    @sell_item.autocomplete('item_id')
    async def sell_item_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocompletes item IDs based on the user's inventory."""
        user_id = str(interaction.user.id)
        character = await self.character_system.get_character(user_id)
        
        # Ensure character and inventory exist and are not empty
        if not character or not hasattr(character, 'inventory') or not character.inventory:
            return []
            
        # Character.inventory is expected to be a List[str] based on dataclass definition
        user_items = character.inventory 
        
        choices = []
        # Combine item definitions for display name lookup
        all_item_defs = {} 
        # Add items from the item shop data (assuming it's loaded in __init__)
        all_item_defs.update(self.item_shop_data)
        # Add equipment items
        if self.equipment_shop_system:
            equipment_inventory = self.equipment_shop_system.get_shop_inventory() or {}
            all_item_defs.update(equipment_inventory)
            
        # Suggest items the user actually has
        # Iterate directly over the inventory list
        for item_id in user_items: 
            item_def = all_item_defs.get(item_id.lower()) # Use lower for consistency
            item_name = item_def.get('name', item_id) if item_def else item_id # Fallback to ID if no def found
            
            # Match against name or ID, case-insensitively
            if current.lower() in item_id.lower() or current.lower() in item_name.lower():
                # Ensure the choice name is reasonably distinct, maybe add type?
                # Example: "Kunai (Weapon)" or just use the name
                display_name = item_name 
                if item_def and item_def.get('type'):
                    display_name += f" ({item_def['type'].title()})" 
                
                choices.append(app_commands.Choice(name=display_name, value=item_id))
            
            if len(choices) >= 25: # Discord limit
                break
                
        return choices
    # --- End Autocomplete for sell --- #

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
        # Ensure inventory is a list (it should be based on dataclass)
        if not hasattr(character, 'inventory') or character.inventory is None:
            # This case might indicate a problem elsewhere if inventory is None
            character.inventory = [] 
        elif not isinstance(character.inventory, list):
             # If it's somehow not a list, log error and try to convert/reset
             self.logger.warning(f"Character {character_id} inventory was not a list ({type(character.inventory)}). Resetting.")
             character.inventory = []
             
        # Append the item ID to the list
        character.inventory.append(item_id_lower)
        
        # Update balance
        # Assume add_balance_and_save handles saving currency data
        self.currency_system.add_balance(character_id, -item_price)
        self.currency_system.save_currency_data()
            
        save_success = await self.character_system.save_character(character)
        
        if not save_success:
            # Roll back the currency change if character save fails
            self.currency_system.add_balance(character_id, item_price)
            self.currency_system.save_currency_data()
            # Need to rollback the inventory change
            try:
                character.inventory.remove(item_id_lower)
            except ValueError:
                # Item wasn't found, which is strange if we just added it
                self.logger.warning(f"Failed to find item {item_id_lower} in inventory during rollback for {character_id}.")
            except Exception as e:
                 self.logger.error(f"Error removing item during rollback for {character_id}: {e}")
            return False, "Transaction failed! Could not save character changes.\n", None
            
        return True, f"Successfully bought **{item_name}** for {item_price:,} Ryō.\n", item_data

    async def _buy_jutsu_scroll(self, character_id: str, jutsu_name: str) -> Tuple[bool, str, Optional[Dict]]:
        """Process the purchase of a jutsu scroll."""
        character = await self.character_system.get_character(character_id)
        if not character:
            return False, "You need a character first (use `/create`).\n", None

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

        # Rank Check
        player_rank = character.rank if hasattr(character, 'rank') and character.rank else "Academy Student"
        jutsu_rank = jutsu_data.get('rank', 'S') 
        max_purchasable_rank = MAX_JUTSU_RANK_BY_CHAR_RANK.get(player_rank, "E")
        
        try:
            if player_rank == "Academy Student":
                return False, (f"⚠️ Rank Requirement Not Met: Academy Students cannot purchase jutsu.\n"
                              f"You need to graduate to Genin rank first."), None
                              
            if player_rank not in RANK_ORDER:
                self.logger.error(f"Unknown player rank '{player_rank}' not in RANK_ORDER")
                player_rank_index = 0
            else:
                player_rank_index = RANK_ORDER.index(player_rank)
                
            if jutsu_rank not in RANK_ORDER:
                self.logger.error(f"Unknown jutsu rank '{jutsu_rank}' not in RANK_ORDER")
                jutsu_rank_index = len(RANK_ORDER) - 1
            else:
                jutsu_rank_index = RANK_ORDER.index(jutsu_rank)
                
            if max_purchasable_rank not in RANK_ORDER:
                self.logger.error(f"Unknown max purchasable rank '{max_purchasable_rank}' not in RANK_ORDER")
                max_purchasable_index = 0
            else:
                max_purchasable_index = RANK_ORDER.index(max_purchasable_rank)
            
            if jutsu_rank_index > max_purchasable_index:
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
            return False, f"You already know **{jutsu_name}**.\n", None

        # Update balance
        self.currency_system.add_balance(character_id, -cost)
        self.currency_system.save_currency_data()
        
        success_message = f"Successfully learned **{jutsu_name}** for {cost:,} Ryō!\n"
        if progression_messages:
            success_message += "\n**Progression Updates:**\n" + "\n".join(progression_messages)
             
        return True, success_message, jutsu_data

class ShopItemButton(ui.Button):
    def __init__(self, item_id: str, item_name: str, price: int, item_type: str, shop_view: 'ShopView', disabled: bool = False, requirements_met: bool = True):
        super().__init__(
            label=f"{item_name} - {price:,} Ryō",
            style=discord.ButtonStyle.green if requirements_met else discord.ButtonStyle.grey,
            disabled=disabled,
            custom_id=f"shop_item_{item_id}"
        )
        self.item_id = item_id
        self.item_name = item_name
        self.price = price
        self.item_type = item_type
        self.shop_view = shop_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Check if player has a character
        character = await self.shop_view.shop_commands.character_system.get_character(str(interaction.user.id))
        if not character:
            await interaction.followup.send("You need to create a character first using `/create`.", ephemeral=True)
            return

        # Handle purchase based on item type
        if self.item_type == ShopType.ITEMS.value:
            success, message, _ = await self.shop_view.shop_commands._buy_consumable_item(str(interaction.user.id), self.item_id)
        elif self.item_type == ShopType.JUTSU.value:
            success, message, _ = await self.shop_view.shop_commands._buy_jutsu_scroll(str(interaction.user.id), self.item_id)
        else:
            success, message = False, "This item type is not yet supported for direct purchase."

        await interaction.followup.send(message, ephemeral=True)
        if success:
            await self.shop_view.refresh_page(interaction)

class ShopFilterSelect(ui.Select):
    def __init__(self, shop_view: 'ShopView', types: List[str]):
        options = [
            discord.SelectOption(label="All Shops", value=ShopType.ALL.value, description="Show all available items"),
            discord.SelectOption(label="Consumables/Misc", value=ShopType.ITEMS.value, description="Show consumable items"),
            discord.SelectOption(label="Jutsu Scrolls", value=ShopType.JUTSU.value, description="Show available jutsu"),
            discord.SelectOption(label="Equipment", value=ShopType.EQUIPMENT.value, description="Show ninja equipment")
        ]
        super().__init__(
            placeholder="Filter by shop type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="shop_filter"
        )
        self.shop_view = shop_view

    async def callback(self, interaction: discord.Interaction):
        self.shop_view.current_filter = self.values[0]
        await self.shop_view.refresh_page(interaction)

class ShopView(ui.View):
    def __init__(self, 
                 shop_commands: 'ShopCommands', 
                 item_inventory: Dict[str, Dict[str, Any]], 
                 jutsu_inventory: List[Dict[str, Any]], 
                 equipment_inventory: Dict[str, Dict[str, Any]], 
                 initial_filter: str = ShopType.ALL.value,
                 timeout: float = 180):
        super().__init__(timeout=timeout)
        self.shop_commands = shop_commands
        self.item_inventory = item_inventory
        self.jutsu_inventory = jutsu_inventory
        self.equipment_inventory = equipment_inventory
        self.current_filter = initial_filter
        self.current_page = 0
        self.items_per_page = 5

        # Add filter select
        self.add_item(ShopFilterSelect(self, [t.value for t in ShopType]))

    async def check_player_eligibility(self, interaction: discord.Interaction):
        """Check if the player has a character and return it."""
        character = await self.shop_commands.character_system.get_character(str(interaction.user.id))
        if not character:
            await interaction.followup.send("You need to create a character first using `/create`.", ephemeral=True)
            return None
        return character

    def can_player_use_jutsu(self, jutsu_data: Dict[str, Any]) -> bool:
        """Check if the player meets the requirements for a jutsu."""
        # This is a placeholder - actual implementation would check character stats
        return True

    def build_page(self):
        """Build the components for the current page."""
        self.clear_items()

        # Add filter select menu
        self.add_item(ShopFilterSelect(self, [t.value for t in ShopType]))

        # Get filtered items
        filtered_items = []
        if self.current_filter == ShopType.ALL.value or self.current_filter == ShopType.ITEMS.value:
            for item_id, item_data in self.item_inventory.items():
                filtered_items.append({
                    'id': item_id,
                    'name': item_data.get('name', 'Unnamed Item'),
                    'price': item_data.get('price', 0),
                    'type': ShopType.ITEMS.value
                })

        if self.current_filter == ShopType.ALL.value or self.current_filter == ShopType.JUTSU.value:
            for jutsu in self.jutsu_inventory:
                filtered_items.append({
                    'id': jutsu.get('name', 'Unknown Jutsu'),
                    'name': jutsu.get('name', 'Unknown Jutsu'),
                    'price': jutsu.get('shop_cost', 0),
                    'type': ShopType.JUTSU.value,
                    'requirements_met': self.can_player_use_jutsu(jutsu)
                })

        if self.current_filter == ShopType.ALL.value or self.current_filter == ShopType.EQUIPMENT.value:
            for equip_id, equip_data in self.equipment_inventory.items():
                filtered_items.append({
                    'id': equip_id,
                    'name': equip_data.get('name', 'Unknown Equipment'),
                    'price': equip_data.get('price', 0),
                    'type': ShopType.EQUIPMENT.value
                })

        # Sort by price
        filtered_items.sort(key=lambda x: x['price'])

        # Paginate
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = filtered_items[start_idx:end_idx]

        # Add item buttons
        for item in page_items:
            self.add_item(ShopItemButton(
                item_id=item['id'],
                item_name=item['name'],
                price=item['price'],
                item_type=item['type'],
                shop_view=self,
                requirements_met=item.get('requirements_met', True)
            ))

        # Add navigation if needed
        total_pages = (len(filtered_items) + self.items_per_page - 1) // self.items_per_page
        if total_pages > 1:
            self.update_navigation(total_pages)

        return page_items, total_pages

    def update_navigation(self, total_pages: int):
        """Add navigation buttons for pagination."""
        prev_button = ui.Button(
            label="Previous",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page == 0,
            custom_id="shop_prev"
        )
        prev_button.callback = self.prev_page_callback
        self.add_item(prev_button)

        next_button = ui.Button(
            label="Next",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page >= total_pages - 1,
            custom_id="shop_next"
        )
        next_button.callback = self.next_page_callback
        self.add_item(next_button)

    async def prev_page_callback(self, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        await self.refresh_page(interaction)

    async def next_page_callback(self, interaction: discord.Interaction):
        self.current_page += 1
        await self.refresh_page(interaction)

    async def refresh_page(self, interaction: discord.Interaction):
        """Refresh the current page and update the message."""
        page_items, total_pages = self.build_page()
        embed = self.create_embed(page_items, total_pages)
        
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    def create_embed(self, page_items: List[Dict], total_pages: int) -> discord.Embed:
        """Create an embed showing the current page of items."""
        embed = discord.Embed(
            title="🏪 HCShinobi Shop",
            description="Browse and purchase items from various shops.",
            color=discord.Color.blue()
        )

        if not page_items:
            embed.add_field(
                name="No Items Available",
                value="There are no items available in this shop category.",
                inline=False
            )
        else:
            for item in page_items:
                embed.add_field(
                    name=item['name'],
                    value=f"Price: {item['price']:,} Ryō\nType: {item['type'].title()}",
                    inline=True
                )

        if total_pages > 1:
            embed.set_footer(text=f"Page {self.current_page + 1}/{total_pages}")

        return embed

    async def on_timeout(self):
        """Handle view timeout."""
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    cog = ShopCommands(bot)
    await bot.add_cog(cog)
    
    # Register commands under the shop group
    shop_group = bot.tree.get_command("shop")
    if shop_group:
        shop_group.add_command(cog.view_shop)
        shop_group.add_command(cog.buy_item)
        shop_group.add_command(cog.sell_item) 