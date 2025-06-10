"""
Basic commands for the Shinobi Chronicles bot.
"""

import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class BasicCommands(commands.Cog):
    """Essential commands for all shinobi."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="inventory", help="Show your ninja tools and items")
    async def inventory(self, ctx):
        """Display the items you are currently carrying."""
        await ctx.send("Your inventory is currently empty. Visit the shop to purchase ninja tools!")

    @commands.command(name="jutsu", help="List all jutsu you have learned")
    async def jutsu(self, ctx):
        """Display your known jutsu techniques."""
        await ctx.send("You haven't learned any jutsu yet. Train with a sensei to learn new techniques!")

    @commands.command(name="status", help="Check your ninja status and conditions")
    async def status(self, ctx):
        """Show your current health, chakra, and status effects."""
        embed = discord.Embed(
            title=f"{ctx.author.name}'s Status",
            color=discord.Color.green()
        )
        embed.add_field(name="Health", value="100/100", inline=True)
        embed.add_field(name="Chakra", value="100/100", inline=True)
        embed.add_field(name="Status", value="Normal", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="missions", help="View available missions")
    async def missions(self, ctx):
        """Display the current mission board."""
        embed = discord.Embed(
            title="Mission Board",
            description="Available Missions:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="D-Rank: Find Lost Cat",
            value="Help find a villager's missing cat. Reward: 500 Ryo",
            inline=False
        )
        embed.add_field(
            name="C-Rank: Escort Mission",
            value="Escort a merchant to the next village. Reward: 2000 Ryo",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name="team", help="Manage your ninja team")
    async def team(self, ctx, action: str = None, member: discord.Member = None):
        """Create or manage your ninja team.
        
        Parameters:
        -----------
        action: str
            The action to perform (create/invite/leave)
        member: discord.Member
            The team member to invite (if inviting)
        """
        if not action:
            await ctx.send("Usage: !team <create/invite/leave> [@member]")
            return

        if action.lower() == "create":
            await ctx.send("Created a new team! Invite members with !team invite @member")
        elif action.lower() == "invite" and member:
            await ctx.send(f"Invited {member.mention} to your team!")
        elif action.lower() == "leave":
            await ctx.send("You left your current team.")
        else:
            await ctx.send("Invalid team command. Use !help team for more information.")

    @commands.command(name="clan", help="View or join a clan")
    async def clan(self, ctx, action: str = None, clan_name: str = None):
        """Manage your clan membership.
        
        Parameters:
        -----------
        action: str
            The action to perform (join/leave/info)
        clan_name: str
            The name of the clan (if joining)
        """
        if not action:
            await ctx.send("Usage: !clan <join/leave/info> [clan_name]")
            return

        if action.lower() == "join" and clan_name:
            await ctx.send(f"Requested to join clan: {clan_name}")
        elif action.lower() == "leave":
            await ctx.send("You left your current clan.")
        elif action.lower() == "info":
            embed = discord.Embed(
                title="Available Clans",
                description="Notable clans of the ninja world:",
                color=discord.Color.gold()
            )
            embed.add_field(name="Uchiha", value="Masters of the Sharingan", inline=False)
            embed.add_field(name="Hyuga", value="Wielders of the Byakugan", inline=False)
            embed.add_field(name="Uzumaki", value="Known for their powerful chakra", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Invalid clan command. Use !help clan for more information.")

    @commands.command(name="shop", help="View items available for purchase")
    async def shop(self, ctx):
        """Display the ninja tool shop inventory."""
        embed = discord.Embed(
            title="Ninja Tool Shop",
            description="Available Items:",
            color=discord.Color.gold()
        )
        embed.add_field(name="Kunai (50 Ryo)", value="Basic throwing knife", inline=False)
        embed.add_field(name="Shuriken (30 Ryo)", value="Throwing stars", inline=False)
        embed.add_field(name="Smoke Bomb (100 Ryo)", value="Creates a smoke screen", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="balance", help="Check your current Ryo")
    async def balance(self, ctx):
        """Check your current amount of Ryo."""
        await ctx.send(f"{ctx.author.mention}, you have 1000 Ryo.")

    @commands.command(name="train", help="Train to improve your skills")
    async def train(self, ctx, skill: str = None):
        """Train a specific ninja skill.
        
        Parameters:
        -----------
        skill: str
            The skill to train (ninjutsu/taijutsu/genjutsu)
        """
        valid_skills = ["ninjutsu", "taijutsu", "genjutsu"]
        
        if not skill or skill.lower() not in valid_skills:
            await ctx.send(f"Please specify a skill to train: {', '.join(valid_skills)}")
            return

        await ctx.send(f"You spent some time training {skill}. Your skills are improving!")

async def setup(bot):
    """Add the basic commands to the bot."""
    await bot.add_cog(BasicCommands(bot))
    logger.info("Basic commands loaded") 