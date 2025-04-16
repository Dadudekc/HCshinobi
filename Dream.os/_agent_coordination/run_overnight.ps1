# Dream.OS - Autonomous Overnight Runner (PowerShell)
# Launches the AgentBus and the four agent workers (1-4) in separate background jobs.

param(
    [switch]$DebugAgents # Add --debug flag to agent launches if specified
)

Write-Host "🚀 Launching Dream.OS Agent Swarm for Overnight Run..."

# --- Configuration ---
$PythonExecutable = "python" # Or specify absolute path e.g., "C:/Python39/python.exe"
$ProjectRoot = $PSScriptRoot # Assumes script is in the project root

# --- Prerequisites ---
Write-Host "🔧 Checking prerequisites..."
# 1. Ensure Python is available
try {
    & $PythonExecutable --version
} catch {
    Write-Error "Python executable '$PythonExecutable' not found or failed to run. Please check path or installation."
    exit 1
}

# 2. Set PYTHONPATH (Crucial for imports)
# Add project root to PYTHONPATH if not already set globally
$env:PYTHONPATH = "$ProjectRoot;" + $env:PYTHONPATH
Write-Host "   PYTHONPATH set to: $env:PYTHONPATH"

# 3. Ensure core directories exist (agents create their own, but state/logs needed)
$StateDir = Join-Path $ProjectRoot "state"
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Path $StateDir | Out-Null }
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# --- Launch Components ---

# Function to launch a component
function Start-DreamOSComponent {
    param(
        [string]$ComponentName,
        [string]$ScriptPath,
        [switch]$Debug = $false
    )
    
    # Construct the base python command arguments within the job's scriptblock
    if ($Debug) {
        Write-Host "   Launching $ComponentName (Debug Mode)..."
    } else {
        Write-Host "   Launching $ComponentName..."
    }
    
    try {
        # Pass the boolean state of the switch parameter
        $debugSwitchState = $Debug.IsPresent 
        
        Start-Job -ScriptBlock { 
            param($pyExecutable, $scriptToRun, [bool]$enableDebug)
            
            # Assign the component name to a local variable within the job scope
            $localComponentName = $using:ComponentName

            # Set thread/process title for better identification (optional)
            # $Host.UI.RawUI.WindowTitle = "DreamOS Agent: $localComponentName"
            
            $cmdArgs = @($scriptToRun) # Start with script path
            if ($enableDebug) { 
                $cmdArgs += "--debug" 
            } 
            Write-Output "Executing: $pyExecutable $cmdArgs"
            & $pyExecutable $cmdArgs 
            # Add error handling or logging from job if needed
            if ($LASTEXITCODE -ne 0) {
                # Use the local variable in the warning message
                Write-Warning "Component $localComponentName exited with code $LASTEXITCODE"
            }
        } -ArgumentList $PythonExecutable, $ScriptPath, $debugSwitchState | Out-Null
        Write-Host "   -> $ComponentName started in background job."
    } catch {
        # Use string formatting or concatenation to avoid parsing issue with $_ inside ""
        Write-Error ("Failed to start {0} from {1}: {2}" -f $ComponentName, $ScriptPath, $_)
    }
    Start-Sleep -Seconds 1 # Stagger launches slightly
}

# 1. Launch AgentBus (with Debug by default for visibility)
Start-DreamOSComponent -ComponentName "AgentBus" -ScriptPath "core/agent_bus.py" -Debug

# 2. Launch Agent 1 (Prompt Planner)
Start-DreamOSComponent -ComponentName "Agent 1 (Planner)" -ScriptPath "agents/agent_1/worker.py" -Debug:$DebugAgents

# 3. Launch Agent 2 (Cursor Executor)
Write-Host "   [INFO] Agent 2 uses CursorExecutorStub unless integrated."
Start-DreamOSComponent -ComponentName "Agent 2 (Executor)" -ScriptPath "agents/agent_2/worker.py" -Debug:$DebugAgents

# 4. Launch Agent 3 (Feedback Verifier)
Start-DreamOSComponent -ComponentName "Agent 3 (Verifier)" -ScriptPath "agents/agent_3/worker.py" -Debug:$DebugAgents

# 5. Launch Agent 4 (Task Orchestrator)
Start-DreamOSComponent -ComponentName "Agent 4 (Orchestrator)" -ScriptPath "agents/agent_4/worker.py" -Debug:$DebugAgents

Write-Host "✅ All core Dream.OS components launched in background jobs."
Write-Host "   Use 'Get-Job' to see running agent processes."
Write-Host "   Use 'Receive-Job -Job <JobObject>' to view output (or check logs/agent_X.log)."
Write-Host "   Use 'Stop-Job -Job <JobObject>' to terminate a specific agent."
Write-Host "   Use 'Get-Job | Stop-Job' to terminate all agents."
Write-Host "🌙 System running in Autonomous Overnight Mode." 