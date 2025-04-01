"""Core constants for the HCshinobi project."""

import os
from enum import Enum

# --- Data File Paths ---
# Assume 'data/' directory is at the project root level relative to run.py
_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

# Create clans directory if it doesn't exist
os.makedirs(os.path.join(_DATA_DIR, "clans"), exist_ok=True)

CLAN_FILE = os.path.join(_DATA_DIR, "clans", "clans.json")
NPC_FILE = os.path.join(_DATA_DIR, "npcs.json")
TOKEN_FILE = os.path.join(_DATA_DIR, "tokens.json")
MODIFIERS_FILE = os.path.join(_DATA_DIR, "modifiers.json")
ASSIGNMENT_HISTORY_FILE = os.path.join(_DATA_DIR, "assignment_history.json") # Added based on assignment_engine

# --- NPC Management ---
MAX_NPC_COUNT = int(os.getenv('MAX_NPC_COUNT', '100'))
DEFAULT_NPC_STATUS = os.getenv('DEFAULT_NPC_STATUS', 'Active')

# --- Token System ---
TOKEN_START_AMOUNT = int(os.getenv('TOKEN_START_AMOUNT', '5'))
TOKEN_FILE = os.path.join(_DATA_DIR, "tokens.json") # Stores player balances and unlocks
TOKEN_LOG_FILE = os.path.join(_DATA_DIR, "token_transactions.json") # Log of all transactions

# Token costs for various actions
TOKEN_COSTS = {
    "clan_boost": int(os.getenv('TOKEN_COST_CLAN_BOOST', '1')),
    "reroll_clan": int(os.getenv('TOKEN_COST_REROLL_CLAN', '10')),
    "unlock_feature_weapon_crafting": int(os.getenv('TOKEN_COST_WEAPON_CRAFTING', '15')),
    "unlock_feature_elemental_affinity": int(os.getenv('TOKEN_COST_ELEMENTAL_AFFINITY', '20')),
    "unlock_feature_style_switching": int(os.getenv('TOKEN_COST_STYLE_SWITCHING', '10')),
    "unlock_feature_summon_contract": int(os.getenv('TOKEN_COST_SUMMON_CONTRACT', '25')),
    "unlock_feature_jutsu_creation": int(os.getenv('TOKEN_COST_JUTSU_CREATION', '30')),
}

# Maximum tokens allowed for specific usages
MAX_CLAN_BOOST_TOKENS = int(os.getenv('MAX_CLAN_BOOST_TOKENS', '3'))

# --- Clan Assignment ---
DEFAULT_CLAN_WEIGHT = float(os.getenv('DEFAULT_CLAN_WEIGHT', '1.0'))
# Population adjustment values (as percentages)
UNDERPOPULATED_BONUS = float(os.getenv('UNDERPOPULATED_BONUS', '5.0'))  # Bonus % weight for clans with < 3 members
OVERPOPULATED_PENALTY_MILD = float(os.getenv('OVERPOPULATED_PENALTY_MILD', '-10.0')) # Penalty % weight for clans with > 10 members
OVERPOPULATED_PENALTY_SEVERE = float(os.getenv('OVERPOPULATED_PENALTY_SEVERE', '-25.0')) # Penalty % weight for clans with > 15 members

# Token boost values (as percentages)
TOKEN_BOOST_PER_TOKEN = float(os.getenv('TOKEN_BOOST_PER_TOKEN', '5.0')) # Additional % weight per token spent
MAX_TOKEN_BOOST = float(os.getenv('MAX_TOKEN_BOOST', '15.0')) # Maximum % boost allowed from tokens (e.g., 3 tokens * 5%)

# --- Rarity Tiers (Moved from clan_data) ---
class RarityTier(Enum):
    """Enum for clan rarity tiers."""
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    # VERY_RARE = "Very Rare" # Original had Very Rare, check if needed or simplify
    EPIC = "Epic" # Assuming Epic/Legendary are preferred tiers now
    LEGENDARY = "Legendary"

# Default base weights for each rarity tier (Moved from clan_data)
DEFAULT_RARITY_WEIGHTS = {
    RarityTier.COMMON.value: float(os.getenv('RARITY_WEIGHT_COMMON', '45.0')),
    RarityTier.UNCOMMON.value: float(os.getenv('RARITY_WEIGHT_UNCOMMON', '30.0')),
    RarityTier.RARE.value: float(os.getenv('RARITY_WEIGHT_RARE', '15.0')),
    # RarityTier.VERY_RARE.value: 8.0, # Adjust if Very Rare tier is removed
    RarityTier.EPIC.value: float(os.getenv('RARITY_WEIGHT_EPIC', '8.0')), # Assigning weight to Epic
    RarityTier.LEGENDARY.value: float(os.getenv('RARITY_WEIGHT_LEGENDARY', '2.0'))
}
# Ensure sum is close to 100: 45+30+15+8+2 = 100

# --- AI Settings ---
# Add AI model names, API keys (via env vars ideally), default prompts etc.
# Example: DEFAULT_AI_PROVIDER = "openai"

# --- Discord Settings ---
# Add default prefixes, status messages, etc.
# Example: DEFAULT_BOT_PREFIX = "!"
