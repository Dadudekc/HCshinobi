import json
import os
import time
import random # Import random
import sys # Import sys for path manipulation
from datetime import datetime, timezone # Import timezone
import traceback # Import traceback

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Service Imports ---
try:
    from utils.browser_controller import BrowserController
    from core.coordination.agent_bus import AgentBus # CORRECTED IMPORT
    from utils.performance_logger import PerformanceLogger # Import PerformanceLogger
    from governance_memory_engine import log_event # Import log_event
    _core_imports_ok = True
except ImportError as e:
    print(f"[ChatGPTCommander Error ❌] Failed to import core services: {e}")
    _core_imports_ok = False
    # Define dummy log_event
    # REMOVED DUMMY AgentBus
    # REMOVED DUMMY PerformanceLogger
    # REMOVED DUMMY BrowserController
    # Define dummy log_event only if governance_memory_engine failed
    # A more robust approach would be to have fallback logging
    # or make core components mandatory.
    # For now, assuming failure means agent cannot run meaningfully.
    if "governance_memory_engine" in str(e):
        def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")
    # Re-raise or exit if critical components are missing?
    print("FATAL: Critical core components failed to import. Agent cannot function.")
    # Consider exiting: sys.exit(1)

# --- Configuration ---
# TASKS_FILE = "tasks/chatgpt_messages.json" # No longer primary source
COOKIES_PATH = "secrets/cookies.json"
LOG_DIR = "memory/chat_logs"
AGENT_ID = "ChatGPTCommander" # Corrected Agent ID case
_SOURCE = AGENT_ID # Define logging source
POLL_INTERVAL_SECONDS = 10 # How often to check for new tasks

# --- Helper Functions ---
# load_tasks is removed as tasks come from AgentBus

