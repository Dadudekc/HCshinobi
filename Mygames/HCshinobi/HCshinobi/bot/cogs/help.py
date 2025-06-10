"""
Custom help command for HCShinobi bot.
Provides more intuitive and explanatory command help.
"""

import discord
from discord.ext import commands
from typing import Optional, List
import logging
import itertools

logger = logging.getLogger(__name__)

class ShinobiHelpCommand(commands.HelpCommand):
    """Custom help command with enhanced formatting and explanations."""

    def __init__(self):
        super().__init__(
            command_attrs={
                'name': 'help',
                'help': 'Shows this help message or information about a specific command.',
                'aliases': ['h', '?']
            }
        )
        self.paginator = commands.Paginator(prefix='', suffix='', max_size=2000)

    async def send_pages(self):
        """Send the help pages to the channel."""
        destination = self.get_destination()
        embed = discord.Embed(
            title="Shinobi Chronicles Help",
            color=discord.Color.blue()
        )
        
        for page in self.paginator.pages:
            if len(embed.description or '') + len(page) > 4096:
                await destination.send(embed=embed)
                embed = discord.Embed(
                    title="Shinobi Chronicles Help (Continued)",
                    color=discord.Color.blue()
                )
            embed.description = (embed.description or '') + page

        if embed.description:
            await destination.send(embed=embed)

    def get_command_signature(self, command):
        """Get the command signature with proper formatting."""
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = f'[{command.name}|{aliases}]'
            if parent:
                fmt = f'{parent} {fmt}'
            alias = fmt
        else:
            alias = command.name if not parent else f'{parent} {command.name}'
        return f'{self.context.clean_prefix}{alias} {command.signature}'

    async def send_bot_help(self, mapping):
        """Send the main help message with all commands."""
        ctx = self.context
        bot = ctx.bot

        # Add welcome message
        self.paginator.add_line("# Welcome to Shinobi Chronicles!\n")
        
        # List available regular commands
        self.paginator.add_line("## Regular Commands")
        self.paginator.add_line("Use these commands with the `!` prefix:\n")

        # Group commands by category
        no_category = '\u200bNo Category'
        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog is not None else no_category

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Add each category and its commands
        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name)
            if category == no_category:
                self.paginator.add_line('### Miscellaneous Commands')
            else:
                self.paginator.add_line(f'### {category}')
            
            for command in commands:
                name = command.name
                if command.help:
                    help_text = command.help
                else:
                    help_text = "No description available"
                
                # Format command entry with signature and help text
                signature = self.get_command_signature(command)
                self.paginator.add_line(f"• `{signature}`")
                self.paginator.add_line(f"  └─ {help_text}\n")

        # List available slash commands
        self.paginator.add_line("## Slash Commands")
        self.paginator.add_line("The following slash commands are available:\n")

        # Get all application commands
        if hasattr(bot, 'tree'):
            for cmd in bot.tree.get_commands():
                self.paginator.add_line(f"• `/{cmd.name}`")
                if cmd.description:
                    self.paginator.add_line(f"  └─ {cmd.description}\n")

        # Add usage instructions
        self.paginator.add_line("## Usage Tips")
        self.paginator.add_line("• Type `!help <command>` for detailed help on a specific command")
        self.paginator.add_line("• Type `!help <category>` for help on a category of commands")
        self.paginator.add_line("• Type `/` to see all available slash commands")
        self.paginator.add_line("• Most commands can be used in any channel")

        await self.send_pages()

    async def send_command_help(self, command):
        """Send help for a specific command."""
        embed = discord.Embed(
            title=f"Command: {command.name}",
            color=discord.Color.blue()
        )

        if command.help:
            embed.description = command.help

        # Add command signature
        embed.add_field(
            name="Usage",
            value=f"```{self.get_command_signature(command)}```",
            inline=False
        )

        # Add aliases if any
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False
            )

        # Add examples if available
        if hasattr(command, 'examples'):
            examples = "\n".join(f"• `{self.context.clean_prefix}{example}`" for example in command.examples)
            embed.add_field(
                name="Examples",
                value=examples,
                inline=False
            )

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        """Send help for a command group."""
        embed = discord.Embed(
            title=f"Command Group: {group.name}",
            color=discord.Color.blue()
        )

        if group.help:
            embed.description = group.help

        # Add command signature
        embed.add_field(
            name="Usage",
            value=f"```{self.get_command_signature(group)}```",
            inline=False
        )

        # Add subcommands
        filtered = await self.filter_commands(group.commands, sort=True)
        if filtered:
            subcommands = "\n".join(
                f"• `{self.get_command_signature(cmd)}` - {cmd.help or 'No description available'}"
                for cmd in filtered
            )
            embed.add_field(
                name="Subcommands",
                value=subcommands,
                inline=False
            )

        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        """Send help for a specific cog/category."""
        embed = discord.Embed(
            title=f"Category: {cog.qualified_name}",
            description=cog.description or "No category description available.",
            color=discord.Color.blue()
        )

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        if filtered:
            for command in filtered:
                signature = self.get_command_signature(command)
                help_text = command.help or "No description available"
                embed.add_field(
                    name=signature,
                    value=help_text,
                    inline=False
                )
        else:
            embed.add_field(
                name="No Commands",
                value="This category has no available commands.",
                inline=False
            )

        await self.get_destination().send(embed=embed)

async def setup(bot):
    """Add the help command to the bot."""
    bot.help_command = ShinobiHelpCommand()
    logger.info("Custom help command loaded") 