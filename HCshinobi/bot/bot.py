from discord.ext import commands
from .config import BotConfig
from .services import ServiceContainer

class HCBot(commands.Bot):
    def __init__(self, config: BotConfig, silent_start: bool = False):
        super().__init__(command_prefix=config.command_prefix)
        self.config = config
        self.silent_start = silent_start
        self.services = ServiceContainer(config)

    async def setup_hook(self) -> None:
        await self.services.initialize(self)
        register_commands_command(self)


def register_commands_command(bot: commands.Bot):
    @bot.command(name="commands")
    async def _list_commands(ctx: commands.Context):
        names = sorted(f"!{c.name}" for c in bot.commands)
        await ctx.send("Available commands: " + " ".join(names))

