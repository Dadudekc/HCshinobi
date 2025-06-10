"""Management script for HCshinobi."""
import click
import logging
from discord.ext import commands
from dreamos.services.command_group_binder import validate_command_map

@click.group()
def cli():
    """HCshinobi management commands."""
    pass

@cli.command()
def validate_commands():
    """Validate the command map and check for potential issues."""
    # Initialize bot (without actually running it)
    bot = commands.Bot(command_prefix="!")
    
    # Load all cogs
    bot.load_extension("bot.cogs.characters")
    bot.load_extension("bot.cogs.training")
    bot.load_extension("bot.cogs.shop")
    bot.load_extension("bot.cogs.room")
    bot.load_extension("bot.cogs.battle")
    bot.load_extension("bot.cogs.mission")
    bot.load_extension("bot.cogs.help")
    
    # Validate command map
    results = validate_command_map(bot)
    
    # Print results
    if results["duplicates"]:
        click.echo("⚠️ Duplicate commands found:")
        for cmd, locations in results["duplicates"].items():
            click.echo(f"  - {cmd}: {', '.join(locations)}")
            
    if results["missing_bindings"]:
        click.echo("⚠️ Missing group bindings:")
        for group in results["missing_bindings"]:
            click.echo(f"  - {group}")
            
    if results["unused_groups"]:
        click.echo("⚠️ Unused command groups:")
        for group in results["unused_groups"]:
            click.echo(f"  - {group}")
            
    if not any([results["duplicates"], results["missing_bindings"], results["unused_groups"]]):
        click.echo("✅ Command map validation passed!")

if __name__ == "__main__":
    cli() 