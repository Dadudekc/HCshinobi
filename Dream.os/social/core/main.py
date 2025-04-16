"""
Main entry point for the autonomous Cursor control system.
Initializes the AgentBus and starts the necessary agents.
"""
import logging
import time
import os
import sys
import json
import signal
import threading
import portalocker

# Adjust path to import from core
script_dir = os.path.dirname(__file__)
if script_dir not in sys.path:
     sys.path.append(script_dir)
if os.path.basename(script_dir) == "core" and os.path.dirname(script_dir) not in sys.path:
     # If running from core/, need parent directory for core. subdir imports
     sys.path.append(os.path.dirname(script_dir))

from coordination.agent_bus import AgentBus
from agents.cursor_control_agent import CursorControlAgent
from agents.task_executor_agent import TaskExecutorAgent, DEFAULT_TASK_LIST_PATH, TaskStatus
from agents.agent_monitor_agent import AgentMonitorAgent, DEFAULT_LOG_PATH
from agents.prompt_feedback_loop_agent import PromptFeedbackLoopAgent
from agents.task_injector import TaskInjector
from agents.social_media_agent import SocialMediaAgent
from core.utils.task_status_updater import TaskStatusUpdater
from agents.meredith_resonance_scanner import MeredithResonanceScanner

# Setup Logging
log_format = '%(asctime)s - %(threadName)s - %(levelname)s - %(name)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger("MainApp")

# --- Global Variables for Signal Handling ---
global_shutdown_event = threading.Event()
global_agents = []
global_bus = None

def signal_handler(signum, frame):
    """Handles termination signals like SIGINT (Ctrl+C)."""
    logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
    global_shutdown_event.set()

def setup_task_list(task_list_path):
    """Creates a sample task list if it doesn't exist."""
    if not os.path.exists(task_list_path):
        logger.info(f"Creating sample task list at: {task_list_path}")
        sample_tasks = [
            {
                "task_id": "main_demo_task_1",
                "status": TaskStatus.PENDING,
                "action": "RUN_TERMINAL_COMMAND",
                "params": {"command": "echo 'Task 1: Hello from Autonomous Agent!'"},
                "target_agent": "CursorControlAgent",
                "priority": 2, # Lower priority
                "depends_on": [], # No dependencies
                "retry_count": 0
            },
            {
                "task_id": "main_demo_task_2",
                "status": TaskStatus.PENDING,
                "action": "GET_EDITOR_CONTENT",
                "params": {},
                "target_agent": "CursorControlAgent",
                "priority": 1, # Higher priority
                "depends_on": [], # No dependencies
                "retry_count": 0
            },
            {
                "task_id": "main_demo_task_3",
                "status": TaskStatus.PENDING,
                "action": "RUN_TERMINAL_COMMAND",
                "params": {"command": "echo 'Task 3: Running after Task 1 completes.'"},
                "target_agent": "CursorControlAgent",
                "priority": 3,
                "depends_on": ["main_demo_task_1"], # Depends on task 1
                "retry_count": 0
            }
        ]
        try:
            os.makedirs(os.path.dirname(task_list_path), exist_ok=True)
            with open(task_list_path, 'w') as f:
                json.dump(sample_tasks, f, indent=2)
        except IOError as e:
             logger.error(f"Failed to create sample task list: {e}")
             return False
    else:
         logger.info(f"Task list found at: {task_list_path}")
         # Optional: Reset PENDING tasks if desired on startup?
         # with open(task_list_path, 'r+') as f:
         #     tasks = json.load(f)
         #     updated = False
         #     for task in tasks:
         #         if task.get('status') not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.INVALID]:
         #              task['status'] = TaskStatus.PENDING
         #              updated = True
         #     if updated:
         #         f.seek(0)
         #         json.dump(tasks, f, indent=2)
         #         f.truncate()
         #         logger.info("Reset non-terminal tasks in task list to PENDING.")
    return True

