import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import random
import asyncio
# from ..bot import HCShinobiBot # Avoid direct import if possible, use TYPE_CHECKING
from ...utils.logging import get_logger
# from ...core.exceptions import TokenError # Incorrect path
from ...core.token_system import TokenError # Correct path
from typing import TYPE_CHECKING

logger = get_logger("rolling")

if TYPE_CHECKING:
    from ..bot import HCShinobiBot

class Rolling(commands.Cog):
    """Commands related to RNG mechanics like dice rolls and clan assignments."""

    # Use string literal for type hint to avoid circular import
    def __init__(self, bot: 'HCShinobiBot'):
        self.bot = bot
        logger.info("Rolling Cog initialized.")

    @app_commands.command(name="roll", description="Rolls a dice (1-100) or your custom range.")
    @app_commands.describe(min="Minimum value", max="Maximum value")
    async def roll(self, interaction: discord.Interaction, min: Optional[int] = 1, max: Optional[int] = 100):
        """Basic random dice roll."""
        if min >= max:
            await interaction.response.send_message("Invalid range. Min must be less than max.", ephemeral=True)
            return

        result = random.randint(min, max)
        await interaction.response.send_message(f"🎲 You rolled: **{result}** (Range: {min}-{max})")

    async def create_roll_animation(self, message: discord.Message):
        """Create a rolling animation by editing a message multiple times."""
        animations = [
            "🎲 Rolling clan...",
            "🎲 Rolling clan..",
            "🎲 Rolling clan.",
            "🎲 Rolling clan..",
            "🎲 Rolling clan..."
        ]
        
        for frame in animations:
            await message.edit(content=frame)
            await asyncio.sleep(0.6)

    async def create_legendary_animation(self, message: discord.Message):
        """Create a special animation for legendary clan rolls."""
        await message.edit(content="✨ The stars align... ✨")
        await asyncio.sleep(1)
        await message.edit(content="🌟 A legendary destiny awaits... 🌟")
        await asyncio.sleep(1)

async def setup(bot: 'HCShinobiBot'):
    await bot.add_cog(Rolling(bot))
    logger.info("Rolling Cog loaded and added to bot.") 