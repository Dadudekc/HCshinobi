"""
Tool: run_script_in_sandbox
Objective: Execute a target Python script in a sandboxed environment (using subprocess)
           and capture its output and errors.

Limitations:
- Sandbox: This is a basic sandbox using subprocess, not a full container or VM.
           It doesn't prevent network access or major file system writes unless
           the underlying execution environment restricts it.
- Dependencies: Assumes the target script's dependencies are available in the
              environment where this tool is run.
"""
import argparse
import os
import sys
import logging
import json
import subprocess
import tempfile
from datetime import datetime
import time

# --- Placeholder Agent Coordination Functions ---
def _log_tool_action(tool_name, status, message, details=None):
    print(f"[TOOL LOG - {tool_name}] Status: {status}, Msg: {message}, Details: {details or 'N/A'}")

def _update_status_file(file_path, status_data):
    abs_path = os.path.abspath(file_path)
    print(f"[STATUS UPDATE] Writing to {abs_path}: {json.dumps(status_data)}")
    # In reality, write status_data to file_path
# --- End Placeholders ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOOL_NAME = "run_script_in_sandbox"

def execute_script(target_script: str, script_args: Optional[list[str]] = None, env_vars: Optional[dict[str, str]] = None, timeout: int = 60) -> dict:
    """
    Executes the target Python script using subprocess and captures output.
    """
    abs_target_script = os.path.abspath(target_script)
    logging.info(f"Attempting to execute '{abs_target_script}'...")
    results = {
        "stdout": "",
        "stderr": "",
        "return_code": None,
        "timed_out": False,
        "execution_time_ms": 0
    }

    if not os.path.exists(abs_target_script):
        logging.error(f"Target script not found: {abs_target_script}")
        results["stderr"] = f"Error: Target script not found: {abs_target_script}"
        return results

    # Prepare environment variables
    current_env = os.environ.copy()
    if env_vars:
        current_env.update(env_vars)
        logging.info(f"Using custom environment variables: {list(env_vars.keys())}")

    # Prepare command
    command = [sys.executable, abs_target_script]
    if script_args:
        command.extend(script_args)
        logging.info(f"With arguments: {script_args}")

    start_time = time.perf_counter()
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=current_env,
            text=True,
            encoding='utf-8' # Be explicit about encoding
        )
        stdout, stderr = process.communicate(timeout=timeout)
        results["return_code"] = process.returncode
        results["stdout"] = stdout
        results["stderr"] = stderr
        logging.info(f"Script execution finished with return code: {process.returncode}")

    except subprocess.TimeoutExpired:
        logging.warning(f"Script execution timed out after {timeout} seconds.")
        process.kill() # Ensure the process is terminated
        stdout, stderr = process.communicate() # Capture any remaining output
        results["timed_out"] = True
        results["stdout"] = stdout
        results["stderr"] = stderr + f"\nError: Process timed out after {timeout} seconds."
        results["return_code"] = -1 # Indicate timeout

    except FileNotFoundError:
        logging.error(f"Error: Python executable not found at '{sys.executable}' or script '{abs_target_script}' invalid.")
        results["stderr"] = f"Error: Python executable not found at '{sys.executable}' or script path invalid."
        results["return_code"] = -1

    except Exception as e:
        logging.exception("An unexpected error occurred during script execution.")
        results["stderr"] = results["stderr"] + f"\nError: Unexpected execution error: {str(e)}"
        results["return_code"] = -1 # Indicate other error
        
    end_time = time.perf_counter()
    results["execution_time_ms"] = int((end_time - start_time) * 1000)
    logging.info(f"Execution took {results['execution_time_ms']} ms.")

    return results

