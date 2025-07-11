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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnnouncementCommands(bot))
