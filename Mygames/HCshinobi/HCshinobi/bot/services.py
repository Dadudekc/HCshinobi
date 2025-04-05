"""
Service container for HCShinobi bot.
Manages initialization and lifecycle of all bot services.
"""

import asyncio
from typing import Optional, List, Dict
import discord
import aiohttp
import logging
import os
import json
import aiofiles

# Core Systems
from ..core.character_system import CharacterSystem
from ..core.battle_system import BattleSystem
from ..core.clan_system import ClanSystem
from ..core.currency_system import CurrencySystem
from ..core.training_system import TrainingSystem
from ..core.quest_system import QuestSystem
from ..core.mission_system import MissionSystem
from ..core.constants import (
    TOKEN_FILE, TOKEN_LOG_FILE, NPC_FILE, CURRENCY_FILE, MODIFIERS_FILE, CLANS_FILE,
    DATA_DIR, CLAN_POPULATION_FILE, ASSIGNMENT_HISTORY_FILE,
    SHOP_ITEMS_FILE, JUTSU_SUBDIR, MASTER_JUTSU_FILE
)

# Notification System
from .core.notifications.notification_dispatcher import NotificationDispatcher

# AI Clients
from ..utils.ollama_client import OllamaClient, OllamaError
from ..utils.openai_client import OpenAIClient

# Config
from .config import BotConfig

