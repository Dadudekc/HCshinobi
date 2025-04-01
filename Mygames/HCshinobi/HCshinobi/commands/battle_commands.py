"""Battle commands for the HCshinobi Discord bot."""
import discord
from discord.ext import commands
import logging
import random

from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.utils.embed_utils import get_rarity_color

class BattleCommands(commands.Cog):
    def __init__(self, bot, battle_system: BattleSystem, character_system: CharacterSystem):
        """Initialize battle commands.
        
        Args:
            bot: The bot instance
            battle_system: The battle system instance
            character_system: The character system instance
        """
        self.bot = bot
        self.battle_system = battle_system
        self.character_system = character_system
        self.logger = logging.getLogger(__name__)

    @commands.command(name="battle", description="Start a battle with another player")
    async def battle(self, ctx, opponent: discord.Member):
        """Start a battle with another player.
        
        Args:
            ctx: The command context
            opponent: The opponent to battle
        """
        challenger_id = str(ctx.author.id)
        opponent_id = str(opponent.id)
        
        # Check if both players have characters
        challenger = self.character_system.get_character(challenger_id)
        opponent_char = self.character_system.get_character(opponent_id)
        
        if not challenger or not opponent_char:
            await ctx.send("Both players need to have characters to battle!")
            return
        
        # Start battle
        battle_id = self.battle_system.start_battle(challenger_id, opponent_id)
        
        if battle_id:
            embed = discord.Embed(
                title="⚔️ Battle Started!",
                description=f"{ctx.author.mention} vs {opponent.mention}",
                color=discord.Color.red()
            )
            
            # Add initial stats
            challenger_stats = challenger['stats']
            opponent_stats = opponent_char['stats']
            
            embed.add_field(
                name=f"{challenger['name']}",
                value=f"HP: {challenger_stats['hp']}\nChakra: {challenger_stats['chakra']}",
                inline=True
            )
            
            embed.add_field(
                name=f"{opponent_char['name']}",
                value=f"HP: {opponent_stats['hp']}\nChakra: {opponent_stats['chakra']}",
                inline=True
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("Failed to start battle. Please try again!")

    @commands.command(name="use_jutsu", description="Use a jutsu in battle")
    async def use_jutsu(self, ctx, jutsu_name: str, target: discord.Member):
        """Use a jutsu in battle.
        
        Args:
            ctx: The command context
            jutsu_name: The name of the jutsu to use
            target: The target of the jutsu
        """
        player_id = str(ctx.author.id)
        target_id = str(target.id)
        
        # Check if there's an active battle
        battle = self.battle_system.get_battle_state(player_id)
        if not battle:
            await ctx.send("You're not in a battle!")
            return
        
        # Use jutsu
        success, damage = self.battle_system.use_jutsu(player_id, target_id, jutsu_name)
        
        if success:
            embed = discord.Embed(
                title="✨ Jutsu Used!",
                description=f"{ctx.author.mention} used {jutsu_name} on {target.mention}!",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Damage",
                value=f"{damage}",
                inline=True
            )
            
            # Add updated stats
            challenger_stats = battle['challenger_stats']
            opponent_stats = battle['opponent_stats']
            
            embed.add_field(
                name=f"{battle['challenger_name']}",
                value=f"HP: {challenger_stats['hp']}\nChakra: {challenger_stats['chakra']}",
                inline=True
            )
            
            embed.add_field(
                name=f"{battle['opponent_name']}",
                value=f"HP: {opponent_stats['hp']}\nChakra: {opponent_stats['chakra']}",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
            # Check for battle end
            if self.battle_system.check_battle_end(battle['id']):
                winner = self.battle_system.get_battle_winner(battle['id'])
                if winner:
                    await ctx.send(f"🏆 {winner.mention} has won the battle!")
        else:
            await ctx.send("Failed to use jutsu. Make sure you have enough chakra!")

    @commands.command(name="surrender", description="Surrender the current battle")
    async def surrender(self, ctx):
        """Surrender the current battle."""
        player_id = str(ctx.author.id)
        
        # Check if there's an active battle
        battle = self.battle_system.get_battle_state(player_id)
        if not battle:
            await ctx.send("You're not in a battle!")
            return
        
        # End battle
        self.battle_system.end_battle(battle['id'])
        
        # Get opponent
        opponent_id = battle['opponent_id'] if battle['challenger_id'] == player_id else battle['challenger_id']
        opponent = await self.bot.fetch_user(int(opponent_id))
        
        await ctx.send(f"🏳️ {ctx.author.mention} has surrendered to {opponent.mention}!")

    @commands.command(
        name="battle_history",
        description="View your battle history"
    )
    async def battle_history(self, ctx):
        """View your battle history."""
        # Get player's character
        character = self.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send(
                "❌ You need a character to view battle history!",
                ephemeral=True
            )
            return
        
        # Determine user's clan rarity color
        user_clan_name = character.clan
        user_clan_info = self.bot.clan_data.get_clan(user_clan_name) if user_clan_name else None
        user_rarity = user_clan_info.get('rarity', RarityTier.COMMON.value) if user_clan_info else RarityTier.COMMON.value
        embed_color = get_rarity_color(user_rarity)

        # Get battle history
        history = self.battle_system.get_battle_history(character.name)
        
        # Create history embed with rarity color
        embed = discord.Embed(
            title="📜 Battle History",
            description=f"Battle history for **{character.name}**",
            color=embed_color
        )
        
        if not history:
            embed.add_field(
                name="No Battles",
                value="You haven't participated in any battles yet!",
                inline=False
            )
        else:
            for entry in history[:10]:  # Show last 10 battles
                result = "Victory" if entry['winner'] == character.name else "Defeat"
                embed.add_field(
                    name=f"{result} vs {entry['loser'] if result == 'Victory' else entry['winner']}",
                    value=f"Rounds: {entry['rounds']}\nDate: {entry['end_time'].strftime('%Y-%m-%d %H:%M')}",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.command(
        name="jutsu_autocomplete",
        description="Get autocomplete suggestions for your jutsu"
    )
    async def jutsu_autocomplete(self, ctx, query: str):
        """Get autocomplete suggestions for your jutsu.
        
        Args:
            ctx: The command context
            query: The query to search for
        """
        # Get character
        character = self.character_system.get_character(str(ctx.author.id))
        if not character:
            await ctx.send(
                "❌ You need a character to view jutsu! Use /create to create one.",
                ephemeral=True
            )
            return
        
        # Filter jutsu based on query
        matching_jutsu = [
            jutsu for jutsu in character.jutsu
            if query.lower() in jutsu.lower()
        ]
        
        # Create embed
        embed = discord.Embed(
            title="Available Jutsu",
            description=f"Found {len(matching_jutsu)} matching jutsu:",
            color=discord.Color.blue()
        )
        
        if matching_jutsu:
            jutsu_list = "\n".join(f"• {jutsu}" for jutsu in matching_jutsu)
            embed.add_field(name="Jutsu", value=jutsu_list, inline=False)
        else:
            embed.add_field(
                name="No Matches",
                value="No jutsu found matching your query.",
                inline=False
            )
        
        await ctx.send(embed=embed, ephemeral=True)

    def register_commands(self, tree):
        """Register slash commands for battle commands.
        
        Args:
            tree: The command tree to register commands with
        """
        # Clear existing commands if any
        to_remove = []
        for cmd in tree.get_commands():
            if cmd.name in ["battle", "battle_history"]:
                to_remove.append(cmd)
        
        for cmd in to_remove:
            tree.remove_command(cmd.name)
        
        # Register slash commands
        @tree.command(name="battle", description="Start a battle with another player")
        @discord.app_commands.describe(opponent="The opponent to battle")
        async def battle_slash(interaction: discord.Interaction, opponent: discord.Member):
            # Convert to context-like object and call existing command
            await interaction.response.send_message(f"Starting battle with {opponent.mention}...")
            # Implementation would follow similar logic to the battle command
        
        @tree.command(name="battle_history", description="View your battle history")
        async def battle_history_slash(interaction: discord.Interaction):
            # Convert interaction to context and call existing method
            character = self.character_system.get_character(str(interaction.user.id))
            if not character:
                await interaction.response.send_message(
                    "❌ You need a character to view battle history!",
                    ephemeral=True
                )
                return
            
            # Follow similar logic to battle_history command
            
        self.logger.info("Battle slash commands registered")

async def setup(bot):
    """Set up the battle commands cog."""
    await bot.add_cog(BattleCommands(bot, bot.battle_system, bot.character_system)) 