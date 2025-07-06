import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any
import json
from pathlib import Path

from ...utils.embeds import create_error_embed


class ShopCommands(commands.Cog):
    """Commands for shopping and purchasing items."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.shop_data = self._load_shop_data()

    def _load_shop_data(self) -> Dict[str, Dict[str, Any]]:
        """Load shop data from JSON files."""
        shop_data = {}
        data_dir = Path("data/shops")
        
        try:
            # Load general items
            general_items_file = data_dir / "general_items.json"
            if general_items_file.exists():
                with open(general_items_file, 'r') as f:
                    shop_data.update(json.load(f))
            
            # Load equipment
            equipment_file = data_dir / "equipment_shop.json"
            if equipment_file.exists():
                with open(equipment_file, 'r') as f:
                    shop_data.update(json.load(f))
            
        except Exception as e:
            print(f"Error loading shop data: {e}")
        
        return shop_data

    @app_commands.command(name="shop", description="Browse available items in the shop")
    @app_commands.describe(category="Filter by item category (weapon, armor, consumable, tool)")
    async def shop(self, interaction: discord.Interaction, category: Optional[str] = None) -> None:
        """Browse items available in the shop."""
        try:
            if not self.shop_data:
                await interaction.response.send_message(
                    embed=create_error_embed("Shop data not available."),
                    ephemeral=True
                )
                return
            
            # Filter items by category if specified
            items_to_show = self.shop_data
            if category:
                items_to_show = {k: v for k, v in self.shop_data.items() 
                               if v.get('type', '').lower() == category.lower()}
                
                if not items_to_show:
                    await interaction.response.send_message(
                        embed=create_error_embed(f"No items found in category '{category}'."),
                        ephemeral=True
                    )
                    return
            
            # Create shop embed
            embed = discord.Embed(
                title="🏪 Ninja Shop",
                description="Browse and purchase items for your adventures!",
                color=discord.Color.gold()
            )
            
            # Group items by type for better organization
            item_groups = {}
            for item_id, item_data in items_to_show.items():
                item_type = item_data.get('type', 'misc').capitalize()
                if item_type not in item_groups:
                    item_groups[item_type] = []
                item_groups[item_type].append((item_id, item_data))
            
            # Add fields for each item type
            for item_type, items in item_groups.items():
                if len(items) > 5:  # Limit items per field to avoid embed limits
                    items = items[:5]
                    
                item_list = []
                for item_id, item_data in items:
                    price = item_data.get('price', 0)
                    rarity = item_data.get('rarity', 'Common')
                    item_list.append(f"**{item_data['name']}** - {price} ryo ({rarity})")
                
                embed.add_field(
                    name=f"{item_type}s",
                    value="\n".join(item_list) if item_list else "No items available",
                    inline=False
                )
            
            embed.add_field(
                name="How to Purchase",
                value="Use `/buy <item_name>` to purchase an item.\nUse `/item_info <item_name>` for details.",
                inline=False
            )
            
            # Show user's balance if available
            if hasattr(self.bot, 'services') and hasattr(self.bot.services, 'currency_system'):
                balance = self.bot.services.currency_system.get_player_balance(interaction.user.id)
                embed.set_footer(text=f"Your balance: {balance:,} ryo")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error browsing shop: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="item_info", description="Get detailed information about an item")
    async def item_info(self, interaction: discord.Interaction, item_name: str) -> None:
        """Get detailed information about a specific item."""
        try:
            # Find item by name (case-insensitive)
            item_data = None
            item_id = None
            
            for key, data in self.shop_data.items():
                if data.get('name', '').lower() == item_name.lower() or key.lower() == item_name.lower():
                    item_data = data
                    item_id = key
                    break
            
            if not item_data:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Item '{item_name}' not found in shop."),
                    ephemeral=True
                )
                return
            
            # Create detailed item embed
            embed = discord.Embed(
                title=f"📦 {item_data['name']}",
                description=item_data.get('description', 'No description available.'),
                color=self._get_rarity_color(item_data.get('rarity', 'Common'))
            )
            
            embed.add_field(
                name="Price",
                value=f"{item_data.get('price', 0)} ryo",
                inline=True
            )
            
            embed.add_field(
                name="Type",
                value=item_data.get('type', 'Unknown').capitalize(),
                inline=True
            )
            
            embed.add_field(
                name="Rarity",
                value=item_data.get('rarity', 'Common'),
                inline=True
            )
            
            # Add stats if available
            if 'stats' in item_data and item_data['stats']:
                stats_text = "\n".join([f"**{stat.capitalize()}**: +{value}" 
                                      for stat, value in item_data['stats'].items()])
                embed.add_field(
                    name="Stats",
                    value=stats_text,
                    inline=False
                )
            
            # Add effect if available
            if 'effect' in item_data and item_data['effect']:
                effect = item_data['effect']
                effect_text = f"**Type**: {effect.get('type', 'Unknown')}"
                if 'amount' in effect:
                    effect_text += f"\n**Amount**: {effect['amount']}"
                if 'duration' in effect:
                    effect_text += f"\n**Duration**: {effect['duration']} turns"
                    
                embed.add_field(
                    name="Effect",
                    value=effect_text,
                    inline=False
                )
            
            # Add usage info
            usable_in_battle = item_data.get('is_usable_in_battle', False)
            target_type = item_data.get('target_type', 'none')
            
            embed.add_field(
                name="Usage",
                value=f"**Battle Use**: {'Yes' if usable_in_battle else 'No'}\n**Target**: {target_type.capitalize()}",
                inline=True
            )
            
            embed.add_field(
                name="Purchase",
                value=f"Use `/buy {item_id}` to purchase this item.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error getting item info: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="buy", description="Purchase an item from the shop")
    @app_commands.describe(quantity="Number of items to purchase (default: 1)")
    async def buy(self, interaction: discord.Interaction, item_name: str, quantity: int = 1) -> None:
        """Purchase an item from the shop."""
        try:
            if quantity <= 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Quantity must be positive!"),
                    ephemeral=True
                )
                return
            
            # Find item by name (case-insensitive)
            item_data = None
            item_id = None
            
            for key, data in self.shop_data.items():
                if data.get('name', '').lower() == item_name.lower() or key.lower() == item_name.lower():
                    item_data = data
                    item_id = key
                    break
            
            if not item_data:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Item '{item_name}' not found in shop."),
                    ephemeral=True
                )
                return
            
            # Check if services are available
            if not hasattr(self.bot, 'services') or not hasattr(self.bot.services, 'currency_system'):
                await interaction.response.send_message(
                    embed=create_error_embed("Shop system not available."),
                    ephemeral=True
                )
                return
            
            # Calculate total cost
            unit_price = item_data.get('price', 0)
            total_cost = unit_price * quantity
            
            # Check player balance
            currency_system = self.bot.services.currency_system
            current_balance = currency_system.get_player_balance(interaction.user.id)
            
            if current_balance < total_cost:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Insufficient funds! You need {total_cost:,} ryo but only have {current_balance:,} ryo."),
                    ephemeral=True
                )
                return
            
            # Process purchase
            currency_system.add_balance_and_save(interaction.user.id, -total_cost)
            new_balance = currency_system.get_player_balance(interaction.user.id)
            
            # Add item to inventory (simplified - would need proper inventory system)
            # For now, just confirm purchase
            
            embed = discord.Embed(
                title="🛒 Purchase Successful!",
                description=f"You purchased **{quantity}x {item_data['name']}**",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Cost",
                value=f"{total_cost:,} ryo",
                inline=True
            )
            
            embed.add_field(
                name="Remaining Balance",
                value=f"{new_balance:,} ryo",
                inline=True
            )
            
            if quantity > 1:
                embed.add_field(
                    name="Unit Price",
                    value=f"{unit_price:,} ryo each",
                    inline=True
                )
            
            embed.add_field(
                name="Item Added",
                value=f"**{item_data['name']}** has been added to your inventory.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error purchasing item: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="shop_categories", description="View available item categories")
    async def shop_categories(self, interaction: discord.Interaction) -> None:
        """Display available item categories."""
        try:
            if not self.shop_data:
                await interaction.response.send_message(
                    embed=create_error_embed("Shop data not available."),
                    ephemeral=True
                )
                return
            
            # Get all unique categories
            categories = {}
            for item_data in self.shop_data.values():
                item_type = item_data.get('type', 'misc').capitalize()
                if item_type not in categories:
                    categories[item_type] = 0
                categories[item_type] += 1
            
            embed = discord.Embed(
                title="🏪 Shop Categories",
                description="Browse items by category:",
                color=discord.Color.blue()
            )
            
            for category, count in categories.items():
                embed.add_field(
                    name=f"{category}s",
                    value=f"{count} items available",
                    inline=True
                )
            
            embed.add_field(
                name="How to Browse",
                value="Use `/shop <category>` to view items in a specific category.\nExample: `/shop weapon`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Error displaying categories: {str(e)}"),
                ephemeral=True
            )

    def _get_rarity_color(self, rarity: str) -> discord.Color:
        """Get color based on item rarity."""
        rarity_colors = {
            'Common': discord.Color.light_grey(),
            'Uncommon': discord.Color.green(),
            'Rare': discord.Color.blue(),
            'Epic': discord.Color.purple(),
            'Legendary': discord.Color.gold()
        }
        return rarity_colors.get(rarity, discord.Color.light_grey())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShopCommands(bot)) 