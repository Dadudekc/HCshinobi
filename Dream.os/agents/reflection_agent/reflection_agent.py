import os
# import sys # Not needed if sys.path manipulation is removed
import asyncio
import json
import traceback
import logging # Add logger import
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional, Any
from uuid import uuid4

# Update core imports
# from dreamforge.core.base_agent import BaseAgent
from core.coordination.base_agent import BaseAgent # Placeholder: Update if BaseAgent location changed
# from dreamforge.core.coordination.agent_bus import AgentBus, Message, MessageType, BusError
from core.coordination.agent_bus import AgentBus, BusError # Removed Message, MessageType
# from dreamforge.core.governance_memory_engine import log_event as log_governance_event
# Assuming governance_memory_engine moved to core/governance/
from core.memory.governance_memory_engine import log_event as log_governance_event # Verified path

# Inherit from BaseAgent
class ReflectionAgent(BaseAgent):
    """Agent responsible for reflecting on and responding to governance alerts.
    Uses BaseAgent for core lifecycle, bus interaction, and logging.
    """

    # Modify __init__ signature and logic
    # def __init__(self, config: Dict[str, Any]):
    def __init__(self, agent_id: str, agent_bus: AgentBus, runtime_dir: Optional[str] = None):
        # Call BaseAgent's __init__ first
        super().__init__(agent_id=agent_id, agent_bus=agent_bus)
        # self.agent_id = config.get('agent_id', f'reflection_agent_{uuid4().hex[:8]}')
        # self.agent_bus = config.get('agent_bus', None) # Handled by BaseAgent
        # self.logger = logging.getLogger(agent_id) # Handled by BaseAgent

        # Path management for reflection log
        # Use provided runtime_dir or default
        # TODO: Consider standardizing runtime path generation (maybe in BaseAgent or config)
        effective_runtime_dir = runtime_dir or "runtime"
        self.base_path = os.path.join(effective_runtime_dir, self.agent_id)
        self.reflection_dir = os.path.join(self.base_path, 'reflection')
        self.log_file = os.path.join(self.reflection_dir, 'reflection_log.md')

        # Ensure reflection directory exists
        try:
             os.makedirs(self.reflection_dir, exist_ok=True)
        except OSError as e:
             # Log error if directory creation fails, but proceed if possible
             self.logger.error(f"Failed to create reflection directory {self.reflection_dir}: {e}")

        # self._running = False # Handled by BaseAgent
    
    # Override _on_start to subscribe to governance alerts
    async def _on_start(self):
        """Agent-specific startup. Subscribe to governance alerts."""
        await super()._on_start() # Call base class method
        alert_topic = "governance.alert" # System-wide topic
        try:
            # Store subscription ID if BaseAgent doesn't manage multiple subs
            self._alert_subscription_id = await self.agent_bus.subscribe(alert_topic, self._handle_alert)
            self.logger.info(f"Subscribed to governance alert topic: {alert_topic}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to {alert_topic}: {e}", exc_info=True)
            # Consider if failure to subscribe is critical

    # Override _on_stop to unsubscribe if needed
    async def _on_stop(self):
        """Agent-specific shutdown. Unsubscribe from alerts."""
        if hasattr(self, '_alert_subscription_id') and self._alert_subscription_id:
             try:
                 await self.agent_bus.unsubscribe(self._alert_subscription_id)
                 self.logger.info("Unsubscribed from governance alert topic.")
             except Exception as e:
                 self.logger.error(f"Failed to unsubscribe from governance alert topic: {e}", exc_info=True)
        await super()._on_stop() # Call base class method

    # BaseAgent start/stop methods are inherited and handle main lifecycle
    # async def start(self) -> None:
    # async def stop(self) -> None:

    # Comment out file watching logic entirely
    # async def _watch_inbox(self) -> None:

    # Update handler to use logger and match expected signature from bus
    async def _handle_alert(self, topic: str, message: Dict[str, Any]) -> None:
        """Handle incoming governance alert messages from the AgentBus."""
        try:
            alert_data = message.get("data", {}) # Assume data is in 'data' field
            correlation_id = message.get("correlation_id") # Track for response

            if not isinstance(alert_data, dict):
                raise ValueError("Alert message content must be a dictionary in the 'data' field")

            alert_id = alert_data.get('alert_id', 'N/A')
            self.logger.info(f"Received alert '{alert_id}' on topic '{topic}' (CorrID: {correlation_id})")

            # Check if already processed to prevent duplicates from bus re-delivery
            if await self._is_already_processed(alert_id):
                self.logger.warning(f"Alert {alert_id} has already been processed. Skipping.")
                return

            disposition, justification = self._decide_response(alert_data)
            self.logger.debug(f"Alert {alert_id} disposition: {disposition}, Justification: {justification}")

            timestamp = await self._write_log_entry(
                alert_id,
                disposition,
                justification,
                alert_data
            )

            if timestamp:
                # Log governance event (already uses correct import)
                await self._log_governance_event(
                    alert_id,
                    disposition,
                    justification,
                    timestamp,
                    alert_data
                )

            # Send response message using topic string
            response_topic = "reflection.response"
            # If a correlation ID exists, we might also send to system.response.{correlation_id}
            response_data = {
                'alert_id': alert_id,
                'disposition': disposition,
                'justification': justification,
                'timestamp': timestamp
            }
            response_message = {
                "sender_id": self.agent_id,
                "correlation_id": correlation_id, # Pass along if available
                "data": response_data
            }
            await self.agent_bus.publish(response_topic, response_message)
            self.logger.info(f"Published reflection response for alert {alert_id} to {response_topic}")

            # Optionally send response via correlation ID topic if it exists
            if correlation_id:
                corr_response_topic = f"system.response.{correlation_id}"
                await self.agent_bus.publish(corr_response_topic, response_message)
                self.logger.debug(f"Also published response to correlation topic: {corr_response_topic}")

        except Exception as e:
            self.logger.error(f"Error handling alert message: {e}", exc_info=True)
            # Publish error using topic string (use helper if available, or manual)
            error_topic = "system.error"
            error_message = {
                 "sender_id": self.agent_id,
                 "correlation_id": message.get("correlation_id"), # Include if possible
                 "data": {
                    'source': self.agent_id,
                    'error': f"Failed to handle alert: {e}",
                    'alert_data': alert_data, # Include original data for context
                    'traceback': traceback.format_exc()
                }
            }
            try:
                await self.agent_bus.publish(error_topic, error_message)
            except Exception as pub_e:
                 self.logger.critical(f"Failed to publish error message about alert handling failure: {pub_e}")

    # Comment out file processing logic
    # async def _process_alert_file(self, filepath: str) -> None:
    # def _parse_md_file(self, filepath: str) -> Dict[str, str]:

    # Keep internal logic methods, ensure they use logger
    def _decide_response(self, alert_data: Dict[str, Any]) -> Tuple[str, str]:
        """Determine the appropriate response to an alert based on its data."""
        reason = alert_data.get('reason', '').lower()
        alert_type = alert_data.get('alert_type', '').lower()
        self.logger.debug(f"Deciding response for alert type '{alert_type}', reason '{reason}'")

        # Logic remains mostly the same, uses .get()
        if alert_type == 'ambiguous_rule':
            return 'disagree_rule', f"Rule {alert_data.get('rule_id', 'N/A')} flagged as ambiguous."
        elif alert_type == 'unexpected_halt':
            return 'disagree_monitor', f"Monitor flagged unexpected halt for task {alert_data.get('task_id', 'N/A')}."
        elif alert_type == 'justified_halt':
             return 'disagree_monitor', f"Monitor flagged halt for task {alert_data.get('task_id', 'N/A')}, but seems justified."

        # Fallback based on original logic
        if any(kw in reason for kw in ['unclear', 'ambiguous', 'unknown']):
            return 'disagree_rule', 'Rule appears ambiguous or unclear based on reason provided.'
        elif 'terminated unclear' in reason or 'halted unexpectedly' in reason:
            return 'disagree_monitor', 'Monitor alert suggests agent halted without clear rule violation/completion.'
        elif 'valid halt' in reason or 'expected behavior' in reason:
            return 'disagree_monitor', 'Monitor alert seems incorrect; agent halt appears justified.'

        return 'agree', 'Monitor alert acknowledged. Agent behavior or rule applicability needs review.'

    async def _write_log_entry(self, alert_id: Optional[str], disposition: str,
                             justification: str, alert_data: Dict[str, Any]) -> Optional[str]:
        """Write a reflection entry to the log file."""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"""---
**Reflection Timestamp:** {timestamp}
**Alert ID:** {alert_id or 'N/A'}
**Disposition:** {disposition.upper()}
**Justification:** {justification}
**Original Alert Details (from bus message):**
  - **Agent ID:** {alert_data.get('agent_id', 'N/A')}
  - **Task ID:** {alert_data.get('task_id', 'N/A')}
  - **Alert Type:** {alert_data.get('alert_type', 'N/A')}
  - **Reason Provided:** {alert_data.get('reason', 'N/A')}
  - **Context Provided:** {str(alert_data.get('context', 'N/A'))[:200]}...
  - **Rule Mentioned:** {alert_data.get('rule_id', 'N/A')}
---
"""
        try:
            # TODO: Implement robust async file locking for concurrent writes (Comment removed)
            # Basic file write for now
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(entry + '\n')
            self.logger.info(f"Logged reflection to file for alert {alert_id or 'N/A'} -> {disposition.upper()}")
            return timestamp
        except Exception as e:
            self.logger.error(f"Failed to write reflection log for alert {alert_id or 'N/A'}: {e}", exc_info=True)
            return None

    async def _is_already_processed(self, alert_id: Optional[str]) -> bool:
        """Check if an alert has already been processed by looking in the log file."""
        if not alert_id or alert_id == 'N/A': # Cannot check without a valid ID
             self.logger.warning("Attempted to check processed status for invalid/missing alert_id.")
             return False
        try:
            if not os.path.exists(self.log_file):
                return False

            # TODO: Implement robust async file locking for concurrent reads if necessary (Comment removed)
            # Basic file read for now
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Check specifically for the alert ID line
                return f"**Alert ID:** {alert_id}" in f.read()
        except Exception as e:
            self.logger.error(f"Error checking processed status for alert {alert_id}: {e}", exc_info=True)
            return False # Assume not processed if error occurs

    async def _log_governance_event(self, alert_id: Optional[str], disposition: str,
                                  justification: str, timestamp: str,
                                  alert_data: Dict[str, Any]) -> None:
        """Log a governance event for the reflection."""
        try:
            log_governance_event(
                event_type="REFLECTION_LOGGED",
                agent_source=self.agent_id,
                details={
                    'reflection_timestamp': timestamp,
                    'alert_id': alert_id or 'N/A',
                    'disposition': disposition.upper(),
                    'justification': justification,
                    'original_alert_agent': alert_data.get('agent_id', 'N/A'),
                    'original_alert_task': alert_data.get('task_id', 'N/A'),
                    'original_alert_type': alert_data.get('alert_type', 'N/A'),
                }
            )
            self.logger.info(f"Logged governance event for reflection on alert {alert_id or 'N/A'}")
        except Exception as e:
            self.logger.error(f"Failed to log governance event for alert {alert_id or 'N/A'}: {e}", exc_info=True)

