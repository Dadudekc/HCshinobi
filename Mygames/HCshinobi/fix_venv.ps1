# PowerShell script to fix virtual environment issues
# Run this script with administrator privileges if possible

Write-Host "Fixing virtual environment issues..." -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow

# Check if venv directory exists
if (Test-Path -Path ".\venv") {
    Write-Host "Found existing virtual environment directory. Removing it..." -ForegroundColor Yellow
    
    # Try to remove the directory
    try {
        Remove-Item -Path ".\venv" -Recurse -Force -ErrorAction Stop
        Write-Host "Successfully removed existing virtual environment." -ForegroundColor Green
    }
    catch {
        Write-Host "Error removing virtual environment: $_" -ForegroundColor Red
        Write-Host "Trying alternative removal method..." -ForegroundColor Yellow
        
        # Use rd command which sometimes has better luck with permissions
        cmd /c "rd /s /q venv"
        
        # Check if it worked
        if (Test-Path -Path ".\venv") {
            Write-Host "Could not remove virtual environment directory." -ForegroundColor Red
            Write-Host "Please try running this script as administrator or delete the venv folder manually." -ForegroundColor Red
            exit 1
        }
        else {
            Write-Host "Successfully removed existing virtual environment using alternative method." -ForegroundColor Green
        }
    }
}

# Create a new virtual environment
Write-Host "Creating a new virtual environment..." -ForegroundColor Yellow
try {
    python -m venv venv
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
}
catch {
    Write-Host "Error creating virtual environment: $_" -ForegroundColor Red
    exit 1
}

# Activate the virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\Activate.ps1
    Write-Host "Virtual environment activated." -ForegroundColor Green
}
catch {
    Write-Host "Error activating virtual environment: $_" -ForegroundColor Red
    Write-Host "Continuing anyway..." -ForegroundColor Yellow
}

# Check if requirements files exist before trying to install them
Write-Host "Installing required packages..." -ForegroundColor Yellow

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install standard requirements
if (Test-Path -Path ".\requirements.txt") {
    Write-Host "Installing packages from requirements.txt..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
}
else {
    Write-Host "requirements.txt not found, installing basic packages..." -ForegroundColor Yellow
    python -m pip install discord.py python-dotenv pytest
}

# Install test requirements
if (Test-Path -Path ".\tests\requirements-test.txt") {
    Write-Host "Installing test packages from tests/requirements-test.txt..." -ForegroundColor Yellow
    python -m pip install -r tests/requirements-test.txt
}

# Install the package in development mode
Write-Host "Installing package in development mode..." -ForegroundColor Yellow
python -m pip install -e .

Write-Host "====================================" -ForegroundColor Yellow
Write-Host "Virtual environment setup completed!" -ForegroundColor Green
Write-Host "You should now be able to run the bot using:" -ForegroundColor Yellow
Write-Host ".\Start_Bot.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "Or directly with Python using:" -ForegroundColor Yellow
Write-Host "python launch_bot.py" -ForegroundColor Cyan 