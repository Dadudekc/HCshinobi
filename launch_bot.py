#!/usr/bin/env python
"""
Simple launcher for HCShinobi bot that fixes import conflicts.
"""
import os
import sys
import subprocess
import shutil
import tempfile
import site
from pathlib import Path

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
    """
    print_color("Creating a clean temporary environment...", Colors.BLUE)
    temp_dir = tempfile.mkdtemp(prefix="hcshinobi_")
    print(f"Temporary directory created: {temp_dir}")
    
    # Create a Python script that will run the bot with modified path
    runner_script = os.path.join(temp_dir, "run_with_discord.py")
    
    with open(runner_script, "w", encoding="utf-8") as f:
        f.write(
            """
import subprocess
import sys
subprocess.run([sys.executable, 'run.py'])
"""
        )
    
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
    print_color("between your project's discord directory and the discord.py package.\\n", Colors.YELLOW)
    
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