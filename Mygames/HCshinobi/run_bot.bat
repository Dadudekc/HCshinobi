@echo off
TITLE HCShinobi Discord Bot
echo Starting HCShinobi Discord Bot...
echo ==============================

:: Change to the directory where this batch file is located
cd /d "%~dp0"

:: Check if virtual environment exists and activate it
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: No virtual environment found. Using system Python.
)

:: Check if run.py exists
if not exist run.py (
    echo Error: run.py not found in the current directory!
    echo Make sure you're running this script from the project root.
    pause
    exit /b 1
)

:: Run the bot
echo Running the bot...
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe run.py
) else (
    python run.py
)

:: If we get here with an error, keep the window open
if %ERRORLEVEL% neq 0 (
    echo The bot exited with code %ERRORLEVEL%
    pause
) 