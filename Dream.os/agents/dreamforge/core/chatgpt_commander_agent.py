"""ChatGPT Commander agent for interacting with ChatGPT."""
import os
import json
import random
import asyncio
import traceback
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

from core.coordination.agent_bus import AgentBus
from services.browser.browser_controller import BrowserController
from core.utils.performance_logger import PerformanceLogger
from core.memory.governance_memory_engine import log_event

# Configure Logging
logger = logging.getLogger(__name__)

# --- Configuration ---
COOKIES_PATH = "secrets/cookies.json"
LOG_DIR = "logs/chat_logs"
AGENT_ID_DEFAULT = "ChatGPTCommander"

class ChatGPTCommander:
    """Agent for commanding and interacting with ChatGPT via AgentBus dispatch."""
    AGENT_NAME = AGENT_ID_DEFAULT
    CAPABILITIES = ["chatgpt_interaction", "command_execution"]

    def __init__(self, agent_id: str = AGENT_ID_DEFAULT, agent_bus: AgentBus = None, config: Dict[str, Any] = None):
        if agent_bus is None:
            raise ValueError("AgentBus instance is required for ChatGPTCommander initialization.")
        if config is None: config = {}

        self.agent_id = agent_id
        self.agent_bus = agent_bus
        self.config = config

        self.cookies_file = config.get('cookies_file', COOKIES_PATH)
        self.log_dir = config.get('log_dir', LOG_DIR)
        self.browser_controller = None
        self.perf_logger = PerformanceLogger(self.agent_id)

        try:
            registration_success = self.agent_bus.register_agent(self)
            if registration_success:
                 log_event("AGENT_REGISTERED", self.agent_id, {"message": "Successfully registered with AgentBus."})
                 logger.info(f"Agent {self.agent_id} registered successfully.")
            else:
                 log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to register with AgentBus (register_agent returned False)."})
                 logger.error("Agent registration failed.")
        except Exception as reg_e:
             log_event("AGENT_ERROR", self.agent_id, {"error": f"Exception during AgentBus registration: {reg_e}", "traceback": traceback.format_exc()})
             logger.exception("Exception during AgentBus registration.")

    def execute_chat_prompt(self, prompt: str, calling_agent_id: str = "Unknown", **kwargs) -> Dict[str, Any] | None:
        """Executes a prompt against ChatGPT, called via AgentBus.dispatch.

        Handles the async interaction with BrowserController using asyncio.run().
        Returns a dictionary with results (status, response, log_file) or None on failure.
        """
        task_id = str(uuid.uuid4())
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "execute_chat_prompt", "caller": calling_agent_id, "task_id": task_id, "prompt_snippet": prompt[:50]})
        logger.info(f"Received execute_chat_prompt from {calling_agent_id} (task_id: {task_id}): '{prompt[:50]}...'")

        with self.perf_logger.track_operation("execute_chat_prompt", {"task_id": task_id, "caller": calling_agent_id}):
            try:
                if not prompt:
                    raise ValueError("Missing 'prompt' for execute_chat_prompt")

                logger.debug(f"Executing async _process_chat_command for task {task_id} using asyncio.run()... (Inefficient)")
                result_payload = asyncio.run(self._process_chat_command(prompt, task_id))
                logger.debug(f"Async _process_chat_command for task {task_id} completed.")

                log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "execute_chat_prompt", "task_id": task_id, "result_status": result_payload.get("status")})
                logger.info(f"Successfully processed chat prompt for task {task_id}. Log file: {result_payload.get('log_file')}")
                return result_payload

            except Exception as e:
                error_msg = f"Failed to execute chat prompt (task_id: {task_id}): {str(e)}"
                log_event("AGENT_ACTION_FAILED", self.agent_id, {
                    "action": "execute_chat_prompt",
                    "task_id": task_id,
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
                logger.exception(f"Error during execute_chat_prompt for task {task_id}.")
                return None

    async def _process_chat_command(self, command_text: str, task_id: str) -> Dict[str, Any]:
        """Internal async helper to process a chat command and return the result."""
        with self.perf_logger.track_operation("_process_chat_command_async", {"task_id": task_id}):
            try:
                if not self.browser_controller:
                    logger.info(f"Initializing BrowserController for task {task_id}...")
                    self.browser_controller = await BrowserController.create(
                        cookies_file=self.cookies_file
                    )
                    logger.info(f"BrowserController initialized for task {task_id}.")
                else:
                     logger.debug(f"Reusing existing BrowserController for task {task_id}.")

                logger.debug(f"Sending message to browser for task {task_id}...")
                response = await self.browser_controller.send_message(command_text)
                logger.debug(f"Received browser response for task {task_id}.")

                log_file = await self._save_log(command_text, response, task_id)

                return {
                    "status": "success",
                    "response": response,
                    "log_file": log_file
                }

            except Exception as e:
                log_event("AGENT_ERROR", self.agent_id, {
                    "task_id": task_id,
                    "method": "_process_chat_command",
                    "error": "Error processing chat command",
                    "details": str(e),
                    "traceback": traceback.format_exc()
                })
                logger.exception(f"Error within _process_chat_command for task {task_id}.")
                raise

    async def _save_log(self, command: str, response: str, task_id: str) -> Optional[str]:
        """Internal async helper to save the conversation log to a file."""
        with self.perf_logger.track_operation("_save_log_async", {"task_id": task_id}):
            try:
                log_path = Path(self.log_dir)
                log_path.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                filename = f"chat_{task_id}_{timestamp}.json"
                filepath = log_path / filename

                log_data = {
                    "task_id": task_id,
                    "timestamp": timestamp,
                    "command": command,
                    "response": response
                }

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, indent=2)
                logger.debug(f"Saved chat log for task {task_id} to {filepath}")

                log_event("AGENT_LOG_SAVED", self.agent_id, {
                    "task_id": task_id,
                    "log_file": str(filepath)
                })

                return str(filepath)

            except Exception as e:
                log_event("AGENT_ERROR", self.agent_id, {
                    "task_id": task_id,
                    "method": "_save_log",
                    "error": "Error saving chat log",
                    "details": str(e),
                    "traceback": traceback.format_exc()
                })
                logger.exception(f"Error saving chat log for task {task_id}.")
                return None

# --- Removed Direct Run Block ---
# async def main():
#    ...
# if __name__ == "__main__":
#    asyncio.run(main()) 