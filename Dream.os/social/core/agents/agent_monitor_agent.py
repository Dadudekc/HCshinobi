"""
Agent responsible for monitoring the system by listening to messages on the AgentBus
and logging key events to a structured log file.
"""
import logging
import os
import sys
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any

# Adjust path for sibling imports if necessary
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from coordination.agent_bus import AgentBus, Message
    # Get TaskStatus constants if needed for logging standardized statuses
    from agents.task_executor_agent import TaskStatus 
except ImportError:
     logger.warning("Could not import AgentBus/TaskStatus relatively, assuming execution context provides them.")
     # Define dummy classes if needed for standalone script execution
     class AgentBus: 
         def register_agent(self, *args, **kwargs): pass
         def register_handler(self, *args, **kwargs): pass
     class Message: pass
     class TaskStatus: # Dummy statuses
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"
        ERROR = "ERROR"
        DISPATCHED = "DISPATCHED"
        PENDING = "PENDING"
        UNKNOWN = "UNKNOWN"

# Ensure logger setup if not done globally
# Note: This agent primarily writes to its own file, but console logging is useful too.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_NAME = "AgentMonitorAgent"
DEFAULT_LOG_PATH = "run/logs/agent_history.jsonl"

class AgentMonitorAgent:
    """Listens to the AgentBus and logs significant events."""

    def __init__(self, agent_bus: AgentBus, log_file_path: str = DEFAULT_LOG_PATH):
        """
        Initializes the agent monitor.

        Args:
            agent_bus: The central AgentBus instance.
            log_file_path: Path to the JSON Lines file for logging events.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.log_file_path = os.path.abspath(log_file_path)
        self._log_lock = threading.Lock() # Lock for writing to the log file

        # Ensure log directory exists
        try:
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
            # Touch the file to ensure it exists, open in append mode
            with open(self.log_file_path, 'a'): 
                pass 
        except IOError as e:
            logger.error(f"Failed to create log directory or file {self.log_file_path}: {e}")
            raise

        # Register agent
        self.bus.register_agent(self.agent_name, capabilities=["monitoring"])
        
        # Register handler to listen to *all* messages (or specific types)
        # Option 1: Subscribe to all messages (requires AgentBus support)
        # self.bus.register_handler("*', self.handle_event_message) # Assuming '*' means all
        
        # Option 2: Register for specific message types we know are relevant
        # This is less comprehensive but might be more performant/simpler if bus doesn't support '*'
        relevant_message_types = [
            # Task lifecycle events (inferred from TaskExecutor responses)
            f"*RESPONSE", # Catch responses like RUN_TERMINAL_COMMAND_RESPONSE etc.
            # Agent lifecycle events (assuming agents send these)
            "AGENT_REGISTERED",
            "AGENT_SHUTDOWN",
            # Specific errors?
            "ERROR",
            # Potentially subscribe directly to TaskExecutor for dispatch events?
             "TASK_DISPATCHED", # If TaskExecutor emits this
             "TASK_STATUS_UPDATE" # Generic status update message type?
        ]
        # For now, let's assume we can get responses directed TO TaskExecutorAgent
        # and potentially system messages. A better approach might be a dedicated event type.
        # Let's listen for responses sent TO the TaskExecutorAgent as a starting point.
        self.bus.register_handler("TaskExecutorAgent", self.handle_event_message) # Messages sent TO TaskExecutor
        # Also, listen for generic ERROR messages
        self.bus.register_handler("ERROR", self.handle_event_message)
        # If agents register/deregister via messages, listen for those too.

        logger.info(f"{self.agent_name} initialized. Logging events to: {self.log_file_path}")

    def _log_event(self, event_data: Dict[str, Any]):
        """Appends a structured event to the JSON Lines log file (thread-safe)."""
        try:
            event_data["log_timestamp"] = datetime.now().isoformat() # Add monitor timestamp
            log_line = json.dumps(event_data)
            with self._log_lock:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(log_line + '\n')
        except Exception as e:
            logger.error(f"Failed to write event to log file {self.log_file_path}: {e} - Event: {event_data}")

    def handle_event_message(self, message: Message):
        """Processes messages received on the bus and logs relevant events."""
        logger.debug(f"{self.agent_name} received message: Type={message.type}, Sender={message.sender}")
        
        event_type = "unknown_message_received"
        log_details = {
            "sender": message.sender,
            "recipient": message.recipient,
            "message_type": message.type,
            "message_id": message.id,
            "message_status": getattr(message, 'status', None),
            "message_payload": getattr(message, 'payload', None),
            "task_id": getattr(message, 'task_id', None)
        }

        # --- Infer Event Type from Message --- 
        # This logic can be quite complex depending on message conventions

        # 1. Task Status Updates (Responses to TaskExecutorAgent)
        if message.recipient == "TaskExecutorAgent" and hasattr(message, 'task_id') and message.task_id:
            task_status = message.status
            if task_status == "SUCCESS":
                event_type = "task_completed"
            elif task_status in ["FAILED", "ERROR", "EXECUTION_ERROR", "BAD_REQUEST", "UNKNOWN_ACTION"]:
                event_type = "task_failed"
            else:
                 event_type = "task_status_update" # Generic update
        
        # 2. Task Dispatched (Need TaskExecutor to send this, or infer otherwise)
        # Example: If TaskExecutor sent a message *from* itself *about* a task dispatch
        # elif message.sender == "TaskExecutorAgent" and message.type == "TASK_DISPATCHED":
        #     event_type = "task_dispatched"

        # 3. Agent Lifecycle Events (Requires agents to send specific messages)
        # elif message.type == "AGENT_REGISTERED":
        #     event_type = "agent_registered"
        #     log_details["registered_agent"] = message.sender
        # elif message.type == "AGENT_SHUTDOWN":
        #     event_type = "agent_shutdown"
        #     log_details["shutdown_agent"] = message.sender

        # 4. Generic Error Messages
        elif message.type == "ERROR" or getattr(message, 'status', "").startswith("ERROR"):
             event_type = "agent_error"
        
        # Add more specific event handling here based on message types/content

        # --- Log the Event --- 
        log_entry = {
            "timestamp": getattr(message, 'timestamp', datetime.now().isoformat()), # Use message timestamp if available
            "event": event_type,
            "details": log_details
        }
        self._log_event(log_entry)

    def shutdown(self):
        """Perform any cleanup needed for the monitor agent."""
        logger.info(f"Shutting down {self.agent_name}...")
        # No background threads to stop in this simple version
        # Unregister?
        # self.bus.deregister_agent(self.agent_name) 
        logger.info(f"{self.agent_name} shutdown complete.")


# ========= USAGE BLOCK START ==========
# Minimal block for basic checks
if __name__ == "__main__":
    print(f">>> Running module: {__file__} (Basic Checks)")
    dummy_log_file = "./temp_monitor_agent_log.jsonl"

    class DummyMessage:
        def __init__(self, sender, recipient, msg_type, payload, status=None, task_id=None, msg_id="dummy_id"):
            self.sender = sender
            self.recipient = recipient
            self.type = msg_type
            self.payload = payload
            self.status = status
            self.task_id = task_id
            self.id = msg_id
            self.timestamp = datetime.now().isoformat()

    class DummyBus:
        registered_handlers = {}
        def register_agent(self, agent_name, *args, **kwargs): print(f"DummyBus: Registering {agent_name}")
        def register_handler(self, target, handler): 
            print(f"DummyBus: Registering handler for target '{target}'")
            if target not in self.registered_handlers:
                 self.registered_handlers[target] = []
            self.registered_handlers[target].append(handler)
        def send_message(self, *args, **kwargs): pass # Not needed for monitor test
        def get_handler(self, target): return self.registered_handlers.get(target, [])

    try:
        print("\n>>> Instantiating AgentMonitorAgent with DummyBus...")
        bus = DummyBus()
        monitor = AgentMonitorAgent(agent_bus=bus, log_file_path=dummy_log_file)
        print(">>> Monitor instantiated.")

        print("\n>>> Simulating messages...")
        # Simulate a task completion response TO TaskExecutorAgent
        msg1 = DummyMessage("CursorControlAgent", "TaskExecutorAgent", "RUN_CMD_RESPONSE", {"output": "OK"}, "SUCCESS", "task123")
        # Simulate a task failure response TO TaskExecutorAgent
        msg2 = DummyMessage("CursorControlAgent", "TaskExecutorAgent", "GET_CONTENT_RESPONSE", {"error": "Timeout"}, "FAILED", "task456")
        # Simulate a generic ERROR message
        msg3 = DummyMessage("SomeOtherAgent", "Coordinator", "ERROR", {"details": "Config not found"})
        # Simulate a message not matching specific handlers
        msg4 = DummyMessage("WebAppAgent", "TaskExecutorAgent", "USER_QUERY", {"query": "status"}, task_id="task789")

        # Manually trigger handlers (as bus processing isn't running)
        print("\n>>> Triggering handlers...")
        handlers_exec = bus.get_handler("TaskExecutorAgent")
        handlers_error = bus.get_handler("ERROR")
        for handler in handlers_exec:
             handler(msg1)
             handler(msg2)
             handler(msg4) # Should log as unknown_message_received
        for handler in handlers_error:
             handler(msg3)

        print("\n>>> Checking log file content...")
        log_content = []
        if os.path.exists(dummy_log_file):
            with open(dummy_log_file, 'r') as f:
                for line in f:
                     try: log_content.append(json.loads(line))
                     except json.JSONDecodeError: print(f"WARN: Invalid JSON line: {line.strip()}")
        else:
             print("ERROR: Log file not created!")

        print(json.dumps(log_content, indent=2))
        
        # Basic assertions
        assert len(log_content) == 4
        assert log_content[0]["event"] == "task_completed"
        assert log_content[0]["details"]["task_id"] == "task123"
        assert log_content[1]["event"] == "task_failed"
        assert log_content[1]["details"]["task_id"] == "task456"
        assert log_content[2]["event"] == "unknown_message_received" # User query not specifically handled
        assert log_content[2]["details"]["task_id"] == "task789"
        assert log_content[3]["event"] == "agent_error"
        print(">>> Log file content looks correct.")

    except Exception as e:
        print(f"ERROR in usage block: {e}", file=sys.stderr)
        raise
    finally:
        if os.path.exists(dummy_log_file):
             try:
                 os.remove(dummy_log_file)
                 print(f"Removed dummy log file: {dummy_log_file}")
             except OSError as e:
                  print(f"Error removing dummy log file: {e}")

    print(f">>> Module {filename} basic checks complete.")
    sys.exit(0)
# ========= USAGE BLOCK END ========== 