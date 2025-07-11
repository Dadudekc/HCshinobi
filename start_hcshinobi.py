#!/usr/bin/env python3
"""
HCShinobi Bot Launcher
Simple script to launch the complete HCShinobi Discord bot.
"""

import sys
import os
from pathlib import Path

def main():
    """Launch the HCShinobi bot."""
    
    print("🎌 HCShinobi Discord Bot Launcher")
    print("=" * 40)
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check for required files
    if not Path(".env").exists():
        print("❌ Error: .env file not found!")
        print("   Please copy .env-example to .env and configure your bot token.")
        return 1
    
    if not Path("data").exists():
        print("⚠️  Warning: data directory not found. Creating...")
        Path("data").mkdir(exist_ok=True)
        
    if not Path("logs").exists():
        print("⚠️  Warning: logs directory not found. Creating...")
        Path("logs").mkdir(exist_ok=True)
    
    print("✅ Environment check passed")
    print("🚀 Starting HCShinobi bot...")
    print()
    
    # Import and run the main bot
    try:
        from main import main as run_main_bot
        run_main_bot()
    except ImportError as e:
        print(f"❌ Error importing main bot: {e}")
        print("   Make sure all dependencies are installed.")
        return 1
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 