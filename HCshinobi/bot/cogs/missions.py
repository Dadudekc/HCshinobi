from discord import app_commands
from discord.ext import commands
from ...utils.embeds import create_error_embed
import discord

class MissionCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mission_board", description="Show missions")
    async def mission_board(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        missions = await self.bot.services.mission_system.get_available_missions(str(interaction.user.id))
        if not missions:
            await interaction.followup.send("No missions are available for you right now. Try ranking up or leveling up!", ephemeral=True)
            return
        embed = discord.Embed(title="📜 Mission Board", color=discord.Color.gold())
        for idx, m in enumerate(missions, start=1):
            embed.add_field(name=f"{idx}. {m.get('name', 'Unknown')}", value=m.get('description', 'No description'), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mission_accept")
    async def mission_accept(self, interaction, mission_number: int):
        missions = await self.bot.services.mission_system.get_available_missions(str(interaction.user.id))
        if mission_number < 1 or mission_number > len(missions):
            await interaction.response.send_message("Invalid mission number.", ephemeral=True)
            return
        mission_id = missions[mission_number - 1].get("mission_id")
        success, msg = await self.bot.services.mission_system.assign_mission(str(interaction.user.id), mission_id)
        if success:
            await interaction.response.send_message(f"Mission '{mission_id}' accepted!", ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MissionCommands(bot))
