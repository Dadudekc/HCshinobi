import os
import time
import uuid
import subprocess
import platform
import sys # Import sys for path manipulation
import traceback # Import traceback

# Add project root for imports
script_dir = os.path.dirname(__file__) # execution/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Go up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Service Imports ---
try:
    from governance_memory_engine import log_event # Import log_event
    _core_imports_ok = True
except ImportError as e:
    print(f"[CursorExecutor Error ❌] Failed to import governance_memory_engine: {e}")
    _core_imports_ok = False
    # Define dummy log_event
    def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")

# Configuration
PROMPT_DIR = ".cursor-prompts" # Directory to exchange prompt/response files
CURSOR_CLI_COMMAND = "cursor" # Hypothetical CLI command, adjust if known
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_POLL_INTERVAL = 1
_SOURCE = "CursorExecutor" # Define logging source

class CursorExecutor:
    """Handles generating prompt files and attempting to trigger local Cursor
       to process them, then retrieving the results.
    """
    def __init__(self):
        try:
            os.makedirs(PROMPT_DIR, exist_ok=True)
            log_event("EXECUTOR_INIT", _SOURCE, {"prompt_dir": PROMPT_DIR})
        except Exception as e:
            log_event("EXECUTOR_CRITICAL", _SOURCE, {"error": "Failed to create prompt directory", "prompt_dir": PROMPT_DIR, "details": str(e)})
            # Decide if this is fatal or if it can proceed without the dir
            raise # Reraise for now, assuming dir is critical

    def _generate_prompt_file(self, prompt_content):
        """Creates a temporary .prompt.md file."""
        filename = f"prompt_{uuid.uuid4()}.prompt.md"
        filepath = os.path.join(PROMPT_DIR, filename)
        log_context = {"filepath": filepath}
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(prompt_content)
            # print(f"Prompt file generated: {filepath}")
            log_event("PROMPT_FILE_GENERATED", _SOURCE, log_context)
            return filepath
        except Exception as e:
            # print(f"Error generating prompt file {filepath}: {e}")
            log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Error generating prompt file", "details": str(e)})
            return None

    def _trigger_cursor_processing(self, prompt_filepath):
        """Attempts to trigger Cursor to process the prompt file.

        Placeholder: This currently relies on a hypothetical CLI.
        Needs refinement based on actual Cursor capabilities.
        """
        # print(f"Attempting to trigger Cursor for: {prompt_filepath}")
        log_context = {"prompt_filepath": prompt_filepath}
        log_event("CURSOR_TRIGGER_START", _SOURCE, log_context)
        
        # --- Method 1: Hypothetical CLI (Preferred if available) ---
        try:
            # Example: cursor --process-prompt <filepath> --output <output_path>
            # The exact command, flags, and output mechanism are unknown.
            response_filepath = prompt_filepath.replace(".prompt.md", ".response.md")
            command = [CURSOR_CLI_COMMAND, "--process-prompt", prompt_filepath, "--output", response_filepath]
            command_str = ' '.join(command)
            # print(f"Executing hypothetical command: {command_str}")
            log_event("EXECUTOR_ACTION", _SOURCE, {**log_context, "action": "Executing CLI command", "command": command_str})
            
            # Run command silently in the background
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # We don't wait for completion here, just trigger it.
            # print(f"CLI command triggered (PID: {process.pid}). Will poll for response file.")
            log_event("CURSOR_CLI_TRIGGERED", _SOURCE, {**log_context, "pid": process.pid, "response_filepath": response_filepath})
            return response_filepath # Assume CLI creates this file
        except FileNotFoundError:
            # print(f"Warning: '{CURSOR_CLI_COMMAND}' command not found. CLI method failed.")
            log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "warning": "Cursor CLI command not found", "command": CURSOR_CLI_COMMAND})
        except Exception as e:
            # print(f"Warning: Error running Cursor CLI command: {e}")
            log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "warning": "Error running Cursor CLI command", "details": str(e)})

        # --- Method 2: Manual Intervention Placeholder ---
        # print("\n***************************************************************")
        # print("** ACTION REQUIRED: Please manually process the prompt in Cursor **")
        # print(f"** Prompt File: {prompt_filepath} **")
        # print("** Once done, create/update the corresponding .response.md file **")
        # print("***************************************************************\n")
        log_event("EXECUTOR_MANUAL_INTERVENTION", _SOURCE, {**log_context, "message": "Manual Cursor processing required"})
        # Assume manual process creates/updates a response file
        response_filepath = prompt_filepath.replace(".prompt.md", ".response.md")
        return response_filepath

        # --- Method 3: UI Automation (Complex, brittle - Avoid if possible) ---
        # Requires libraries like pyautogui or platform-specific APIs.
        # Highly dependent on screen layout, OS, etc.
        # log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "warning": "UI automation not implemented"})
        # return None
        

    def _wait_for_response(self, response_filepath, timeout=DEFAULT_TIMEOUT_SECONDS):
        """Waits for the response file to be created/modified."""
        # print(f"Waiting for response file: {response_filepath} (timeout: {timeout}s)")
        log_context = {"response_filepath": response_filepath, "timeout": timeout}
        log_event("CURSOR_WAIT_START", _SOURCE, log_context)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(response_filepath):
                try:
                    with open(response_filepath, 'r', encoding='utf-8') as f:
                         content = f.read()
                    # print(f"Response file found and read.")
                    log_event("CURSOR_RESPONSE_FOUND", _SOURCE, log_context)
                    return content
                except Exception as e:
                    # print(f"Error reading response file {response_filepath}: {e}")
                    log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Error reading response file", "details": str(e)})
                    return None # Error reading the file
            time.sleep(DEFAULT_POLL_INTERVAL)
        
        # print(f"Error: Timed out waiting for response file {response_filepath}.")
        log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Timed out waiting for response file"})
        return None

    def _cleanup_temp_files(self, prompt_filepath=None, response_filepath=None):
        """Utility to attempt cleanup of temporary files."""
        if prompt_filepath and os.path.exists(prompt_filepath):
            log_context = {"filepath": prompt_filepath}
            try: 
                os.remove(prompt_filepath)
                # print(f"Cleaned up prompt file: {prompt_filepath}")
                log_event("TEMP_FILE_CLEANUP", _SOURCE, {**log_context, "file_type": "prompt", "status": "success"})
            except OSError as e: # Catch specific OSError 
                 # print(f"Warning: Failed to remove temp prompt file {prompt_filepath}: {e}")
                 log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "file_type": "prompt", "warning": "Failed to remove temp file (OSError)", "details": str(e)})
            except Exception as e: # Catch any other unexpected error during cleanup
                 # print(f"Warning: Unexpected error removing temp prompt file {prompt_filepath}: {e}")
                 log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "file_type": "prompt", "warning": "Unexpected error removing temp file", "details": str(e)})
                 
        if response_filepath and os.path.exists(response_filepath):
            log_context = {"filepath": response_filepath}
            try: 
                os.remove(response_filepath)
                # print(f"Cleaned up response file: {response_filepath}")
                log_event("TEMP_FILE_CLEANUP", _SOURCE, {**log_context, "file_type": "response", "status": "success"})
            except OSError as e: # Catch specific OSError
                 # print(f"Warning: Failed to remove temp response file {response_filepath}: {e}")
                 log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "file_type": "response", "warning": "Failed to remove temp file (OSError)", "details": str(e)})
            except Exception as e: # Catch any other unexpected error during cleanup
                 # print(f"Warning: Unexpected error removing temp response file {response_filepath}: {e}")
                 log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "file_type": "response", "warning": "Unexpected error removing temp file", "details": str(e)})

    def execute_prompt(self, prompt_content, timeout=DEFAULT_TIMEOUT_SECONDS):
        """Coordinates the process: generate prompt, trigger Cursor, get response."""
        prompt_filepath = None
        response_filepath = None # Initialize response_filepath
        log_context = {"timeout": timeout}
        log_event("EXECUTE_PROMPT_START", _SOURCE, log_context)
        try:
            # 1. Generate prompt file
            prompt_filepath = self._generate_prompt_file(prompt_content)
            if not prompt_filepath:
                log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Prompt file generation failed"})
                return None
            log_context["prompt_filepath"] = prompt_filepath # Add to context

            # 2. Trigger Cursor (gets expected response path)
            response_filepath = self._trigger_cursor_processing(prompt_filepath)
            if not response_filepath:
                 # print("Failed to determine response filepath or trigger Cursor.")
                 log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Failed to determine response filepath or trigger Cursor"})
                 return None
            log_context["response_filepath"] = response_filepath # Add to context

            # 3. Wait for and read response
            response_content = self._wait_for_response(response_filepath, timeout)

            # 4. Clean up prompt file (optional) - Moved to finally
            # if prompt_filepath and os.path.exists(prompt_filepath):
            #     os.remove(prompt_filepath)
            # Optional: Clean up response file? - Moved to finally
            # if response_filepath and os.path.exists(response_filepath):
            #     os.remove(response_filepath)

            log_event("EXECUTE_PROMPT_COMPLETE", _SOURCE, {**log_context, "status": "success" if response_content is not None else "failure"})
            return response_content

        except Exception as e:
            # print(f"An unexpected error occurred during Cursor execution: {e}")
            log_event("EXECUTOR_CRITICAL", _SOURCE, {**log_context, "error": "Unexpected exception during execute_prompt", "details": str(e), "traceback": traceback.format_exc()})
            return None
        finally:
            # Ensure prompt file is cleaned up even on error, if desired
            # print("Temp file cleanup attempted in finally block.") # Too verbose for log?
            self._cleanup_temp_files(prompt_filepath=prompt_filepath, response_filepath=response_filepath)


# Example Usage
if __name__ == '__main__':
    # Check dependencies before starting
    if not _core_imports_ok:
        print("Error: Core services failed to import. Cursor Executor cannot log properly.")
        # Exit or handle appropriately
    
    executor = CursorExecutor()

    print("\n--- Example: Sending a prompt to Cursor (requires manual interaction or CLI) ---")
    prompt = """
    # Task: Refactor the following Python code
    # Goal: Improve readability and add type hints

    def calculate( a, b, op):
      if op == 'add':
        return a+b
      elif op == 'sub':
        return a-b
      else:
        return None
    """

    response = executor.execute_prompt(prompt)

    if response is not None:
        print("\n--- Response Received From Cursor (Simulated/Actual) ---")
        print(response)
        print("---------------------------------------------------------")
    else:
        print("\nFailed to get response from Cursor.") 