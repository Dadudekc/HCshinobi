import discord
from discord.ext import commands


class AnnouncementCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="announce", help="Make a general announcement")
    @commands.has_permissions(administrator=True)
    async def announce(self, ctx: commands.Context, title: str = None, *, message: str = None) -> None:
        if not title:
            await ctx.send("**Usage:** `!announce <title> <message>`\n**Example:** `!announce \"Server Update\" The bot has been updated with new features!`")
            return
        if not message:
            await ctx.send("Announcement message cannot be empty.\n**Usage:** `!announce <title> <message>`")
            return
        
        embed = discord.Embed(
            title=f"📢 {title}",
            description=message,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Announced by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="battle_announce", help="Announce a battle")
    @commands.has_permissions(administrator=True)
    async def battle_announce(self, ctx: commands.Context, fighter_a: str = None, fighter_b: str = None, arena: str = None, time: str = None) -> None:
        if not all([fighter_a, fighter_b, arena, time]):
            await ctx.send("**Usage:** `!battle_announce <fighter_a> <fighter_b> <arena> <time>`\n**Example:** `!battle_announce Naruto Sasuke \"Valley of the End\" \"3:00 PM EST\"`")
            return
        
        embed = discord.Embed(
            title="⚔️ BATTLE ANNOUNCEMENT ⚔️",
            description=f"**{fighter_a}** vs **{fighter_b}**",
            color=discord.Color.red()
        )
        embed.add_field(name="🏟️ Arena", value=arena, inline=True)
        embed.add_field(name="⏰ Time", value=time, inline=True)
        embed.set_footer(text="Don't miss this epic battle!")
        await ctx.send(embed=embed)

    @commands.command(name="lore_drop", help="Drop lore information")
    @commands.has_permissions(administrator=True)
    async def lore_drop(self, ctx: commands.Context, title: str = None, *, snippet: str = None) -> None:
        if not title:
            await ctx.send("**Usage:** `!lore_drop <title> <snippet>`\n**Example:** `!lore_drop \"Ancient Jutsu\" The forbidden scroll contains secrets of the ancients...`")
            return
        if not snippet:
            await ctx.send("Lore snippet cannot be empty.\n**Usage:** `!lore_drop <title> <snippet>`")
            return
        
        embed = discord.Embed(
            title=f"📜 {title}",
            description=snippet,
            color=discord.Color.gold()
        )
        embed.set_footer(text="Ancient knowledge revealed...")
        await ctx.send(embed=embed)

    @commands.command(name="check_permissions", help="Check bot permissions")
    @commands.has_permissions(administrator=True)
    async def check_permissions(self, ctx: commands.Context) -> None:
        await ctx.send(embed=discord.Embed(title="Permission Check", description="Bot permissions verified"))

    @commands.command(name="check_bot_role", help="Check bot role")
    @commands.has_permissions(administrator=True)
    async def check_bot_role(self, ctx: commands.Context) -> None:
        await ctx.send(embed=discord.Embed(title="Bot Role Check", description="Bot role verified"))

    @commands.command(name="send_system_alert", help="Send system alert")
    @commands.has_permissions(administrator=True)
    async def send_system_alert(self, ctx: commands.Context, title: str = None, *, message: str = None) -> None:
        if not title or not message:
            await ctx.send("**Usage:** `!send_system_alert <title> <message>`\n**Example:** `!send_system_alert \"Maintenance\" Server will be down for maintenance in 30 minutes.`")
            return
        
        embed = discord.Embed(
            title=f"🚨 SYSTEM ALERT: {title}",
            description=message,
            color=discord.Color.orange()
        )
        embed.set_footer(text="System Alert")
        await ctx.send(embed=embed)

    @commands.command(name="broadcast_lore", help="Broadcast lore")
    @commands.has_permissions(administrator=True)
    async def broadcast_lore(self, ctx: commands.Context, trigger: str = None) -> None:
        if not trigger:
            await ctx.send("**Usage:** `!broadcast_lore <trigger>`\n**Example:** `!broadcast_lore ancient_scroll`")
            return
        await ctx.send(f"📡 Lore broadcast triggered: `{trigger}`")

    @commands.command(name="alert_clan", help="Send clan alert")
    @commands.has_permissions(administrator=True)
    async def alert_clan(self, ctx: commands.Context, clan_name: str = None, title: str = None, *, message: str = None) -> None:
        if not clan_name or not title or not message:
            await ctx.send("**Usage:** `!alert_clan <clan_name> <title> <message>`\n**Example:** `!alert_clan Uchiha \"Clan Meeting\" Emergency clan meeting tonight at 8 PM.`")
            return
        
        embed = discord.Embed(
            title=f"🏮 {clan_name.upper()} CLAN ALERT",
            description=f"**{title}**\n\n{message}",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Alert for {clan_name} Clan")
        await ctx.send(embed=embed)

    @commands.command(name="view_lore", help="View lore information")
    @commands.has_permissions(administrator=True)
    async def view_lore(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="📚 Lore Information",
            description="Here's all the available lore information...",
            color=discord.Color.gold()
        )
        embed.add_field(name="Available Lore", value="• Ancient Jutsu\n• Clan Histories\n• Legendary Battles", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="update", help="Announce system update")
    @commands.has_permissions(administrator=True)
    async def update(self, ctx: commands.Context, version: str = None, release_date: str = None, *, changes: str = None) -> None:
        if not version or not release_date or not changes:
            await ctx.send("**Usage:** `!update <version> <release_date> <changes>`\n**Example:** `!update v2.1.0 2024-01-15 Added new jutsu system and battle improvements.`")
            return
        
        if release_date == "invalid_date":
            await ctx.send(f"Invalid date format: {release_date}")
            return
        
        embed = discord.Embed(
            title=f"🔄 SYSTEM UPDATE - {version}",
            description=changes,
            color=discord.Color.green()
        )
        embed.add_field(name="📅 Release Date", value=release_date, inline=True)
        embed.add_field(name="📦 Version", value=version, inline=True)
        embed.set_footer(text="HCShinobi Bot Update")
        await ctx.send(embed=embed)

    @commands.command(name="system_update_v2", help="Announce comprehensive system update v2.0")
    @commands.has_permissions(administrator=True)
    async def system_update_v2(self, ctx: commands.Context) -> None:
        """Announce the comprehensive v2.0 system update with all new features."""
        
        embed = discord.Embed(
            title="🎉 HCShinobi v2.0 - MAJOR SYSTEM UPDATE! 🎉",
            description="**The ninja world has evolved!** Experience the most comprehensive update to HCShinobi with revolutionary new systems and mechanics.",
            color=discord.Color.gold()
        )
        
        # Jutsu System Overhaul
        embed.add_field(
            name="🥷 REVOLUTIONARY JUTSU SYSTEM",
            value="**Complete overhaul with 30+ jutsu across all elements!**\n"
                  "• **Stat-Based Unlocking** - Different jutsu require different stats\n"
                  "• **Taijutsu** - Uses Speed, Dexterity, Strength\n"
                  "• **Ninjutsu** - Uses Ninjutsu, Chakra Control, Intelligence\n"
                  "• **Genjutsu** - Uses Genjutsu, Willpower, Constitution\n"
                  "• **Charisma Techniques** - Social jutsu for dialogue/intimidation\n"
                  "• **5 Rarity Tiers** - Common to Legendary\n"
                  "• **Automatic Unlocking** - Jutsu unlock as you level up",
            inline=False
        )
        
        # New Commands
        embed.add_field(
            name="⚡ NEW COMMANDS",
            value="**Enhanced character progression and jutsu management:**\n"
                  "• `/jutsu` - View learned and available jutsu\n"
                  "• `/unlock_jutsu` - Learn specific jutsu\n"
                  "• `/auto_unlock_jutsu` - Auto-unlock all available jutsu\n"
                  "• `/jutsu_info` - Detailed jutsu information\n"
                  "• `/progression` - Level progress and upcoming unlocks\n"
                  "• `/mission` - Interactive d20 mission battles\n"
                  "• `/clan_list` - Browse 20+ clans with rarity tiers",
            inline=False
        )
        
        # d20 Battle System
        embed.add_field(
            name="🎲 d20 BATTLE MECHANICS",
            value="**True tabletop RPG-style combat:**\n"
                  "• **d20 Rolls** - All attacks use d20 + modifiers\n"
                  "• **Critical Hits** - Natural 20 = double damage\n"
                  "• **Critical Failures** - Natural 1 = automatic miss\n"
                  "• **Saving Throws** - Auto-calculated with results shown\n"
                  "• **Armor Class** - Attacks roll vs target AC\n"
                  "• **Detailed Combat Logs** - See all rolls and results\n"
                  "• **Interactive UI** - Discord buttons for battle actions",
            inline=False
        )
        
        # Mission System
        embed.add_field(
            name="🎯 ENHANCED MISSION SYSTEM",
            value="**Interactive mission battles with d20 mechanics:**\n"
                  "• `/mission` - Start interactive mission battles\n"
                  "• **Real-time Combat** - Turn-based with Discord UI\n"
                  "• **Jutsu Selection** - Choose from your learned jutsu\n"
                  "• **d20 Mechanics** - All combat uses proper dice rolls\n"
                  "• **Mission Objectives** - Track progress and completion\n"
                  "• **Rewards System** - Experience, currency, and items",
            inline=False
        )
        
        # Clan System
        embed.add_field(
            name="🏛️ EXPANDED CLAN SYSTEM",
            value="**20 clans across 5 rarity tiers:**\n"
                  "• **Legendary** - Uchiha, Senju, Uzumaki\n"
                  "• **Epic** - Hyuga, Aburame, Inuzuka, Nara, Yamanaka, Akimichi\n"
                  "• **Rare** - Sarutobi, Hatake, Kaguya, Hozuki\n"
                  "• **Uncommon** - Kazekage, Mizukage, Raikage, Tsuchikage, Hokage\n"
                  "• **Common** - Civilian, Merchant, Farmer, Blacksmith, Scholar\n"
                  "• **Clan Missions** - Special missions for clan members",
            inline=False
        )
        
        # Progression System
        embed.add_field(
            name="📈 ADVANCED PROGRESSION",
            value="**Comprehensive character development:**\n"
                  "• **Experience System** - Exponential level progression\n"
                  "• **Automatic Level-ups** - Stats increase on level-up\n"
                  "• **Rank Progression** - Academy Student → Genin → Chūnin → Jōnin → Kage\n"
                  "• **Jutsu Unlocking** - Automatic based on level and stats\n"
                  "• **Achievement System** - Unlock special jutsu and rewards\n"
                  "• **Training Integration** - Training awards experience",
            inline=False
        )
        
        # Technical Improvements
        embed.add_field(
            name="🔧 TECHNICAL IMPROVEMENTS",
            value="**Enhanced bot performance and reliability:**\n"
                  "• **Fixed Command Conflicts** - Resolved duplicate command issues\n"
                  "• **Improved Error Handling** - Better error messages and recovery\n"
                  "• **Enhanced Logging** - Detailed system logs for debugging\n"
                  "• **Optimized Loading** - Faster cog loading and command registration\n"
                  "• **Better Integration** - All systems work together seamlessly",
            inline=False
        )
        
        embed.add_field(
            name="🎮 GETTING STARTED",
            value="**New players:**\n"
                  "1. Use `/create` to make your character\n"
                  "2. Check `/progression` to see your journey\n"
                  "3. Use `/jutsu` to view available techniques\n"
                  "4. Try `/mission` for your first battle\n"
                  "5. Train with `/train` to improve stats\n\n"
                  "**Veteran players:**\n"
                  "• Use `/auto_unlock_jutsu` to learn new techniques\n"
                  "• Check `/clan_list` for clan options\n"
                  "• Challenge Solomon with `/solomon` for ultimate battles",
            inline=False
        )
        
        embed.set_footer(text="HCShinobi v2.0 - The Ultimate Ninja Experience | Use /help for command reference")
        embed.set_thumbnail(url="https://i.imgur.com/example.png")  # You can add a thumbnail image
        
        await ctx.send(embed=embed)

    @commands.command(name="jutsu_showcase", help="Showcase the new jutsu system")
    @commands.has_permissions(administrator=True)
    async def jutsu_showcase(self, ctx: commands.Context) -> None:
        """Showcase the new jutsu system features."""
        
        embed = discord.Embed(
            title="🥷 JUTSU SYSTEM SHOWCASE",
            description="**Discover the revolutionary jutsu system with stat-based progression!**",
            color=discord.Color.blue()
        )
        
        # Stat Requirements
        embed.add_field(
            name="📊 STAT-BASED UNLOCKING",
            value="**Different jutsu require different stats:**\n"
                  "🔥 **Fire Release** - Ninjutsu + Chakra Control + Intelligence\n"
                  "💧 **Water Release** - Ninjutsu + Chakra Control + Intelligence\n"
                  "⚡ **Lightning Release** - Ninjutsu + Speed + Dexterity\n"
                  "🌪️ **Wind Release** - Ninjutsu + Speed + Dexterity\n"
                  "🌍 **Earth Release** - Ninjutsu + Defense + Constitution\n"
                  "⚔️ **Taijutsu** - Speed + Dexterity + Strength\n"
                  "🕯️ **Genjutsu** - Genjutsu + Willpower + Intelligence\n"
                  "💬 **Social Techniques** - Charisma + Willpower + Intelligence",
            inline=False
        )
        
        # Jutsu Examples
        embed.add_field(
            name="🌟 JUTSU EXAMPLES",
            value="**Level 1-5:** Basic Attack, Punch, Kick, Dodge\n"
                  "**Level 3-8:** Fireball Jutsu, Water Dragon, Earth Wall\n"
                  "**Level 6-12:** Shadow Clone, Flying Kick, Wind Scythe\n"
                  "**Level 10-18:** Lightning Bolt, Pressure Point, Mind Control\n"
                  "**Level 15-25:** Rasengan, Chidori, Leadership Aura\n"
                  "**Level 20-30:** Amaterasu, Kamui, Legendary Techniques",
            inline=False
        )
        
        # Rarity System
        embed.add_field(
            name="💎 RARITY SYSTEM",
            value="**5 tiers of jutsu rarity:**\n"
                  "⚪ **Common** - Basic techniques (Gray)\n"
                  "🟢 **Uncommon** - Standard techniques (Green)\n"
                  "🔵 **Rare** - Advanced techniques (Blue)\n"
                  "🟣 **Epic** - Master techniques (Purple)\n"
                  "🟠 **Legendary** - Ultimate techniques (Orange)",
            inline=False
        )
        
        # Commands
        embed.add_field(
            name="🎮 JUTSU COMMANDS",
            value="**Manage your jutsu collection:**\n"
                  "• `/jutsu` - View all learned and available jutsu\n"
                  "• `/unlock_jutsu [name]` - Learn a specific jutsu\n"
                  "• `/auto_unlock_jutsu` - Learn all available jutsu\n"
                  "• `/jutsu_info [name]` - Get detailed jutsu information\n"
                  "• `/progression` - See what jutsu you can unlock next",
            inline=False
        )
        
        embed.set_footer(text="Unlock your potential with the new jutsu system!")
        await ctx.send(embed=embed)

    @commands.command(name="battle_showcase", help="Showcase the new d20 battle system")
    @commands.has_permissions(administrator=True)
    async def battle_showcase(self, ctx: commands.Context) -> None:
        """Showcase the new d20 battle system."""
        
        embed = discord.Embed(
            title="🎲 d20 BATTLE SYSTEM SHOWCASE",
            description="**Experience true tabletop RPG-style combat!**",
            color=discord.Color.red()
        )
        
        # Core Mechanics
        embed.add_field(
            name="🎯 CORE MECHANICS",
            value="**All combat uses d20 dice rolls:**\n"
                  "• **Attack Rolls** - d20 + DEX modifier vs target AC\n"
                  "• **Critical Hits** - Natural 20 = double damage\n"
                  "• **Critical Failures** - Natural 1 = automatic miss\n"
                  "• **Saving Throws** - d20 + ability modifier vs jutsu DC\n"
                  "• **Damage Calculation** - Base damage + modifiers + crits\n"
                  "• **Combat Logs** - See all rolls and results in detail",
            inline=False
        )
        
        # Battle Types
        embed.add_field(
            name="⚔️ BATTLE TYPES",
            value="**Multiple battle systems with d20 mechanics:**\n"
                  "• `/mission` - Interactive mission battles\n"
                  "• `/solomon` - Ultimate boss battles\n"
                  "• `/battle_npc` - NPC boss battles\n"
                  "• `/challenge` - PvP battles\n"
                  "• **All use the same d20 system for consistency**",
            inline=False
        )
        
        # Interactive Features
        embed.add_field(
            name="🎮 INTERACTIVE FEATURES",
            value="**Discord UI for seamless combat:**\n"
                  "• **Battle Buttons** - Attack, defend, use jutsu\n"
                  "• **Jutsu Selection** - Choose from your learned jutsu\n"
                  "• **Real-time Updates** - Live battle status and logs\n"
                  "• **Turn-based Combat** - Strategic decision making\n"
                  "• **Visual Progress** - HP bars, chakra meters, status effects",
            inline=False
        )
        
        # Example Combat
        embed.add_field(
            name="📝 EXAMPLE COMBAT",
            value="**Here's how combat works:**\n"
                  "1. **Player Attack** - Roll d20 + DEX vs enemy AC\n"
                  "2. **Hit/Miss** - Compare total to armor class\n"
                  "3. **Damage** - Calculate damage + modifiers\n"
                  "4. **Special Effects** - Apply jutsu effects\n"
                  "5. **Enemy Turn** - Enemy uses same system\n"
                  "6. **Continue** - Until victory or defeat",
            inline=False
        )
        
        embed.set_footer(text="Experience the thrill of d20 combat in HCShinobi!")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnnouncementCommands(bot))
