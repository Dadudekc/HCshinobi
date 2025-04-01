"""
Service container for HCShinobi bot.
Manages initialization and lifecycle of all bot services.
"""

import asyncio
from typing import Optional
import discord
import aiohttp
import logging
import os

# Core Systems
from ..core.character_system import CharacterSystem
from ..core.battle_system import BattleSystem
from ..core.clan_system import ClanSystem

# Notification System
from .core.notifications.notification_dispatcher import NotificationDispatcher

# AI Clients (Imported from utils)
from ..utils.ollama_client import OllamaClient, OllamaError
from ..utils.openai_client import OpenAIClient

# Config
from .config import BotConfig

# Other core components (Keep existing imports as needed)
from ..core.clan_data import ClanData
from ..core.token_system import TokenSystem
from ..core.personality_modifiers import PersonalityModifiers
from ..core.npc_manager import NPCManager
from ..core.clan_assignment_engine import ClanAssignmentEngine
from ..core.character_manager import CharacterManager
from ..core.battle_manager import BattleManager

logger = logging.getLogger(__name__)

class ServiceContainer:
    """Container for all bot services."""
    
    def __init__(self, config: BotConfig):
        """Initialize service container."""
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.notification_dispatcher: Optional[NotificationDispatcher] = None
        self._ollama_client: Optional[OllamaClient] = None
        self._openai_client: Optional[OpenAIClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all services."""
        logger.info("Initializing services...")
        
        # Initialize session
        self.session = aiohttp.ClientSession()
        
        # Initialize data/core systems
        self._clan_data = ClanData(data_dir=self.config.data_dir)
        await self._clan_data.initialize()

        self._personality_modifiers = PersonalityModifiers(
            # Construct path relative to data_dir if needed
            # Assuming MODIFIERS_FILE is relative or absolute path handled by the class
        )
        await self._personality_modifiers.initialize()

        self._token_system = TokenSystem(
            token_file=os.path.join(self.config.data_dir, TOKEN_FILE),
            log_file=os.path.join(self.config.data_dir, TOKEN_LOG_FILE)
        )
        await self._token_system.initialize()

        # Initialize systems that depend on data
        self._character_system = CharacterSystem(
            data_dir=self.config.data_dir,
            clan_data=self._clan_data,
            personality_modifiers=self._personality_modifiers
        )
        await self._character_system.initialize()

        self._clan_system = ClanSystem(
            clan_data=self._clan_data,
            character_system=self._character_system
            # Add token_system if needed
        )
        # ClanSystem might need an async initialize() if it does setup
        # await self._clan_system.initialize()

        self._battle_system = BattleSystem(
            character_system=self._character_system
            # Add other dependencies if needed
        )
        # BattleSystem might need an async initialize()
        # await self._battle_system.initialize()

        # Create webhook object if URL exists
        webhook_obj = None
        if self.config.webhook_url:
            try:
                webhook_obj = discord.Webhook.from_url(self.config.webhook_url, session=self.session)
                logger.info(f"Webhook created successfully from URL.")
            except Exception as e:
                logger.error(f"Failed to create webhook from URL {self.config.webhook_url}: {e}")

        # Initialize NotificationDispatcher
        self.notification_dispatcher = NotificationDispatcher(
            webhook=webhook_obj
            # Fallback channel and clan channels could be added later if needed
        )
        
        # Initialize AI Clients directly (assign to private attributes)
        try:
            self._ollama_client = OllamaClient(
                base_url=self.config.ollama_base_url,
                default_model=self.config.ollama_model
            )
            logger.info("OllamaClient initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize OllamaClient: {e}")
            # Decide if this is critical. Maybe allow bot to run without Ollama?

        if self.config.openai_api_key:
            try:
                self._openai_client = OpenAIClient(
                    api_key=self.config.openai_api_key,
                    target_gpt_url=self.config.openai_target_url, # Pass the correct URL
                    headless=self.config.openai_headless
                    # profile_dir and cookie_dir are not set here, assuming API key usage is primary
                )
                # OpenAIClient boot is synchronous, call it if needed for web scraping mode, but not for API key mode.
                # self._openai_client.boot() # Only needed if web scraping is the intended primary use
                logger.info("OpenAIClient initialized with API key.")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAIClient: {e}")
        else:
            logger.warning("OpenAI API key not provided, OpenAIClient not initialized.")

        self._initialized = True
        logger.info("All services initialized.")
    
    async def shutdown(self):
        """Shutdown all services."""
        logger.info("Shutting down services...")
        
        # Shutdown systems in reverse dependency order
        
        # Shutdown AI Clients (using private attributes)
        if self._ollama_client:
            await self._ollama_client.close()
            logger.info("OllamaClient closed.")
            
        if self._openai_client:
            self._openai_client.shutdown() # Synchronous shutdown
            logger.info("OpenAIClient shut down.")
        
        # No shutdown for notification dispatcher needed
        
        if self._clan_system:
            await self._clan_system.shutdown()
            logger.info("ClanSystem shut down.")
        
        if self._battle_system:
            await self._battle_system.shutdown()
            logger.info("BattleSystem shut down.")
        
        if self._character_system:
            await self._character_system.shutdown()
            logger.info("CharacterSystem shut down.")
            
        # Close the aiohttp session last
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Aiohttp session closed.")
        
        self._initialized = False
        logger.info("Service container shut down.")
    
    # Property accessors for services
    @property
    def clan_data(self) -> ClanData:
        self._check_initialized()
        return self._clan_data
    
    @property
    def personality_modifiers(self) -> PersonalityModifiers:
        self._check_initialized()
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
    def battle_system(self) -> BattleSystem:
        self._check_initialized()
        return self._battle_system
    
    @property
    def token_system(self) -> TokenSystem:
        """Get the initialized token system service."""
        self._check_initialized()
        # Return the instance created during initialize()
        return self._token_system
    
    @property
    def npc_manager(self) -> NPCManager:
        """Get NPC manager service."""
        # Similar to TokenSystem, assuming this isn't directly on ClanSystem
        raise NotImplementedError("NPCManager access needs review based on its location")
        # if not self.clan_system:
        #     raise RuntimeError("Services not initialized. Call initialize() first.")
        # return self.clan_system.npc_manager # Assuming NPCManager is part of ClanSystem
    
    @property
    def clan_engine(self) -> ClanAssignmentEngine:
        # Similar to TokenSystem, assuming this isn't directly on ClanSystem
        raise NotImplementedError("ClanAssignmentEngine access needs review based on its location")
        # if not self.clan_system:
        #     raise RuntimeError("Services not initialized. Call initialize() first.")
        # return self.clan_system.clan_engine # Assuming ClanAssignmentEngine is part of ClanSystem
    
    # Properties accessing CharacterSystem attributes
    @property
    def character_manager(self) -> CharacterManager:
        """Get character manager service."""
        if not self.character_system:
            raise RuntimeError("Services not initialized. Call initialize() first.")
        # Return CharacterSystem itself if it acts as the manager
        return self.character_system
    
    # Properties accessing BattleSystem attributes
    @property
    def battle_manager(self) -> BattleManager:
        if not self.battle_system:
            raise RuntimeError("Services not initialized. Call initialize() first.")
        # Return BattleSystem itself if it acts as the manager
        return self.battle_system
    
    # Updated properties for AI clients
    @property
    def ollama_client(self) -> OllamaClient:
        """Get the initialized Ollama client."""
        # Access private attribute
        if not self._ollama_client:
            raise RuntimeError("Ollama client not initialized.")
        return self._ollama_client
    
    @property
    def openai_client(self) -> Optional[OpenAIClient]:
        """Get the initialized OpenAI client (if API key was provided)."""
        # Access private attribute
        return self._openai_client
    
    @property
    def webhook(self) -> Optional[discord.Webhook]:
        """Get webhook instance from the notification dispatcher."""
        if not self.notification_dispatcher:
             raise RuntimeError("Notification dispatcher not initialized.")
        return self.notification_dispatcher.webhook 

    def _check_initialized(self):
        if not self._initialized:
            raise RuntimeError("Services not initialized. Call initialize() first.") 