"""
Tool to launch and manage the Dream.OS Agent Swarm processes.
"""

import argparse
import subprocess
import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
import signal

# --- Configuration ---
AGENT_SCRIPTS = {
    "bus": "core/agent_bus.py",
    "1": "agents/agent_1/worker.py",
    "2": "agents/agent_2/worker.py",
    "3": "agents/agent_3/worker.py",
    "4": "agents/agent_4/worker.py",
    # Add more agents here as needed
}
PYTHON_EXECUTABLE = sys.executable # Use the same python that runs this script
DEFAULT_AGENTS_TO_RUN = ["bus", "1", "2", "3", "4"] # Default set to launch

# Dictionary to keep track of running processes
running_processes: Dict[str, subprocess.Popen] = {}

def launch_component(component_id: str, script_path: str, base_dir: Path, debug: bool = False):
    """Launches a single component (agent or bus) as a subprocess."""
    if component_id in running_processes and running_processes[component_id].poll() is None:
        print(f"Component '{component_id}' is already running (PID: {running_processes[component_id].pid}). Skipping.")
        return
        
    full_script_path = base_dir / script_path
    if not full_script_path.exists():
        print(f"Error: Script path not found for component '{component_id}': {full_script_path}", file=sys.stderr)
        return
        
    command = [PYTHON_EXECUTABLE, str(full_script_path)]
    if debug:
        command.append("--debug")
        print(f"Launching component '{component_id}' (Debug Mode)... Command: {' '.join(command)}")
    else:
        print(f"Launching component '{component_id}'... Command: {' '.join(command)}")

    try:
        # Set PYTHONPATH environment variable for the subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = str(base_dir) + os.pathsep + env.get("PYTHONPATH", "")
        
        # Use Popen for non-blocking execution
        # Capture stdout/stderr if needed later, for now let them inherit
        process = subprocess.Popen(
            command, 
            cwd=base_dir, # Run from project root
            env=env,
            # Optional: Redirect stdout/stderr to files or PIPE
            # stdout=subprocess.PIPE, 
            # stderr=subprocess.PIPE,
            # universal_newlines=True # If capturing output
        )
        running_processes[component_id] = process
        print(f" -> Component '{component_id}' started (PID: {process.pid})")
    except Exception as e:
        print(f"Error launching component '{component_id}': {e}", file=sys.stderr)

def terminate_component(component_id: str):
    """Terminates a running component process gracefully (SIGTERM)."""
    if component_id in running_processes and running_processes[component_id].poll() is None:
        process = running_processes[component_id]
        print(f"Terminating component '{component_id}' (PID: {process.pid})...")
        try:
            # Send SIGTERM first for graceful shutdown
            process.terminate() 
            try:
                # Wait a bit for graceful exit
                process.wait(timeout=5)
                print(f" -> Component '{component_id}' terminated gracefully.")
            except subprocess.TimeoutExpired:
                print(f" -> Component '{component_id}' did not terminate gracefully. Sending SIGKILL...")
                process.kill()
                process.wait(timeout=2)
                print(f" -> Component '{component_id}' killed.")
        except Exception as e:
            print(f"Error terminating component '{component_id}': {e}")
        del running_processes[component_id]
    elif component_id in running_processes: # Process existed but already terminated
        print(f"Component '{component_id}' was already terminated (Exit code: {running_processes[component_id].poll()}).")
        del running_processes[component_id]
    else:
        print(f"Component '{component_id}' not found or not running.")

def signal_handler(signum, frame):
    """Handle Ctrl+C or SIGTERM to terminate all child processes."""
    print(f"\nSignal {signal.Signals(signum).name} received. Terminating all components...")
    component_ids = list(running_processes.keys())
    for component_id in component_ids: # Iterate over a copy of keys
        terminate_component(component_id)
    print("All components terminated. Exiting runner.")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Dream.OS Agent Swarm")
    parser.add_argument("--agents", nargs='+', default=DEFAULT_AGENTS_TO_RUN, 
                        help=f"List of agent IDs (and 'bus') to run (default: {' '.join(DEFAULT_AGENTS_TO_RUN)}). Available: {', '.join(AGENT_SCRIPTS.keys())}")
    parser.add_argument("--base-dir", default=".", help="Base project directory (default: current directory)")
    parser.add_argument("--debug-bus", action="store_true", help="Run AgentBus with --debug flag")
    parser.add_argument("--debug-agents", action="store_true", help="Run specified agents with --debug flag")
    parser.add_argument("--skip-bus", action="store_true", help="Do not launch the AgentBus (assume it is running elsewhere)")

    args = parser.parse_args()

    base_directory = Path(args.base_dir).resolve()
    print(f"Using base directory: {base_directory}")
    print(f"Python executable: {PYTHON_EXECUTABLE}")

    # Register signal handlers for graceful shutdown of the runner and its children
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    agents_to_launch = []
    if not args.skip_bus:
        if "bus" in args.agents:
             agents_to_launch.append("bus")
        else:
             print("Warning: 'bus' not specified in --agents, but --skip-bus not used. Launching bus anyway.")
             agents_to_launch.append("bus")
             
    for agent_id in args.agents:
        if agent_id != "bus":
             if agent_id in AGENT_SCRIPTS:
                 agents_to_launch.append(agent_id)
             else:
                 print(f"Warning: Unknown agent ID '{agent_id}' specified. Skipping.")

    print(f"Launching components: {', '.join(agents_to_launch)}")

    for component_id in agents_to_launch:
        script = AGENT_SCRIPTS.get(component_id)
        if script:
            debug_flag = False
            if component_id == "bus":
                debug_flag = args.debug_bus
            else:
                debug_flag = args.debug_agents
                
            launch_component(component_id, script, base_directory, debug=debug_flag)
            time.sleep(0.5) # Stagger launches a bit
        else:
             # Should not happen due to check above, but safeguard
             print(f"Error: No script defined for component '{component_id}'.")
             
    print("--- Agent Swarm Runner Initialized ---")
    print("Agents are running in the background.")
    print("Press Ctrl+C to terminate the runner and all agents gracefully.")

    # Keep the main script alive to manage children until Ctrl+C
    try:
        while True:
            # Optional: Check status of child processes periodically
            # for component_id, process in list(running_processes.items()):
            #     if process.poll() is not None: # Process terminated
            #         print(f"Warning: Component '{component_id}' terminated unexpectedly with code {process.poll()}. Removing from active list.")
            #         del running_processes[component_id]
            #         # TODO: Add restart logic here if desired
            time.sleep(5)
    except KeyboardInterrupt:
        # Handled by signal handler
        pass
    finally:
        # Final cleanup if loop exits unexpectedly
        print("Runner script ending. Ensuring all components are terminated...")
        component_ids = list(running_processes.keys())
        for component_id in component_ids: 
            terminate_component(component_id)
        print("Runner finished.") 