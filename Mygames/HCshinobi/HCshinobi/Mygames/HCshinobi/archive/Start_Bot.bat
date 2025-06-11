@echo off
TITLE HCShinobi Discord Bot
echo Starting HCShinobi Discord Bot...
echo ==============================
echo.
echo This launcher will start the bot with a special configuration to fix
echo the import conflict between your project's discord directory and
echo the discord.py package.
echo.
echo NEW FEATURE: The terminal will now notify you when the bot is online
echo and ready to receive commands in Discord. You'll see:
echo  - The bot's name and ID
echo  - Number of Discord servers it's connected to
echo  - Confirmation when it's fully ready to use
echo.
echo ALSO NEW: The bot will now post a status message in your Discord battle
echo channel (ID: 1355761212343975966) when it comes online!
echo.
echo If you see any errors related to discord.ext, please use this launcher
echo instead of directly running the bot with python run.py
echo.
echo Press any key to start the bot...
pause > nul

:: Change to the directory where this batch file is located
cd /d "%~dp0"

:: Check if virtual environment exists and activate it
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: No virtual environment found. Using system Python.
)

:: Run the bot using the launcher script instead of run_bot.py
echo Running bot with special launcher to fix import conflicts...
python launch_bot.py

echo Bot exited.
pause 