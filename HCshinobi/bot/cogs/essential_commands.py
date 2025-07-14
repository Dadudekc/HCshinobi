"""
Essential Commands - Missing core functionality that users expect
"""

import discord
from discord import app_commands
from discord.ext import commands

from ...utils.embeds import create_error_embed, create_info_embed

class EssentialCommands(commands.Cog):
    """Essential commands that users expect in a ninja game."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Show available commands and systems")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """Display all available commands organized by system."""
        embed = discord.Embed(
            title="🎮 HCShinobi Commands",
            description="Complete ninja game command reference",
            color=0x00ff00
        )
        
        # Character Commands
        embed.add_field(
            name="🥷 Character",
            value="• `/create` - Create character ⚰️\n• `/profile` - View profile\n• `/jutsu` - View jutsu\n• `/delete_character` - Delete permanently",
            inline=True
        )
        
        # Economy Commands
        embed.add_field(
            name="💰 Economy",
            value="• `/balance` - Check currency\n• `/transfer` - Send currency\n• `/daily` - Daily reward",
            inline=True
        )
        
        # Combat Commands  
        embed.add_field(
            name="⚔️ Combat",
            value="• `/solomon` - Ultimate boss\n• `/battle_npc` - Fight NPCs\n• `/challenge` - PvP battles",
            inline=True
        )
        
        # Mission Commands
        embed.add_field(
            name="🎯 Missions", 
            value="• `/mission_board` - View missions\n• `/shinobios_mission` - Battle missions\n• `/clan_mission_board` - Clan missions",
            inline=True
        )
        
        # Training Commands
        embed.add_field(
            name="🏃‍♂️ Training",
            value="• `/train` - Train attributes\n• `/training_status` - Check progress\n• `/complete_training` - Finish training",
            inline=True
        )
        
        # Shop Commands
        embed.add_field(
            name="🛒 Shopping",
            value="• `/shop` - Browse items\n• `/buy` - Purchase items\n• `/tokens` - Token balance",
            inline=True
        )
        
        # Clan Commands
        embed.add_field(
            name="🏛️ Clans",
            value="• `/my_clan` - Your clan info\n• `/clan_list` - Browse clans\n• `/join_clan` - Join a clan",
            inline=True
        )
        
        embed.set_footer(text="⚰️ PERMADEATH SYSTEM: One character until death | HCShinobi")
        await interaction.response.send_message(embed=embed, ephemeral=True)



    @app_commands.command(name="achievements", description="View your achievements and progress")
    async def achievements_command(self, interaction: discord.Interaction) -> None:
        """Display user achievements and progress."""
        embed = discord.Embed(
            title="🏆 Achievements",
            description="Your ninja accomplishments and progress",
            color=0xffd700
        )
        
        # Combat Achievements
        embed.add_field(
            name="⚔️ Combat Achievements",
            value="🔓 **First Battle** - Win your first fight\n🔓 **Boss Slayer** - Defeat your first boss\n🔒 **Solomon's Equal** - Defeat Solomon\n🔒 **Perfect Victory** - Win without taking damage",
            inline=False
        )
        
        # Training Achievements
        embed.add_field(
            name="🏃‍♂️ Training Achievements", 
            value="🔓 **Dedicated Student** - Complete 10 training sessions\n🔒 **Master Trainer** - Complete 100 training sessions\n🔒 **Attribute Master** - Max out any attribute",
            inline=False
        )
        
        # Economic Achievements
        embed.add_field(
            name="💰 Economic Achievements",
            value="🔓 **First Transaction** - Make your first purchase\n🔒 **Wealthy Ninja** - Accumulate 100,000 ryo\n🔒 **Generous Soul** - Transfer 50,000 ryo to others",
            inline=False
        )
        
        embed.add_field(
            name="📊 Progress Tracking",
            value="Check your progress with:\n• Battle statistics in combat\n• Training progress with `/training_status`\n• Economic status with `/balance`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="jutsu_shop", description="Browse and purchase new jutsu techniques")  
    async def jutsu_shop_command(self, interaction: discord.Interaction) -> None:
        """Browse available jutsu for purchase."""
        embed = discord.Embed(
            title="🛒 Jutsu Shop",
            description="Advanced ninja techniques for purchase",
            color=0x8b4513
        )
        
        # Advanced Fire Jutsu
        embed.add_field(
            name="🔥 Advanced Fire Release",
            value="• **Amaterasu** - 50,000 ryo\n• **Great Fireball** - 25,000 ryo\n• **Phoenix Sage Fire** - 30,000 ryo",
            inline=True
        )
        
        # Advanced Water Jutsu
        embed.add_field(
            name="💧 Advanced Water Release",
            value="• **Great Waterfall** - 35,000 ryo\n• **Water Shark Bomb** - 40,000 ryo\n• **Thousand Needles** - 20,000 ryo",
            inline=True
        )
        
        # Lightning Jutsu
        embed.add_field(
            name="⚡ Advanced Lightning Release", 
            value="• **Kirin** - 60,000 ryo\n• **Lightning Armor** - 45,000 ryo\n• **Thunder God** - 55,000 ryo",
            inline=True
        )
        
        # Legendary Jutsu
        embed.add_field(
            name="🌟 Legendary Techniques",
            value="• **Rasengan** - 100,000 ryo\n• **Kamui** - 150,000 ryo\n• **Susanoo** - 200,000 ryo",
            inline=False
        )
        
        embed.add_field(
            name="💳 How to Purchase",
            value="Visit the main `/shop` to purchase jutsu scrolls\nCheck your `/balance` first to ensure you have enough ryo",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EssentialCommands(bot)) 