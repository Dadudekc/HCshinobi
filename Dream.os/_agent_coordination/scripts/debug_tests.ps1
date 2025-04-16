# Debug test runner for Cursor Result Listener
param(
    [switch]$Verbose = $false,
    [switch]$FailFast = $false,
    [switch]$NoParallel = $false
)

$ErrorActionPreference = "Stop"
$DebugPreference = if ($Verbose) { "Continue" } else { "SilentlyContinue" }

# Ensure we're in the right directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $scriptPath)

# Setup Python virtual environment if needed
if (-not (Test-Path ".venv")) {
    Write-Host "🔧 Creating virtual environment..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create virtual environment"
    }
}

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

# Install/upgrade dependencies
Write-Host "📦 Installing dependencies..."
python -m pip install --upgrade pip pytest pytest-cov pytest-asyncio pytest-xdist

# Clean previous test artifacts
Write-Host "🧹 Cleaning previous test artifacts..."
Remove-Item -Path "logs/test_debug/*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "htmlcov/*" -Recurse -Force -ErrorAction SilentlyContinue

# Set environment variables for testing
$env:PYTHONPATH = "."
$env:TEST_ENV = "debug"
$env:CURSOR_CONFIG = "config/cursor.yaml"

# Build command arguments
$args = @()
if ($Verbose) { $args += "-v" }
if ($FailFast) { $args += "--exitfirst" }
if (-not $NoParallel) { $args += "-n auto" }

# Run debug tests
Write-Host "🧪 Running debug tests..."
try {
    python scripts/debug_tests.py $args
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "❌ Error running tests: $_" -ForegroundColor Red
    exit 1
}

# Open coverage report if tests passed
if ($LASTEXITCODE -eq 0) {
    Write-Host "📊 Opening coverage report..."
    Start-Process "htmlcov/index.html"
}

Write-Host "✅ Debug session completed!" 