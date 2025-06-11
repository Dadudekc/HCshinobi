"""
Discord integration for HCShinobi.
Handles Discord bot setup and integration.
"""
import os
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, TYPE_CHECKING

from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.core.personality_modifiers import PersonalityModifier
from HCshinobi.core.clan_data import get_all_clans, get_clan_rarity
from HCshinobi.bot.config import BotConfig

if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

# Set up the Discord bot
config = BotConfig(
    command_prefix="!",
    application_id=int(os.getenv("DISCORD_APPLICATION_ID", "0")),
    guild_id=int(os.getenv("DISCORD_GUILD_ID", "0")),
    battle_channel_id=int(os.getenv("DISCORD_BATTLE_CHANNEL_ID", "0")),
    online_channel_id=int(os.getenv("DISCORD_ONLINE_CHANNEL_ID", "0")),
    log_level="INFO"
)

# Import HCBot here to avoid circular imports
from HCshinobi.bot.bot import HCBot
client: "HCBot" = HCBot(config=config)
tree = app_commands.CommandTree(client)

# Initialize the clan assignment engine
engine = ClanAssignmentEngine()

@tree.command(
    name="assign_clan",
    description="Assign a clan to yourself based on the weighted system"
)
async def assign_clan(
    interaction: discord.Interaction,
    personality: Optional[str] = None,
    token_boost_clan: Optional[str] = None,
    token_count: Optional[int] = 0
):
    """
    Assign a clan to a Discord user.
    
    Args:
        interaction: Discord interaction object
        personality: Optional personality trait
        token_boost_clan: Optional clan to boost with tokens
        token_count: Number of tokens to spend
    """
    # Verify personality is valid if provided
    if personality and personality not in PersonalityModifier.get_valid_personalities():
        valid_personalities = ", ".join(PersonalityModifier.get_valid_personalities())
        await interaction.response.send_message(
            f"Invalid personality trait. Valid options are: {valid_personalities}",
            ephemeral=True
        )
        return
    
    # Verify clan is valid if provided
    if token_boost_clan and token_boost_clan not in get_all_clans():
        await interaction.response.send_message(
            f"Invalid clan name: {token_boost_clan}",
            ephemeral=True
        )
        return
    
    # Verify token count is valid
    if token_count and (token_count < 0 or token_count > 3):
        await interaction.response.send_message(
            "Token count must be between 0 and 3",
            ephemeral=True
        )
        return
    
    # Defer response since clan assignment might take time
    await interaction.response.defer(ephemeral=False, thinking=True)
    
    # Assign clan
    result = engine.assign_clan(
        player_id=str(interaction.user.id),
        player_name=interaction.user.display_name,
        personality=personality,
        token_boost_clan=token_boost_clan,
        token_count=token_count
    )
    
    # Create response embed
    embed = discord.Embed(
        title="Clan Assignment Result",
        description=f"**{interaction.user.mention}, you have been assigned to the {result['assigned_clan']} clan!**",
        color=0x00ff00
    )
    
    # Add clan rarity
    embed.add_field(
        name="Clan Rarity",
        value=result["clan_rarity"],
        inline=True
    )
    
    # Add personality if provided
    if personality:
        embed.add_field(
            name="Personality",
            value=personality,
            inline=True
        )
    
    # Add token info if tokens were used
    if token_count and token_count > 0:
        embed.add_field(
            name="Token Boost",
            value=f"{token_count} tokens used on {token_boost_clan}",
            inline=True
        )
    
    # Send the result
    await interaction.followup.send(embed=embed)


@tree.command(
    name="clan_populations",
    description="View the current populations of all clans"
)
async def clan_populations(interaction: discord.Interaction):
    """Show the current population of all clans."""
    populations = engine.get_clan_populations()
    
    # Create embed
    embed = discord.Embed(
        title="Current Clan Populations",
        description="Number of active players in each clan",
        color=0x0099ff
    )
    
    # Group clans by rarity
    for rarity in ["Legendary", "Epic", "Rare", "Uncommon", "Common"]:
        clan_list = []
        for clan, count in populations.items():
            clan_rarity = get_clan_rarity(clan)
            if clan_rarity and clan_rarity.value == rarity:
                clan_list.append(f"{clan}: {count}")
        
        if clan_list:
            embed.add_field(
                name=f"{rarity} Clans",
                value="\n".join(clan_list),
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)


@tree.command(
    name="mark_death",
    description="Mark a player as dead (admin only)"
)
@app_commands.checks.has_permissions(administrator=True)
async def mark_death(
    interaction: discord.Interaction,
    user: discord.User,
    clan: str
):
    """
    Mark a player as dead and convert them to an NPC.
    
    Args:
        interaction: Discord interaction object
        user: The user to mark as dead
        clan: The clan the user belonged to
    """
    # Verify clan is valid
    if clan not in get_all_clans():
        await interaction.response.send_message(
            f"Invalid clan name: {clan}",
            ephemeral=True
        )
        return
    
    # Mark player as dead
    npc = engine.mark_player_death(
        player_id=str(user.id),
        player_name=user.display_name,
        clan=clan
    )
    
    # Create response embed
    embed = discord.Embed(
        title="Player Death",
        description=f"**{user.mention} has died and been converted to an NPC**",
        color=0xff0000
    )
    
    embed.add_field(
        name="Clan",
        value=clan,
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)


@client.event
async def on_ready():
    """Called when the bot is ready."""
    await tree.sync()
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print("------")


def run_bot(token: str):
    """
    Run the Discord bot.
    
    Args:
        token: Discord bot token
    """
    client.run(token)


if __name__ == "__main__":
    # Get token from environment variable
    token = os.getenv("DISCORD_BOT_TOKEN")
    
    if not token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set")
        exit(1)
    
    run_bot(token) 