# Running the HCShinobi Discord Bot

## Solution to Discord.py Import Conflict Issue

Your project has a name conflict between the directory `discord` and the `discord.py` package. This causes Python to import the wrong module, resulting in errors like:

```
ModuleNotFoundError: No module named 'discord.ext'
```

## Virtual Environment Setup

If you encounter permission issues when setting up your virtual environment, we've created scripts to help:

### For PowerShell Users:
```
.\fix_venv.ps1
```

### For Command Prompt Users:
```
fix_venv.bat
```

These scripts will:
1. Remove the existing virtual environment (if present)
2. Create a new virtual environment
3. Install all required packages
4. Install the package in development mode

## How to Run the Bot

### Option 1: Double-click Start_Bot.bat (Recommended for Windows)

Simply double-click the `Start_Bot.bat` file we've created. This will:
1. Activate your virtual environment if available
2. Run the bot with our special launcher that fixes the import path
3. Provide clear feedback about what's happening

### Option 2: Run with Python

If you prefer to run from a terminal:

```
python launch_bot.py
```

This launcher creates an isolated environment where discord.py can be imported correctly, without being affected by your project's directory structure.

## New Feature: Bot Online Notification

The launcher now monitors the log files and will show a clear notification when your bot is online and ready to use in Discord. You'll see:

- A prominent "DISCORD BOT IS NOW ONLINE!" message
- The bot's name and ID 
- Number of Discord servers it's connected to
- Confirmation when it's fully ready to receive commands

This feature helps you know exactly when your bot is ready to use after startup.

## New Feature: Discord Channel Status Message

In addition to the console notification, the bot will now automatically post a status message to your Discord channel (ID: 1355761212343975966) when it comes online. This message includes:

- A green embed with a "Bot is Online" title
- A message indicating the battle system is ready for commands
- The timestamp when the bot was started

This lets your Discord users know when the bot is available for use without requiring you to manually notify them.

## What We Fixed

1. **Import Conflict**: Fixed the conflict between your `discord` directory and the `discord.py` package
2. **Typo in clans.py**: Fixed a typo where `__le__` was used instead of `__file__`
3. **Path to clans.json**: Updated the path to point to the data directory where clans.json is actually located
4. **Virtual Environment Setup**: Added scripts to fix permission issues with virtual environments
5. **Bot Status Notification**: Added feature to notify when the bot is online in Discord
6. **Discord Channel Status Message**: Added automatic posting to your Discord channel when the bot comes online

## Long-term Solution (Optional)

For a permanent solution, consider renaming your project's directory structure:

```
HCshinobi/discord/ -> HCshinobi/discord_bot/
```

This would require updating imports throughout your code, but would resolve the conflict permanently.

## Troubleshooting

If you still have issues:

1. Make sure you're using the provided launchers (`Start_Bot.bat` or `launch_bot.py`)
2. Check that all required files exist (`data/clans.json`, etc.)
3. Ensure your Discord bot token is correctly set in your `.env` file
4. If you have permission issues with the virtual environment, try running `fix_venv.bat` or `fix_venv.ps1` as administrator
5. If the bot online notification doesn't appear, check that your logs directory exists and the bot has permissions to write to it
6. If the Discord channel status message doesn't appear, verify the bot has proper permissions to post in that channel

## System Requirements

- Python 3.8 or higher
- discord.py 2.5.0 or higher
- python-dotenv package 