import discord
from discord import app_commands
from discord.ext import commands
import logging
import traceback # For logging errors

# Assume systems/models are correctly typed/imported
# from HCshinobi.core.currency_system import CurrencySystem
# from HCshinobi.core.battle_system import BattleSystem
# from HCshinobi.core.clan_system import ClanSystem
# from HCshinobi.core.lore_system import LoreSystem
# from HCshinobi.bot.bot import HCShinobiBot

logger = logging.getLogger(__name__)

@app_commands.checks.has_permissions(administrator=True)
class AdminCommands(commands.Cog):
    """Cog for administrative commands."""

    def __init__(self, bot: 'HCShinobiBot', currency_system, battle_system, clan_system):
        self.bot = bot
        self.currency_system = currency_system
        self.battle_system = battle_system
        self.clan_system = clan_system
        # self.lore_system = lore_system # Commented out
        logger.info("AdminCommands Cog initialized.")
        
    # --- Error Handling for Admin commands ---
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            # Check if response already sent before sending again
            if not interaction.response.is_done():
                 await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            else:
                 # If response is done (e.g., deferred), use followup
                 await interaction.followup.send("❌ You do not have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in Admin command '{interaction.command.name if interaction.command else 'unknown'}': {error}")
            traceback.print_exception(type(error), error, error.__traceback__)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)

    # --- Commands ---

    @app_commands.command(name="add_tokens", description="[Admin] Add tokens (e.g., Ryō) to a user.")
    @app_commands.describe(user="The user to add tokens to.", amount="The amount of tokens to add.")
    async def add_tokens(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Adds a specified amount of currency to a user."""
        if amount <= 0:
             await interaction.response.send_message("Amount must be positive.", ephemeral=True)
             return
             
        success = await self.currency_system.add_balance_and_save(str(user.id), amount)
        if success:
            await interaction.response.send_message(f"✅ Successfully added {amount:,} tokens to {user.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to add tokens. Check logs.", ephemeral=True)

    # Removed duplicate admin_clear_battle command - it resides in BattleSystemCommands
    # @app_commands.command(name="admin_clear_battle", description="[Admin] Force clear a player's active battle.")
    # @app_commands.describe(user="The user whose battle to clear.")
    # async def admin_clear_battle(self, interaction: discord.Interaction, user: discord.User):
    #     """Forcefully clears a player's active battle state."""
    #     success = await self.battle_system.admin_clear_battle(str(user.id))
    #     if success:
    #         await interaction.response.send_message(f"✅ Successfully cleared active battle for {user.mention}.", ephemeral=True)
    #     else:
    #         await interaction.response.send_message(f"❌ Failed to clear battle for {user.mention}. They might not be in one.", ephemeral=True)

    @app_commands.command(name="alert_clan", description="[Admin] Send an alert to a specific clan.")
    @app_commands.describe(clan_name="The name of the clan.", message="The message to send.")
    async def alert_clan(self, interaction: discord.Interaction, clan_name: str, message: str):
        """Sends a DM alert to all members of a specified clan."""
        clan_info = await self.clan_system.get_clan_info(clan_name)
        if not clan_info:
            await interaction.response.send_message(f"❌ Clan '{clan_name}' not found.", ephemeral=True)
            return

        member_ids = clan_info.get('members', [])
        sent_count = 0
        failed_count = 0

        alert_prefix = f"**[Clan Alert - {clan_name}]**\n"
        full_message = alert_prefix + message

        for member_id in member_ids:
            try:
                member = await self.bot.fetch_user(int(member_id))
                if member and not member.bot:
                    await member.send(full_message)
                    sent_count += 1
            except (discord.NotFound, discord.Forbidden):
                logger.warning(f"Could not send alert DM to user ID: {member_id} (Forbidden or Not Found)")
                failed_count += 1
            except Exception as e:
                 logger.error(f"Error sending alert DM to user ID {member_id}: {e}")
                 failed_count += 1
                 
        await interaction.response.send_message(f"✅ Alert sent to {sent_count} members of {clan_name}. ({failed_count} failed attempts).", ephemeral=True)
        
    # Announce and Battle Announce are assumed to be in AnnouncementCommands cog

    # Comment out broadcast_lore command
    # @app_commands.command(name="broadcast_lore", description="[Admin] Broadcast a lore entry to the server.")
    # @app_commands.describe(lore_id="The ID of the lore entry to broadcast.")
    # async def broadcast_lore(self, interaction: discord.Interaction, lore_id: str):
    #     """Broadcasts a lore entry to a default channel in all guilds."""
    #     lore_entry = await self.lore_system.get_lore_entry(lore_id)
    #     if not lore_entry:
    #         await interaction.response.send_message(f"❌ Lore entry '{lore_id}' not found.", ephemeral=True)
    #         return
    # 
    #     # Build Embed (simple example)
    #     embed = discord.Embed(title=f"📜 Lore: {lore_entry.get('title', lore_id)}", description=lore_entry.get('content', '...'))
    #     if image := lore_entry.get('image_url'):
    #         embed.set_image(url=image)
    # 
    #     sent_to_guilds = 0
    #     # Find a suitable channel (e.g., first text channel) in each guild
    #     for guild in self.bot.guilds:
    #         target_channel = discord.utils.find(lambda c: isinstance(c, discord.TextChannel) and c.permissions_for(guild.me).send_messages, guild.text_channels)
    #         if target_channel:
    #             try:
    #                 await target_channel.send(embed=embed)
    #                 sent_to_guilds += 1
    #             except discord.Forbidden:
    #                 logger.warning(f"Missing permissions to send broadcast in {target_channel.name} ({guild.name})")
    #             except Exception as e:
    #                  logger.error(f"Failed to send broadcast to {guild.name}: {e}")
    #                  
    #     await interaction.response.send_message(f"✅ Lore entry '{lore_id}' broadcasted to {sent_to_guilds} guild(s).", ephemeral=True)

    @app_commands.command(name="check_bot_role", description="[Admin] Check the bot's roles and permissions.")
    async def check_bot_role(self, interaction: discord.Interaction):
        """Displays the bot's roles and highest permissions in the current guild."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
            
        bot_member = interaction.guild.me
        roles = [role.name for role in bot_member.roles if role != interaction.guild.default_role]
        permissions = bot_member.guild_permissions

        embed = discord.Embed(title="🤖 Bot Roles and Permissions", color=discord.Color.blue())
        embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
        
        # Format permission names
        perms_list = [perm.replace('_', ' ').title() for perm, value in permissions if value]
        embed.add_field(name="Guild Permissions", value=", ".join(perms_list) if perms_list else "None", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="check_permissions", description="[Admin] Check the bot's permissions in this channel.")
    async def check_permissions(self, interaction: discord.Interaction):
        """Checks and displays the bot's specific permissions in the interaction channel."""
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command must be used in a server text channel.", ephemeral=True)
            return
            
        bot_member = interaction.guild.me
        channel_perms = interaction.channel.permissions_for(bot_member)

        embed = discord.Embed(title=f"🔑 Bot Permissions in #{interaction.channel.name}", color=discord.Color.orange())
        
        # Example permissions to check
        perms_to_check = [
            'send_messages', 'embed_links', 'attach_files', 'read_message_history', 'manage_messages'
        ]
        perm_desc = "\n".join([f"{perm.replace('_', ' ').title()}: {'Yes' if getattr(channel_perms, perm) else 'No'}" for perm in perms_to_check])
        
        embed.description = perm_desc
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: 'HCShinobiBot'):
    if not hasattr(bot, 'services'):
        logger.error("Service container not found on bot object.")
        return
        
    currency_system = getattr(bot.services, 'currency_system', None)
    battle_system = getattr(bot.services, 'battle_system', None)
    clan_system = getattr(bot.services, 'clan_system', None)
    # lore_system = getattr(bot.services, 'lore_system', None) # Commented out

    # Adjust dependency check
    if not all([currency_system, battle_system, clan_system]): 
        logger.error("One or more required systems not found in services for AdminCommands.")
        return
        
    # Adjust cog instantiation
    await bot.add_cog(AdminCommands(bot, currency_system, battle_system, clan_system))
    logger.info("AdminCommands Cog loaded successfully.") 