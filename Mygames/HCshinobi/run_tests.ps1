# run_tests.ps1

# Stop on first error
$ErrorActionPreference = "Stop"

# Function to check if virtual environment exists and create if needed
function Ensure-Venv {
    if (-not (Test-Path "venv")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
    }
}

# Function to activate virtual environment
function Activate-Venv {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    pip install -r requirements-test.txt
}

# Function to ensure __init__.py files exist in all necessary directories
function Ensure-InitFiles {
    Write-Host "Ensuring __init__.py files exist in all necessary directories..." -ForegroundColor Yellow
    $dirs = @(
        "HCshinobi",
        "HCshinobi/core",
        "HCshinobi/cogs",
        "HCshinobi/utils",
        "tests"
    )
    
    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            $initFile = Join-Path $dir "__init__.py"
            if (-not (Test-Path $initFile)) {
                Write-Host "Creating $initFile" -ForegroundColor Green
                New-Item -ItemType File -Path $initFile -Force
            }
        }
    }
}

# Main execution
try {
    # Get the absolute path of the workspace
    $workspacePath = $PSScriptRoot
    Write-Host "Workspace path: $workspacePath" -ForegroundColor Cyan

    # Ensure virtual environment exists and is activated
    Ensure-Venv
    Activate-Venv

    # Install dependencies
    Install-Dependencies

    # Ensure __init__.py files exist
    Ensure-InitFiles

    # Set PYTHONPATH
    $env:PYTHONPATH = $workspacePath

    # Run pytest with coverage
    Write-Host "Running tests..." -ForegroundColor Yellow
    pytest --maxfail=5 -v

    Write-Host "Tests completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
} 