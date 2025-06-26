import logging
from discord.ext import commands
import discord

from .config import BotConfig
from .services import ServiceContainer


def register_commands_command(bot: commands.Bot):
    @bot.command(name="commands")
    async def list_commands(ctx: commands.Context):
        names = sorted(c.name for c in bot.commands)
        prefix = getattr(bot, "command_prefix", "!")
        message = "Available commands: " + ", ".join(f"{prefix}{n}" for n in names)
        await ctx.send(message)
    return list_commands


class HCBot(commands.Bot):
    def __init__(self, config: BotConfig, *args, silent_start: bool = False, **kwargs) -> None:
        intents = kwargs.pop("intents", discord.Intents.default())
        super().__init__(command_prefix=config.command_prefix, intents=intents, *args, **kwargs)
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.services: ServiceContainer | None = None
        register_commands_command(self)

    async def setup_hook(self) -> None:
        if not self.services:
            self.services = ServiceContainer(self.config)
            await self.services.initialize(self)
