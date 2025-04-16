import logging
import os # Keep os for dirname, but use filesystem abstraction for IO/checks
import subprocess # Import subprocess
import sys # Import sys

# Assume these abstractions are defined elsewhere and passed in
# from ..utils.filesystem import FilesystemProvider # Example
# from ..utils.memory import MemoryProvider # Example

# --- Add path calculation relative to this file if needed, or assume WORKSPACE_ROOT is passed/known ---
COMMAND_HANDLER_DIR = os.path.dirname(os.path.abspath(__file__))
# Example: Assuming agent_tools is sibling to agents/ directory at workspace root
AGENT_TOOLS_DIR = os.path.abspath(os.path.join(COMMAND_HANDLER_DIR, '..', '..', '_agent_coordination', 'agent_tools')) 
SNIFFER_SCRIPT_PATH = os.path.join(AGENT_TOOLS_DIR, 'dead_code_sniffer.py')

class CommandHandler:
    def __init__(self, agent_id: str, specialization: str, filesystem, memory, logger):
        self.agent_id = agent_id
        self.specialization = specialization
        self.filesystem = filesystem # Filesystem abstraction instance
        self.memory = memory       # Memory abstraction instance
        self.logger = logger       # Logger instance
        self._is_main_loop_running = False # Example internal state

    def handle_command(self, command_name: str, params: dict):
        """Main dispatcher for agent commands."""
        try:
            match command_name:
                case "initial_onboarding":
                    self.logger.info(f"Received command: {command_name}")
                    self.handle_initial_onboarding(params)
                    return {"status": "success", "message": "Onboarding initiated."}
                
                # Placeholder for other commands
                # case "execute_task":
                #     self.logger.info(f"Received command: {command_name}")
                #     result = self.handle_execute_task(params) 
                #     return {"status": "success", "data": result} # Example return
                
                case "find_dead_code":
                    self.logger.info(f"Received command: {command_name}")
                    result_data = self.handle_find_dead_code(params)
                    if result_data is None: # Check for error during handling
                         return {"status": "error", "message": "Error occurred during dead code analysis."}
                    else:
                         return {"status": "success", "data": {"unused_code_lines": result_data}}
                    
                case "terminate":
                    self.logger.info(f"Received command: {command_name}")
                    self.handle_terminate(params)
                    return {"status": "success", "message": "Termination sequence initiated."}
                    
                case _:
                    self.logger.warning(f"Received unknown command: {command_name}")
                    return {"status": "error", "message": f"Unknown command: {command_name}"}
        except Exception as e:
            self.logger.error(f"Error handling command '{command_name}': {e}", exc_info=True)
            return {"status": "error", "message": f"Internal error processing command: {e}"}

    def handle_initial_onboarding(self, params: dict) -> None:
        """
        Handles the 'initial_onboarding' command by reading and internalizing 
        the onboarding template specified in params.
        """
        
        # Step 1: Get template path (provide a default relative to agent execution?)
        # Assuming the default path should be relative to the workspace root, not the handler file itself.
        default_template_path = "user_prompts/agent_activation_template.txt"
        template_path = params.get("prompt_template_path", default_template_path)
        self.logger.info(f"Attempting to load onboarding template from: {template_path}")

        # Step 2: Resolve path using filesystem abstraction
        # Use the abstracted filesystem.exists() instead of os.path.exists()
        if not self.filesystem.exists(template_path):
            self.logger.warning(f"Template not found at resolved path: {template_path}. Attempting parent directory scan.")
            try:
                parent_dir = os.path.dirname(template_path) if os.path.dirname(template_path) else '.' # Handle edge case
                # Assuming list_dir returns a list of filenames or raises an error
                file_list = self.filesystem.list_dir(parent_dir)
                self.logger.info(f"Available files/dirs in '{parent_dir}': {file_list}")
            except Exception as list_err:
                self.logger.error(f"Failed to list directory '{parent_dir}': {list_err}")
            # Explicitly mark onboarding as failed if template isn't found
            self.memory.set("onboarded", False)
            self.memory.set("onboarding_error", f"Template file not found: {template_path}")
            return # Stop processing if template doesn't exist

        try:
            # Step 3: Read template using filesystem abstraction
            onboarding_text = self.filesystem.read_file(template_path)
            self.logger.debug(f"Successfully read template file: {template_path}")

            # Step 4: Replace agent-specific fields (flexible for future use)
            onboarding_text = onboarding_text.replace("{{ agent_id }}", self.agent_id)
            onboarding_text = onboarding_text.replace("{{ specialization }}", self.specialization)

            # Step 5: Internalize (log + save to memory)
            self.logger.info(f"--- Begin Onboarding Protocol Internalization for {self.agent_id} ---")
            self.logger.info("Applying onboarding directives:")
            # Log potentially large prompt at INFO or DEBUG level based on needs
            for line in onboarding_text.splitlines():
                 self.logger.info(f"> {line}") # Prefix lines for clarity
            # Store the processed prompt and status in memory
            self.memory.set("onboarding_prompt_processed", onboarding_text)
            self.memory.set("onboarding_error", None) # Clear any previous error
            self.memory.set("onboarded", True)
            self.logger.info(f"--- Onboarding Protocol Internalized for {self.agent_id}. Status: Success --- ")

            # Step 6: Optional: auto-initiate first task scan/main loop
            # Consider if onboarding itself should trigger the loop, or if it waits for external start signal
            # self.start_main_loop() # Removed auto-start; let entrypoint manage loop start

        except Exception as read_err:
            self.logger.error(f"Error reading or processing template '{template_path}': {read_err}", exc_info=True)
            self.memory.set("onboarded", False)
            self.memory.set("onboarding_error", f"Error processing template: {read_err}")

    def start_main_loop(self):
        """Placeholder: Kicks off the agent's main operational loop if not already running."""
        if not self._is_main_loop_running:
            self.logger.info("Onboarding complete. Initiating main operational loop.")
            self._is_main_loop_running = True
            # In a real implementation, this would likely trigger an async task
            # or set a flag that the main agent loop checks.
            # For now, just log the intention.
            # Example: asyncio.create_task(self.run_task_cycle()) 
        else:
            self.logger.info("Main loop already running.")

    def handle_terminate(self, params: dict):
        """Handles the 'terminate' command by setting a flag in memory."""
        reason = params.get("reason", "No reason provided")
        delay = params.get("delay_seconds", 0) # Delay currently not implemented, but logged
        self.logger.warning(f"Termination requested by command. Reason: {reason}. Delay: {delay}s")
        # Setting the signal will be checked by the main loop in agent_entrypoint.py
        self.memory.set("terminate_signal", True)
        self.memory.set("terminate_reason", reason)
        self.logger.info("Terminate signal set in memory.")

    def handle_find_dead_code(self, params: dict) -> list | None:
        """Handles the 'find_dead_code' command by running the sniffer script."""
        target_dir = params.get("target_directory")
        if not target_dir:
            self.logger.error("'find_dead_code' command missing required parameter: 'target_directory'")
            return None # Indicate error

        # Construct absolute path for target if it's relative
        # Assuming relative paths are relative to the workspace root where agent operates
        # This might need adjustment based on how agents perceive paths
        if not os.path.isabs(target_dir):
             # This assumes self.filesystem provides a way to get workspace root or resolve paths
             # Placeholder: Resolve relative to current working directory (less robust)
             abs_target_dir = os.path.abspath(target_dir)
             self.logger.warning(f"Received relative target '{target_dir}', resolved to '{abs_target_dir}'. Ensure this is correct relative to workspace root.")
        else:
            abs_target_dir = target_dir

        if not os.path.isdir(abs_target_dir):
             self.logger.error(f"Target directory does not exist or is not a directory: {abs_target_dir}")
             return None
             
        # Verify the sniffer script exists
        if not os.path.exists(SNIFFER_SCRIPT_PATH):
             self.logger.critical(f"Dead code sniffer script not found at expected location: {SNIFFER_SCRIPT_PATH}")
             return None
             
        self.logger.info(f"Running dead code sniffer on target: {abs_target_dir}")
        command = [
            sys.executable, # Use the agent's python interpreter
            SNIFFER_SCRIPT_PATH,
            abs_target_dir
            # No --dry-run needed as script defaults to it / no deletion implemented
        ]

        try:
            # Execute the script
            # Use a timeout? Redirect stderr?
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=120) # 2 min timeout
            
            self.logger.info(f"Sniffer script finished. Return Code: {result.returncode}")
            if result.stderr:
                 # Log script's stderr messages (where its prints go)
                 self.logger.info(f"Sniffer script stderr output:\n{result.stderr}")
            if result.stdout:
                 # Log script's stdout (if it ever prints there)
                 self.logger.info(f"Sniffer script stdout output:\n{result.stdout}")

            # Vulture outputs findings to stdout. Parse stdout.
            lines = result.stdout.splitlines()
            unused_items = [line for line in lines if "% confidence" in line]

            if result.returncode != 0 and not unused_items:
                # Script exited non-zero but didn't report items via stdout?
                 self.logger.error(f"Sniffer script exited with code {result.returncode} but no findings reported in stdout. Check script stderr logs.")
                 # Treat as error for now, could be more nuanced
                 return None 

            self.logger.info(f"Found {len(unused_items)} potential dead code items.")
            return unused_items # Return the list of finding lines
            
        except subprocess.TimeoutExpired:
             self.logger.error(f"Dead code sniffer timed out after 120 seconds for target: {abs_target_dir}")
             return None
        except Exception as e:
            self.logger.error(f"Error executing dead code sniffer script: {e}", exc_info=True)
            return None

# Example Usage (would likely be instantiated within the agent's entrypoint)
# logger = logging.getLogger("Agent_CommandHandler")
# fs = FilesystemProvider()
# mem = MemoryProvider()
# handler = CommandHandler(agent_id="Agent_2", specialization="coord", filesystem=fs, memory=mem, logger=logger)
# result = handler.handle_command("initial_onboarding", {"prompt_template_path": "../user_prompts/agent_activation_template.txt"})
# print(result) 