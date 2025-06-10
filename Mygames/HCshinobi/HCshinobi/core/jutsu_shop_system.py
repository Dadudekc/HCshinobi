"""
System for managing the rotating Jutsu Shop inventory.
"""
import os
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Set

import aiofiles
import discord # Needed for posting

# Assuming bot instance is passed for channel access
# from HCshinobi.bot.bot import HCBot 

from .constants import DATA_DIR, JUTSU_SHOP_REFRESH_HOURS, JUTSU_SHOP_SIZE, JUTSU_SHOP_MAX_RANK, SHOPS_SUBDIR, JUTSU_SHOP_STATE_FILE
from ..utils.file_io import load_json, save_json

logger = logging.getLogger(__name__)

class JutsuShopSystem:
    """Manages the rotating Jutsu shop inventory and posts updates."""

    def __init__(self, data_dir: str, master_jutsu_data: Dict[str, Dict]):
        """
        Initializes the JutsuShopSystem.

        Args:
            data_dir: The base data directory.
            master_jutsu_data: Dictionary of all loaded jutsu data, keyed by name.
        """
        self.base_data_dir = data_dir
        # Construct specific path for shop files
        self.shop_data_dir = os.path.join(data_dir, SHOPS_SUBDIR)
        self.state_file_path = os.path.join(self.shop_data_dir, JUTSU_SHOP_STATE_FILE)
        self.master_jutsu_data = master_jutsu_data
        self.current_inventory_names: List[str] = [] # List of Jutsu names currently in shop
        self.previous_inventory_names: List[str] = [] # NEW: Track previous inventory
        self.last_refresh: Optional[datetime] = None
        self.shop_channel_id: Optional[int] = None # Loaded from state
        self.shop_message_id: Optional[int] = None # Loaded from state

        os.makedirs(self.shop_data_dir, exist_ok=True)

        logger.info("JutsuShopSystem initialized.")
        # Loading state is handled by an explicit async call (load_shop_state)

    async def ready_hook(self):
        """Hook called when bot is ready. Loads shop state."""
        await self.load_shop_state()
        logger.info(f"JutsuShopSystem ready. State loaded.")

    async def load_shop_state(self):
        """Loads the shop state (inventory, refresh time, message ID) from file."""
        try:
            # Corrected: Call load_json synchronously
            state_data = load_json(self.state_file_path)
            if state_data is None:
                logger.info(f"Jutsu shop state file not found or invalid: {self.state_file_path}. Initializing fresh state.")
                self.current_inventory_names = []
                self.last_refresh = None
                # Don't reset channel/message ID here if they might be set via config/post
                return
            elif not isinstance(state_data, dict):
                logger.warning(f"Invalid data format in {self.state_file_path}. Resetting state.")
                state_data = {} # Use empty dict to proceed with .get calls

            self.current_inventory_names = state_data.get('current_inventory_names', [])
            timestamp_str = state_data.get('last_refresh_time')
            self.last_refresh = datetime.fromisoformat(timestamp_str) if timestamp_str else None
            self.shop_channel_id = state_data.get('shop_channel_id')
            self.shop_message_id = state_data.get('shop_message_id')
            logger.info(f"Loaded Jutsu shop state: Channel={self.shop_channel_id}, Message={self.shop_message_id}, LastRefresh={self.last_refresh}")
        except Exception as e:
            logger.error(f"Error loading Jutsu shop state from {self.state_file_path}: {e}")
            # Reset to default state on error
            self.current_inventory_names = []
            self.last_refresh = None
            self.shop_channel_id = None
            self.shop_message_id = None

    async def save_shop_state(self):
        """Saves the current shop state to file."""
        state_data = {
            'current_inventory_names': self.current_inventory_names,
            'last_refresh_time': self.last_refresh.isoformat() if self.last_refresh else None,
            'shop_channel_id': self.shop_channel_id,
            'shop_message_id': self.shop_message_id
        }
        try:
            # Use self.state_file_path constructed in __init__
            await save_json(self.state_file_path, state_data)
            logger.debug(f"Saved Jutsu shop state to {self.state_file_path}")
        except Exception as e:
            logger.error(f"Error saving Jutsu shop state to {self.state_file_path}: {e}")

    def _needs_refresh(self) -> bool:
        """Checks if the shop inventory needs refreshing based on time."""
        if not self.last_refresh:
            return True
        now = datetime.now(timezone.utc) # Use timezone-aware datetime
        # Ensure last_refresh is timezone-aware for comparison
        if self.last_refresh.tzinfo is None:
             # Attempt to localize if naive, assuming UTC if created by older code
             try:
                 # This might fail if last_refresh is already timezone aware from newer code
                 self.last_refresh = self.last_refresh.replace(tzinfo=timezone.utc)
             except ValueError:
                  pass # Already timezone aware
             
        return now >= (self.last_refresh + timedelta(hours=JUTSU_SHOP_REFRESH_HOURS))

    async def refresh_shop_if_needed(self) -> bool:
        """Refreshes the shop inventory if enough time has passed. Returns True if refreshed."""
        needs_refresh = self._needs_refresh()
        logger.debug(f"Checking if Jutsu shop needs refresh... Needs refresh: {needs_refresh}")
        
        if not needs_refresh:
            return False

        logger.info("Refreshing Jutsu shop inventory...")

        rank_order = ['E', 'D', 'C', 'B', 'A', 'S']
        try:
            max_rank_index = rank_order.index(JUTSU_SHOP_MAX_RANK)
            allowed_ranks = rank_order[:max_rank_index + 1]
        except ValueError:
             logger.error(f"Invalid JUTSU_SHOP_MAX_RANK '{JUTSU_SHOP_MAX_RANK}' in constants. Defaulting to C.")
             allowed_ranks = ['E', 'D', 'C']
             
        # Filter master data for eligible jutsu
        eligible_jutsu = [
            jutsu_data for jutsu_data in self.master_jutsu_data.values() 
            if jutsu_data.get('rank') in allowed_ranks and jutsu_data.get('shop_cost', 0) > 0
        ]
        logger.info(f"Found {len(eligible_jutsu)} eligible jutsu for shop (Rank <= {JUTSU_SHOP_MAX_RANK}, Cost > 0).")

        if not eligible_jutsu:
            logger.error("No eligible Jutsu found in master data for shop refresh! Check ranks and costs.")
            # --- Store current (empty) inventory as previous before clearing --- #
            self.previous_inventory_names = self.current_inventory_names[:]
            self.current_inventory_names = [] 
            self.last_refresh = datetime.now(timezone.utc)
            await self.save_shop_state()
            return True 
            
        # --- Weighted Selection Logic (with repeat penalty) --- #
        rank_weights = { 'E': 100, 'D': 75, 'C': 50, 'B': 25, 'A': 10, 'S': 1 }
        repeat_decay_factor = 0.5 # How much to reduce weight if it was in the last shop
        
        previous_set = set(self.previous_inventory_names)
        jutsu_population = []
        weights = []
        
        for jutsu in eligible_jutsu:
            name = jutsu.get('name')
            rank = jutsu.get('rank', 'E') 
            weight = rank_weights.get(rank, 1)

            # Apply decay if item was in the previous shop
            if name in previous_set:
                weight *= repeat_decay_factor
                logger.debug(f"Applying repeat penalty to '{name}'. New weight: {weight}")
            
            # Ensure weight is at least a very small positive number to avoid issues with random.choices
            weight = max(0.01, weight)
            
            jutsu_population.append(jutsu)
            weights.append(weight)
            
        selected_jutsu = []
        selected_names = set() 
        shop_size = min(JUTSU_SHOP_SIZE, len(eligible_jutsu))
        
        if not weights or not jutsu_population: 
             logger.error("Failed to assign weights or no eligible jutsu population. Falling back to random sample.")
             if len(eligible_jutsu) <= shop_size:
                 selected_jutsu = eligible_jutsu
             else:
                 selected_jutsu = random.sample(eligible_jutsu, shop_size)
        else:
            # Use weighted random choice (without replacement logic)
            while len(selected_jutsu) < shop_size and jutsu_population:
                # Need to re-calculate choices if we remove items
                chosen_jutsu_list = random.choices(jutsu_population, weights=weights, k=1)
                if not chosen_jutsu_list:
                    logger.error("random.choices returned empty list unexpectedly.")
                    break # Should not happen if population/weights exist
                chosen_jutsu = chosen_jutsu_list[0]
                
                # Avoid duplicates in the *same* refresh cycle
                if chosen_jutsu['name'] not in selected_names:
                    selected_jutsu.append(chosen_jutsu)
                    selected_names.add(chosen_jutsu['name'])
                    
                    # Find and remove the chosen item and its weight for next iteration
                    try:
                         idx = jutsu_population.index(chosen_jutsu)
                         jutsu_population.pop(idx)
                         weights.pop(idx)
                    except ValueError:
                         logger.error(f"Failed to find chosen jutsu '{chosen_jutsu['name']}' in population list for removal.")
                         # Continue loop, but this indicates a potential issue
                else:
                     # If we picked a duplicate, try to remove it from population to avoid infinite loop
                     # This handles cases where few high-weight items dominate the pool
                     try:
                         idx = jutsu_population.index(chosen_jutsu)
                         jutsu_population.pop(idx)
                         weights.pop(idx)
                     except ValueError:
                          # Item already removed, maybe by duplicate selection logic, continue
                          pass 
                     # Ensure loop terminates if population becomes empty
                     if not jutsu_population:
                         break
                          
            logger.info(f"Selected {len(selected_jutsu)} jutsu via weighted sampling (with repeat penalty)." )
        # --- End Weighted Selection Logic --- #

        # --- Update Previous Inventory BEFORE assigning new current --- #
        self.previous_inventory_names = self.current_inventory_names[:]
        self.current_inventory_names = [j['name'] for j in selected_jutsu]
        self.last_refresh = datetime.now(timezone.utc)
        await self.save_shop_state() # Save includes previous_inventory_names now
        logger.info(f"Jutsu shop refreshed successfully with {len(self.current_inventory_names)} items: {self.current_inventory_names}")
        return True

    def get_current_shop_inventory_details(self) -> List[Dict]:
        """Returns the full details for jutsu currently in the shop."""
        details = []
        for name in self.current_inventory_names:
            # Use the stored master data dictionary
            jutsu_data = self.master_jutsu_data.get(name)
            if jutsu_data:
                details.append(jutsu_data)
            else:
                 logger.warning(f"Jutsu '{name}' from current inventory not found in master_jutsu_data during detail fetch.")
        return details

    async def post_shop_inventory(self, bot, channel_id: int):
        """Formats and posts the current shop inventory to the specified channel."""
        if not channel_id:
            logger.error("Jutsu Shop Channel ID not configured. Cannot post inventory.")
            return

        channel = bot.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            logger.error(f"Could not find Jutsu Shop channel with ID {channel_id} or it's not a text channel.")
            return
            
        inventory_details = self.get_current_shop_inventory_details()
        if not inventory_details:
            logger.warning("Attempted to post Jutsu shop inventory, but it was empty.")
            # --- Send Empty Shop Message --- #
            try:
                await channel.send("公告 (Announcement): The Jutsu Scroll Shop is currently restocking. Check back later!")
                logger.info(f"Sent 'shop empty' message to channel {channel_id}.")
            except Exception as e:
                 logger.error(f"Failed to send 'shop empty' message: {e}")
            # --- End Empty Shop Message --- #
            return

        embed = discord.Embed(
            title="📜 Daily Jutsu Shop Rotation",
            description=f"Today's available Jutsu scrolls! Use `/buy jutsu <Jutsu Name>` to purchase.",
            color=discord.Color.blue(),
            timestamp=self.last_refresh or datetime.now(timezone.utc) # Use refresh time if available
        )

        # Group by rank for better display
        inventory_details.sort(key=lambda j: (['E', 'D', 'C', 'B', 'A', 'S'].index(j.get('rank', 'E')), j.get('name', '')))

        current_rank = None
        field_value = ""
        for jutsu in inventory_details:
            rank = jutsu.get('rank', '??')
            name = jutsu.get('name', 'Unknown Jutsu')
            cost = jutsu.get('shop_cost', 'N/A')
            desc = jutsu.get('description', 'No description available.')[:100] # Truncate description
            
            jutsu_line = f"**{name}** ({rank}) - {cost:,} Ryō\n*\"{desc}...\"*\n"
            
            # Check if adding this line exceeds field limits
            if len(field_value) + len(jutsu_line) > 1024:
                embed.add_field(name=f"{current_rank or 'Jutsu'} Rank", value=field_value, inline=False)
                field_value = jutsu_line
                current_rank = rank
            # Check if starting a new rank group
            elif rank != current_rank and field_value:
                 embed.add_field(name=f"{current_rank or 'Jutsu'} Rank", value=field_value, inline=False)
                 field_value = jutsu_line
                 current_rank = rank
            else:
                field_value += jutsu_line
                if not current_rank:
                     current_rank = rank

        # Add the last field
        if field_value:
            embed.add_field(name=f"{current_rank or 'Jutsu'} Rank", value=field_value, inline=False)

        embed.set_footer(text=f"Shop refreshed at {self.last_refresh.strftime('%Y-%m-%d %H:%M UTC') if self.last_refresh else 'N/A'}. New rotation in ~{JUTSU_SHOP_REFRESH_HOURS} hours.")

        try:
            # Clear previous messages from the bot in the channel? Optional.
            # async for message in channel.history(limit=10):
            #     if message.author == bot.user:
            #         await message.delete()
            
            await channel.send(embed=embed)
            logger.info(f"Successfully posted Jutsu shop inventory to channel {channel_id}.")
        except discord.Forbidden:
            logger.error(f"Missing permissions to post Jutsu shop inventory to channel {channel_id}.")
        except discord.HTTPException as e:
            logger.error(f"HTTP error posting Jutsu shop inventory: {e}")
        except Exception as e:
            logger.error(f"Unexpected error posting Jutsu shop inventory: {e}", exc_info=True) 