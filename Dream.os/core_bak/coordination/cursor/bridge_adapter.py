# core/coordination/cursor/bridge_adapter.py

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid # Import uuid for default task_id generation

# Corrected import path assuming task_execution_state_machine is in the same directory
# If it's elsewhere, adjust the import accordingly.
# Example: from core.coordination.cursor.task_execution_state_machine import (
#             TaskExecutionPlan, TaskStep
#          )
# Assuming the structure allows direct import:
from .task_execution_state_machine import TaskExecutionPlan, TaskStep

logger = logging.getLogger("CursorBridgeAdapter")

@dataclass
class CursorGoal:
    """Represents a high-level goal for Cursor automation."""
    type: str
    target_file: Optional[str] = None
    prompt_text: Optional[str] = None
    test_framework: Optional[str] = None
    # Use field for mutable default
    additional_params: Dict = field(default_factory=dict)
    # Add optional task_id for pre-assignment
    task_id: Optional[str] = None 

class CursorBridgeAdapter:
    """Translates high-level Cursor-related goals into executable TaskExecutionPlans."""

    def __init__(self):
        """Initializes the adapter, potentially loading templates in the future."""
        # In the future, load goal-to-plan templates from config or fine-tune via feedback
        # The keys here MUST match the `type` field in CursorGoal
        self.goal_templates = {
            "refactor": self._build_refactor_plan,
            "generate_tests": self._build_generate_tests_plan,
            "execute_prompt": self._build_execute_prompt_plan,
            # Add more predefined plans here
        }
        logger.info("CursorBridgeAdapter initialized with %d goal templates.", len(self.goal_templates))

    def translate_goal_to_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """Main entry point to convert a CursorGoal into a TaskExecutionPlan."""
        logger.info(f"Translating goal: type={goal.type}, target={goal.target_file or 'N/A'}")
        handler = self.goal_templates.get(goal.type)
        
        if not handler:
            logger.error(f"No plan template defined for goal type: {goal.type}")
            raise ValueError(f"No plan template defined for goal type: {goal.type}")
            
        try:
            plan = handler(goal)
            # Assign or generate task_id if not provided in goal
            if goal.task_id:
                plan.task_id = goal.task_id
            elif not plan.task_id: # Ensure handler didn't already set one
                 # Generate a default task ID based on type and target
                 target_suffix = f"_{Path(goal.target_file).name}" if goal.target_file else ""
                 plan.task_id = f"CURSOR_{goal.type.upper()}{target_suffix}_{uuid.uuid4().hex[:8]}"
                 
            logger.info(f"Successfully generated plan with {len(plan.steps)} steps for task {plan.task_id}")
            return plan
        except Exception as e:
            logger.error(f"Error building plan for goal type {goal.type}: {e}", exc_info=True)
            # Re-raise or return a failed plan state? Re-raising for now.
            raise

    # --- Plan Building Methods --- 
    # These methods construct the sequence of TaskSteps for each goal type.
    # NOTE: These are simplified examples. Actual element names and required steps 
    # might differ based on Cursor's UI and require refinement using cursor_ui_trainer.
    # Also, error handling steps (e.g., wait_for_error_message) might be needed.

    def _build_refactor_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """Builds a plan to request and apply a refactor in Cursor."""
        if not goal.target_file:
            raise ValueError("'target_file' is required for refactor goal.")
            
        # Placeholder element names - MUST be trained with cursor_ui_trainer
        chat_input_element = "chat_input"
        send_button_element = "send_button" 
        diff_modal_element = "diff_modal" # Element indicating diff is shown
        apply_button_element = "accept_button" # Or specific apply button
        loading_indicator_element = "loading_indicator" # Element shown during processing
        
        return TaskExecutionPlan(
            task_id=goal.task_id, # Allow pre-assignment
            steps=[
                # Step 1: Focus chat input (optional, depends on state)
                # TaskStep(action="wait_for_element", element=chat_input_element, timeout=5),
                # TaskStep(action="click", element=chat_input_element),
                
                # Step 2: Type the refactor command
                # TaskStep(action="type_text", params={"text": f"Refactor {goal.target_file}"}, timeout=10), # Placeholder action
                
                # Step 3: Click send
                # TaskStep(action="wait_for_element", element=send_button_element, timeout=5),
                # TaskStep(action="click", element=send_button_element),
                
                # Step 4: Wait for Cursor's response (e.g., the diff view)
                TaskStep(action="wait_for_element", element=diff_modal_element, timeout=30, required=True), # Wait longer for AI
                
                # Step 5: Click Apply/Accept
                TaskStep(action="wait_for_element", element=apply_button_element, timeout=5),
                TaskStep(action="click", element=apply_button_element, required=True),
                
                # Step 6: Wait for processing to finish (e.g., loading indicator disappears)
                # TaskStep(action="wait_for_element_gone", element=loading_indicator_element, timeout=20, required=False), # Optional verification
            ]
        )

    def _build_generate_tests_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """Builds a plan to generate unit tests in Cursor."""
        if not goal.target_file or not goal.test_framework:
            raise ValueError("'target_file' and 'test_framework' are required for generate_tests goal.")

        # Placeholder element names
        chat_input_element = "chat_input"
        send_button_element = "send_button" 
        test_modal_element = "test_generation_modal" # Or specific output area
        apply_test_button_element = "apply_test_button" # Placeholder
        loading_indicator_element = "loading_indicator"

        return TaskExecutionPlan(
            task_id=goal.task_id,
            steps=[
                # TaskStep(action="wait_for_element", element=chat_input_element, timeout=5),
                # TaskStep(action="click", element=chat_input_element),
                # TaskStep(action="type_text", params={"text": f"Write {goal.test_framework} unit tests for {goal.target_file}"}, timeout=10), 
                # TaskStep(action="wait_for_element", element=send_button_element, timeout=5),
                # TaskStep(action="click", element=send_button_element),
                TaskStep(action="wait_for_element", element=test_modal_element, timeout=45, required=True), # Wait longer for test gen
                TaskStep(action="wait_for_element", element=apply_test_button_element, timeout=5),
                TaskStep(action="click", element=apply_test_button_element, required=True),
                # TaskStep(action="wait_for_element_gone", element=loading_indicator_element, timeout=20, required=False),
            ]
        )

    def _build_execute_prompt_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        """Builds a plan to execute a generic prompt in Cursor chat."""
        if not goal.prompt_text:
            raise ValueError("'prompt_text' is required for execute_prompt goal.")

        # Placeholder element names
        chat_input_element = "chat_input"
        send_button_element = "send_button" 
        response_output_element = "response_output_area" # Placeholder

        return TaskExecutionPlan(
            task_id=goal.task_id,
            steps=[
                # TaskStep(action="wait_for_element", element=chat_input_element, timeout=5),
                # TaskStep(action="click", element=chat_input_element),
                # TaskStep(action="type_text", params={"text": goal.prompt_text}, timeout=10),
                # TaskStep(action="wait_for_element", element=send_button_element, timeout=5),
                # TaskStep(action="click", element=send_button_element),
                TaskStep(action="wait_for_element", element=response_output_element, timeout=60, required=True), # Wait potentially long for response
                # Future step: TaskStep(action="get_text", element=response_output_element) 
            ]
        )

# Example of how to add more plan builders:
# def _build_run_tests_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
#     if not goal.target_file:
#         raise ValueError("'target_file' is required for run_tests goal.")
#     return TaskExecutionPlan(
#         task_id=goal.task_id,
#         steps=[
#             TaskStep(action="click", element="run_tests_button"),
#             TaskStep(action="wait_for_element", element="test_results_indicator", timeout=120), # Wait long for tests
#             # TaskStep(action="verify_element", element="test_passed_badge") # Check for success state
#         ]
#     ) 