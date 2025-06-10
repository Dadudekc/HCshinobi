@echo off
title Fix Virtual Environment
echo Fixing virtual environment issues...
echo ====================================

:: Check if venv directory exists
if exist venv (
    echo Found existing virtual environment directory. Removing it...
    
    :: Try to remove the directory
    rd /s /q venv
    
    :: Check if it worked
    if exist venv (
        echo Could not remove virtual environment directory.
        echo Please try running this script as administrator or delete the venv folder manually.
        pause
        exit /b 1
    ) else (
        echo Successfully removed existing virtual environment.
    )
)

:: Create a new virtual environment
echo Creating a new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Error creating virtual environment.
    pause
    exit /b 1
)
echo Virtual environment created successfully.

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated.

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install standard requirements
if exist requirements.txt (
    echo Installing packages from requirements.txt...
    python -m pip install -r requirements.txt
) else (
    echo requirements.txt not found, installing basic packages...
    python -m pip install discord.py python-dotenv pytest
)

:: Install test requirements
if exist tests\requirements-test.txt (
    echo Installing test packages from tests/requirements-test.txt...
    python -m pip install -r tests\requirements-test.txt
)

:: Install the package in development mode
echo Installing package in development mode...
python -m pip install -e .

echo ====================================
echo Virtual environment setup completed!
echo You should now be able to run the bot using:
echo Start_Bot.bat
echo.
echo Or directly with Python using:
echo python launch_bot.py

pause 