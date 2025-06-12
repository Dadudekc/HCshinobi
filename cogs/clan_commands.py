import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import json

from ..core.clan_system import ClanSystem
from ..core.character_system import CharacterSystem
from ..utils.embed_builder import EmbedBuilder
from ..utils.errors import CharacterNotFoundError, ClanError

class ClanCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.clan_system = ClanSystem(bot.db, bot.character_system)
        self.embed_builder = EmbedBuilder()

    @app_commands.command(name="clans")
    @app_commands.describe(village="Filter clans by village")
    async def clans(self, interaction: discord.Interaction, village: Optional[str] = None):
        """List all available clans, optionally filtered by village"""
        try:
            clans = self.clan_system.get_clans(village)
            if not clans:
                await interaction.response.send_message("No clans found." if not village else f"No clans found in {village}.")
                return

            embed = discord.Embed(title="Available Clans", color=discord.Color.blue())
            for clan in clans:
                value = f"Village: {clan['village']}\n"
                value += f"Population: {clan['population']}\n"
                value += f"Rarity: {clan['rarity']}\n"
                if clan['required_level'] > 0:
                    value += f"Required Level: {clan['required_level']}\n"
                embed.add_field(name=clan['name'], value=value, inline=False)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="join_clan")
    @app_commands.describe(clan_name="Name of the clan you want to join")
    async def join_clan(self, interaction: discord.Interaction, clan_name: str):
        """Join a clan if you meet the requirements"""
        try:
            character = await self.bot.character_system.get_character(interaction.user.id)
            await self.clan_system.join_clan(character['id'], clan_name)
            
            embed = discord.Embed(
                title="Clan Joined",
                description=f"You have successfully joined the {clan_name} clan!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except (CharacterNotFoundError, ClanError) as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="leave_clan")
    async def leave_clan(self, interaction: discord.Interaction):
        """Leave your current clan"""
        try:
            character = await self.bot.character_system.get_character(interaction.user.id)
            await self.clan_system.leave_clan(character['id'])
            
            embed = discord.Embed(
                title="Clan Left",
                description="You have successfully left your clan.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
        except (CharacterNotFoundError, ClanError) as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="clan_info")
    @app_commands.describe(clan_name="Name of the clan to get information about")
    async def clan_info(self, interaction: discord.Interaction, clan_name: Optional[str] = None):
        """Get detailed information about a clan"""
        try:
            character = await self.bot.character_system.get_character(interaction.user.id)
            if not clan_name and not character['clan']:
                await interaction.response.send_message("You are not in a clan and no clan name was provided.", ephemeral=True)
                return

            clan_info = await self.clan_system.get_clan_info(clan_name or character['clan'])
            
            embed = discord.Embed(
                title=f"{clan_info['name']} Clan Information",
                description=clan_info['description'],
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Village", value=clan_info['village'], inline=True)
            embed.add_field(name="Population", value=str(clan_info['population']), inline=True)
            embed.add_field(name="Rarity", value=clan_info['rarity'], inline=True)
            
            if clan_info['kekkei_genkai']:
                kekkei_genkai = json.loads(clan_info['kekkei_genkai'])
                if kekkei_genkai:
                    embed.add_field(name="Kekkei Genkai", value=", ".join(kekkei_genkai), inline=False)
            
            if clan_info['traits']:
                traits = json.loads(clan_info['traits'])
                if traits:
                    embed.add_field(name="Traits", value=", ".join(traits), inline=False)
            
            requirements = []
            if clan_info['required_level']:
                requirements.append(f"Level: {clan_info['required_level']}")
            if clan_info['required_village']:
                requirements.append(f"Village: {clan_info['required_village']}")
            if clan_info['required_strength']:
                requirements.append(f"Strength: {clan_info['required_strength']}")
            if clan_info['required_speed']:
                requirements.append(f"Speed: {clan_info['required_speed']}")
            if clan_info['required_defense']:
                requirements.append(f"Defense: {clan_info['required_defense']}")
            if clan_info['required_chakra']:
                requirements.append(f"Chakra: {clan_info['required_chakra']}")
            
            if requirements:
                embed.add_field(name="Requirements", value="\n".join(requirements), inline=False)
            
            await interaction.response.send_message(embed=embed)
        except (CharacterNotFoundError, ClanError) as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="clan_members")
    @app_commands.describe(clan_name="Name of the clan to list members from")
    async def clan_members(self, interaction: discord.Interaction, clan_name: Optional[str] = None):
        """List all members of a clan"""
        try:
            character = await self.bot.character_system.get_character(interaction.user.id)
            if not clan_name and not character['clan']:
                await interaction.response.send_message("You are not in a clan and no clan name was provided.", ephemeral=True)
                return

            members = await self.clan_system.get_clan_members(clan_name or character['clan'])
            
            embed = discord.Embed(
                title=f"{clan_name or character['clan']} Clan Members",
                color=discord.Color.blue()
            )
            
            for member in members:
                value = f"Level: {member['level']}\n"
                value += f"Joined: <t:{int(member['clan_joined_at'].timestamp())}:R>\n"
                embed.add_field(name=member['name'], value=value, inline=True)
            
            await interaction.response.send_message(embed=embed)
        except (CharacterNotFoundError, ClanError) as e:
            await interaction.response.send_message(str(e), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="clan_leaderboard")
    @app_commands.describe(village="Filter clan rankings by village")
    async def clan_leaderboard(self, interaction: discord.Interaction, village: Optional[str] = None):
        """View clan rankings based on total power"""
        try:
            rankings = await self.clan_system.get_clan_rankings(village)
            
            embed = discord.Embed(
                title="Clan Rankings" if not village else f"Clan Rankings - {village}",
                color=discord.Color.gold()
            )
            
            for i, clan in enumerate(rankings, 1):
                value = f"Total Power: {clan['total_power']:,}\n"
                value += f"Members: {clan['population']}\n"
                value += f"Average Power: {clan['avg_power']:,.0f}\n"
                embed.add_field(name=f"{i}. {clan['name']}", value=value, inline=False)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ClanCommands(bot)) 