# Other core components
from ..core.clan_data import ClanData
from ..core.token_system import TokenSystem
from ..core.personality_modifiers import PersonalityModifiers
from ..core.npc_manager import NPCManager
from ..core.clan_assignment_engine import ClanAssignmentEngine
from ..core.character_manager import CharacterManager
from ..core.battle_manager import BattleManager
from ..core.clan_missions import ClanMissions
from ..core.loot_system import LootSystem
from ..core.room_system import RoomSystem
from ..core.jutsu_shop_system import JutsuShopSystem
from ..core.progression_engine import ShinobiProgressionEngine
from ..core.equipment_shop_system import EquipmentShopSystem

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Container for all bot services, handling initialization and shutdown."""

    def __init__(self, config: BotConfig):
        """
        Initialize the service container with a given bot config.

        Args:
            config (BotConfig): The bot's configuration object.
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.notification_dispatcher: Optional[NotificationDispatcher] = None
        self._ollama_client: Optional[OllamaClient] = None
        self._openai_client: Optional[OpenAIClient] = None

        # Core references
        self._npc_manager: Optional[NPCManager] = None
        self._currency_system: Optional[CurrencySystem] = None
        self._training_system: Optional[TrainingSystem] = None
        self._quest_system: Optional[QuestSystem] = None
        self._mission_system: Optional[MissionSystem] = None
        self._character_system: Optional[CharacterSystem] = None
        self._clan_data: Optional[ClanData] = None
        self._clan_system: Optional[ClanSystem] = None
        self._battle_system: Optional[BattleSystem] = None
        self._clan_assignment_engine: Optional[ClanAssignmentEngine] = None
        self._clan_missions: Optional[ClanMissions] = None
        self._loot_system: Optional[LootSystem] = None
        self._room_system: Optional[RoomSystem] = None
        self.jutsu_shop_system: Optional[JutsuShopSystem] = None
        self._equipment_shop_system: Optional[EquipmentShopSystem] = None
        self._progression_engine: Optional[ShinobiProgressionEngine] = None
        self._battle_manager: Optional[BattleManager] = None
        self._personality_modifiers: Optional[PersonalityModifiers] = None
        self._token_system: Optional[TokenSystem] = None

        # Data
        self.master_jutsu_data: Dict[str, Dict] = {}

        # Internal state
        self._initialized = False

        # Resolve data directory
        self._data_dir = self.config.data_dir or DATA_DIR
        if not self.config.data_dir:
            logger.warning(f"BotConfig did not specify data_dir, using default: {self._data_dir}")

    async def initialize(self):
        """
        Initialize all services in proper dependency order.
        This method should be called once before using any services.
        """
        logger.info("Initializing services...")
        try:
            self.session = aiohttp.ClientSession()

            # Instantiate core data and systems (deferred hooking in ready_hooks)
            self._clan_data = ClanData(data_dir=self._data_dir)
            self._personality_modifiers = PersonalityModifiers(data_dir=self._data_dir)
            self._token_system = TokenSystem(data_dir=self._data_dir)
            self._currency_system = CurrencySystem(data_dir=self._data_dir)
            self._character_system = CharacterSystem(data_dir=self._data_dir)
            self._progression_engine = ShinobiProgressionEngine(
                character_system=self._character_system,
                data_dir=self._data_dir
            )
            self._character_system.progression_engine = self._progression_engine

            self._training_system = TrainingSystem(
                data_dir=self._data_dir,
                character_system=self._character_system,
                currency_system=self._currency_system
            )
            self._quest_system = QuestSystem(
                data_dir=self._data_dir,
                character_system=self._character_system
            )
            self._npc_manager = NPCManager(data_dir=self._data_dir)
            self._clan_system = ClanSystem(data_dir=self._data_dir)

            # Load Jutsu data before systems that rely on it
            await self.load_master_jutsu_data()

            self._battle_system = BattleSystem(
                data_dir=self._data_dir,
                character_system=self._character_system,
                progression_engine=self._progression_engine,
                master_jutsu_data=self.master_jutsu_data
            )
            self._clan_assignment_engine = ClanAssignmentEngine(
                clan_data_service=self._clan_data,
                personality_modifiers_service=self._personality_modifiers,
            )
            self._mission_system = MissionSystem(
                character_system=self._character_system,
                currency_system=self._currency_system,
                data_dir=self._data_dir,
                progression_engine=self._progression_engine
            )
            self._clan_missions = ClanMissions(data_dir=self._data_dir)
            self._loot_system = LootSystem(self._character_system, self._currency_system)
            self._room_system = RoomSystem(self._character_system, self._battle_system)

            self.jutsu_shop_system = JutsuShopSystem(
                data_dir=self._data_dir,
                master_jutsu_data=self.master_jutsu_data
            )
            self._equipment_shop_system = EquipmentShopSystem(
                data_dir=self._data_dir,
                character_system=self._character_system,
                currency_system=self._currency_system,
                equipment_shop_channel_id=self.config.equipment_shop_channel_id
            )

            # Notification dispatcher
            webhook_obj = None
            if self.config.webhook_url:
                try:
                    webhook_obj = discord.Webhook.from_url(
                        self.config.webhook_url, session=self.session
                    )
                    logger.info("Webhook created successfully from URL.")
                except Exception as e:
                    logger.error(
                        f"Failed to create webhook from URL {self.config.webhook_url}: {e}"
                    )
            self.notification_dispatcher = NotificationDispatcher(webhook=webhook_obj)

            # AI clients
            try:
                self._ollama_client = OllamaClient(
                    base_url=self.config.ollama_base_url,
                    default_model=self.config.ollama_model
                )
                logger.info("OllamaClient initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize OllamaClient: {e}")

            if self.config.openai_api_key:
                # Initialize the OpenAIClient with proper API key
                try:
                    self._openai_client = OpenAIClient(api_key=self.config.openai_api_key)
                    logger.info("OpenAIClient initialized with API key.")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAIClient: {e}")
                    self._openai_client = None
            else:
                logger.warning("OpenAI API key not provided, OpenAIClient not initialized.")

            # Call async ready hooks
            logger.info("Calling ready hooks for initialized services...")
            service_instances = [
                self._character_system, self._clan_data, self._token_system,
                self._progression_engine, self._battle_system, self._mission_system,
                self.jutsu_shop_system, self._equipment_shop_system,
                self._personality_modifiers, self._currency_system,
                self._training_system,
                self._clan_assignment_engine,
                self._clan_missions,
                self._loot_system,
                self._room_system,
                self._quest_system,
                self._npc_manager,
                self._clan_system,
            ]

            ready_tasks = []
            for service in service_instances:
                if service and hasattr(service, "ready_hook") and callable(service.ready_hook):
                    ready_tasks.append(asyncio.create_task(service.ready_hook()))
                elif service and hasattr(service, "load_characters") and callable(service.load_characters):
                    ready_tasks.append(asyncio.create_task(service.load_characters()))

            if ready_tasks:
                await asyncio.gather(*ready_tasks)
                logger.info(f"Finished awaiting {len(ready_tasks)} ready hooks/load tasks.")
            else:
                logger.warning("No ready hooks found to execute.")

            # Initialize BattleManager if dependencies are ready
            if self._character_system and self._battle_system:
                self._battle_manager = BattleManager(
                    character_manager=self._character_system,
                    ollama_client=self._ollama_client,
                    battle_system=self._battle_system
                )
                logger.info("BattleManager initialized.")
            else:
                logger.error(
                    "Failed to initialize BattleManager: Dependencies not met "
                    "(CharacterSystem/BattleSystem)."
                )

            self._initialized = True
            logger.info("All services initialized successfully.")

        except Exception as e:
            logger.error(f"Error during service initialization: {e}", exc_info=True)
            self._initialized = False
            raise

    async def shutdown(self):
        """
        Shutdown all services in reverse dependency order.
        Close active sessions and perform any necessary cleanup.
        """
        logger.info("Shutting down services...")

        # Shutdown AI clients
        if self._ollama_client:
            await self._ollama_client.close()
            logger.info("OllamaClient closed.")
        
        # Shutdown OpenAI client using async method
        if self._openai_client:
            try:
                await self._openai_client.shutdown()
                logger.info("OpenAIClient closed.")
            except Exception as e:
                logger.error(f"Error shutting down OpenAIClient: {e}")

        # Example: shutting down clan system
        if self._clan_system:
            await self._clan_system.shutdown()
            logger.info("ClanSystem shut down.")

        if self._battle_system:
            await self._battle_system.shutdown()
            logger.info("BattleSystem shut down.")

        if self._character_system:
            await self._character_system.shutdown()
            logger.info("CharacterSystem shut down.")

        # Close aiohttp session last
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Aiohttp session closed.")

        self._initialized = False
        logger.info("Service container shut down.")

    async def load_master_jutsu_data(self):
        """
        Loads the master Jutsu definitions from JSON and stores them in `master_jutsu_data`.
        """
        filepath = os.path.join(self._data_dir, JUTSU_SUBDIR, MASTER_JUTSU_FILE)
        logger.info(f"Attempting to load master jutsu data from {filepath}")

        try:
            if not os.path.exists(filepath):
                logger.error(f"Master jutsu data file NOT FOUND at: {filepath}")
                self.master_jutsu_data = {}
                return

            async with aiofiles.open(filepath, mode='r', encoding='utf-8') as f:
                content = await f.read()
                logger.debug(f"Read {len(content)} bytes from master jutsu data file.")

            jutsu_definitions = json.loads(content)
            if isinstance(jutsu_definitions, list):
                loaded_data = {}
                for jutsu_def in jutsu_definitions:
                    if isinstance(jutsu_def, dict) and 'name' in jutsu_def:
                        jutsu_name = jutsu_def['name']
                        if jutsu_name in loaded_data:
                            logger.warning(
                                f"Duplicate jutsu name found: '{jutsu_name}'. Overwriting."
                            )
                        loaded_data[jutsu_name] = jutsu_def
                    else:
                        logger.warning(
                            f"Skipping invalid entry in {MASTER_JUTSU_FILE}: {jutsu_def}"
                        )

                self.master_jutsu_data = loaded_data
                logger.info(
                    f"Loaded {len(loaded_data)} jutsu definitions into master_jutsu_data."
                )
            else:
                logger.error(
                    f"Master jutsu data file ({filepath}) does not contain a valid JSON list."
                )
                self.master_jutsu_data = {}

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {filepath}: {e}")
            self.master_jutsu_data = {}
        except Exception as e:
            logger.error(f"Unexpected error loading master jutsu data: {e}", exc_info=True)
            self.master_jutsu_data = {}

    def _check_initialized(self):
        """
        Internal helper to ensure services are ready before being accessed.
        """
        if not self._initialized:
            raise RuntimeError("Services not initialized. Call initialize() first.")

    # ------------------------------------------------------------------------
    # Service Accessors
    # ------------------------------------------------------------------------

    @property
    def clan_data(self) -> ClanData:
        self._check_initialized()
        return self._clan_data

    @property
    def personality_modifiers(self) -> Optional[PersonalityModifiers]:
        return self._personality_modifiers

    @property
    def character_system(self) -> CharacterSystem:
        self._check_initialized()
        return self._character_system

    @property
    def clan_system(self) -> ClanSystem:
        self._check_initialized()
        return self._clan_system

    @property
    def battle_system(self) -> Optional[BattleSystem]:
        self._check_initialized()
        return self._battle_system

    @property
    def token_system(self) -> Optional[TokenSystem]:
        return self._token_system

    @property
    def npc_manager(self) -> Optional[NPCManager]:
        return self._npc_manager

    @property
    def clan_assignment_engine(self) -> ClanAssignmentEngine:
        self._check_initialized()
        if self._clan_assignment_engine is None:
            raise RuntimeError("ClanAssignmentEngine not initialized.")
        return self._clan_assignment_engine

    @property
    def character_manager(self) -> CharacterManager:
        """
        Returns the character system itself, if it acts as the manager.
        """
        if not self.character_system:
            raise RuntimeError("Services not initialized. Call initialize() first.")
        return self.character_system

    @property
    def battle_manager(self) -> Optional[BattleManager]:
        return self._battle_manager

    @property
    def ollama_client(self) -> OllamaClient:
        if not self._ollama_client:
            raise RuntimeError("Ollama client not initialized.")
        return self._ollama_client

    @property
    def openai_client(self) -> Optional[OpenAIClient]:
        return self._openai_client

    @property
    def webhook(self) -> Optional[discord.Webhook]:
        """
        Returns the webhook instance from the notification dispatcher.
        """
        if not self.notification_dispatcher:
            raise RuntimeError("Notification dispatcher not initialized.")
        return self.notification_dispatcher.webhook

    @property
    def currency_system(self) -> CurrencySystem:
        self._check_initialized()
        return self._currency_system

    @property
    def training_system(self) -> TrainingSystem:
        self._check_initialized()
        return self._training_system

    @property
    def quest_system(self) -> QuestSystem:
        self._check_initialized()
        return self._quest_system

    @property
    def mission_system(self) -> MissionSystem:
        self._check_initialized()
        return self._mission_system

    @property
    def clan_missions(self) -> ClanMissions:
        if not self._initialized:
            raise RuntimeError("Services not initialized.")
        return self._clan_missions

    @property
    def loot_system(self) -> LootSystem:
        if not self._initialized:
            raise RuntimeError("Services not initialized.")
        return self._loot_system

    @property
    def room_system(self) -> RoomSystem:
        if not self._initialized:
            raise RuntimeError("Services not initialized.")
        return self._room_system

    @property
    def progression_engine(self) -> Optional[ShinobiProgressionEngine]:
        self._check_initialized()
        return self._progression_engine

    @property
    def equipment_shop_system(self) -> EquipmentShopSystem:
        self._check_initialized()
        if not self._equipment_shop_system:
            raise RuntimeError("EquipmentShopSystem was not initialized properly.")
        return self._equipment_shop_system
