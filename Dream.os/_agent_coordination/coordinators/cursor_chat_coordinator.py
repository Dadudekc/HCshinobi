# _agent_coordination/coordinators/cursor_chat_coordinator.py

import asyncio
import logging
import time
import uuid
import re
import difflib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple, Any, List, Set

# --- Dependencies for Phase 1 wait_for_response --- 
try:
    import cv2  # For image processing
    import pytesseract 
    from PIL import Image
    # If using easyocr instead:
    # import easyocr
    # reader = easyocr.Reader(['en']) # Initialize reader once if using easyocr
    OCR_AVAILABLE = True
except ImportError:
    logging.warning("opencv-python, pytesseract or Pillow not found. OCR functionality will be unavailable.")
    logging.warning("Install using: pip install opencv-python pytesseract Pillow")
    logging.warning("Also ensure Tesseract OCR engine is installed and in PATH.")
    cv2 = None
    pytesseract = None
    Image = None
    OCR_AVAILABLE = False
# -----------------------------------------------------

# Import core components using relative paths within _agent_coordination
# Assuming state machine, bridge adapter, controller are siblings or in known subdirs
from ..state_machines.task_execution_state_machine import TaskExecutionStateMachine, TaskState # Adjusted path
from ..bridge_adapters.cursor_bridge_adapter import CursorBridgeAdapter, CursorGoal # Adjusted path
from ..controllers.cursor_instance_controller import CursorInstanceController, CursorInstance # Adjusted path
from ..agent_bus import agent_bus, EventType, Event # Adjusted path

# Use the central logger setup
from ..core.utils.logging import get_logger # Adjusted path
logger = get_logger(__name__, component="CursorChatCoordinator") # Use component logging
AGENT_ID = "agent_cursor_chat_coordinator"

