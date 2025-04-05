"""Core constants for the HCshinobi project."""

import os
from enum import Enum

# --- Base Directories --- 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Should resolve to HCshinobi workspace root
print(f"Base directory: {BASE_DIR}")
DATA_DIR = "data"
LOG_DIR = os.path.join(DATA_DIR, "logs")  # Log dir based on data dir is fine

# --- Standardized Subdirectory Names (Used within systems) --- 
CHARACTERS_SUBDIR = "characters"
CLANS_SUBDIR = "clans"
SHOPS_SUBDIR = "shops"
CURRENCY_SUBDIR = "currency"
TOKENS_SUBDIR = "tokens"
HISTORY_SUBDIR = "history"
MISSIONS_SUBDIR = "missions"
PROGRESSION_SUBDIR = "progression"  # For ranks, achievements, titles
JUTSU_SUBDIR = "jutsu"  # For master list?
BATTLES_SUBDIR = "battles"

# --- Database Subdirectory --- 
DATABASE_SUBDIR = "database"  # New subdirectory for persistent DB files

# --- NEW: Battle Filenames --- #
ACTIVE_BATTLES_FILENAME = "active_battles.json" # Resides in BATTLES_SUBDIR
BATTLE_HISTORY_FILENAME = "battle_history.json" # Added
# --- END NEW --- #

# --- NEW: Mission Filenames --- #
ACTIVE_MISSIONS_FILENAME = "active_missions.json" # Resides in MISSIONS_SUBDIR
COMPLETED_MISSIONS_FILE = "completed_missions.json" # Resides in MISSIONS_SUBDIR? Or HISTORY_SUBDIR?
MISSION_DEFINITIONS_FILE = "mission_definitions.json" # Resides in MISSIONS_SUBDIR?
# --- END NEW --- #

# --- Core Data Filenames (Relative to DATA_DIR or subdir) --- 
CLANS_FILE = "clans.json"  # Legacy format - being phased out
NPC_FILE = "npcs.json"  # Resides in DATA_DIR root
MODIFIERS_FILE = "modifiers.json"  # Resides in DATA_DIR root
CLAN_POPULATION_FILE = "clan_populations.json"
ASSIGNMENT_HISTORY_FILE = "assignment_history.json"
MASTER_JUTSU_FILE = "master_jutsu_list.json"  # Resides in JUTSU_SUBDIR

# --- Currency/Token Filenames --- 
CURRENCY_FILE = "currency.json"  # Resides in DATA_DIR root?
TOKEN_FILE = "tokens.json"  # Resides in TOKENS_SUBDIR
TOKEN_LOG_FILE = "token_log.json"  # Resides in TOKENS_SUBDIR or LOG_DIR?

# --- Shop Filenames --- 
SHOP_ITEMS_FILE = "general_items.json"  # General items, resides in SHOPS_SUBDIR
JUTSU_SHOP_STATE_FILE = "jutsu_shop_state.json"  # Resides in SHOPS_SUBDIR
EQUIPMENT_SHOP_FILE = "equipment_shop.json"  # Resides in SHOPS_SUBDIR
EQUIPMENT_SHOP_STATE_FILE = "equipment_shop_state.json"  # Resides in SHOPS_SUBDIR

# --- Shop Gameplay Constants --- 
DEFAULT_SELL_MODIFIER = 0.5 # Items sell for 50% of base price

# --- Progression Filenames --- 
RANKS_FILE = "ranks.json"  # Resides in PROGRESSION_SUBDIR
ACHIEVEMENTS_FILE = "achievements.json"  # Resides in PROGRESSION_SUBDIR
TITLES_FILE = "titles.json"  # Resides in PROGRESSION_SUBDIR

# --- Logging Filenames (Relative to LOG_DIR) --- 
BOT_LOG_FILE = "bot.log"
CLAN_ASSIGNMENT_LOG_FILE = "clan_assignment.log"
DEV_LOG_FILE = "devlog.md"  # Still maybe not a log?

# --- Database Filenames --- 
LOOT_HISTORY_DB_FILE = "loot_history.db"  # New file for persistent loot history storage

# --- Rarity Definitions --- 
class RarityTier(Enum):
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"

# Default weights mapping RarityTier values to base weights
DEFAULT_RARITY_WEIGHTS = {
    RarityTier.COMMON.value: 50, 
    RarityTier.UNCOMMON.value: 30,
    RarityTier.RARE.value: 15,
    RarityTier.EPIC.value: 4, 
    RarityTier.LEGENDARY.value: 1
}

