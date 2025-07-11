"""
Character Commands - Character creation and management
"""

import discord
from discord import app_commands
from discord.ext import commands

from ...utils.embeds import create_error_embed, create_info_embed
from ...core.character import Character


class CharacterCommands(commands.Cog):
    """Commands for character creation and management."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create", description="Create your ninja character")
    async def create(self, interaction: discord.Interaction) -> None:
        """Create a new character for the user."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            user_name = interaction.user.display_name
            
            # Check if services are available
            if not hasattr(self.bot, 'services'):
                await interaction.followup.send("Character system not available. Please try again later.", ephemeral=True)
                return
            
            character_system = self.bot.services.character_system
            clan_assignment_engine = self.bot.services.clan_assignment_engine
            
            # Check if character already exists - PERMADEATH SYSTEM
            existing_char = await character_system.get_character(user_id)
            if existing_char:
                # In permadeath system, only allow new character if current one is dead (hp = 0)
                if existing_char.hp > 0:
                    embed = discord.Embed(
                        title="🚫 Character Already Exists",
                        description=f"**{existing_char.name}** is still alive!\n\n"
                                   "In this **PERMADEATH** system, you can only create a new character after your current one dies.\n\n"
                                   "Use `/profile` to view your character or `/delete_character` to permanently delete them.",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="🎮 Current Status", 
                        value=f"**HP:** {existing_char.hp}/{existing_char.max_hp}\n**Level:** {existing_char.level}\n**Clan:** {existing_char.clan}",
                        inline=False
                    )
                    embed.set_footer(text="⚰️ Only death allows rebirth in the ninja world")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                else:
                    # Character is dead (hp = 0), allow new character creation
                    # First delete the dead character
                    await character_system.delete_character(user_id)
                    embed = discord.Embed(
                        title="⚰️ Honoring the Fallen",
                        description=f"**{existing_char.name}** has fallen in battle.\n\n"
                                   "Their sacrifice will be remembered. Creating your new ninja...",
                        color=discord.Color.dark_grey()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    # Continue with character creation below
            
            # Assign a clan
            clan_result = await clan_assignment_engine.assign_clan(user_id)
            assigned_clan = clan_result.get("assigned_clan", "Civilian")
            
            # Create the character
            character = await character_system.create_character(user_id, user_name, assigned_clan)
            
            # Create success embed
            embed = discord.Embed(
                title="Character Created!",
                description=f"Welcome, {character.name} of the {character.clan} clan!",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Name", value=character.name, inline=True)
            embed.add_field(name="Clan", value=character.clan, inline=True)
            embed.add_field(name="Rank", value=character.rank, inline=True)
            embed.add_field(name="Level", value=str(character.level), inline=True)
            embed.add_field(name="HP", value=f"{character.hp}/{character.max_hp}", inline=True)
            embed.add_field(name="Chakra", value=f"{character.chakra}/{character.max_chakra}", inline=True)
            
            embed.add_field(
                name="🎯 Next Steps",
                value="• Use `/profile` to view your full stats\n"
                      "• Use `/train` to improve your abilities\n"
                      "• Use `/mission_board` to start missions\n"
                      "• Use `/solomon` to challenge the ultimate boss",
                inline=False
            )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Your ninja journey begins now!")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"An error occurred during character creation: {str(e)}", ephemeral=True)

    @app_commands.command(name="profile", description="View your character profile")
    async def profile(self, interaction: discord.Interaction) -> None:
        """Display the user's character profile."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            
            # Check if services are available
            if not hasattr(self.bot, 'services'):
                await interaction.followup.send("Character system not available. Please try again later.", ephemeral=True)
                return
            
            character_system = self.bot.services.character_system
            character = await character_system.get_character(user_id)
            
            if not character:
                await interaction.followup.send("You don't have a character yet! Use `/create` to start your journey.", ephemeral=True)
                return
            
            # Get currency and tokens if available
            ryo = 0
            tokens = 0
            
            if hasattr(self.bot.services, 'currency_system'):
                ryo = await self.bot.services.currency_system.get_player_balance(user_id)
            
            if hasattr(self.bot.services, 'token_system'):
                tokens = await self.bot.services.token_system.get_player_tokens(user_id)
            
            # Create profile embed
            embed = discord.Embed(
                title=f"🥷 {character.name}'s Profile",
                description=f"**{character.clan} Clan** | **{character.rank}** | **Level {character.level}**",
                color=discord.Color.blue()
            )
            
            # Basic stats
            embed.add_field(
                name="💪 Combat Stats",
                value=f"**HP:** {character.hp}/{character.max_hp}\n"
                      f"**Chakra:** {character.chakra}/{character.max_chakra}\n"
                      f"**Stamina:** {character.stamina}/{character.max_stamina}",
                inline=True
            )
            
            embed.add_field(
                name="⚔️ Physical Attributes",
                value=f"**Strength:** {character.strength}\n"
                      f"**Defense:** {character.defense}\n"
                      f"**Speed:** {character.speed:.1f}",
                inline=True
            )
            
            embed.add_field(
                name="🧠 Mental Attributes",
                value=f"**Intelligence:** {character.intelligence}\n"
                      f"**Willpower:** {character.willpower}\n"
                      f"**Perception:** {character.perception}",
                inline=True
            )
            
            embed.add_field(
                name="🌟 Jutsu Stats",
                value=f"**Ninjutsu:** {character.ninjutsu}\n"
                      f"**Genjutsu:** {character.genjutsu}\n"
                      f"**Taijutsu:** {character.taijutsu}\n"
                      f"**Chakra Control:** {character.chakra_control}",
                inline=True
            )
            
            # Jutsu and achievements
            jutsu_list = character.jutsu[:5] if character.jutsu else ["None"]
            jutsu_display = "\n".join([f"• {jutsu}" for jutsu in jutsu_list])
            if len(character.jutsu) > 5:
                jutsu_display += f"\n... and {len(character.jutsu) - 5} more"
            
            embed.add_field(
                name="📜 Known Jutsu",
                value=jutsu_display,
                inline=True
            )
            
            # Battle record
            embed.add_field(
                name="🏆 Battle Record",
                value=f"**Wins:** {character.wins}\n"
                      f"**Losses:** {character.losses}\n"
                      f"**Draws:** {character.draws}",
                inline=True
            )
            
            # Currency
            embed.add_field(
                name="💰 Resources",
                value=f"**Ryo:** {ryo:,}\n**Tokens:** {tokens:,}",
                inline=True
            )
            
            # Commands
            embed.add_field(
                name="🎮 Quick Actions",
                value="• `/train` - Train attributes\n"
                      "• `/mission_board` - View missions\n"
                      "• `/shop` - Browse items\n"
                      "• `/solomon` - Boss battle",
                inline=True
            )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"Ninja ID: {character.id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"Error loading profile: {str(e)}", ephemeral=True)

    @app_commands.command(name="delete_character", description="Delete your character (PERMANENT)")
    async def delete_character(self, interaction: discord.Interaction) -> None:
        """Delete the user's character permanently."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = interaction.user.id
            
            # Check if services are available
            if not hasattr(self.bot, 'services'):
                await interaction.followup.send(
                    "Character system not available. Please try again later.",
                    ephemeral=True
                )
                return
            
            character_system = self.bot.services.character_system
            character = await character_system.get_character(user_id)
            
            if not character:
                await interaction.followup.send(
                    "You don't have a character to delete.",
                    ephemeral=True
                )
                return
            
            # Delete the character
            await character_system.delete_character(user_id)
            
            await interaction.followup.send(
                f"Character **{character.name}** has been permanently deleted. Use `/create` to start a new journey.",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"Error deleting character: {str(e)}",
                ephemeral=True
            )

    @commands.command(name="create_test_character", help="Create a high-level test character for Solomon battles")
    @commands.has_permissions(administrator=True)
    async def create_test_character(self, ctx: commands.Context) -> None:
        """Create a test character with high stats for Solomon testing."""
        
        try:
            user_id = ctx.author.id
            user_name = ctx.author.display_name
            
            # Check if services are available
            if not hasattr(self.bot, 'services'):
                await ctx.send("Character system not available. Please try again later.")
                return
            
            character_system = self.bot.services.character_system
            clan_assignment_engine = self.bot.services.clan_assignment_engine
            
            # Check if character already exists
            existing_char = await character_system.get_character(user_id)
            if existing_char:
                await ctx.send(f"You already have a character: **{existing_char.name}**! Use `!delete_character` first if you want to create a new one.")
                return
            
            # Assign a clan
            clan_result = await clan_assignment_engine.assign_clan(user_id)
            assigned_clan = clan_result.get("assigned_clan", "Uchiha")  # Default to Uchiha for testing
            
            # Create high-level test character
            character = await character_system.create_character(user_id, f"Test {user_name}", assigned_clan)
            
            # Boost stats for Solomon testing
            character.level = 60  # High level for Solomon
            character.hp = 800
            character.max_hp = 800
            character.chakra = 600
            character.max_chakra = 600
            character.stamina = 400
            character.max_stamina = 400
            character.strength = 45
            character.defense = 40
            character.speed = 42
            character.ninjutsu = 50
            character.genjutsu = 45
            character.taijutsu = 48
            character.willpower = 35
            character.chakra_control = 40
            character.intelligence = 38
            character.perception = 35
            
            # Add some powerful jutsu
            character.jutsu = [
                "Fireball Jutsu",
                "Great Fireball Jutsu", 
                "Phoenix Sage Fire",
                "Dragon Flame Jutsu",
                "Shadow Clone Jutsu",
                "Rasengan",
                "Chidori",
                "Substitution Jutsu"
            ]
            
            # Add achievements for Solomon qualification (including required ones)
            character.achievements = [
                "First Battle Won",
                "Defeated 10 Opponents", 
                "Defeated 50 Opponents",
                "Elite Warrior",
                "Jutsu Master",
                "Master of Elements",  # Required for Solomon
                "Battle Hardened"      # Required for Solomon
            ]
            
            # Save the boosted character
            await character_system.save_character(character)
            
            # Create success embed
            embed = discord.Embed(
                title="🧪 Test Character Created!",
                description=f"**{character.name}** of the **{character.clan}** clan is ready for Solomon!\n\n"
                           "⚠️ **This is a test character with boosted stats for Solomon battles.**",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="Level", value=str(character.level), inline=True)
            embed.add_field(name="Clan", value=character.clan, inline=True)
            embed.add_field(name="HP", value=f"{character.hp}/{character.max_hp}", inline=True)
            embed.add_field(name="Strength", value=str(character.strength), inline=True)
            embed.add_field(name="Ninjutsu", value=str(character.ninjutsu), inline=True)
            embed.add_field(name="Jutsu Known", value=str(len(character.jutsu)), inline=True)
            
            embed.add_field(
                name="🎯 Ready for Battle!",
                value="• Use `!solomon_interactive` for the new interactive battle system\n"
                      "• Use `!profile` to view your full stats\n"
                      "• Use `!solomon info` to learn about Solomon",
                inline=False
            )
            
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text="Test character created! Ready for Solomon battle testing.")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"An error occurred during test character creation: {str(e)}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCommands(bot)) 