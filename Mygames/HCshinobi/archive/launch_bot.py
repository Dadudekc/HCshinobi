#!/usr/bin/env python
"""
Launcher script for HCShinobi bot that fixes import conflicts.
This script ensures the package is properly installed before running.
"""
import sys
import os
import subprocess
import shutil
import tempfile
import site
from pathlib import Path
import time

# ANSI colors for Windows terminals
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_color(text, color):
    """Print colored text."""
    print(f"{color}{text}{Colors.END}")

def create_temp_environment():
    """
    Create a temporary environment where discord.py can be properly imported.
    This works by creating a temporary directory and installing discord.py there.
    """
    print_color("Creating a clean temporary environment...", Colors.BLUE)
    temp_dir = tempfile.mkdtemp(prefix="hcshinobi_")
    print(f"Temporary directory created: {temp_dir}")
    
    # Create a Python script that will run the bot with modified path
    runner_script = os.path.join(temp_dir, "run_with_discord.py")
    
    with open(runner_script, "w") as f:
        f.write("""
import sys
import os
import re
import time
import threading

# Set up color codes
class Colors:
    GREEN = '\\033[92m'
    YELLOW = '\\033[93m'
    RED = '\\033[91m'
    BLUE = '\\033[94m'
    MAGENTA = '\\033[95m'
    CYAN = '\\033[96m'
    BOLD = '\\033[1m'
    UNDERLINE = '\\033[4m'
    END = '\\033[0m'

def print_color(text, color):
    print(f"{color}{text}{Colors.END}")

# Add the site-packages to the path
if 'DISCORD_SITE_PACKAGES' in os.environ:
    sys.path.insert(0, os.environ['DISCORD_SITE_PACKAGES'])

# Remove the current directory from path to avoid importing local discord
if '' in sys.path:
    sys.path.remove('')

# Try to import discord to verify
try:
    import discord
    from discord.ext import commands
    print_color(f"Successfully imported discord.py from {discord.__file__}", Colors.GREEN)
except ImportError as e:
    print_color(f"ERROR: Failed to import discord: {e}", Colors.RED)
    sys.exit(1)

# Channel ID where the bot should post its online status
BATTLE_CHANNEL_ID = 1355761212343975966

# Flag to ensure we only post the status message once
status_posted = False

# Create a listener for the bot's ready event
class BotReadyListener:
    def __init__(self):
        self.bot_ready = False
        
    async def on_ready_handler(self, bot):
        """Handle the bot's ready event"""
        global status_posted
        if status_posted:
            return
            
        print_color("\\n" + "=" * 50, Colors.BOLD)
        print_color("DISCORD BOT IS NOW ONLINE!", Colors.GREEN + Colors.BOLD)
        print_color(f"Bot Name: {bot.user.name}", Colors.CYAN)
        print_color(f"Bot ID: {bot.user.id}", Colors.CYAN)
        
        guild_count = len(bot.guilds)
        print_color(f"Connected to {guild_count} Discord server(s)", Colors.CYAN)
        
        # Post status message to the specified channel
        try:
            channel = bot.get_channel(BATTLE_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="🟢 Bot is Online",
                    description="The HCShinobi battle system is now online and ready for commands!",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Bot started at {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                await channel.send(embed=embed)
                print_color(f"Status message posted to channel ID: {BATTLE_CHANNEL_ID}", Colors.GREEN)
            else:
                print_color(f"WARNING: Could not find channel with ID {BATTLE_CHANNEL_ID}", Colors.YELLOW)
                print_color("Make sure the bot has access to this channel.", Colors.YELLOW)
                print_color("The bot is still online but no status message was posted.", Colors.YELLOW)
                
        except Exception as e:
            print_color(f"ERROR posting status message: {e}", Colors.RED)
            
        print_color("Bot is ready to receive commands!", Colors.GREEN)
        print_color("=" * 50 + "\\n", Colors.BOLD)
        
        status_posted = True
        self.bot_ready = True

# Set up a listener to monitor the log file for the "Bot is ready" message
def watch_log_file():
    logfile = None
    
    # Try to find the log file in common locations
    possible_logs = [
        "logs/game.log",
        "logs/bot.log",
        "logs/discord.log",
        "game.log",
        "bot.log",
        "discord.log"
    ]
    
    # Wait for log file to appear (it might be created when bot starts)
    max_attempts = 10
    attempts = 0
    
    while attempts < max_attempts:
        for log_path in possible_logs:
            if os.path.exists(log_path):
                logfile = log_path
                break
        
        if logfile:
            break
            
        attempts += 1
        time.sleep(1)
    
    if not logfile:
        print_color("Could not find log file to monitor. Will rely on console output.", Colors.YELLOW)
        return
        
    print_color(f"Monitoring log file: {logfile}", Colors.BLUE)
    
    # Patterns to look for
    ready_pattern = re.compile(r"Bot is ready and online|Logged in as")
    guild_pattern = re.compile(r"Connected to (\d+) guilds?")
    bot_name_pattern = re.compile(r"Logged in as ([^#(]+).*?\(ID: (\d+)\)")
    
    with open(logfile, 'r') as f:
        # Go to the end of the file
        f.seek(0, 2)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            # Check for bot online message
            if ready_pattern.search(line):
                print_color("\\n" + "=" * 50, Colors.BOLD)
                print_color("DISCORD BOT IS NOW ONLINE!", Colors.GREEN + Colors.BOLD)
                
                # Extract bot name if available
                name_match = bot_name_pattern.search(line)
                if name_match:
                    bot_name = name_match.group(1).strip()
                    bot_id = name_match.group(2)
                    print_color(f"Bot Name: {bot_name}", Colors.CYAN)
                    print_color(f"Bot ID: {bot_id}", Colors.CYAN)
                
                # Look for guild count
                guild_match = guild_pattern.search(line)
                if guild_match:
                    guild_count = guild_match.group(1)
                    print_color(f"Connected to {guild_count} Discord servers", Colors.CYAN)
                    
                print_color("Bot is ready to receive commands!", Colors.GREEN)
                print_color("=" * 50 + "\\n", Colors.BOLD)
                break

# Start the log monitor in a separate thread
monitor_thread = threading.Thread(target=watch_log_file, daemon=True)
monitor_thread.start()

# Prepare a listener for the bot's ready event
ready_listener = BotReadyListener()

# Now run the actual entry script with our custom ready event handler
print_color("Running the main bot script with status message posting...", Colors.BLUE)

# Get the run.py contents
with open("run.py", "r") as f:
    run_script = f.read()

# Add a patch to insert our on_ready handler before executing the script
patch = '''
# Patch the bot to include our on_ready handler
import asyncio
import discord
from discord.ext import commands

# Store the original setup_hook method
original_setup_hook = discord.Client.setup_hook

async def patched_setup_hook(self, *args, **kwargs):
    # Call the original method first
    if hasattr(self, '_HCShinobiBot__original_setup_hook'):
        await self._HCShinobiBot__original_setup_hook(*args, **kwargs)
    elif original_setup_hook is not discord.Client.setup_hook:
        await original_setup_hook(self, *args, **kwargs)
    
    # Store original on_ready if it exists
    original_on_ready = getattr(self, 'on_ready', None)
    
    # Define a new on_ready that calls both
    async def new_on_ready():
        # Call our custom handler
        await ready_listener.on_ready_handler(self)
        
        # Then call the original if it exists
        if original_on_ready:
            if asyncio.iscoroutinefunction(original_on_ready):
                await original_on_ready()
            else:
                original_on_ready()
    
    # Replace the on_ready event
    self.on_ready = new_on_ready

# Apply our patched method
discord.Client.setup_hook = patched_setup_hook
'''

# Execute the patched script
exec(patch + run_script)
""")
    
    return temp_dir, runner_script

def install_discord_isolated():
    """Install discord.py to a separate temporary directory."""
    temp_site_packages = tempfile.mkdtemp(prefix="discord_py_")
    print_color(f"Installing discord.py to isolated directory: {temp_site_packages}", Colors.YELLOW)
    
    try:
        # Install discord.py to the temporary directory
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--target", temp_site_packages, 
            "--upgrade", 
            "discord.py"
        ])
        
        # Install python-dotenv as well
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--target", temp_site_packages, 
            "--upgrade", 
            "python-dotenv"
        ])
        
        print_color("Packages installed successfully to isolated directory.", Colors.GREEN)
        return temp_site_packages
    except subprocess.CalledProcessError as e:
        print_color(f"Failed to install packages to isolated directory: {e}", Colors.RED)
        return None

def run_bot_with_temp_env(temp_dir, runner_script, site_packages_dir):
    """Run the bot using the temporary environment."""
    if not os.path.exists("run.py"):
        print_color("Error: run.py not found!", Colors.RED)
        return False
    
    # Set up environment variables
    env = os.environ.copy()
    env["DISCORD_SITE_PACKAGES"] = site_packages_dir
    
    try:
        print_color("\nStarting the bot with isolated discord.py...", Colors.BLUE)
        print_color("=" * 50, Colors.BOLD)
        print_color("BOT IS STARTING UP", Colors.YELLOW + Colors.BOLD)
        print_color("The terminal will update when the bot is online and ready", Colors.CYAN)
        print_color("=" * 50, Colors.BOLD)
        
        subprocess.check_call([sys.executable, runner_script], env=env)
        return True
    except subprocess.CalledProcessError as e:
        print_color(f"Bot execution failed: {e}", Colors.RED)
        return False
    except KeyboardInterrupt:
        print_color("\nBot shutdown requested by user.", Colors.YELLOW)
        return True
    finally:
        # Clean up
        try:
            shutil.rmtree(temp_dir)
            shutil.rmtree(site_packages_dir)
            print_color("Temporary directories cleaned up.", Colors.BLUE)
        except Exception as e:
            print_color(f"Warning: Could not clean up temporary directories: {e}", Colors.YELLOW)

if __name__ == "__main__":
    # Enable Windows ANSI colors
    os.system("")  # This trick enables ANSI colors in Windows terminals
    
    print_color("HCShinobi Discord Bot Launcher", Colors.BOLD + Colors.CYAN)
    print_color("==============================", Colors.BOLD)
    print_color("This launcher creates an isolated environment to avoid import conflicts", Colors.YELLOW)
    print_color("between your project's discord directory and the discord.py package.\n", Colors.YELLOW)
    
    # Create temporary environment
    temp_dir, runner_script = create_temp_environment()
    
    # Install discord.py to isolated directory
    site_packages_dir = install_discord_isolated()
    
    if site_packages_dir:
        print_color("\nIsolated environment set up successfully.", Colors.GREEN)
        print_color("Running bot...", Colors.BLUE)
        run_bot_with_temp_env(temp_dir, runner_script, site_packages_dir)
    else:
        print_color("Failed to set up isolated environment. Cannot run the bot.", Colors.RED)
    
    print_color("\nBot execution completed.", Colors.BLUE)
    input("Press Enter to exit...") 