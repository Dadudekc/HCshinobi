"""Minimal discord bot implementation for tests."""
from __future__ import annotations

import logging
from typing import Any

import discord
from discord.ext import commands

from .services import ServiceContainer


class HCBot(commands.Bot):
    def __init__(self, config, silent_start: bool = False) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=getattr(config, "command_prefix", "!"), intents=intents)
        self.config = config
        self.services = ServiceContainer(config)
        self.logger = logging.getLogger("HCBot")
        self.silent_start = silent_start
        self.loop.create_task(self.services.initialize(self))
        self.add_command(self.commands_command)

    async def close(self) -> None:
        await self.services.shutdown()
        await super().close()

    async def on_ready(self) -> None:
        if not self.silent_start:
            print(f"Logged in as {self.user}")

    @commands.command(name="commands")
    async def commands_command(self, ctx: commands.Context) -> None:
        cmds = [c.name for c in self.commands]
        await ctx.send("Available commands: " + ", ".join(cmds))
