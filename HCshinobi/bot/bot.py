"""Discord bot implementation."""
from __future__ import annotations

import logging
from typing import Optional

import discord
from discord.ext import commands

from .config import BotConfig
from .services import ServiceContainer


def register_commands_command(bot: commands.Bot):
    """Register a simple command that lists all available prefix commands."""

    @bot.command(name="commands")
    async def list_commands(ctx: commands.Context) -> None:
        prefix = bot.command_prefix
        names = [f"{prefix}{cmd.name}" for cmd in bot.commands]
        names.sort()
        message = "Available commands: " + ", ".join(names)
        await ctx.send(message)

    return list_commands


class HCBot(commands.Bot):
    """Basic bot class with configuration and services."""

    def __init__(self, config: BotConfig, *, silent_start: bool = False, **kwargs) -> None:
        intents = kwargs.pop("intents", discord.Intents.default())
        super().__init__(command_prefix=config.command_prefix, intents=intents, **kwargs)
        self.config = config
        self.silent_start = silent_start
        self.services: Optional[ServiceContainer] = None

        # Register helper commands
        register_commands_command(self)

    async def setup_hook(self) -> None:  # Called by discord.py during startup
        if self.services and not getattr(self, "_initialized_services", False):
            await self.services.initialize(self)
            self._initialized_services = True

    async def on_ready(self) -> None:
        if not self.silent_start:
            logging.getLogger(__name__).info("Bot logged in as %s", self.user)
