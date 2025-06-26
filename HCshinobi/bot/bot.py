from __future__ import annotations
import logging
import discord
from discord.ext import commands

from .config import BotConfig
from .services import ServiceContainer


class HCBot(commands.Bot):
    """Discord bot for HCShinobi."""

    def __init__(self, config: BotConfig, silent_start: bool = False) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=config.command_prefix, intents=intents)
        self.config = config
        self.services = ServiceContainer(config)
        self.logger = logging.getLogger("HCShinobi")
        if not silent_start:
            self.logger.setLevel(config.log_level)

    async def setup_hook(self) -> None:
        await self.services.initialize(self)

    async def close(self) -> None:
        await self.services.shutdown()
        await super().close()
