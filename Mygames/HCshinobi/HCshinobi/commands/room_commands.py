"""Commands for the room system."""
import discord
from discord.ext import commands
import logging

from HCshinobi.core.room_system import RoomSystem
from HCshinobi.core.character_system import CharacterSystem

class RoomCommands(commands.Cog):
    def __init__(self, bot, room_system: RoomSystem, character_system: CharacterSystem):
        """Initialize room commands.
        
        Args:
            bot: The bot instance
            room_system: The room system instance
            character_system: The character system instance
        """
        self.bot = bot
        self.room_system = room_system
        self.character_system = character_system
        self.logger = logging.getLogger(__name__)

    async def cog_command_error(self, ctx, error):
        """Handle errors for all commands in this cog."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have permission to do that!")
        else:
            self.logger.error(f"Error in {ctx.command.name}: {error}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    @commands.command(
        name="rooms",
        aliases=["areas", "locations"],
        description="View available rooms and their requirements",
        help="Shows a list of all available rooms and what you need to enter them"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def rooms(self, ctx):
        """View available rooms and their requirements.
        
        Args:
            ctx: The command context
        """
        try:
            player_id = str(ctx.author.id)
            
            # Get available rooms
            available_rooms = self.room_system.get_available_rooms(player_id)
            
            # Create embed
            embed = discord.Embed(
                title="🏰 Available Rooms",
                description="Explore different areas of the village based on your rank!",
                color=discord.Color.blue()
            )
            
            # Add room information
            for room in available_rooms:
                embed.add_field(
                    name=f"🏛️ {room['name']}",
                    value=f"Required Rank: **{room['required_rank']}**\n"
                          f"{room['description']}\n\n"
                          f"**NPCs:** {', '.join(room['npcs'])}\n"
                          f"**Missions:** {', '.join(room['missions'])}",
                    inline=False
                )
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in rooms command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            
    @commands.command(
        name="battle_npc",
        aliases=["fight_npc", "challenge_npc"],
        description="Start a battle with an NPC in your current room",
        help="Battle an NPC by specifying the room ID and NPC name"
    )
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def battle_npc(self, ctx, room_id: str, *, npc_name: str):
        """Start a battle with an NPC.
        
        Args:
            ctx: The command context
            room_id: The room's ID
            npc_name: Name of the NPC to battle
        """
        try:
            player_id = str(ctx.author.id)
            
            # Check if player is already in battle
            if self.room_system.is_in_battle(player_id):
                await ctx.send("❌ You are already in a battle!")
                return
                
            # Start NPC battle
            battle_id = self.room_system.start_npc_battle(player_id, room_id, npc_name)
            
            if not battle_id:
                await ctx.send("❌ Failed to start battle! Make sure you have the required rank and the NPC exists.")
                return
                
            # Create battle embed
            embed = discord.Embed(
                title="⚔️ NPC Battle Started!",
                description=f"Battle ID: `{battle_id}`\n"
                          f"Use `!attack {battle_id} <type>` to make your move!",
                color=discord.Color.red()
            )
            
            # Add NPC info
            npc = self.room_system.create_npc_character(npc_name, room_id)
            if npc:
                embed.add_field(
                    name="NPC Info",
                    value=f"Name: {npc.name}\n"
                          f"Rank: {npc.rank}\n"
                          f"Level: {npc.level}",
                    inline=False
                )
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in battle_npc command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            
    @commands.command(
        name="room_npcs",
        aliases=["npcs", "room_characters"],
        description="View NPCs available in a specific room",
        help="See all NPCs in a room by specifying the room ID"
    )
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def room_npcs(self, ctx, room_id: str):
        """View NPCs available in a specific room.
        
        Args:
            ctx: The command context
            room_id: The room's ID
        """
        try:
            # Get room NPCs
            npcs = self.room_system.get_room_npcs(room_id)
            
            if not npcs:
                await ctx.send("❌ No NPCs found in this room!")
                return
                
            # Create embed
            embed = discord.Embed(
                title="👥 Room NPCs",
                description=f"Available NPCs in {room_id.replace('_', ' ').title()}",
                color=discord.Color.blue()
            )
            
            # Add NPC information
            for npc in npcs:
                template = npc["template"]
                embed.add_field(
                    name=f"⚔️ {npc['name']}",
                    value=f"Base Stats:\n"
                          f"• Ninjutsu: {template['base_stats']['ninjutsu']}\n"
                          f"• Taijutsu: {template['base_stats']['taijutsu']}\n"
                          f"• Genjutsu: {template['base_stats']['genjutsu']}\n"
                          f"• Strength: {template['base_stats']['strength']}\n"
                          f"• Speed: {template['base_stats']['speed']}\n"
                          f"• Stamina: {template['base_stats']['stamina']}\n"
                          f"• Chakra Control: {template['base_stats']['chakra_control']}\n"
                          f"• Willpower: {template['base_stats']['willpower']}\n"
                          f"Scaling Factor: {template['scaling_factor']}x",
                    inline=False
                )
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in room_npcs command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

async def setup(bot):
    """Set up the room commands cog."""
    await bot.add_cog(RoomCommands(bot, bot.services.room_system, bot.services.character_system)) 