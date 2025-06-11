"""
Help system for HCShinobi bot.
Provides interactive help menus and command documentation using Discord's slash commands.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict, Tuple
import logging
import itertools
import asyncio
from discord.ui import Button, View, Select
import random

logger = logging.getLogger(__name__)

class TutorialStep:
    def __init__(self, title: str, content: str, image_url: Optional[str] = None):
        self.title = title
        self.content = content
        self.image_url = image_url

class TutorialNavigationView(View):
    def __init__(self, tutorial_button: 'TutorialButton', current_step: int = 0):
        super().__init__(timeout=300)  # 5 minute timeout
        self.tutorial_button = tutorial_button
        self.current_step = current_step
        self.add_item(PreviousButton())
        self.add_item(NextButton())
        self.add_item(FinishButton())

class PreviousButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            label="Previous",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        view: TutorialNavigationView = self.view
        if view.current_step > 0:
            await view.tutorial_button.show_step(interaction, view.current_step - 1)

class NextButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji="➡️",
            label="Next",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        view: TutorialNavigationView = self.view
        if view.current_step < len(view.tutorial_button.tutorial_steps) - 1:
            await view.tutorial_button.show_step(interaction, view.current_step + 1)

class FinishButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            emoji="✅",
            label="Finish Tutorial",
            row=0
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="Tutorial Complete!",
                description="You've completed the tutorial! Here's what to do next:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next Steps",
                value="1. Create your character with `/character create`\n"
                      "2. Start training with `/training start`\n"
                      "3. Take on missions with `/mission`\n"
                      "4. Join a clan with `/clan join`\n"
                      "5. Visit the shop with `/shop`",
                inline=False
            )
            embed.add_field(
                name="Need Help?",
                value="Use `/help` to see all available commands\n"
                      "Join our support server for assistance\n"
                      "Check the #rules channel for game rules",
                inline=False
            )
            
            try:
                await interaction.edit_original_response(embed=embed, view=None)
            except discord.NotFound:
                try:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                except discord.NotFound:
                    try:
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    except:
                        pass
        except Exception as e:
            print(f"Error in finish tutorial: {e}")
            try:
                await interaction.response.send_message(
                    "An error occurred while completing the tutorial. Please try again.",
                    ephemeral=True
                )
            except:
                pass

class TutorialButton(Button):
    def __init__(self, bot: commands.Bot):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Take the Tutorial",
            emoji="📚",
            row=0
        )
        self.bot = bot
        self.tutorial_steps = [
            {
                "title": "Welcome to HCShinobi!",
                "description": "Let's get you started on your ninja journey.",
                "fields": [
                    ("Getting Started", "Use `/help` to see all available commands\nUse `/character create` to create your character\nUse `/tutorial` to view this guide again", False)
                ]
            },
            {
                "title": "Character Creation",
                "description": "Your character is your ninja identity.",
                "fields": [
                    ("Basic Info", "Choose your name, village, and clan\nSelect your starting stats\nPick your first jutsu", False),
                    ("Stats", "Strength: Affects physical damage\nSpeed: Affects dodge chance\nChakra: Affects jutsu power\nIntelligence: Affects learning speed", False)
                ]
            },
            {
                "title": "Training System",
                "description": "Train to become stronger!",
                "fields": [
                    ("Training Types", "Physical: Increases Strength\nSpeed: Increases Speed\nChakra: Increases Chakra\nMental: Increases Intelligence", False),
                    ("Training Tips", "Training takes real time\nLonger sessions = better rewards\nRest between sessions\nUse `/training start` to begin", False)
                ]
            },
            {
                "title": "Mission System",
                "description": "Take on missions to earn rewards!",
                "fields": [
                    ("Mission Types", "D-Rank: Basic missions\nC-Rank: Moderate difficulty\nB-Rank: Challenging\nA-Rank: Very difficult\nS-Rank: Extreme difficulty", False),
                    ("Rewards", "Experience points\nCurrency\nItems\nReputation", False)
                ]
            },
            {
                "title": "Combat System",
                "description": "Fight other ninja in battle!",
                "fields": [
                    ("Battle Types", "PvP: Fight other players\nPvE: Fight NPCs\nClan Wars: Fight for your clan", False),
                    ("Combat Tips", "Use your jutsu wisely\nManage your chakra\nWatch your health\nUse items when needed", False)
                ]
            }
        ]

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.show_step(interaction, 0)
        except discord.NotFound:
            # If the interaction is not found, try to send a new message
            try:
                await interaction.response.send_message(
                    "The tutorial has expired. Please use `/help` to see the tutorial again.",
                    ephemeral=True
                )
            except discord.NotFound:
                # If we can't send a new message, just log the error
                print("Failed to send tutorial message - interaction expired")

    async def show_step(self, interaction: discord.Interaction, step: int):
        try:
            # Create the embed for this step
            embed = discord.Embed(
                title=self.tutorial_steps[step]["title"],
                description=self.tutorial_steps[step]["description"],
                color=discord.Color.blue()
            )
            
            # Add fields
            for name, value, inline in self.tutorial_steps[step]["fields"]:
                embed.add_field(name=name, value=value, inline=inline)
            
            # Create navigation buttons
            view = TutorialNavigationView(self, step)
            
            # Try to edit the original message first
            try:
                await interaction.edit_original_response(embed=embed, view=view)
            except discord.NotFound:
                # If that fails, try to send a follow-up message
                try:
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                except discord.NotFound:
                    # If that also fails, try to send a new message
                    try:
                        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                    except discord.NotFound:
                        # If all attempts fail, just log the error
                        print("Failed to show tutorial step - interaction expired")
                        
        except Exception as e:
            print(f"Error showing tutorial step: {e}")
            try:
                await interaction.response.send_message(
                    "An error occurred while showing the tutorial. Please try again.",
                    ephemeral=True
                )
            except:
                pass

class CommandExample:
    def __init__(self, command: str, description: str, example: str):
        self.command = command
        self.description = description
        self.example = example

class ManualButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Open Command Manual",
            emoji="📖",
            custom_id="manual_button"
        )
        self.command_examples = {
            "combat": [
                CommandExample("/train", "Start training a skill", "/train ninjutsu"),
                CommandExample("/duel", "Challenge another player", "/duel @player"),
                CommandExample("/jutsu", "View your techniques", "/jutsu list")
            ],
            "character": [
                CommandExample("/profile", "View your character", "/profile"),
                CommandExample("/stats", "Check your stats", "/stats"),
                CommandExample("/specialize", "Choose a path", "/specialize ninjutsu")
            ],
            "missions": [
                CommandExample("/missions", "View available missions", "/missions"),
                CommandExample("/mission_status", "Check progress", "/mission_status"),
                CommandExample("/mission_rewards", "Claim rewards", "/mission_rewards")
            ]
        }

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        select = CommandCategorySelect(self.command_examples)
        view = View()
        view.add_item(select)
        
        embed = discord.Embed(
            title="📖 HCShinobi Command Manual",
            description="Select a category to view detailed command information:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class CommandCategorySelect(Select):
    def __init__(self, command_examples: Dict[str, List[CommandExample]]):
        options = [
            discord.SelectOption(label="Combat Commands", value="combat", emoji="⚔️"),
            discord.SelectOption(label="Character Commands", value="character", emoji="👤"),
            discord.SelectOption(label="Mission Commands", value="missions", emoji="📜")
        ]
        super().__init__(
            placeholder="Choose a command category...",
            options=options,
            custom_id="command_category"
        )
        self.command_examples = command_examples

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        examples = self.command_examples[category]
        
        embed = discord.Embed(
            title=f"📖 {category.title()} Commands",
            description="Here are the available commands and their usage:",
            color=discord.Color.blue()
        )
        
        for example in examples:
            embed.add_field(
                name=f"`{example.command}`",
                value=f"{example.description}\n**Example:** `{example.example}`",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed)

class SupportButton(Button):
    def __init__(self, support_url: str):
        super().__init__(
            style=discord.ButtonStyle.link,
            label="Join Support Server",
            emoji="🛠️",
            url=support_url
        )

class HelpView(View):
    def __init__(self, bot: commands.Bot, support_url: str):
        super().__init__(timeout=None)
        self.add_item(TutorialButton(bot))
        self.add_item(ManualButton())
        self.add_item(SupportButton(support_url))

class HelpCommands(commands.Cog):
    """Provides help and documentation for HCShinobi commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.support_url = "https://discord.gg/hcshinobi"  # Update with your support server URL
        
        # Define command categories
        self.categories: Dict[str, Dict] = {
            "character": {
                "name": "Character Commands",
                "description": "Commands for managing your character",
                "commands": [
                    ("/profile", "View your character profile"),
                    ("/create", "Create a new character"),
                    ("/inventory", "View your inventory")
                ]
            },
            "training": {
                "name": "Training Commands",
                "description": "Commands for training and improving your character",
                "commands": [
                    ("/train", "Start a training session"),
                    ("/training_status", "Check your training progress"),
                    ("/training_history", "View your training history")
                ]
            },
            "mission": {
                "name": "Mission Commands",
                "description": "Commands for missions and quests",
                "commands": [
                    ("/mission_board", "View available missions"),
                    ("/mission_start", "Start a mission"),
                    ("/mission_status", "Check mission progress")
                ]
            },
            "battle": {
                "name": "Battle Commands",
                "description": "Commands for combat and battles",
                "commands": [
                    ("/battle", "Challenge another player"),
                    ("/battle_status", "Check battle status"),
                    ("/battle_history", "View battle history")
                ]
            },
            "shop": {
                "name": "Shop Commands",
                "description": "Commands for shopping and items",
                "commands": [
                    ("/shop", "View the shop"),
                    ("/buy", "Buy items from the shop"),
                    ("/sell", "Sell items to the shop")
                ]
            },
            "clan": {
                "name": "Clan Commands",
                "description": "Commands for clan management",
                "commands": [
                    ("/clan_info", "View clan information"),
                    ("/clan_join", "Join a clan"),
                    ("/clan_leave", "Leave your current clan")
                ]
            }
        }
        logger.info("HelpCommands Cog loaded.")

    def get_welcome_embed(self) -> discord.Embed:
        """Create the welcome embed for the help menu."""
        embed = discord.Embed(
            title="🌀 HCShinobi Help Center",
            description="Welcome to the HCShinobi help system! Here you can learn about all available commands and features.",
            color=discord.Color.blue()
        )
        
        # Add main sections
        embed.add_field(
            name="📚 Command Categories",
            value="Use the buttons below to explore different command categories.",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Getting Started",
            value="1. Create your character with `/create`\n"
                  "2. Start training with `/train`\n"
                  "3. Take on missions with `/mission_board`",
            inline=False
        )
        
        embed.add_field(
            name="❓ Need More Help?",
            value=f"Join our [Support Server]({self.support_url}) for additional assistance!",
            inline=False
        )
        
        return embed

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
        
        # First, get all cogs
        cogs = {cog.qualified_name.lower(): cog for cog in self.bot.cogs.values()}
        
        for cmd in all_commands:
            # Try to find the cog by command name pattern
            cmd_name = cmd.name.lower()
            found_cog = None
            
            # Check if command name matches any cog name
            for cog_name, cog in cogs.items():
                if cmd_name.startswith(cog_name.replace('commands', '')):
                    found_cog = cog
                    break
            
            # If no cog found, use Uncategorized
            if found_cog not in mapping:
                mapping[found_cog] = []
            mapping[found_cog].append(cmd)
            
        return mapping

    @app_commands.command(name="help", description="Get help with HCshinobi commands")
    @app_commands.describe(
        command_or_category="The specific command or category to get help for (e.g., /profile or Character)"
    )
    async def help(self, interaction: discord.Interaction, command_or_category: Optional[str] = None):
        """Provides help for slash commands and categories."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if command_or_category:
                # Check if it's a command name (potentially qualified)
                target_command_name = command_or_category.lower().replace("/", "") # Clean input
                found_command: Optional[app_commands.Command] = None

                for cmd in self.bot.tree.get_commands():
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
                for cog, cmds in self.get_all_commands_by_cog().items():
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
                # Show main help menu with buttons
                embed = self.get_welcome_embed()
                view = HelpView(self.bot, self.support_url)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"Error in /help command: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while fetching help.", ephemeral=True)

    @help.autocomplete('command_or_category')
    async def help_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Provide autocomplete suggestions for the help command."""
        choices = []
        
        # Add categories
        for cat_key, cat_info in self.categories.items():
            if current.lower() in cat_key.lower() or current.lower() in cat_info['name'].lower():
                choices.append(app_commands.Choice(name=cat_info['name'], value=cat_key))
        
        # Add commands
        for cmd in self.bot.tree.get_commands():
            if current.lower() in cmd.name.lower():
                choices.append(app_commands.Choice(name=f"/{cmd.name}", value=cmd.name))
        
        return choices[:25]  # Discord has a limit of 25 choices

async def setup(bot: commands.Bot):
    """Add the help cog to the bot."""
    await bot.add_cog(HelpCommands(bot))
    logger.info("HelpCommands Cog loaded.") 