def main():
    """Main execution function."""
    global global_agents, global_bus
    logger.info("Starting Autonomous Cursor Control System...")

    # --- Configuration ---
    # Use absolute paths for reliability
    base_dir = os.path.dirname(os.path.abspath(__file__)) # core directory
    project_root = os.path.dirname(base_dir) # Project root directory
    run_dir = os.path.join(project_root, "run")
    mailbox_dir = os.path.join(run_dir, "mailboxes")
    task_list_path = os.path.join(project_root, DEFAULT_TASK_LIST_PATH)
    input_tasks_path = os.path.join(run_dir, "input_tasks.jsonl") # File to watch for new tasks
    log_dir = os.path.join(run_dir, "logs")
    monitor_log_path = os.path.join(log_dir, os.path.basename(DEFAULT_LOG_PATH))
    status_dir = os.path.join(run_dir, "status") # For status files
    os.makedirs(mailbox_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True) # Ensure log dir exists
    os.makedirs(status_dir, exist_ok=True)

    # Setup task list
    if not setup_task_list(task_list_path):
        logger.error("Failed to set up task list. Exiting.")
        return 1

    # Create shared lock for task list access
    task_list_lock = portalocker.Lock(task_list_path + ".lock", fail_when_locked=True, flags=portalocker.LOCK_EX)

    # --- Initialization ---
    try:
        logger.info(f"Initializing AgentBus (Mailbox Dir: {mailbox_dir})...")
        bus = AgentBus(mailbox_base_dir=mailbox_dir)
        global_bus = bus

        logger.info("Initializing TaskStatusUpdater...")
        task_status_updater = TaskStatusUpdater(
            agent_bus=bus,
            task_list_path=os.path.abspath(task_list_path), # Ensure absolute path
            lock=task_list_lock
        )

        logger.info("Initializing CursorControlAgent...")
        # Decide if you want to force a new instance or use existing
        # For dev/demo, launching new might be cleaner if cleanup works
        cursor_agent = CursorControlAgent(agent_bus=bus, launch_new_instance=True)
        if not cursor_agent.coordinator:
             logger.error("CursorControlAgent failed to initialize coordinator. System cannot function.")
             return 1
        global_agents.append(cursor_agent)

        logger.info("Initializing AgentMonitorAgent...")
        monitor_agent = AgentMonitorAgent(agent_bus=bus, log_file_path=monitor_log_path)
        global_agents.append(monitor_agent)
        # Monitor agent currently has no background thread, processes messages via main loop polling

        logger.info("Initializing TaskExecutorAgent...")
        task_executor = TaskExecutorAgent(
            agent_bus=bus,
            task_status_updater=task_status_updater,
            task_list_path=task_list_path,
            task_list_lock=task_list_lock
        )
        global_agents.append(task_executor)

        logger.info("Initializing PromptFeedbackLoopAgent...")
        feedback_agent = PromptFeedbackLoopAgent(
            agent_bus=bus,
            task_list_path=task_list_path,
            task_list_lock=task_list_lock
        )
        global_agents.append(feedback_agent)

        logger.info("Initializing TaskInjector...")
        task_injector = TaskInjector(
            agent_bus=bus,
            task_list_path=task_list_path,
            input_task_file_path=input_tasks_path,
            task_list_lock=task_list_lock
        )
        global_agents.append(task_injector)

        logger.info("Initializing SocialMediaAgent...")
        social_agent = SocialMediaAgent(agent_bus=bus)
        global_agents.append(social_agent)

        logger.info("Initializing MeredithResonanceScanner...")
        meredith_scanner_agent = MeredithResonanceScanner(agent_name="MeredithResonanceScanner", bus=bus)
        global_agents.append(meredith_scanner_agent)

    except Exception as e:
        logger.error(f"Fatal error during agent initialization: {e}", exc_info=True)
        # Attempt cleanup if bus was created
        if global_bus: global_bus.shutdown()
        return 1

    # --- Start Agents ---
    logger.info("Starting agent background threads...")
    task_executor.start() # Start the executor's loop
    feedback_agent.start() # Start the feedback loop's monitoring thread
    task_injector.start() # Start the injector's file watching thread
    # CursorControlAgent currently processes messages directly when bus.process_messages is called,
    # but could be made multi-threaded if needed.
    # SocialMediaAgent needs to be started if it has a background loop
    if hasattr(social_agent, 'start') and callable(social_agent.start):
        social_agent.start()

    # Start MeredithResonanceScanner if it has a start method
    if hasattr(meredith_scanner_agent, 'start') and callable(meredith_scanner_agent.start):
        meredith_scanner_agent.start()

    # --- Main Loop ---
    logger.info("System running. Monitoring tasks and processing messages. Press Ctrl+C to exit.")
    while not global_shutdown_event.is_set():
        try:
            # Periodically process messages waiting for specific agents
            # This allows agents without their own dedicated message processing loops
            # (like TaskExecutorAgent currently) to handle responses.
            # We process messages for the TaskExecutorAgent to handle responses
            # and CursorControlAgent to handle direct commands if any were sent outside the task list.
            # Add AgentMonitorAgent to the polling list to process events it subscribes to
            # Add SocialMediaAgent if it needs polling
            # Add MeredithResonanceScanner for polling
            agents_to_poll = [
                TaskExecutorAgent.AGENT_NAME,
                CursorControlAgent.AGENT_NAME,
                AgentMonitorAgent.AGENT_NAME,
                SocialMediaAgent.AGENT_NAME,
                meredith_scanner_agent.agent_name
            ]
            total_processed = 0
            for agent_name in agents_to_poll:
                processed_count = bus.process_messages(agent_name, max_messages=5) # Process up to 5 per agent per cycle
                if processed_count > 0:
                    logger.debug(f"Processed {processed_count} messages for {agent_name} in main loop.")
                    total_processed += processed_count
            
            # if total_processed == 0:
            #      logger.debug("Main loop: No messages processed in this cycle.")

            # Keep main thread alive, agents run in background
            time.sleep(1) # Check/Process messages roughly every second
        except KeyboardInterrupt:
             logger.warning("KeyboardInterrupt caught in main loop. Initiating shutdown...")
             global_shutdown_event.set()
        except Exception as e:
             logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)
             # Decide if this should trigger shutdown
             # global_shutdown_event.set()

    # --- Shutdown Sequence ---
    logger.info("Shutdown signal received. Stopping agents and cleaning up...")

    # Stop agents in reverse order of dependency (or based on function)
    if task_executor in global_agents:
        task_executor.stop()
    
    if 'feedback_agent' in locals() and feedback_agent in global_agents:
        feedback_agent.stop()
    
    if 'task_injector' in locals() and task_injector in global_agents:
        task_injector.stop()
    
    # Call shutdown on cursor_agent to potentially close the app
    if 'cursor_agent' in locals() and cursor_agent in global_agents:
         cursor_agent.shutdown()
    
    # Call shutdown on monitor_agent
    if 'monitor_agent' in locals() and monitor_agent in global_agents:
        monitor_agent.shutdown()
    
    # Shutdown the bus
    if global_bus:
        global_bus.shutdown()

    logger.info("Autonomous Cursor Control System shutdown complete.")
    return 0

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the main function
    exit_code = main()
    sys.exit(exit_code) 