# Update main function for testing
async def main():
    """Main entry point for testing the reflection agent."""
    print("Starting ReflectionAgent test...")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Basic mock AgentBus (reuse definition or import)
    class MockAgentBus:
        def __init__(self):
            self.subscriptions = {}
            self.published_messages = []
            self.logger = logging.getLogger("MockAgentBus")
            self._sub_ids = 0

        async def subscribe(self, topic, handler):
            if topic not in self.subscriptions:
                self.subscriptions[topic] = []
            sub_id = f"sub_{self._sub_ids}"
            self._sub_ids += 1
            self.subscriptions[topic].append((sub_id, handler))
            self.logger.info(f"Subscribed handler to {topic} with ID {sub_id}")
            return sub_id

        async def publish(self, topic, message):
            self.published_messages.append((topic, message))
            self.logger.info(f"Published to {topic}: {json.dumps(message, indent=2)}")
            # Simulate message delivery
            if topic in self.subscriptions:
                self.logger.debug(f"Delivering message on {topic} to {len(self.subscriptions[topic])} handler(s)." )
                for sub_id, handler in self.subscriptions[topic]:
                    asyncio.create_task(handler(topic, message))
            else:
                self.logger.debug(f"No subscriptions found for topic {topic}")

        async def unsubscribe(self, sub_id_to_remove):
            removed = False
            for topic in list(self.subscriptions.keys()):
                initial_len = len(self.subscriptions[topic])
                self.subscriptions[topic] = [(sub_id, handler) for sub_id, handler in self.subscriptions[topic] if sub_id != sub_id_to_remove]
                if len(self.subscriptions[topic]) < initial_len:
                    self.logger.info(f"Unsubscribed handler with ID {sub_id_to_remove} from topic: {topic}")
                    removed = True
                    if not self.subscriptions[topic]: # Clean up empty topic list
                        del self.subscriptions[topic]
                    break # Assume only one sub ID per topic in this mock
            if not removed:
                self.logger.warning(f"Attempted to unsubscribe with unknown ID: {sub_id_to_remove}")

        async def stop(self): self.logger.info("Stop called (no-op in mock)")
        async def start(self): self.logger.info("Start called (no-op in mock)")
        async def shutdown(self): self.logger.info("Shutdown called (no-op in mock)")

    mock_bus = MockAgentBus()
    agent_id = f'reflection_agent_test_{uuid4().hex[:6]}'
    runtime_dir_test = os.path.join("runtime", "test_reflection") # Use a test-specific dir

    # Create agent instance with new signature
    agent = ReflectionAgent(agent_id=agent_id, agent_bus=mock_bus, runtime_dir=runtime_dir_test)

    try:
        # Start the agent (calls _on_start, subscribes to governance.alert)
        await agent.start()
        print(f"Agent {agent.agent_id} started. Log file: {agent.log_file}")

        # Simulate receiving a governance alert message
        test_alert_id_1 = f"alert_{uuid4().hex[:8]}"
        correlation_id_1 = f"corr_{uuid4().hex[:4]}"
        alert_message_1 = {
            "sender_id": "governance_monitor_01",
            "correlation_id": correlation_id_1,
            "data": {
                'alert_id': test_alert_id_1,
                'agent_id': 'worker_agent_007',
                'task_id': 'task_abc_123',
                'alert_type': 'ambiguous_rule',
                'reason': 'Rule R12 is unclear regarding state X.',
                'context': {'state': 'X', 'action': 'Y'},
                'rule_id': 'R12'
            }
        }
        print(f"\nSimulating publish of alert {test_alert_id_1} to 'governance.alert'")
        await mock_bus.publish("governance.alert", alert_message_1)
        await asyncio.sleep(0.5) # Allow time for processing

        # Simulate a second alert
        test_alert_id_2 = f"alert_{uuid4().hex[:8]}"
        correlation_id_2 = f"corr_{uuid4().hex[:4]}"
        alert_message_2 = {
            "sender_id": "governance_monitor_02",
            "correlation_id": correlation_id_2,
            "data": {
                'alert_id': test_alert_id_2,
                'agent_id': 'planner_agent_01',
                'task_id': 'task_plan_xyz',
                'alert_type': 'unexpected_halt',
                'reason': 'Agent halted unexpectedly during planning phase.',
                'context': {'phase': 'planning', 'last_state': 'evaluating options'},
                'rule_id': None
            }
        }
        print(f"\nSimulating publish of alert {test_alert_id_2} to 'governance.alert'")
        await mock_bus.publish("governance.alert", alert_message_2)
        await asyncio.sleep(0.5) # Allow time for processing

        # Simulate duplicate alert
        print(f"\nSimulating publish of duplicate alert {test_alert_id_1} to 'governance.alert'")
        await mock_bus.publish("governance.alert", alert_message_1) # Send first alert again
        await asyncio.sleep(0.5) # Allow time for processing

        print("\nChecking published messages on mock bus:")
        response_count = 0
        for topic, msg in mock_bus.published_messages:
             if topic == "reflection.response":
                 response_count += 1
                 alert_id_in_resp = msg.get('data',{}).get('alert_id')
                 disposition_in_resp = msg.get('data',{}).get('disposition')
                 print(f"  Found reflection response for alert {alert_id_in_resp} (Disposition: {disposition_in_resp})")
                 if alert_id_in_resp == test_alert_id_1:
                     assert disposition_in_resp == 'disagree_rule'
                 elif alert_id_in_resp == test_alert_id_2:
                     assert disposition_in_resp == 'disagree_monitor'
             elif topic.startswith("system.response."):
                  alert_id_in_resp = msg.get('data',{}).get('alert_id')
                  print(f"  Found correlation response for alert {alert_id_in_resp} on {topic}")

        print(f"Total reflection responses published: {response_count}")
        assert response_count == 2, "Expected exactly two responses (no duplicate)"

        print("\nChecking reflection log file content...")
        log_path = agent.log_file
        processed_alerts_in_log = 0
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
                if f"**Alert ID:** {test_alert_id_1}" in log_content:
                    processed_alerts_in_log += 1
                    print(f"  Log entry for alert {test_alert_id_1} verified.")
                else:
                    print(f"  ERROR: Log entry for alert {test_alert_id_1} NOT found.")
                if f"**Alert ID:** {test_alert_id_2}" in log_content:
                    processed_alerts_in_log += 1
                    print(f"  Log entry for alert {test_alert_id_2} verified.")
                else:
                    print(f"  ERROR: Log entry for alert {test_alert_id_2} NOT found.")
            assert processed_alerts_in_log == 2, "Expected exactly two alerts processed in log file."
        else:
             print(f"  ERROR: Log file not found at {log_path}")
             assert False, "Log file missing"

    except Exception as e:
        logging.getLogger(agent_id).error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        # Stop the agent
        print("\nStopping agent...")
        await agent.stop()
        # Clean up test directory/log file
        # import shutil
        # if os.path.exists(runtime_dir_test):
        #     print(f"Cleaning up test directory: {runtime_dir_test}")
        #     # shutil.rmtree(runtime_dir_test) # Be careful with auto-deletion
        # if os.path.exists(log_path):
        #      os.remove(log_path)

if __name__ == "__main__":
    # Note: If run directly, ensure 'core' modules are importable from this location
    # This might require adjusting PYTHONPATH or running from the project root.
    print("Running ReflectionAgent main test...")
    asyncio.run(main())
    print("ReflectionAgent main test finished.") 