if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, and simulation
    print(f">>> Running module: {__file__}")

    parser = argparse.ArgumentParser(description=f"Tool: {TOOL_NAME} - Run Python scripts sandboxed.")
    parser.add_argument("target_script", help="Path to the Python script to execute (can be relative).")
    parser.add_argument("--args", nargs='*', help="Optional arguments to pass to the target script.")
    parser.add_argument("--env", nargs='*', help="Optional environment variables (KEY=VALUE pairs).")
    parser.add_argument("--timeout", type=int, default=60, help="Execution timeout in seconds.")
    parser.add_argument("--status_file", help="Optional: Path to JSON file for status updates (can be relative).")

    # --- Example Simulation ---
    # Create a temporary script to execute for the demo
    temp_script_content = r"""
import sys
import os
import time
print(f'Hello from test script! Args: {sys.argv[1:]}')
print(f'Env TEST_VAR: {os.getenv("TEST_VAR", "Not Set")}')
sys.stderr.write('This is a test error message.\n')
# time.sleep(5) # Uncomment to test timeout
sys.exit(0)
"""
    temp_script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
            tf.write(temp_script_content)
            temp_script_path = tf.name
        print(f"Created temporary script for demo: {temp_script_path}")

        example_args = [
            temp_script_path,
            "--args", "arg1", "Value for arg2",
            "--env", "TEST_VAR=HelloAgent", "OTHER_VAR=Data",
            # "--timeout", "3", # Example timeout
            "--status_file", "../status/run_script_status.json"
        ]
        args = parser.parse_args(example_args) # Use example for demo
        # args = parser.parse_args(sys.argv[1:]) # Use this for actual command line execution
        print(f">>> Parsed Arguments (raw): {vars(args)}")

        args.target_script = os.path.abspath(args.target_script)
        if args.status_file:
            args.status_file = os.path.abspath(args.status_file)
        env_vars = dict(item.split('=') for item in args.env) if args.env else None
        print(f">>> Parsed Arguments (processed): target='{args.target_script}', args={args.args}, env={env_vars}, timeout={args.timeout}")
        # -------------------------

        _log_tool_action(TOOL_NAME, "STARTED", f"Executing script '{args.target_script}'.")

        execution_result = execute_script(args.target_script, args.args, env_vars, args.timeout)

        print(f">>> Tool Result:")
        print(f"  Return Code: {execution_result['return_code']}")
        print(f"  Timed Out: {execution_result['timed_out']}")
        print(f"  Execution Time: {execution_result['execution_time_ms']} ms")
        print(f"  --- STDOUT ---\n{execution_result['stdout'].strip()}
  ----------------")
        print(f"  --- STDERR ---\n{execution_result['stderr'].strip()}
  ----------------")

        status = "COMPLETED" if execution_result["return_code"] == 0 else "FAILED"
        if execution_result["timed_out"]:
            status = "TIMED_OUT"
        message = f"Script execution finished for '{os.path.basename(args.target_script)}'. Status: {status}"
        _log_tool_action(TOOL_NAME, status, message)

        if args.status_file:
            status_data = {
                "tool": TOOL_NAME,
                "timestamp": datetime.now().isoformat(),
                "parameters": vars(args),
                "result": execution_result
            }
            _update_status_file(args.status_file, status_data)

    except Exception as e:
        logging.exception("An error occurred during script execution tool.")
        error_result = {"status": "ERROR", "message": str(e)}
        print(f">>> Tool Error: {json.dumps(error_result, indent=2)}")
        _log_tool_action(TOOL_NAME, "ERROR", str(e))
        if args.status_file:
             status_data = {
                "tool": TOOL_NAME,
                "timestamp": datetime.now().isoformat(),
                "parameters": vars(args) if 'args' in locals() else {},
                "result": error_result
            }
             _update_status_file(args.status_file, status_data)
        sys.exit(1)

    finally:
        # Clean up the temporary script
        if temp_script_path and os.path.exists(temp_script_path):
            os.remove(temp_script_path)
            print(f"Cleaned up temporary script: {temp_script_path}")

    # Exit with the script's return code if it's valid, otherwise 1 for tool error
    final_exit_code = execution_result.get("return_code", 1)
    if final_exit_code is None or final_exit_code < 0: # Handle timeout or other errors
        final_exit_code = 1
    sys.exit(final_exit_code) 