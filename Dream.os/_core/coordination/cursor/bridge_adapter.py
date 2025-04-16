from .task_execution_state_machine import TaskExecutionPlan, TaskStep

logger = logging.getLogger("CursorBridgeAdapter")

@dataclass
class CursorGoal:
    text_to_type: Optional[str] = None

class CursorBridgeAdapter:
    def __init__(self):
        self.goal_templates = {
            "refactor": self._build_refactor_plan,
            "generate_tests": self._build_generate_tests_plan,
            "execute_prompt": self._build_execute_prompt_plan,
            "type_text": self._build_type_text_plan,
        }
        logger.info("CursorBridgeAdapter initialized with %d goal templates.", len(self.goal_templates))
        
    def translate_goal_to_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        pass

    def _build_refactor_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        pass

    def _build_generate_tests_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        pass
        
    def _build_execute_prompt_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        if not goal.prompt_text:
            raise ValueError("'prompt_text' is required for execute_prompt goal.")

        chat_input_element = "chat_input"
        send_button_element = "send_button"
        response_output_element = "response_output_area"

        steps = [
            TaskStep(action="wait_for_element", element=chat_input_element, timeout=5),
            TaskStep(action="click", element=chat_input_element, required=True),
            TaskStep(action="type_text", params={"text": goal.prompt_text}, timeout=30, required=True),
            TaskStep(action="wait_for_element", element=send_button_element, timeout=5),
            TaskStep(action="click", element=send_button_element, required=True),
            TaskStep(action="wait_for_element", element=response_output_element, timeout=60, required=True),
        ]
        return TaskExecutionPlan(task_id=goal.task_id, steps=steps)
        
    def _build_type_text_plan(self, goal: CursorGoal) -> TaskExecutionPlan:
        target_element = goal.additional_params.get("target_element", "chat_input")
        text_to_type = goal.text_to_type
        if not text_to_type:
             raise ValueError("'text_to_type' is required for type_text goal.")
             
        steps = [
             TaskStep(action="wait_for_element", element=target_element, timeout=5),
             TaskStep(action="click", element=target_element, required=True),
             TaskStep(action="type_text", params={"text": text_to_type}, timeout=30, required=True),
        ]
        return TaskExecutionPlan(task_id=goal.task_id, steps=steps) 