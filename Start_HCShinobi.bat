@echo off
TITLE HCShinobi Discord Bot - Complete System
cls
echo.
echo  ████████████████████████████████████████████
echo  █                                          █
echo  █          HCShinobi Discord Bot           █
echo  █         Complete Command Suite           █  
echo  █                                          █
echo  ████████████████████████████████████████████
echo.
echo Loading all systems:
echo ✓ Character & Clan Systems
echo ✓ Battle & Training Systems  
echo ✓ Mission & Quest Systems
echo ✓ Economy & Token Systems
echo ✓ Boss Battle Systems
echo ✓ ShinobiOS Battle Missions
echo.
echo ════════════════════════════════════════════
echo.

:: Change to the script directory
cd /d "%~dp0"

:: Check if .env file exists
if not exist ".env" (
    echo ❌ ERROR: .env file not found!
    echo.
    echo Please copy .env-example to .env and configure your Discord bot token.
    echo.
    pause
    exit /b 1
)

:: Check and activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
    echo.
) else (
    echo ⚠️  Warning: No virtual environment found at 'venv\'
    echo    Using system Python installation
    echo.
)

:: Create required directories
if not exist "logs" mkdir logs
if not exist "data" mkdir data

echo 🚀 Starting HCShinobi bot with comprehensive command suite...
echo ════════════════════════════════════════════
echo.

:: Run the bot using our new main system
python start_hcshinobi.py

echo.
echo ════════════════════════════════════════════
echo Bot has stopped running.
echo.
pause 