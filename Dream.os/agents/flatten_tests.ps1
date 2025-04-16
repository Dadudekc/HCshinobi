# flatten_tests.ps1
# Script to flatten test directories into D:\Dream.os\tests\
# WARNING: Contains destructive Remove-Item commands. Review carefully before running.

# Set ErrorActionPreference to Stop to halt on any error
$ErrorActionPreference = 'Stop'

Write-Host "Starting test directory flattening process..."

# --- ✅ Directories to Create ---
Write-Host "Creating new target directories under D:\Dream.os\tests\"
try {
    # Agents-based test destinations
    mkdir D:\Dream.os\tests\agents -ErrorAction Stop
    mkdir D:\Dream.os\tests\agents\dreamforge -ErrorAction Stop
    mkdir D:\Dream.os\tests\agents\dreamforge\core -ErrorAction Stop

    # Core, Dreamforge, and Social test targets
    mkdir D:\Dream.os\tests\core -ErrorAction Stop
    mkdir D:\Dream.os\tests\dreamforge -ErrorAction Stop
    mkdir D:\Dream.os\tests\social -ErrorAction Stop
    Write-Host "Target directories created successfully."
} catch {
    Write-Error "Failed to create target directories: $_"
    exit 1
}

# --- 🚚 Moves to Execute ---
Write-Host "Moving test files..."
try {
    # Move agents\dreamforge\core\tests
    Write-Host "- Moving from D:\Dream.os\agents\dreamforge\core\tests..."
    Move-Item -Path "D:\Dream.os\agents\dreamforge\core\tests\*.py" -Destination "D:\Dream.os\tests\agents\dreamforge\core\" -Force -ErrorAction Stop

    # Move agents\dreamforge\tests
    Write-Host "- Moving from D:\Dream.os\agents\dreamforge\tests..."
    # Note: Moving subdirectories first might be safer if structure is complex, but user provided flat *.py moves.
    # We'll move specific sub-items first if they exist to avoid errors when moving *.py later
    if (Test-Path "D:\Dream.os\agents\dreamforge\tests\agents") { Move-Item -Path "D:\Dream.os\agents\dreamforge\tests\agents\*.py" -Destination "D:\Dream.os\tests\agents\dreamforge\" -Force -ErrorAction SilentlyContinue } # Continue if empty
    if (Test-Path "D:\Dream.os\agents\dreamforge\tests\core\coordination") { Move-Item -Path "D:\Dream.os\agents\dreamforge\tests\core\coordination\*.py" -Destination "D:\Dream.os\tests\agents\dreamforge\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\agents\dreamforge\tests\core\utils") { Move-Item -Path "D:\Dream.os\agents\dreamforge\tests\core\utils\*.py" -Destination "D:\Dream.os\tests\agents\dreamforge\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\agents\dreamforge\tests\core") { Move-Item -Path "D:\Dream.os\agents\dreamforge\tests\core\*.py" -Destination "D:\Dream.os\tests\agents\dreamforge\" -Force -ErrorAction SilentlyContinue }
    Move-Item -Path "D:\Dream.os\agents\dreamforge\tests\*.py" -Destination "D:\Dream.os\tests\agents\dreamforge\" -Force -ErrorAction Stop # Top-level files

    # Move agents\tests and agents\tests\tests
    Write-Host "- Moving from D:\Dream.os\agents\tests..."
    if (Test-Path "D:\Dream.os\agents\tests\tests") { Move-Item -Path "D:\Dream.os\agents\tests\tests\*.py" -Destination "D:\Dream.os\tests\agents\" -Force -ErrorAction SilentlyContinue }
    Move-Item -Path "D:\Dream.os\agents\tests\*.py" -Destination "D:\Dream.os\tests\agents\" -Force -ErrorAction Stop

    # Move core\tests
    Write-Host "- Moving from D:\Dream.os\core\tests..."
    Move-Item -Path "D:\Dream.os\core\tests\*.py" -Destination "D:\Dream.os\tests\core\" -Force -ErrorAction Stop

    # Move dreamforge\tests
    Write-Host "- Moving from D:\Dream.os\dreamforge\tests..."
    Move-Item -Path "D:\Dream.os\dreamforge\tests\*.py" -Destination "D:\Dream.os\tests\dreamforge\" -Force -ErrorAction Stop

    # Move social\tests
    Write-Host "- Moving from D:\Dream.os\social\tests..."
    # Handle nested directories first
    if (Test-Path "D:\Dream.os\social\tests\core\memory") { Move-Item -Path "D:\Dream.os\social\tests\core\memory\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\social\tests\core") { Move-Item -Path "D:\Dream.os\social\tests\core\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\social\tests\integration") { Move-Item -Path "D:\Dream.os\social\tests\integration\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\social\tests\social\strategies") { Move-Item -Path "D:\Dream.os\social\tests\social\strategies\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\social\tests\social") { Move-Item -Path "D:\Dream.os\social\tests\social\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\social\tests\strategies") { Move-Item -Path "D:\Dream.os\social\tests\strategies\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\social\tests\tools") { Move-Item -Path "D:\Dream.os\social\tests\tools\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    if (Test-Path "D:\Dream.os\social\tests\utils") { Move-Item -Path "D:\Dream.os\social\tests\utils\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction SilentlyContinue }
    Move-Item -Path "D:\Dream.os\social\tests\*.py" -Destination "D:\Dream.os\tests\social\" -Force -ErrorAction Stop # Top-level files

    Write-Host "Test files moved successfully."
} catch {
    Write-Error "Failed during file move operation: $_"
    Write-Warning "Manual cleanup might be required. Old directories have NOT been deleted."
    exit 1
}

# --- 🧼 Post-Move: Clean Up Old Test Folders ---
Write-Host "Cleaning up old, empty test directories..."
Write-Warning "This step is destructive. Ensure files were moved correctly."
# Add a brief pause for review if needed? Start-Sleep -Seconds 5
try {
    Remove-Item -Recurse -Force "D:\Dream.os\agents\dreamforge\core\tests" -ErrorAction Stop
    Remove-Item -Recurse -Force "D:\Dream.os\agents\dreamforge\tests" -ErrorAction Stop
    Remove-Item -Recurse -Force "D:\Dream.os\agents\tests" -ErrorAction Stop
    Remove-Item -Recurse -Force "D:\Dream.os\core\tests" -ErrorAction Stop
    Remove-Item -Recurse -Force "D:\Dream.os\dreamforge\tests" -ErrorAction Stop
    Remove-Item -Recurse -Force "D:\Dream.os\social\tests" -ErrorAction Stop
    Write-Host "Old test directories removed successfully."
} catch {
    Write-Error "Failed to remove old directories: $_"
    Write-Warning "Manual cleanup of old directories might be required."
    exit 1
}

Write-Host "Test directory flattening process completed." 