import unittest
import os
import sys
import json
import time
from queue import Queue, Empty
from threading import Lock
from unittest.mock import MagicMock, patch

# Adjust path
script_dir = os.path.dirname(__file__)
integration_dir = script_dir # tests/integration/
project_root = os.path.dirname(os.path.dirname(integration_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Add core paths
core_path = os.path.join(project_root, 'core')
coordination_path = os.path.join(project_root, 'core', 'coordination')
agents_path = os.path.join(project_root, 'core', 'agents')
utils_path = os.path.join(project_root, 'core', 'utils')
for p in [core_path, coordination_path, agents_path, utils_path]:
     if p not in sys.path:
         sys.path.insert(0, p)

# Mock low-level dependencies before importing agents
sys.modules['core.coordination.cursor_coordinator'] = MagicMock()

# Import Agents and Utilities
from core.agents.task_executor_agent import TaskExecutorAgent, TaskStatus
from core.agents.cursor_control_agent import CursorControlAgent
from core.agents.agent_monitor_agent import AgentMonitorAgent
# from core.agents.prompt_feedback_loop_agent import PromptFeedbackLoopAgent # Cannot test yet
from core.utils.task_status_updater import TaskStatusUpdater
from core.coordination.agent_bus import AgentBus, Message # Need real AgentBus structure

# --- Mock AgentBus with Simple Queueing --- 
# More functional than MagicMock for integration tests
class MockQueueAgentBus:
    def __init__(self):
        self.agents = {}
        self.handlers = {}
        self.message_queues = {}
        self.queue_locks = {}
        self.capabilities = {}
        self._id_counter = 0
        self._id_lock = Lock()

    def _get_next_id(self):
        with self._id_lock:
            self._id_counter += 1
            return f"mock_msg_{self._id_counter}"

    def register_agent(self, agent_name, capabilities=None, handler=None):
        print(f"[MockBus] Registering agent: {agent_name}")
        self.agents[agent_name] = handler # Store main handler if provided
        self.capabilities[agent_name] = capabilities or []
        if agent_name not in self.message_queues:
            self.message_queues[agent_name] = Queue()
            self.queue_locks[agent_name] = Lock()

    def register_handler(self, target_name_or_type, handler):
        print(f"[MockBus] Registering handler for: {target_name_or_type}")
        if target_name_or_type not in self.handlers:
            self.handlers[target_name_or_type] = []
        self.handlers[target_name_or_type].append(handler)

    def send_message(self, sender, recipient, message_type, payload, status=None, request_id=None, task_id=None):
        msg_id = self._get_next_id()
        message = MagicMock() # Use MagicMock to easily set attributes
        message.id = msg_id
        message.sender = sender
        message.recipient = recipient
        message.type = message_type
        message.payload = payload
        message.status = status
        message.request_id = request_id
        message.task_id = task_id
        message.timestamp = time.time()
        
        print(f"[MockBus] Send: {sender} -> {recipient} ({message_type}) Task: {task_id} Status: {status} ID: {msg_id}")
        
        delivered = False
        # Deliver to specific recipient queue
        if recipient in self.message_queues:
            with self.queue_locks[recipient]:
                self.message_queues[recipient].put(message)
            delivered = True
        # Deliver to handlers registered for message type
        if message_type in self.handlers:
             for handler in self.handlers[message_type]:
                 try: handler(message) # Call directly for simplicity
                 except Exception as e: print(f"[MockBus] Error in type handler: {e}")
             delivered = True
        # Deliver to handlers registered for recipient name (redundant? depends on AgentBus logic)
        # if recipient in self.handlers:
        #     for handler in self.handlers[recipient]:
        #         try: handler(message)
        #         except Exception as e: print(f"[MockBus] Error in recipient handler: {e}")
        #     delivered = True
            
        if not delivered:
            print(f"[MockBus] Warning: Message ID {msg_id} not delivered to any queue or handler.")
            
        return msg_id # Return message ID

    def process_messages(self, agent_name, max_messages=1):
        """Simplified processing: Get message and call agent's main handler."""
        count = 0
        if agent_name in self.message_queues:
            agent_handler = self.agents.get(agent_name)
            if not agent_handler:
                 print(f"[MockBus] No main handler registered for {agent_name} to process queue.")
                 return 0
            try:
                with self.queue_locks[agent_name]:
                    for _ in range(max_messages):
                        message = self.message_queues[agent_name].get_nowait()
                        print(f"[MockBus] Processing message for {agent_name}: ID={message.id} Type={message.type}")
                        try:
                            agent_handler(message) # Use the main registered handler
                            count += 1
                        except Exception as e:
                            print(f"[MockBus] Error processing message {message.id} for {agent_name}: {e}")
                        self.message_queues[agent_name].task_done()
            except Empty:
                pass # No messages
        return count

    def get_agents_with_capability(self, capability):
        """Basic mock capability lookup."""
        return [name for name, caps in self.capabilities.items() if capability in caps]


# --- Test Class --- 
class TestCoreTaskExecution(unittest.TestCase):

    def setUp(self):
        self.bus = MockQueueAgentBus()
        self.mock_coordinator = MagicMock()
        self.test_task_list_path = "./temp_integration_tasks.json"
        self.test_log_path = "./temp_integration_monitor.jsonl"
        self.lock = Lock() # Use a real lock for testing interactions

        # Clean up files before test
        if os.path.exists(self.test_task_list_path):
            os.remove(self.test_task_list_path)
        if os.path.exists(self.test_log_path):
             os.remove(self.test_log_path)
        if os.path.exists(self.test_task_list_path + ".lock"): # Clean lock file too
             os.remove(self.test_task_list_path + ".lock")

    def tearDown(self):
         # Clean up files after test
        if os.path.exists(self.test_task_list_path):
            os.remove(self.test_task_list_path)
        if os.path.exists(self.test_log_path):
             os.remove(self.test_log_path)
        if os.path.exists(self.test_task_list_path + ".lock"): 
             os.remove(self.test_task_list_path + ".lock")

    def _create_test_task_list(self, tasks):
        with open(self.test_task_list_path, 'w') as f:
            json.dump(tasks, f, indent=2)

    def test_simple_task_execution_success(self):
        """Test dispatch, execution (mocked success), and completion update."""
        # --- Setup ---
        initial_tasks = [
            {"task_id": "int-task-1", "status": "PENDING", "action": "RUN_TERMINAL_COMMAND", "params": {"command": "echo OK"}, "priority": 1}
        ]
        self._create_test_task_list(initial_tasks)

        # Mock CursorCoordinator behavior
        self.mock_coordinator.run_terminal_command.return_value = True # Simulate success
        
        # Patch the CursorCoordinator instantiation within CursorControlAgent
        with patch('core.agents.cursor_control_agent.CursorCoordinator', return_value=self.mock_coordinator):
            # Instantiate Agents
            updater = TaskStatusUpdater(agent_bus=self.bus, task_list_path=self.test_task_list_path, lock=self.lock)
            executor = TaskExecutorAgent(agent_bus=self.bus, task_status_updater=updater, task_list_path=self.test_task_list_path, task_list_lock=self.lock)
            controller = CursorControlAgent(agent_bus=self.bus)
            monitor = AgentMonitorAgent(agent_bus=self.bus, log_file_path=self.test_log_path)

            # --- Execution --- 
            # 1. Executor runs, finds task, dispatches message
            print("\n>>> Executor Run Cycle 1...")
            executor.run_cycle()
            time.sleep(0.1) # Allow potential message processing

            # 2. Process message for CursorControlAgent
            print("\n>>> Processing message for Controller...")
            # Need to manually trigger handler or simulate bus processing
            # Find the message in the queue
            controller_queue = self.bus.message_queues.get(controller.agent_name)
            self.assertIsNotNone(controller_queue)
            try:
                 msg_to_controller = controller_queue.get(timeout=1)
                 controller.handle_message(msg_to_controller) # Call handler directly
                 controller_queue.task_done()
            except Empty:
                self.fail("Message not delivered to CursorControlAgent queue")
            
            time.sleep(0.1)
            
            # 3. Process response message for TaskExecutorAgent
            print("\n>>> Processing response for Executor...")
            executor_queue = self.bus.message_queues.get(executor.agent_name)
            self.assertIsNotNone(executor_queue)
            try:
                 msg_to_executor = executor_queue.get(timeout=1)
                 executor.handle_response(msg_to_executor) # Call handler directly
                 executor_queue.task_done()
            except Empty:
                self.fail("Response message not delivered to TaskExecutorAgent queue")

            # --- Verification --- 
            # Check coordinator was called
            self.mock_coordinator.run_terminal_command.assert_called_once_with("echo OK", wait=True)

            # Check final task status in file (requires reading the file)
            with open(self.test_task_list_path, 'r') as f:
                final_tasks = json.load(f)
            self.assertEqual(len(final_tasks), 1)
            self.assertEqual(final_tasks[0]['task_id'], "int-task-1")
            self.assertEqual(final_tasks[0]['status'], TaskStatus.COMPLETED)
            self.assertIsNotNone(final_tasks[0].get('result_summary')) # Updater adds summary

            # Check monitor log (optional)
            with open(self.test_log_path, 'r') as f:
                 log_lines = f.readlines()
            # Expect at least task completed event
            self.assertTrue(any('"event": "task_completed"' in line for line in log_lines))
            self.assertTrue(any('"task_id": "int-task-1"' in line for line in log_lines))

    def test_simple_task_execution_failure(self):
        """Test dispatch, execution (mocked failure), and failure update."""
        # --- Setup ---
        initial_tasks = [
            {"task_id": "int-task-fail-1", "status": "PENDING", "action": "RUN_TERMINAL_COMMAND", "params": {"command": "bad command"}, "priority": 1}
        ]
        self._create_test_task_list(initial_tasks)

        # Mock CursorCoordinator behavior for failure
        self.mock_coordinator.run_terminal_command.return_value = False # Simulate failure
        
        with patch('core.agents.cursor_control_agent.CursorCoordinator', return_value=self.mock_coordinator):
            updater = TaskStatusUpdater(agent_bus=self.bus, task_list_path=self.test_task_list_path, lock=self.lock)
            executor = TaskExecutorAgent(agent_bus=self.bus, task_status_updater=updater, task_list_path=self.test_task_list_path, task_list_lock=self.lock)
            controller = CursorControlAgent(agent_bus=self.bus)
            monitor = AgentMonitorAgent(agent_bus=self.bus, log_file_path=self.test_log_path)

            # --- Execution --- 
            print("\n>>> Executor Run Cycle (Failure Test)...")
            executor.run_cycle()
            time.sleep(0.1)

            print("\n>>> Processing message for Controller (Failure Test)...")
            controller_queue = self.bus.message_queues.get(controller.agent_name)
            self.assertIsNotNone(controller_queue)
            try:
                 msg_to_controller = controller_queue.get(timeout=1)
                 controller.handle_message(msg_to_controller)
                 controller_queue.task_done()
            except Empty:
                self.fail("Message not delivered to CursorControlAgent queue")
            
            time.sleep(0.1)
            
            print("\n>>> Processing response for Executor (Failure Test)...")
            executor_queue = self.bus.message_queues.get(executor.agent_name)
            self.assertIsNotNone(executor_queue)
            try:
                 msg_to_executor = executor_queue.get(timeout=1)
                 executor.handle_response(msg_to_executor)
                 executor_queue.task_done()
            except Empty:
                self.fail("Response message not delivered to TaskExecutorAgent queue")

            # --- Verification --- 
            self.mock_coordinator.run_terminal_command.assert_called_once_with("bad command", wait=True)

            with open(self.test_task_list_path, 'r') as f:
                final_tasks = json.load(f)
            self.assertEqual(len(final_tasks), 1)
            self.assertEqual(final_tasks[0]['task_id'], "int-task-fail-1")
            # Check for FAILED or ERROR status (depending on normalization)
            self.assertIn(final_tasks[0]['status'], [TaskStatus.FAILED, TaskStatus.ERROR]) 
            self.assertIsNotNone(final_tasks[0].get('error_details')) # Updater adds error details

            with open(self.test_log_path, 'r') as f:
                 log_lines = f.readlines()
            self.assertTrue(any('"event": "task_failed"' in line for line in log_lines))
            self.assertTrue(any('"task_id": "int-task-fail-1"' in line for line in log_lines))

    # TODO: Add test for task dependency flow
    def test_task_dependency_flow(self):
        """Test that a task is only dispatched after its dependency is COMPLETED."""
        # --- Setup ---
        initial_tasks = [
            {"task_id": "dep-task", "status": "PENDING", "action": "GET_EDITOR_CONTENT", "priority": 1},
            {"task_id": "main-task", "status": "PENDING", "action": "RUN_TERMINAL_COMMAND", "params": {"command": "dep complete"}, "priority": 2, "depends_on": ["dep-task"]}
        ]
        self._create_test_task_list(initial_tasks)

        # Mock Coordinator behavior
        self.mock_coordinator.get_editor_content.return_value = "Some content"
        self.mock_coordinator.run_terminal_command.return_value = True

        with patch('core.agents.cursor_control_agent.CursorCoordinator', return_value=self.mock_coordinator):
            updater = TaskStatusUpdater(agent_bus=self.bus, task_list_path=self.test_task_list_path, lock=self.lock)
            executor = TaskExecutorAgent(agent_bus=self.bus, task_status_updater=updater, task_list_path=self.test_task_list_path, task_list_lock=self.lock)
            controller = CursorControlAgent(agent_bus=self.bus)
            # Monitor agent not strictly needed for this test flow, but harmless
            monitor = AgentMonitorAgent(agent_bus=self.bus, log_file_path=self.test_log_path)

            # --- Execution Cycle 1: Dispatch dep-task --- 
            print("\n>>> Executor Run Cycle (Dependency Test - Cycle 1)...")
            executor.run_cycle()
            time.sleep(0.1)

            # Verify only dep-task message is sent (main-task blocked)
            self.assertEqual(self.bus.message_queues[controller.agent_name].qsize(), 1, "Only dependency task should be queued initially")
            msg_to_controller = self.bus.message_queues[controller.agent_name].get(timeout=1)
            self.assertEqual(msg_to_controller.task_id, "dep-task")
            self.bus.message_queues[controller.agent_name].task_done()
            
            # --- Simulate dep-task completion --- 
            print("\n>>> Simulating dep-task completion...")
            controller.handle_message(msg_to_controller) # Controller processes dep-task
            time.sleep(0.1)
            executor_queue = self.bus.message_queues.get(executor.agent_name)
            msg_to_executor = executor_queue.get(timeout=1) # Executor receives response
            executor.handle_response(msg_to_executor) # Executor processes response, updates dep-task to COMPLETED
            executor_queue.task_done()

            # Verify dep-task is marked completed in file
            with open(self.test_task_list_path, 'r') as f:
                tasks_after_dep = json.load(f)
            dep_task_status = next((t['status'] for t in tasks_after_dep if t['task_id'] == 'dep-task'), None)
            self.assertEqual(dep_task_status, TaskStatus.COMPLETED)

            # --- Execution Cycle 2: Dispatch main-task --- 
            print("\n>>> Executor Run Cycle (Dependency Test - Cycle 2)...")
            executor.run_cycle()
            time.sleep(0.1)

            # Verify main-task message is now sent
            self.assertEqual(self.bus.message_queues[controller.agent_name].qsize(), 1, "Main task should be queued now")
            msg2_to_controller = self.bus.message_queues[controller.agent_name].get(timeout=1)
            self.assertEqual(msg2_to_controller.task_id, "main-task")
            self.bus.message_queues[controller.agent_name].task_done()

            # --- Verification --- 
            # Verify coordinator calls happened for both tasks
            self.mock_coordinator.get_editor_content.assert_called_once()
            # Need to process the second message to trigger this
            # controller.handle_message(msg2_to_controller) 
            # self.mock_coordinator.run_terminal_command.assert_called_once_with("dep complete", wait=True)

            # Verify final status of main-task (should be DISPATCHED after cycle 2)
            with open(self.test_task_list_path, 'r') as f:
                tasks_final = json.load(f)
            main_task_status = next((t['status'] for t in tasks_final if t['task_id'] == 'main-task'), None)
            self.assertEqual(main_task_status, TaskStatus.DISPATCHED)

    # TODO: Add test for feedback loop integration (when agent is available)

if __name__ == '__main__':
    unittest.main() 