# --- Clan Assignment Adjustments --- 
UNDERPOPULATED_BONUS = 1.2  # 20% boost
OVERPOPULATED_PENALTY_MILD = 0.8  # 20% reduction
OVERPOPULATED_PENALTY_SEVERE = 0.5  # 50% reduction

TOKEN_BOOST_PER_TOKEN = 10  # Add 10% (additive) per token
MAX_TOKEN_BOOST = 30       # Maximum boost from tokens (e.g., 3 tokens max)

# Ensure base directory exists (optional, could be done at bot startup)
# os.makedirs(DATA_DIR, exist_ok=True)
# os.makedirs(LOG_DIR, exist_ok=True)

# --- NPC Management --- 
MAX_NPC_COUNT = int(os.getenv('MAX_NPC_COUNT', '100'))
DEFAULT_NPC_STATUS = os.getenv('DEFAULT_NPC_STATUS', 'Active')

# --- Token System --- 
TOKEN_START_AMOUNT = int(os.getenv('TOKEN_START_AMOUNT', '5'))
# TOKEN_FILE and TOKEN_LOG_FILE are defined above

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

# Token usage limits and cooldowns
TOKENS_PER_REROLL = int(os.getenv('TOKENS_PER_REROLL', '1')) # Renamed from TOKEN_COSTS['reroll_clan']?
REROLL_COOLDOWN_HOURS = int(os.getenv('REROLL_COOLDOWN_HOURS', '24')) # Added missing constant
MAX_CLAN_BOOST_TOKENS = int(os.getenv('MAX_CLAN_BOOST_TOKENS', '3'))

# --- Clan Assignment --- (Note: These are also defined above, potential duplication)
DEFAULT_CLAN_WEIGHT = float(os.getenv('DEFAULT_CLAN_WEIGHT', '1.0'))
# Under- and over-population adjustments are defined above

# --- AI Settings --- 
# Example: DEFAULT_AI_PROVIDER = "openai"

# --- Discord Settings --- 
# Example: DEFAULT_BOT_PREFIX = "!"

# --- Jutsu Mastery --- 
MAX_JUTSU_LEVEL = 5
MAX_JUTSU_GAUGE = 100
MASTERY_GAIN_PER_USE = 1  # Example value, adjust for balance

# --- Jutsu Shop --- 
JUTSU_SHOP_REFRESH_HOURS = 24  # How often the shop rotates (in hours)
JUTSU_SHOP_SIZE = 20  # How many jutsu are available at once
JUTSU_SHOP_MAX_RANK = "C"  # Maximum rank of jutsu to appear in the shop (overall filter)
JUTSU_SHOP_CHANNEL_ID = 1356279770412875777  # Channel ID provided by user

# Defines the order of ranks for comparison (Lower index = lower rank)
RANK_ORDER = ['Academy Student', 'E', 'D', 'C', 'B', 'A', 'S']

# Defines the maximum Jutsu rank purchaseable by character rank
MAX_JUTSU_RANK_BY_CHAR_RANK = {
    "Academy Student": "E",  # Assuming E is lowest char rank
    "Genin": "D",
    "Chunin": "C",
    "Jonin": "A",  # Jonin can buy up to A
    "Kage": "S"   # Kage can buy anything
    # Add other character ranks if they exist (e.g., ANBU, Special Jonin)
}

# --- Specializations --- #
AVAILABLE_SPECIALIZATIONS = [
    "Ninjutsu", 
    "Taijutsu", 
    "Genjutsu", 
    "Medical", 
    "Sensory", 
    "Fuinjutsu", # Sealing Techniques
    "Bukijutsu" # Weapon Techniques
]

# Clan system constants
CLANS_FILE = "clans.json"  # Legacy format - being phased out
CLAN_POPULATION_FILE = "clan_populations.json"
ASSIGNMENT_HISTORY_FILE = "assignment_history.json"
CLAN_FORMAT_TRANSITION_VERSION = "1.0"  # Current version of clan format transition
CLAN_FORMAT_TRANSITION_MESSAGE = ("The clan system is transitioning from a single clans.json file to "
                                "multiple village-specific files. The legacy format will eventually "
                                "be removed entirely. Please migrate any custom clans to the new format.")
