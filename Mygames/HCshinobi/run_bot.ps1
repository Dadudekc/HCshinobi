# PowerShell script to run the Naruto-themed Discord bot
# Usage: .\run_bot.ps1

# Display startup message
Write-Host "Starting HCShinobi Discord Bot..."
Write-Host "=============================="

# Get the directory where this script is located
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptPath

# Check if we're in a virtual environment and activate it if needed
if (Test-Path -Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..."
    . .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Warning: No virtual environment found. Using system Python."
}

# Check if run.py exists
if (-not (Test-Path -Path ".\run.py")) {
    Write-Host "Error: run.py not found in the current directory!" -ForegroundColor Red
    Write-Host "Make sure you're running this script from the project root." -ForegroundColor Red
    exit 1
}

# Check if Python exists in venv
if (Test-Path -Path ".\venv\Scripts\python.exe") {
    $pythonPath = ".\venv\Scripts\python.exe"
} else {
    # Fallback to system Python
    $pythonPath = "python"
}

# Run the bot
Write-Host "Running the bot with: $pythonPath run.py"
try {
    & $pythonPath run.py
} catch {
    Write-Host "Error running the bot: $_" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
}

# Keep the console window open if there was an error
if ($LASTEXITCODE -ne 0) {
    Write-Host "The bot exited with code $LASTEXITCODE" -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} 