class CursorChatCoordinator:
    """Agent responsible for managing high-level conversational task execution inside a Cursor instance."""

    def __init__(self, 
                 instance_controller: CursorInstanceController, 
                 bridge_adapter: CursorBridgeAdapter, 
                 state_machine: TaskExecutionStateMachine, 
                 agent_bus_instance: Any,  # For AgentBus stub compatibility 
                 pytesseract_cmd: Optional[str] = None,
                 chat_area_coords: Optional[Tuple[int, int, int, int]] = None):
        """
        Initializes the coordinator.
        
        Args:
            instance_controller: Provides access to CursorInstance capture functionality.
            bridge_adapter: Translates high-level Cursor goals into TaskExecutionPlans.
            state_machine: Executes the TaskExecutionPlan.
            agent_bus_instance: The central AgentBus (or a stub).
            pytesseract_cmd: Optional path to Tesseract executable.
            chat_area_coords: Optional coordinates (x1, y1, x2, y2) for cropping the chat response area.
        """
        self.instance_controller = instance_controller
        self.bridge_adapter = bridge_adapter
        self.state_machine = state_machine
        self.agent_bus = agent_bus_instance
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.instance_states: Dict[str, Dict[str, str]] = {}  # Stores {"last_response": text} per instance
        self.running = True
        self.chat_area_coords = chat_area_coords  # e.g., (10, 100, 790, 500)
        self.pending_subtask_futures: Dict[str, asyncio.Future] = {}  # Tracks sub-task completion
        self.processed_subtask_events: Set[str] = set()  # Avoid reprocessing feedback

        if OCR_AVAILABLE and pytesseract_cmd:
            try:
                 pytesseract.pytesseract.tesseract_cmd = pytesseract_cmd
                 logger.info(f"Set pytesseract command path to: {pytesseract_cmd}")
            except Exception as e:
                 logger.error(f"Failed to set pytesseract command path: {e}", exc_info=True)
        elif not OCR_AVAILABLE:
            logger.error(f"OCR dependencies missing. wait_for_response will fail.")

        logger.info(f"Initialized.") # Shortened log

    async def wait_for_response(self, instance_id: str, timeout: float = 60.0) -> Optional[str]:
        """
        Monitors the specified Cursor instance's chat UI for a new response using OCR.

        Args:
            instance_id: The ID of the target Cursor instance (e.g., "CURSOR-1").
            timeout: Maximum time in seconds to wait for a new response.

        Returns:
            The extracted text of the new response portion, or None if timed out or error occurs.
        """
        if not OCR_AVAILABLE:
            logger.error(f"[{instance_id}] OCR dependencies unavailable.")
            return None

        start_time = time.time()
        logger.info(f"[{instance_id}] Waiting for new chat response (timeout: {timeout}s)...")
        last_known_response = self.instance_states.get(instance_id, {}).get("last_response", "")

        instance: Optional[CursorInstance] = self.instance_controller.get_instance_by_id(instance_id)
        if not instance or not hasattr(instance, 'capture'):
            logger.error(f"[{instance_id}] Cannot find valid Cursor instance or capture method for OCR.")
            return None

        try:
            while time.time() - start_time < timeout:
                await asyncio.sleep(3)
                screenshot_np = instance.capture()
                if screenshot_np is None:
                    logger.warning(f"[{instance_id}] Failed to capture screenshot; retrying...")
                    continue

                # Ensure cv2 is available here
                if cv2 is None or Image is None or pytesseract is None:
                     logger.error(f"[{instance_id}] OCR component became unavailable unexpectedly.")
                     return None

                img_rgb = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2RGB)
                h, w = img_rgb.shape[:2]
                if self.chat_area_coords:
                    x1, y1, x2, y2 = self.chat_area_coords
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    if x1 < x2 and y1 < y2:
                        cropped_np = img_rgb[y1:y2, x1:x2]
                        img_for_ocr_pil = Image.fromarray(cropped_np)
                        logger.debug(f"[{instance_id}] Cropped screenshot to {x1},{y1}-{x2},{y2} for OCR.")
                    else:
                        logger.warning(f"[{instance_id}] Invalid chat area coords ({self.chat_area_coords}) for image size ({w}x{h}). Using full image.")
                        img_for_ocr_pil = Image.fromarray(img_rgb)
                else:
                    logger.debug(f"[{instance_id}] No chat area coords specified. Using full image for OCR.")
                    img_for_ocr_pil = Image.fromarray(img_rgb)

                current_text = pytesseract.image_to_string(img_for_ocr_pil).strip()
                current_text = current_text.replace('\n\n', '\n') # Basic normalization
                logger.debug(f"[{instance_id}] OCR text (len {len(current_text)}): {current_text[:100]}...")

                if current_text and current_text != last_known_response:
                    matcher = difflib.SequenceMatcher(None, last_known_response, current_text, autojunk=False)
                    diff_ratio = matcher.ratio()
                    # Heuristic: significant change or substantial addition
                    is_new_content = (diff_ratio < 0.95) or (len(current_text) > len(last_known_response) + 10)
                    if is_new_content:
                        new_text_parts = []
                        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                            if tag in ['insert', 'replace']:
                                new_text_parts.append(current_text[j1:j2])
                        new_text_portion = "\n".join(new_text_parts).strip()
                        if new_text_portion:
                            logger.info(f"[{instance_id}] Detected new response segment (ratio: {diff_ratio:.2f}): '{new_text_portion[:70]}...'")
                            self.instance_states.setdefault(instance_id, {})["last_response"] = current_text
                            return new_text_portion
                        else:
                            # If diff detected but no new segment extracted, still update state
                            logger.debug(f"[{instance_id}] Text changed (ratio: {diff_ratio:.2f}) but no new segment extracted. Updating state.")
                            self.instance_states.setdefault(instance_id, {})["last_response"] = current_text
                    else:
                        # Log slight changes but don't consider it a new response yet
                        logger.debug(f"[{instance_id}] Text changed slightly (ratio: {diff_ratio:.2f}); no significant new content.")
                        # Update state even for slight changes to prevent re-detecting same minor diff
                        self.instance_states.setdefault(instance_id, {})["last_response"] = current_text
                else:
                    logger.debug(f"[{instance_id}] No change detected from last known response.")
            logger.warning(f"[{instance_id}] OCR wait_for_response timed out after {timeout}s.")
            return None
        except Exception as e:
            logger.error(f"[{instance_id}] Error in wait_for_response: {e}", exc_info=True)
            return None

    def interpret_response(self, chat_text: str, task_context: Optional[Dict] = None) -> Optional[Dict]:
        """
        Parses the new chat text segment to determine the next required action.
        Enhanced with additional patterns and rules.

        Args:
            chat_text: The new text segment obtained via wait_for_response.
            task_context: Optional context from the original task for refined parsing.

        Returns:
            A structured action dictionary (e.g., {'action': 'save_file', 'params': {...}}) or None.
        """
        logger.info(f"Interpreting response segment (length {len(chat_text)})...")
        if not chat_text or chat_text.isspace():
            logger.debug("Empty or whitespace-only text segment; skipping interpretation.")
            return None

        # --- Define Regex Patterns ---
        python_code_pattern = r"```python\s*(.*?)```"
        diff_pattern = r"```diff\s*(.*?)```"
        generic_code_pattern = r"```(?:\w*\s*)?(.*?)```"
        file_path_pattern = r"(?:save to|in|path:|file:)\s*[`\"]?([\w\.\/\-\\\s]+(?:\.[a-zA-Z0-9]+)?)[`\"]?" # Improved file path regex

        # --- Keyword Groups ---
        accept_keywords = ["click accept", "apply changes", "apply the diff", "accept this", "use this suggestion"]
        completion_keywords = ["task complete", "finished successfully", "all done", "applied successfully", "code saved", "refactoring complete", "tests generated"]
        error_keywords = ["error occurred", "failed to", "unable to proceed", "encountered an issue", "cannot apply", "syntax error"]
        clarification_keywords = ["which file", "specify the path", "need more details", "ambiguous request"]

        lower_text = chat_text.lower()
        action = None

        # 1. Check for error phrases first.
        if any(phrase in lower_text for phrase in error_keywords):
            logger.warning(f"Interpreted ERROR signal: '{chat_text[:100]}...'")
            return {"action": "error_detected", "params": {"message": chat_text}}

        # 2. Check for explicit acceptance commands.
        if any(phrase in lower_text for phrase in accept_keywords):
            logger.info("Interpreted 'apply/accept' command from response.")
            return {"action": "execute_cursor_goal", "goal": {"type": "apply_changes"}}

        # 3. Look for code blocks (priority: python > diff > generic)
        python_match = re.search(python_code_pattern, chat_text, re.DOTALL)
        diff_match = re.search(diff_pattern, chat_text, re.DOTALL)
        generic_match = re.search(generic_code_pattern, chat_text, re.DOTALL)

        code_content = None
        code_type = None
        if python_match:
            code_content = python_match.group(1).strip()
            code_type = "python"
        elif diff_match:
            code_content = diff_match.group(1).strip()
            code_type = "diff"
        elif generic_match:
            code_content = generic_match.group(1).strip()
            code_type = "generic"

        if code_content:
            logger.info(f"Interpreted {code_type or 'generic'} code block.")
            # Search for filename suggestion *before* the code block
            text_before_code = chat_text[:chat_text.find("```")]
            filename_match = re.search(file_path_pattern, text_before_code, re.IGNORECASE)
            filename = None
            if filename_match:
                # Basic normalization: replace backslashes, remove surrounding quotes/backticks
                filename = filename_match.group(1).strip().replace('\\', '/')
                filename = re.sub(r'^[`"]+|[`"]+$', '', filename)
                logger.info(f"Extracted suggested filename: {filename}")
            else:
                # Fallback filename generation using context
                filename_base = f"extracted_{code_type or 'code'}"
                if task_context:
                    goal_params = task_context.get("params", {}).get("cursor_goal", {})
                    target_file = goal_params.get('target_file')
                    if target_file:
                        try:
                            filename_base = f"generated_{Path(target_file).stem}"
                        except Exception:
                             logger.warning(f"Could not parse stem from target_file: {target_file}")
                             pass # Use default filename_base
                # Determine extension based on code type
                if code_type == 'python':
                    extension = '.py'
                elif code_type == 'diff':
                    extension = '.diff'
                else: # Includes 'generic' or None
                    extension = '.txt'
                filename = f"{filename_base}_{uuid.uuid4().hex[:6]}{extension}"
                logger.info(f"Generated fallback filename: {filename}")

            # Return action to save the file
            return {"action": "save_file", "params": {"path": filename, "content": code_content, "type": code_type}}

        # 4. Check for completion signals.
        if any(phrase in lower_text for phrase in completion_keywords):
            logger.info("Interpreted COMPLETION signal from response.")
            return {"action": "task_complete"}

        # 5. Check for clarification needs.
        if any(phrase in lower_text for phrase in clarification_keywords):
            logger.info("Interpreted CLARIFICATION request from response.")
            return {"action": "clarification_needed", "params": {"message": chat_text}}

        # --- Fallback --- 
        logger.debug("No specific actionable patterns identified in the response segment.")
        return None # No specific action identified

    # --- Dispatching Logic --- 
    async def dispatch_to_agents(self, task_dict: Dict, target_instance_id: Optional[str] = None, original_task_id: Optional[str] = None) -> Optional[str]:
        """Routes the interpreted action, returning the sub-task ID if trackable."""
        action = task_dict.get("action")
        params = task_dict.get("params", {})
        goal_dict = task_dict.get("goal")
        parent_task_id = original_task_id or "unknown_parent"
        dispatched_sub_task_id = None
        agent_bus_available = hasattr(self.agent_bus, '_dispatcher') and hasattr(self.agent_bus._dispatcher, 'dispatch_event')

        logger.info(f"[{parent_task_id}] Dispatching action: {action}")
        
        if action == "save_file":
            filename = params.get("path")
            content = params.get("content")
            if filename and content is not None:
                logger.info(f"Dispatching 'save_file' action for file: {filename}")
                if agent_bus_available:
                    sub_task_id = f"{parent_task_id}_save_{uuid.uuid4().hex[:4]}"
                    event_data = {
                        "type": "file_write_request", # Standardize event type
                        "task_id": sub_task_id,
                        "agent": "FileManagerAgent", # Target Agent ID
                        "path": filename,
                        "content": content,
                        "source_agent": AGENT_ID,
                        "parent_task_id": parent_task_id
                    }
                    event = Event(type=EventType.TASK, source_id=AGENT_ID, data=event_data)
                    try:
                        # Create a future to wait for feedback
                        future = asyncio.get_running_loop().create_future()
                        self.pending_subtask_futures[sub_task_id] = future
                        await self.agent_bus._dispatcher.dispatch_event(event)
                        dispatched_sub_task_id = sub_task_id
                        logger.info(f"Dispatched file write request event for {filename}. Sub-task: {dispatched_sub_task_id}")
                    except Exception as e:
                        logger.error(f"Failed to dispatch file write request: {e}", exc_info=True)
                        self.pending_subtask_futures.pop(sub_task_id, None) # Clean up future on error
                else:
                    logger.warning("AgentBus not available/configured correctly. Cannot dispatch file_write_request event.")
                    # Potential fallback: Directly write file? (Less ideal)
            else:
                logger.error("Missing path or content for save_file dispatch.")

        elif action == "execute_cursor_goal":
            if goal_dict and isinstance(goal_dict, dict):
                try:
                    goal = CursorGoal(**goal_dict)
                    sub_task_id = f"{parent_task_id}_ui_{goal.type}_{uuid.uuid4().hex[:4]}"
                    plan = self.bridge_adapter.translate_goal_to_plan(goal)
                    plan.task_id = sub_task_id 
                    plan.cursor_instance_id = target_instance_id
                    
                    if not target_instance_id:
                         logger.error("Cannot execute cursor goal: target_instance_id is missing.")
                         return None # Cannot proceed
                         
                    # Create future before starting the task
                    future = asyncio.get_running_loop().create_future()
                    self.pending_subtask_futures[sub_task_id] = future
                    
                    # Schedule execution
                    asyncio.create_task(self._execute_and_track_sub_plan(parent_task_id, sub_task_id, plan))
                    dispatched_sub_task_id = sub_task_id
                    logger.info(f"Scheduled UI sub-plan {sub_task_id} execution for instance {target_instance_id}.")
                except Exception as e:
                     logger.error(f"Failed to create/dispatch CursorGoal plan: {e}", exc_info=True)
                     if 'sub_task_id' in locals():
                         self.pending_subtask_futures.pop(sub_task_id, None) # Clean up future
            else:
                logger.error("Invalid goal data for execute_cursor_goal dispatch.")

        elif action == "task_complete":
            logger.info(f"Interpreter indicated completion for parent task {parent_task_id}.")
            # Report the parent task as complete
            await self.report_status(parent_task_id, "complete", instance_id=target_instance_id, result={"message": "Interpreted as complete from chat response."})
            # Signal the main loop for this instance to stop? Or let Supervisor handle it?
            # self.instance_states[target_instance_id]["status"] = "stopped" # Example state update
            
        elif action == "error_detected":
            error_message = params.get("message", "Unspecified error interpreted from chat response.")
            logger.error(f"Interpreter detected error for parent task {parent_task_id}. Reporting failure.")
            await self.report_status(parent_task_id, "failed", instance_id=target_instance_id, error=error_message, result={"message": "Interpreted error from chat response."})
            # No trackable sub-task ID for error detection itself
            
        elif action == "clarification_needed":
            clarification_msg = params.get("message", "Clarification needed based on Cursor response.")
            logger.warning(f"[{parent_task_id}] Clarification needed. Reporting back to supervisor/user.")
            # Report status as 'pending_clarification' or similar?
            # Or emit a specific event type?
            await self.report_status(parent_task_id, "pending_clarification", instance_id=target_instance_id, result={"message": clarification_msg})
            # No trackable sub-task ID for needing clarification
             
        else:
            logger.warning(f"Unhandled action type dispatched: {action}")
            
        return dispatched_sub_task_id # Return the ID to wait for

    async def _execute_and_track_sub_plan(self, parent_task_id: str, sub_task_id: str, plan: Any):
        """Executes a UI plan. Feedback is handled by handle_bus_event setting the future."""
        logger.info(f"Executing sub-plan {sub_task_id} for parent {parent_task_id} on instance {plan.cursor_instance_id}.")
        future = self.pending_subtask_futures.get(sub_task_id)
        if not future:
             logger.error(f"Future not found for sub-task {sub_task_id} before execution! Cannot track completion.")
             # Attempt execution anyway, but feedback is lost
             try:
                  await self.state_machine.execute_plan(plan)
             except Exception as e:
                  logger.error(f"Error executing untracked sub-plan {sub_task_id}: {e}", exc_info=True)
             return
             
        try:
            final_plan_state = await self.state_machine.execute_plan(plan)
            logger.info(f"Sub-plan {sub_task_id} finished execution with state: {final_plan_state.state.value}")
            # The future result will be set by handle_bus_event based on feedback
            # We don't set future result here directly based on final_plan_state, 
            # as the feedback event is the source of truth for success/failure.
        except Exception as e:
             logger.error(f"Error executing sub-plan {sub_task_id}: {e}", exc_info=True)
             # Set future exception if execution itself fails critically
             if not future.done():
                  future.set_exception(e)
             # Clean up the future if it hasn't been removed already by feedback handler
             self.pending_subtask_futures.pop(sub_task_id, None)
             # Report failure status for the parent task?
             # await self.report_status(parent_task_id, "failed", error=f"Sub-task {sub_task_id} failed: {e}")

    async def handle_bus_event(self, event: Event):
        """Processes events from the AgentBus, particularly sub-task feedback."""
        if event.type != EventType.TASK_FEEDBACK:
            return
            
        feedback_data = event.data
        sub_task_id = feedback_data.get("task_id")
        status = feedback_data.get("status")
        result = feedback_data.get("result")
        error = feedback_data.get("error")
        
        if not sub_task_id or sub_task_id not in self.pending_subtask_futures:
            # logger.debug(f"Received feedback for unknown or already processed sub-task: {sub_task_id}")
            return
            
        if sub_task_id in self.processed_subtask_events:
            logger.debug(f"Already processed feedback for sub-task {sub_task_id}, skipping.")
            return
            
        future = self.pending_subtask_futures.get(sub_task_id)
        if future and not future.done():
            logger.info(f"Received feedback for sub-task {sub_task_id}: Status={status}, Error={error}")
            if status == "complete":
                future.set_result(result or True) # Set result (or True if no specific result data)
            elif status == "failed":
                 exc = Exception(f"Sub-task {sub_task_id} failed: {error}")
                 future.set_exception(exc)
            else:
                 # Handle other statuses (e.g., progress) if needed, or just log
                 logger.warning(f"Received unexpected status '{status}' for sub-task {sub_task_id}")
                 # Optionally set a default result or exception based on interpretation
                 # future.set_result(False) # Example: treat unknown status as failure indication
                 
            # Mark as processed *after* setting future result/exception
            self.processed_subtask_events.add(sub_task_id)
            # Remove future once handled (maybe with a small delay?)
            # Consider timing if execution task might still be logging
            self.pending_subtask_futures.pop(sub_task_id, None)
        else:
             # Future might be done if execution finished/failed before feedback arrived
             logger.warning(f"Received feedback for sub-task {sub_task_id}, but future was already done or missing.")
             # Ensure it's marked processed anyway to prevent duplicates if feedback is resent
             self.processed_subtask_events.add(sub_task_id)
             self.pending_subtask_futures.pop(sub_task_id, None) # Clean up just in case

    async def report_status(self, task_id: str, status: str, instance_id: Optional[str] = None, result: Optional[Dict] = None, error: Optional[str] = None):
        """Reports the status of a high-level task back via the AgentBus."""
        if not hasattr(self.agent_bus, '_dispatcher') or not hasattr(self.agent_bus._dispatcher, 'dispatch_event'):
            logger.error("Cannot report status: AgentBus dispatcher not available.")
            return

        event_data = {
            "type": "task_status_update", # Use a specific type
            "task_id": task_id,
            "source_agent": AGENT_ID,
            "status": status,
            "cursor_instance_id": instance_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        if result:
            event_data["result"] = result
        if error:
            event_data["error"] = error
            
        event = Event(type=EventType.STATUS, source_id=AGENT_ID, data=event_data)
        try:
            await self.agent_bus._dispatcher.dispatch_event(event)
            logger.info(f"Reported status '{status}' for task {task_id}.")
        except Exception as e:
            logger.error(f"Failed to report status for task {task_id}: {e}", exc_info=True)

    async def execute_task(self, task_id: str, cursor_goal: Dict, target_instance_id: str):
        """Handles the execution of a single conversational task within a Cursor instance."""
        logger.info(f"[{task_id}] Starting execution for instance {target_instance_id}.")
        await self.report_status(task_id, "running", instance_id=target_instance_id)
        
        # Step 1: Translate goal to initial plan (e.g., type prompt)
        try:
            initial_plan = self.bridge_adapter.translate_goal_to_plan(CursorGoal(**cursor_goal))
            initial_plan.task_id = f"{task_id}_initial"
            initial_plan.cursor_instance_id = target_instance_id
        except Exception as e:
            logger.error(f"[{task_id}] Failed to translate initial goal: {e}", exc_info=True)
            await self.report_status(task_id, "failed", instance_id=target_instance_id, error=f"Goal translation failed: {e}")
            return

        # Step 2: Execute initial plan (e.g., sending the message)
        logger.info(f"[{task_id}] Executing initial plan...")
        try:
            # No need to track future here, we assume sending message is synchronous enough
            # or fire-and-forget for this stage.
            await self.state_machine.execute_plan(initial_plan)
            logger.info(f"[{task_id}] Initial plan execution complete.")
        except Exception as e:
            logger.error(f"[{task_id}] Failed to execute initial plan: {e}", exc_info=True)
            await self.report_status(task_id, "failed", instance_id=target_instance_id, error=f"Initial plan failed: {e}")
            return

        # Step 3: Loop: Wait for response, Interpret, Dispatch, Wait for sub-tasks
        loop_count = 0
        max_loops = 10 # Prevent infinite loops
        while loop_count < max_loops:
            loop_count += 1
            logger.info(f"[{task_id}] Entering interpretation loop {loop_count}/{max_loops}...")

            # Step 3a: Wait for new text response
            response_text = await self.wait_for_response(target_instance_id, timeout=120.0) # Increased timeout?
            if response_text is None:
                logger.error(f"[{task_id}] Failed to get response from Cursor instance {target_instance_id}.")
                await self.report_status(task_id, "failed", instance_id=target_instance_id, error="No response from Cursor instance.")
                return

            # Step 3b: Interpret the response
            task_context = {"params": {"cursor_goal": cursor_goal}} # Provide context
            interpreted_action = self.interpret_response(response_text, task_context)

            if interpreted_action is None:
                logger.warning(f"[{task_id}] Could not interpret response segment. Assuming loop should end or wait longer?")
                # Decide: End task as failed/stalled, or try waiting again?
                # For now, let's assume completion if no action is clear.
                await self.report_status(task_id, "complete", instance_id=target_instance_id, result={"message": "Conversation ended, no further action interpreted."})
                return

            action_type = interpreted_action.get("action")
            logger.info(f"[{task_id}] Interpreted action: {action_type}")

            # Step 3c: Handle terminal actions (complete, error, clarification)
            if action_type == "task_complete":
                logger.info(f"[{task_id}] Task interpreted as complete.")
                await self.report_status(task_id, "complete", instance_id=target_instance_id, result={"message": "Interpreted as complete from chat response."})
                return
            elif action_type == "error_detected":
                logger.error(f"[{task_id}] Task interpreted as failed due to error signal.")
                await self.report_status(task_id, "failed", instance_id=target_instance_id, error=interpreted_action.get("params", {}).get("message", "Error detected in response"))
                return
            elif action_type == "clarification_needed":
                logger.warning(f"[{task_id}] Clarification needed. Task stalled.")
                await self.report_status(task_id, "pending_clarification", instance_id=target_instance_id, result=interpreted_action.get("params", {}))
                return

            # Step 3d: Dispatch non-terminal actions and wait for feedback
            logger.info(f"[{task_id}] Dispatching sub-task for action: {action_type}...")
            sub_task_id = await self.dispatch_to_agents(interpreted_action, target_instance_id, task_id)

            if sub_task_id:
                logger.info(f"[{task_id}] Waiting for feedback on sub-task {sub_task_id}...")
                future = self.pending_subtask_futures.get(sub_task_id)
                if future:
                    try:
                        # Wait for the future to complete (set by handle_bus_event)
                        # Add a timeout to prevent indefinite waits
                        sub_task_result = await asyncio.wait_for(future, timeout=120.0) 
                        logger.info(f"[{task_id}] Sub-task {sub_task_id} completed successfully. Result: {sub_task_result}")
                        # Continue the loop
                    except asyncio.TimeoutError:
                         logger.error(f"[{task_id}] Timeout waiting for feedback on sub-task {sub_task_id}.")
                         await self.report_status(task_id, "failed", instance_id=target_instance_id, error=f"Timeout waiting for sub-task {sub_task_id}")
                         self.pending_subtask_futures.pop(sub_task_id, None) # Clean up
                         return
                    except Exception as sub_task_exception:
                        logger.error(f"[{task_id}] Sub-task {sub_task_id} failed: {sub_task_exception}", exc_info=False)
                        await self.report_status(task_id, "failed", instance_id=target_instance_id, error=f"Sub-task {sub_task_id} failed: {sub_task_exception}")
                        # Future should have been removed by handler, but pop just in case
                        self.pending_subtask_futures.pop(sub_task_id, None) 
                        return # Exit loop on sub-task failure
                else:
                    logger.warning(f"[{task_id}] Future not found for dispatched sub-task {sub_task_id} immediately after dispatch. Feedback might be missed.")
                    # Potentially wait a short time? Or assume failure?
                    await asyncio.sleep(1) # Short wait to see if future appears
                    if sub_task_id not in self.pending_subtask_futures:
                        logger.error(f"[{task_id}] Failed to track sub-task {sub_task_id}. Assuming failure.")
                        await self.report_status(task_id, "failed", instance_id=target_instance_id, error=f"Failed to track sub-task {sub_task_id}")
                        return
                    # If it appeared, continue the loop (it will be awaited next iteration or handled above)
            else:
                logger.warning(f"[{task_id}] Dispatch did not return a trackable sub-task ID for action {action_type}. Ending loop or assuming immediate completion? For now, ending loop.")
                # This case might happen if dispatch fails or the action doesn't need tracking (though most should)
                # Decide how to handle this - for now, assume task cannot proceed.
                await self.report_status(task_id, "failed", instance_id=target_instance_id, error=f"Dispatch failed or untrackable for action {action_type}")
                return

        logger.error(f"[{task_id}] Exceeded maximum interpretation loops ({max_loops}). Task failed.")
        await self.report_status(task_id, "failed", instance_id=target_instance_id, error=f"Exceeded max loops ({max_loops})")

    async def start(self):
        """Start the coordinator's main loop (if needed, e.g., for polling)."""
        logger.info(f"[{AGENT_ID}] Starting coordinator...")
        # If the coordinator needs to actively poll or listen, start its loop here.
        # For now, assuming tasks are pushed via execute_task and events via handle_bus_event.
        # Example listener loop:
        # while self.running:
        #     event = await self.agent_bus.get_event() # Example method
        #     if event:
        #         await self.handle_bus_event(event)
        #     await asyncio.sleep(0.1)
        pass # No active loop needed based on current design

    async def stop(self):
        """Stop the coordinator and clean up resources."""
        logger.info(f"[{AGENT_ID}] Stopping coordinator...")
        self.running = False
        # Cancel any active tasks managed by this coordinator
        for task_id, task in self.active_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled active task: {task_id}")
        # Wait for tasks to finish cancelling
        await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        self.active_tasks.clear()
        logger.info(f"[{AGENT_ID}] Coordinator stopped.") 