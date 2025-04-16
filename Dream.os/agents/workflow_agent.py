import os
import json
import time
import traceback
from core import config
from core.template_engine import default_template_engine as template_engine
from core.coordination.agent_bus import AgentBus
from core.memory.governance_memory_engine import log_event

WORKFLOW_DIR = os.path.join(config.get("memory_dir", "memory"), "workflows")
os.makedirs(WORKFLOW_DIR, exist_ok=True)

class WorkflowAgent:
    def __init__(self, agent_id="WorkflowAgent"):
        self.agent_id = agent_id
        self.bus = AgentBus()

    def _get_workflow_path(self, workflow_id: str) -> str:
        return os.path.join(WORKFLOW_DIR, f"{workflow_id}.json")

    def create_workflow(self, workflow_definition: dict) -> bool:
        try:
            workflow_id = workflow_definition.get("id") or f"workflow_{int(time.time())}"
            workflow_definition["id"] = workflow_id
            with open(self._get_workflow_path(workflow_id), "w") as f:
                json.dump(workflow_definition, f, indent=2)
            log_event("WORKFLOW_CREATED", self.agent_id, {"workflow_id": workflow_id})
            return True
        except Exception as e:
            log_event("WORKFLOW_CREATE_FAILED", self.agent_id, {"error": str(e), "traceback": traceback.format_exc()})
            return False

    def list_workflows(self) -> list:
        try:
            return [f.replace(".json", "") for f in os.listdir(WORKFLOW_DIR) if f.endswith(".json")]
        except Exception as e:
            log_event("WORKFLOW_LIST_FAILED", self.agent_id, {"error": str(e)})
            return []

    def delete_workflow(self, workflow_id: str) -> bool:
        try:
            os.remove(self._get_workflow_path(workflow_id))
            log_event("WORKFLOW_DELETED", self.agent_id, {"workflow_id": workflow_id})
            return True
        except FileNotFoundError:
            log_event("WORKFLOW_NOT_FOUND", self.agent_id, {"workflow_id": workflow_id})
            return False
        except Exception as e:
            log_event("WORKFLOW_DELETE_FAILED", self.agent_id, {"error": str(e)})
            return False

    def execute_workflow(self, workflow_id: str) -> dict:
        try:
            path = self._get_workflow_path(workflow_id)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Workflow {workflow_id} not found")

            with open(path, "r") as f:
                workflow = json.load(f)

            results = []
            for idx, step in enumerate(workflow.get("steps", [])):
                agent = step.get("agent")
                task = step.get("task")
                inputs = step.get("input", {})
                log_event("WORKFLOW_STEP_START", self.agent_id, {
                    "workflow_id": workflow_id,
                    "step": idx,
                    "agent": agent,
                    "task": task
                })
                result = self.bus.dispatch(agent_id=agent, task_name=task, task_input=inputs)
                results.append({"step": idx, "result": result})
                log_event("WORKFLOW_STEP_SUCCESS", self.agent_id, {"step": idx, "result": result})
            return {"workflow_id": workflow_id, "results": results}

        except Exception as e:
            log_event("WORKFLOW_EXECUTION_FAILED", self.agent_id, {"workflow_id": workflow_id, "error": str(e), "traceback": traceback.format_exc()})
            return {"error": str(e)}
