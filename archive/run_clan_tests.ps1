# PowerShell script to run clan system tests
# Usage: .\run_clan_tests.ps1

Write-Host "Running clan system tests..."
Write-Host "=========================="

# Activate virtual environment if it exists
if (Test-Path -Path ".\venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
    Write-Host "Virtual environment activated."
} else {
    Write-Host "No virtual environment found. Using system Python."
}

# Install test requirements if needed
if (Test-Path -Path ".\tests\requirements-test.txt") {
    Write-Host "Installing test requirements..."
    pip install -r tests\requirements-test.txt
}

# Run specific tests for clan system
Write-Host "Running clan system tests..."
python -m pytest tests/extensions/test_clans.py -v --no-header
python -m pytest tests/core/test_clan_data.py -v --no-header
python -m pytest tests/test_clan_assignment.py -v --no-header

Write-Host "=========================="
Write-Host "Tests completed." 