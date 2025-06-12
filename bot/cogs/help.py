"""
Custom help command for HCShinobi bot.
Provides more intuitive and explanatory command help.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict
import logging
import itertools
import asyncio

logger = logging.getLogger(__name__)

class HelpCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        """Initialize help commands."""
        self.bot = bot
        self.logger = logging.getLogger(__name__)

        # Command categories and descriptions (May need updating based on final cogs)
        # Consider dynamically generating this or ensuring cog names match keys
        self.categories = {
            "charactercommands": { # Match Cog class name (lowercase)
                "description": "Manage your character, view stats, and customize your ninja",
                "emoji": "👤"
            },
            "trainingcommands": { # Match Cog class name
                "description": "Train your character's abilities and skills",
                "emoji": "🏋️"
            },
            "shopcommands": { # Example, add if Shop cog exists
                "description": "Buy and sell items, equipment, and jutsu",
                "emoji": "🏪"
            },
            "battlesystemcommands": { # Match Cog class name
                "description": "Engage in combat with other players or NPCs",
                "emoji": "⚔️"
            },
            "missioncommands": { # Match Cog class name
                "description": "Accept and complete missions for rewards",
                "emoji": "📜"
            },
            # "room": { # Example, add if Room cog exists
            #     "description": "Navigate and interact with the game world",
            #     "emoji": "🏠"
            # },
            "currencycommands": {
                 "description": "Manage your Ryō and view leaderboards",
                 "emoji": "💰"
             },
             "clancommands": {
                 "description": "Manage clans, view members, and leaderboards",
                 "emoji": "⚜️"
             },
             "helpcommands": {
                  "description": "Provides help information for commands",
                  "emoji": "❓"
              }
             # Add other cogs like DevLog, Announcement if desired
        }

    def get_command_help_embed(self, command: app_commands.Command) -> discord.Embed:
        """Create an embed for a specific command's help."""
        embed = discord.Embed(
            title=f"`/{command.qualified_name}`", # Use qualified_name for subcommands
            description=command.description or "No description provided.",
            color=discord.Color.blue()
        )

        # Add parameters if any
        if command.parameters:
            params = "\n".join(f"• `{param.name}`: {param.description or 'No description.'}" for param in command.parameters)
            embed.add_field(name="Parameters", value=params, inline=False)

        # Add parent command if it's a subcommand
        if command.parent:
             embed.set_footer(text=f"Subcommand of /{command.parent.name}")

        return embed

    def get_category_help_embed(self, category_name: str, commands_in_category: List[app_commands.Command]) -> discord.Embed:
        """Create an embed for a category's help."""
        category_info = self.categories.get(category_name.lower(), {})
        embed = discord.Embed(
            title=f"{category_info.get('emoji', '📚')} {category_name.title()} Commands",
            description=category_info.get("description", "Commands related to this category."),
            color=discord.Color.blue()
        )

        # Add commands
        if commands_in_category:
            # Sort commands alphabetically
            sorted_commands = sorted(commands_in_category, key=lambda cmd: cmd.name)
            command_list = "\n".join(f"• `/{cmd.qualified_name}`: {cmd.description or 'No description.'}" for cmd in sorted_commands)
            embed.add_field(name="Available Commands", value=command_list, inline=False)
        else:
            embed.description += "\n\nNo commands found in this category."

        return embed

    def get_all_commands_by_cog(self) -> Dict[Optional[commands.Cog], List[app_commands.Command]]:
        """Helper to get all slash commands grouped by their Cog."""
        # Use bot.tree to get application commands
        all_commands = self.bot.tree.get_commands()
        mapping: Dict[Optional[commands.Cog], List[app_commands.Command]] = {}
        for cmd in all_commands:
            cog = cmd.cog # app_commands.Command stores its cog directly
            if cog not in mapping:
                mapping[cog] = []
            mapping[cog].append(cmd)
        return mapping

    @app_commands.command(name="help", description="Get help with HCshinobi slash commands")
    @app_commands.describe(
        # Changed argument name for clarity
        command_or_category="The specific command or category to get help for (e.g., /profile or Character)"
    )
    async def help(self, interaction: discord.Interaction, command_or_category: Optional[str] = None):
        """Provides help for slash commands and categories."""
        await interaction.response.defer(ephemeral=True)
        all_commands_mapping = self.get_all_commands_by_cog()
        all_app_commands = self.bot.tree.get_commands()

        try:
            if command_or_category:
                # Check if it's a command name (potentially qualified)
                target_command_name = command_or_category.lower().replace("/", "") # Clean input
                found_command: Optional[app_commands.Command] = None

                for cmd in all_app_commands:
                    # Check base command name and qualified name (for subcommands)
                    if cmd.name == target_command_name or cmd.qualified_name == target_command_name:
                        found_command = cmd
                        break
                    # Check subcommands within groups
                    if isinstance(cmd, app_commands.Group):
                         try:
                             sub_cmd = cmd.get_command(target_command_name)
                             if sub_cmd:
                                 found_command = sub_cmd
                                 break
                         except Exception:
                             pass # Ignore if get_command fails for a name

                if found_command:
                    # Show help for the specific command found
                    embed = self.get_command_help_embed(found_command)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                # Check if it's a category name
                target_category_name = command_or_category.lower()
                found_category = False
                for cog, cmds in all_commands_mapping.items():
                    cog_name = getattr(cog, 'qualified_name', 'Uncategorized').lower()
                    # Match against defined categories or cog names
                    if target_category_name == cog_name or target_category_name in self.categories:
                         # Use the display name (from self.categories or Cog name)
                         display_name = getattr(cog, 'qualified_name', 'Uncategorized')
                         embed = self.get_category_help_embed(display_name, cmds)
                         await interaction.followup.send(embed=embed, ephemeral=True)
                         found_category = True
                         break

                if not found_command and not found_category:
                    await interaction.followup.send(f"❌ Command or Category `{command_or_category}` not found.", ephemeral=True)

            else:
                # General help: List categories
                embed = discord.Embed(
                    title="HCshinobi Help",
                    description="Welcome to HCshinobi! Use `/help <command>` or `/help <Category>` for more details.",
                    color=discord.Color.blue()
                )

                # Get commands grouped by cog
                categorized_commands = self.get_all_commands_by_cog()

                # Add fields for each category/cog found
                added_categories = set()
                for cog, cmds in categorized_commands.items():
                    if not cmds: continue # Skip cogs with no registered slash commands

                    cog_name = getattr(cog, 'qualified_name', 'Uncategorized')
                    category_key = cog_name.lower()
                    if category_key in added_categories: continue # Avoid duplicate category listings if cog names clash

                    category_info = self.categories.get(category_key, {})
                    emoji = category_info.get('emoji', '📚')
                    description = category_info.get('description', cog.__doc__ or 'No description.')

                    # List only top-level commands for brevity in general help?
                    # cmd_list = " ".join(sorted([f"`/{cmd.name}`" for cmd in cmds]))
                    # embed.add_field(name=f"{emoji} {cog_name}", value=f"{description}\n*Commands: {cmd_list}*", inline=False)

                    # Or just list the category and its description
                    embed.add_field(name=f"{emoji} {cog_name}", value=description, inline=False)
                    added_categories.add(category_key)

                # Handle commands without a cog if any exist (shouldn't usually happen with good structure)
                if None in categorized_commands and categorized_commands[None]:
                     uncategorized_cmds = categorized_commands[None]
                     cmd_list = " ".join(sorted([f"`/{cmd.name}`" for cmd in uncategorized_cmds]))
                     embed.add_field(name="🔧 Uncategorized", value=cmd_list, inline=False)

                embed.set_footer(text="Use /help <CommandName> or /help <CategoryName>")
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error in /help command: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ An error occurred while fetching help.", ephemeral=True)
            except discord.errors.HTTPException as http_err_fatal:
                self.logger.error(f"HTTP error sending help error followup: {http_err_fatal}", exc_info=True)

    @help.autocomplete('command_or_category')
    async def help_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for the command_or_category parameter."""
        choices = []
        all_commands = self.bot.tree.get_commands()

        # Add Categories first
        for cat_key, cat_info in self.categories.items():
            display_name = cat_key.title() # Use title case for display
            if current.lower() in display_name.lower():
                choices.append(app_commands.Choice(name=f"Category: {display_name}", value=cat_key))

        # Add Commands (including subcommands)
        added_commands = set() # Prevent duplicates if qualified_name == name
        for cmd in all_commands:
             # Add base command
             if current.lower() in cmd.name.lower() and cmd.name not in added_commands:
                 choices.append(app_commands.Choice(name=f"Command: /{cmd.name}", value=cmd.name))
                 added_commands.add(cmd.name)
             # Add qualified name if different (for subcommands)
             if cmd.qualified_name != cmd.name and current.lower() in cmd.qualified_name.lower() and cmd.qualified_name not in added_commands:
                  choices.append(app_commands.Choice(name=f"Command: /{cmd.qualified_name}", value=cmd.qualified_name))
                  added_commands.add(cmd.qualified_name)
             # Check group commands explicitly
             if isinstance(cmd, app_commands.Group):
                 for sub_cmd in cmd.commands:
                      if current.lower() in sub_cmd.qualified_name.lower() and sub_cmd.qualified_name not in added_commands:
                          choices.append(app_commands.Choice(name=f"Command: /{sub_cmd.qualified_name}", value=sub_cmd.qualified_name))
                          added_commands.add(sub_cmd.qualified_name)

        # Limit choices to Discord's max (25)
        return choices[:25]

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCommands(bot))
    logger.info("HelpCommands Cog loaded.") 