# --- Helper Functions ---
def save_log(log_data, chat_title, task_id, log_dir=LOG_DIR):
    """Saves the conversation log to a timestamped JSON file, linked to a task."""
    log_context = {"method": "save_log", "task_id": task_id, "chat_title": chat_title}
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            # print(f"Created log directory: {log_dir}")
            log_event("AGENT_INFO", _SOURCE, {**log_context, "message": "Created log directory", "log_dir": log_dir})
        except Exception as mkdir_e:
            log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": "Failed to create log directory", "log_dir": log_dir, "details": str(mkdir_e)})
            return None # Cannot save if dir creation fails

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize title for filename
    safe_title = "".join(c for c in chat_title if c.isalnum() or c in (' ', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_') if safe_title else "untitled_chat"
    # Include task_id in filename for better tracking
    filename = f"{safe_title}_task_{task_id}_{timestamp}.json"
    filepath = os.path.join(log_dir, filename)
    log_context["filepath"] = filepath

    try:
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=4)
        # print(f"Log saved successfully to {filepath}")
        log_event("AGENT_LOG_SAVED", _SOURCE, {**log_context, "message": "Log saved successfully"})
        return filepath # Return the path to the log file
    except Exception as e:
        # print(f"Error saving log file {filepath}: {e}")
        log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": "Error saving log file", "details": str(e)})
        return None

# --- Main Agent Logic ---
def process_single_task(self, task):
    """Processes a single task received from the AgentBus."""
    task_id = task.get('task_id', 'UNKNOWN_TASK') # Handle missing key
    task_type = task.get('task_type', 'chatgpt_command') # Get task type
    log_context = {"task_id": task_id, "task_type": task_type}
    # print(f"\n--- Processing Task {task_id} ({task_type}) ---")
    log_event("AGENT_TASK_PROCESSING_START", _SOURCE, log_context)
    start_time = datetime.now(timezone.utc) # Record start time in UTC
    
    if not _core_imports_ok:
         log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": "AgentBus unavailable due to import failure, cannot complete task."})
         # Cannot complete task, need to handle this state properly without AgentBus instance
         # Maybe raise exception here?
         print("ERROR: Cannot proceed, core imports failed.")
         return # Or raise
    
    # REMOVE LOCAL INSTANTIATION - AgentBus instance should be passed in during __init__
    # agent_bus = AgentBus() # Create instance for task completion
    # Assume self.agent_bus exists if agent was initialized correctly
    agent_bus = self.agent_bus # Requires agent_bus to be passed to the class/method
    
    input_data = task.get("input", {})
    input_summary = f"chat: '{input_data.get('chat_title_keyword', 'LATEST')}', msgs: {len(input_data.get('messages', []))}"
    output_summary = None
    final_status = "ERROR" # Default to error unless success
    error_message = None
    full_response_text = None # Initialize
    result_data = None # Initialize

    # Validate input immediately
    if not isinstance(input_data, dict):
        error_message = "Task input format invalid."
        # print(f"Error: {error_message} Found: {type(input_data)}")
        log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": error_message, "input_type": str(type(input_data))})
        agent_bus.complete_task(task_id, is_error=True, error_message=error_message)
        # Log performance even for input validation failure
        end_time = datetime.now(timezone.utc)
        PerformanceLogger.log_outcome(
            task_id=task_id, agent_id=AGENT_ID, task_type=task_type, status="ERROR",
            start_time=start_time, end_time=end_time, error_message=error_message,
            input_summary=input_summary
        )
        return

    chat_title_keyword = input_data.get("chat_title_keyword", "")
    messages_to_send = input_data.get("messages", [])

    if not messages_to_send:
        error_message = "No messages provided in task input."
        # print(f"Error: {error_message}")
        log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": error_message})
        agent_bus.complete_task(task_id, is_error=True, error_message=error_message)
        end_time = datetime.now(timezone.utc)
        PerformanceLogger.log_outcome(
            task_id=task_id, agent_id=AGENT_ID, task_type=task_type, status="ERROR",
            start_time=start_time, end_time=end_time, error_message=error_message,
            input_summary=input_summary
        )
        return

    controller = None # Initialize controller to None for finally block
    conversation_log = []
    all_responses = []
    log_filepath = None
    success = False # Track if main logic succeeds

    try:
        controller = BrowserController(cookies_path=COOKIES_PATH)
        # print("\nStep 1: Attempting Login...")
        log_event("AGENT_TASK_STEP", _SOURCE, {**log_context, "step": "Login via cookies"})
        if not controller.login_via_cookies():
            raise Exception("Login via cookies failed.")

        # print("\nStep 2: Finding Chat...")
        log_event("AGENT_TASK_STEP", _SOURCE, {**log_context, "step": "Find chat", "keyword": chat_title_keyword})
        if not controller.find_chat_by_title(chat_title_keyword if chat_title_keyword else "", fallback_to_latest=True):
            raise Exception(f"Failed to find chat matching '{chat_title_keyword}' or fallback.")

        # print("\nStep 3: Processing Messages...")
        log_event("AGENT_TASK_STEP", _SOURCE, {**log_context, "step": "Processing messages", "count": len(messages_to_send)})
        for i, message in enumerate(messages_to_send):
            # print(f"\n--- Sending Message {i+1}/{len(messages_to_send)} ---")
            # print(f"Message: {message[:100]}..." if len(message) > 100 else f"Message: {message}")
            log_event("AGENT_ACTION_START", _SOURCE, {**log_context, "action": "Send message", "index": i+1, "total": len(messages_to_send)})
            log_entry = {"prompt": message, "response": None, "timestamp": datetime.now().isoformat()}

            if controller.send_message(message, simulate_typing=True):
                response = controller.get_latest_response()
                if response:
                    # print(f"Response {i+1} received.")
                    log_event("AGENT_ACTION_SUCCESS", _SOURCE, {**log_context, "action": "Received response", "index": i+1})
                    log_entry["response"] = response
                    all_responses.append(response)
                else:
                    # Treat failure to get response as potentially recoverable for logging, but raise error for task status
                    # print(f"Failed to get response for message {i+1}.")
                    log_event("AGENT_WARNING", _SOURCE, {**log_context, "warning": "Failed to get response", "index": i+1})
                    log_entry["response"] = "<ERROR: Failed to retrieve response>"
                    all_responses.append(None)
                    # Don't raise immediately, let loop finish, mark task failed later
            else:
                # Treat failure to send as critical
                raise Exception(f"Failed to send message {i+1} during task execution.")

            conversation_log.append(log_entry)
            time.sleep(random.uniform(1, 3))

        # Check if any response failed to retrieve
        if None in all_responses and any(r is not None for r in all_responses):
             # print("Warning: Some responses failed to retrieve.")
             log_event("AGENT_WARNING", _SOURCE, {**log_context, "warning": "Some responses failed to retrieve"})
             # Decide if this constitutes a full task failure or partial success
             # For now, let's count it as success but log potentially reflects partial data

        # print("\nStep 4: Saving Log...")
        log_event("AGENT_TASK_STEP", _SOURCE, {**log_context, "step": "Save conversation log"})
        log_title_base = chat_title_keyword if chat_title_keyword else "CommanderSession"
        log_filepath = save_log(
            {"task_id": task_id, "input": input_data, "conversation": conversation_log},
            log_title_base,
            task_id # Pass task_id to save_log
        )

        # Construct output summary
        output_summary = f"log: {os.path.basename(log_filepath) if log_filepath else 'N/A'}, responses: {len(all_responses)}"
        
        # Construct result data
        full_response_text = "\n\n---\n\n".join(filter(None, all_responses)) # Combine responses
        result_data = {"conversation_log_path": log_filepath, "responses": all_responses}

        # If we reached here without critical errors, mark success
        final_status = "SUCCESS"
        success = True

    except Exception as e:
        error_message = str(e)
        # print(f"An error occurred during task {task_id} execution: {error_message}")
        log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": "Exception during task execution", "details": error_message, "traceback": traceback.format_exc()})
        # Mark final status as ERROR
        final_status = "ERROR" 
        # Attempt to save partial log if any messages were processed
        if conversation_log:
             save_log(
                 {"task_id": task_id, "status": "PARTIAL_ERROR", "error_message": error_message, "input": input_data, "conversation": conversation_log},
                 "ErrorSession",
                 task_id
             )
        # Mark task as failed on the bus - This will be handled by the performance logger block now
        # agent_bus.complete_task(task_id, is_error=True, error_message=error_message)

    finally:
        end_time = datetime.now(timezone.utc) # Record end time
        # Ensure browser is closed
        if controller:
            try:
                controller.close()
            except Exception as close_e:
                 log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": "Failed to close browser controller", "details": str(close_e)})
        
        # Mark task complete on the bus (success or failure)
        try:
            agent_bus.complete_task(
                task_id=task_id, 
                response_file_content=full_response_text, # Can be None
                is_error=(final_status != "SUCCESS"), 
                error_message=error_message if final_status != "SUCCESS" else None,
                result=result_data # Pass structured result/error details
            )
            log_event("AGENT_TASK_COMPLETED_BUS", _SOURCE, {**log_context, "final_status": final_status})
        except Exception as bus_e:
            log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": "Failed to mark task complete on AgentBus", "details": str(bus_e)})

        # Log performance outcome regardless of success or failure
        try:
            PerformanceLogger.log_outcome(
                task_id=task_id,
                agent_id=AGENT_ID,
                task_type=task_type,
                status=final_status,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message, # Will be None on success
                input_summary=input_summary,
                output_summary=output_summary # May be None if error occurred early
            )
        except Exception as perf_e:
             log_event("AGENT_ERROR", _SOURCE, {**log_context, "error": "Failed to log performance outcome", "details": str(perf_e)})


def run_chatgpt_commander_agent_loop(self):
    """Runs the agent loop, checking the AgentBus for tasks."""
    # print(f"--- Starting ChatGPT Commander Agent ({AGENT_ID}) ---")
    log_event("AGENT_LOOP_START", _SOURCE, {"poll_interval": POLL_INTERVAL_SECONDS})
    
    if not _core_imports_ok:
         log_event("AGENT_CRITICAL", _SOURCE, {"error": "Core services unavailable, cannot run commander loop."})
         return
         
    agent_bus = AgentBus()
    # print(f"Polling {agent_bus.inbox_file} every {POLL_INTERVAL_SECONDS} seconds for tasks...")
    log_event("AGENT_INFO", _SOURCE, {"message": "Polling for tasks", "target_inbox": agent_bus.inbox_file})

    while True:
        try:
            pending_tasks = agent_bus.get_pending_tasks(target_agent_id=AGENT_ID)

            if pending_tasks:
                # print(f"Found {len(pending_tasks)} pending task(s).")
                log_event("AGENT_TASKS_FOUND", _SOURCE, {"count": len(pending_tasks)})
                # Process one task per loop iteration for simplicity
                task_to_process = pending_tasks[0]
                task_id_to_process = task_to_process.get('task_id', 'UNKNOWN_TASK') # Get ID for logging

                # Claim the task
                if agent_bus.claim_task(task_id_to_process, agent_id=AGENT_ID):
                    log_event("AGENT_TASK_CLAIMED", _SOURCE, {"task_id": task_id_to_process})
                    # Process the claimed task
                    self.process_single_task(task_to_process)
                    # Brief pause after processing before checking again
                    time.sleep(1)
                else:
                    # Claim failed (maybe another instance got it?), wait before retrying
                    # print(f"Failed to claim task {task_to_process['task_id']}, likely claimed by another instance or error.")
                    log_event("AGENT_TASK_CLAIM_FAILED", _SOURCE, {"task_id": task_id_to_process})
                    time.sleep(POLL_INTERVAL_SECONDS / 2)

            else:
                # No tasks found, wait for the poll interval
                # print(".", end="", flush=True) # Optional: print dot for visual feedback
                log_event("AGENT_LOOP_POLL", _SOURCE, {"status": "No pending tasks"})
                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            # print("\nCtrl+C detected. Shutting down agent loop.")
            log_event("AGENT_LOOP_STOP", _SOURCE, {"reason": "KeyboardInterrupt"})
            break
        except Exception as e:
            # print(f"\nAn unexpected error occurred in the main loop: {e}")
            # print("Agent loop will restart after a short delay...")
            log_event("AGENT_LOOP_ERROR", _SOURCE, {"error": "Unexpected exception in main loop", "details": str(e), "traceback": traceback.format_exc()})
            time.sleep(30) # Delay before restarting loop after major error

# --- Run Agent ---
if __name__ == '__main__':
    # Ensure necessary directories exist (AgentBus constructor handles outbox)
    os.makedirs(os.path.dirname(COOKIES_PATH), exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # Create placeholder files if they don't exist
    if not os.path.exists(COOKIES_PATH):
        with open(COOKIES_PATH, 'w') as f:
            json.dump([], f)
        print(f"Created placeholder cookies file: {COOKIES_PATH}")

    # Placeholder task file is no longer needed for operation
    # AgentBus ensures shared_inbox.json exists

    # Check dependencies before starting
    if not _core_imports_ok:
        print("Error: Core services failed to import. ChatGPT Commander cannot start.")
        # Exit or handle appropriately
    else:
        # Start the agent loop
        print("ChatGPT Commander starting...") # Keep startup print
        run_chatgpt_commander_agent_loop() 