import time
import os
import json
import sys # Import sys for path manipulation
import traceback # Import traceback

# Add project root for imports
script_dir = os.path.dirname(__file__) # execution/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Go up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Service Imports ---
try:
    from coordination.agent_bus import AgentBus
    from governance_memory_engine import log_event # Import log_event
    _core_imports_ok = True
except ImportError as e:
    print(f"[ChatGPTExecutor Error ❌] Failed to import core services: {e}")
    _core_imports_ok = False
    # Define dummy log_event and AgentBus for basic execution
    def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")
    class AgentBus:
        def send_task(self, target_agent_id, input_data, task_type): return None
        def _read_tasks(self): return []

# Configuration
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_POLL_INTERVAL = 2
_SOURCE = "ChatGPTExecutor" # Define logging source

class ChatGPTExecutor:
    """Handles sending prompts to the ChatGPT Commander agent via AgentBus
       and retrieving the results.
    """
    def __init__(self, agent_bus=None):
        # Use real AgentBus only if imports succeeded
        self.agent_bus = agent_bus if agent_bus and _core_imports_ok else AgentBus()
        self.target_agent_id = "ChatGPTCommander" # Corrected case
        log_event("EXECUTOR_INIT", _SOURCE, {"target_agent": self.target_agent_id, "imports_ok": _core_imports_ok})

    def execute_prompt(self, messages, chat_title_keyword="", timeout=DEFAULT_TIMEOUT_SECONDS):
        """Sends messages to the ChatGPT Commander agent and waits for the response file.

        Args:
            messages (list): A list of strings, where each string is a message/prompt.
            chat_title_keyword (str, optional): Keyword to find the target chat.
                                               Defaults to "" (uses latest chat).
            timeout (int, optional): Maximum time to wait for the task completion.
                                      Defaults to DEFAULT_TIMEOUT_SECONDS.

        Returns:
            str or None: The content of the response file if successful, None otherwise.
        """
        log_context = {"target_agent": self.target_agent_id, "chat_keyword": chat_title_keyword, "timeout": timeout}
        # print(f"Sending prompt task to {self.target_agent_id}...")
        log_event("EXECUTE_PROMPT_START", _SOURCE, log_context)
        
        if not _core_imports_ok:
            log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "AgentBus unavailable due to import failure"})
            return None
            
        input_data = {
            "chat_title_keyword": chat_title_keyword,
            "messages": messages
        }
        task_id = self.agent_bus.send_task(
            target_agent_id=self.target_agent_id,
            input_data=input_data,
            task_type="chatgpt_prompt"
        )

        if not task_id:
            # print(f"Error: Failed to send task to {self.target_agent_id}.")
            log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Failed to send task via AgentBus"})
            return None

        # print(f"Task {task_id} sent. Waiting for completion (timeout: {timeout}s)...")
        log_context["task_id"] = task_id # Add task_id to context
        log_event("AGENTBUS_TASK_SENT", _SOURCE, {**log_context, "status": "Waiting for completion"})

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                tasks = self.agent_bus._read_tasks() # Use internal read for efficiency here
            except Exception as read_e:
                log_event("AGENTBUS_ERROR", _SOURCE, {**log_context, "error": "Failed to read tasks from AgentBus", "details": str(read_e)})
                time.sleep(DEFAULT_POLL_INTERVAL * 2) # Wait longer on read error
                continue # Skip this iteration
                
            task_status = None
            response_file = None
            error_message = None

            for task in tasks:
                if task.get("task_id") == task_id:
                    task_status = task.get("status")
                    response_file = task.get("response_file")
                    error_message = task.get("error_message")
                    break
            
            if task_status == "complete":
                # print(f"Task {task_id} completed.")
                log_event("AGENTBUS_TASK_COMPLETE", _SOURCE, {**log_context, "status": "complete"})
                if response_file and os.path.exists(response_file):
                    try:
                        with open(response_file, 'r') as f:
                            response_content = f.read()
                        # Optional: Clean up response file?
                        # os.remove(response_file)
                        log_event("EXECUTOR_RESPONSE_READ", _SOURCE, {**log_context, "response_file": response_file})
                        return response_content
                    except Exception as e:
                         # print(f"Error reading response file {response_file}: {e}")
                         log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Error reading response file", "response_file": response_file, "details": str(e)})
                         return None # Indicate error reading result
                else:
                     # print(f"Task {task_id} completed, but response file missing or not specified.")
                     log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "warning": "Task complete, but response file missing/not specified", "response_file": response_file})
                     # Return empty string or None depending on desired behavior
                     return "" 
            elif task_status == "failed":
                 # print(f"Task {task_id} failed. Error: {error_message}")
                 log_event("AGENTBUS_TASK_FAILED", _SOURCE, {**log_context, "status": "failed", "error_message": error_message})
                 return None
            elif task_status in ["pending", "claimed"]:
                 # Task still in progress, wait
                 # log_event("AGENTBUS_TASK_WAITING", _SOURCE, {**log_context, "status": task_status}) # Optional: More verbose logging
                 time.sleep(DEFAULT_POLL_INTERVAL)
            else:
                 # Task not found or unknown status - potential issue
                 # print(f"Warning: Task {task_id} not found or has unexpected status '{task_status}' after {time.time() - start_time:.1f}s.")
                 log_event("AGENTBUS_WARNING", _SOURCE, {**log_context, "warning": "Task not found or unexpected status", "current_status": task_status, "elapsed_time": time.time() - start_time})
                 time.sleep(DEFAULT_POLL_INTERVAL * 2)

        # print(f"Error: Task {task_id} timed out after {timeout} seconds.")
        log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Task timed out"})
        return None

# Example Usage
if __name__ == '__main__':
    # Check dependencies before starting
    if not _core_imports_ok:
        print("Error: Core services failed to import. ChatGPT Executor cannot run.")
        # Exit or handle appropriately
    else:
        executor = ChatGPTExecutor()
        
        # Ensure the chatgpt_commander_agent is running separately
        print("\n--- Example: Sending a simple prompt ---")
        # This requires the agent to be running and logged in.
        # Replace "Test Chat" with a relevant keyword if needed.
        response = executor.execute_prompt(
            messages=["Explain the concept of recursion in one sentence."],
            chat_title_keyword="Test Chat" 
        )

        if response is not None:
            print("\n--- Response Received ---")
            print(response)
            print("-------------------------")
        else:
            print("\nFailed to get response from ChatGPT Commander Agent.") 