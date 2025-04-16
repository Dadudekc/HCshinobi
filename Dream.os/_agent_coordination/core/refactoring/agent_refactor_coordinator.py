"""
Core logic and architecture for the Agent Refactor Coordinator.

This agent is responsible for planning and orchestrating code refactoring tasks,
leveraging analysis tools and (eventually) execution tools.
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid
import os

# --- Potential Future Imports (if integrated into swarm) ---
# from core.agent_bus import agent_bus, Event, EventType
# from dreamos.coordinator import AgentDomain, AgentState 
# Assuming this might eventually run as Agent 5 or similar
AGENT_ID_PLACEHOLDER = "refactor_coordinator_0"

# --- Tool Paths (Relative to project root) ---
# Assumes the project root is correctly set in PYTHONPATH or cwd
TOOL_DIR = Path(__file__).parent.parent.parent / "tools"
ANALYZE_SCRIPT = TOOL_DIR / "analyze_file_structure.py"
IDENTIFY_SCRIPT = TOOL_DIR / "identify_refactor_candidates.py"
MOVE_SCRIPT = TOOL_DIR / "refactor_move_symbol.py"

PYTHON_EXECUTABLE = sys.executable

# --- Setup Logging ---
# In a real worker, this would be configured per-agent
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentRefactorCoordinator")


class RefactorTask:
    """Dataclass or structure for representing a refactoring task."""
    def __init__(self, task_id: str, goal: str, target_file: str, criteria: Optional[List[str]] = None, params: Optional[Dict] = None):
        self.task_id = task_id
        self.goal = goal # e.g., "modularize", "deduplicate", "extract_class"
        self.target_file = Path(target_file).resolve()
        self.criteria = criteria if criteria else [] # e.g., ["group by responsibility", "split >500 LOC modules"]
        self.params = params if params else {} # e.g., {"symbols_to_extract": ["MyClass"]}
        self.status = "received"
        self.plan: Optional[List[Dict]] = None
        self.error: Optional[str] = None
        self.analysis_result: Optional[Dict] = None
        self.candidate_locations: Optional[Dict] = None
        
    def update_status(self, status: str, error: Optional[str] = None):
        self.status = status
        self.error = error
        logger.info(f"Refactor task '{self.task_id}' status updated to: {status}" + (f" Error: {error}" if error else ""))
        # TODO: Send event to AgentBus if running in swarm

class AgentRefactorCoordinator:
    """Orchestrates code refactoring tasks."""

    def __init__(self):
        self.active_tasks: Dict[str, RefactorTask] = {}
        logger.info("AgentRefactorCoordinator initialized.")
        # TODO: Add registration logic if running as a full agent
        
    # --- Task Intake --- 
    def receive_task(self, task_data: Dict) -> Optional[str]:
        """Receives a new refactoring task description."""
        # Basic validation
        if not all(k in task_data for k in ["goal", "target_file"]):
            logger.error(f"Received task with missing required fields: {task_data}")
            return None
            
        task_id = task_data.get("task_id", f"refactor_{uuid.uuid4().hex[:8]}")
        if task_id in self.active_tasks:
            logger.warning(f"Task {task_id} already exists. Ignoring.")
            return task_id

        task = RefactorTask(
            task_id=task_id,
            goal=task_data["goal"],
            target_file=task_data["target_file"],
            criteria=task_data.get("criteria"),
            params=task_data.get("params")
        )
        self.active_tasks[task_id] = task
        logger.info(f"Received refactor task: {task_id} ({task.goal} on {task.target_file.name})")
        # Immediately start processing
        asyncio.create_task(self.process_task(task_id))
        return task_id

    # --- Core Orchestration --- 
    async def process_task(self, task_id: str):
        """Main processing loop for a single refactoring task."""
        task = self.active_tasks.get(task_id)
        if not task:
            logger.error(f"Attempted to process non-existent task: {task_id}")
            return
            
        try:
            task.update_status("analyzing")
            # 1. Analyze Structure
            task.analysis_result = await self.analyze_structure(task.target_file)
            if not task.analysis_result:
                 raise ValueError("Failed to analyze file structure.")

            task.update_status("planning")
            # 2. Generate Refactor Plan
            # This step uses the analysis result and task criteria
            task.plan = await self.generate_refactor_plan(task)
            if not task.plan:
                 raise ValueError("Failed to generate a refactoring plan.")
            
            # 3. Identify Candidates (if needed by plan, e.g., for specific symbols)
            # This might be integrated into planning or done separately
            symbols_to_locate = [] 
            for step in task.plan:
                 if step.get("action") == "move_symbol" and "symbol" in step:
                     symbols_to_locate.append(step["symbol"]) 
                     
            if symbols_to_locate:
                task.candidate_locations = await self.identify_candidates(task.target_file, list(set(symbols_to_locate)))
                # TODO: Update plan steps with location info if needed

            task.update_status("dispatching")
            # 4. Dispatch Refactor Tasks (Execution - Stubbed)
            await self.dispatch_refactor_plan(task)
            
            # 5. Report Completion (Simplified)
            task.update_status("complete")
            await self.report_progress(task, final_status="Success")
            
        except Exception as e:
             error_msg = f"Refactor task {task_id} failed: {e}"
             logger.error(error_msg, exc_info=True)
             if task: task.update_status("failed", error=str(e))
             await self.report_progress(task, final_status="Failure", message=error_msg)

    # --- Tool Integration Methods --- 
    async def _run_tool_script(self, script_path: Path, args: List[str]) -> Optional[Dict]:
        """Helper to run a tool script and parse its JSON output."""
        command = [PYTHON_EXECUTABLE, str(script_path)] + args
        logger.info(f"Running tool: {' '.join(command)}")
        try:
            # Ensure PYTHONPATH includes project root for tool imports
            env = os.environ.copy()
            project_root = Path(__file__).parent.parent.parent
            env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=project_root # Run tools from project root
            )
            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()

            if stderr_str:
                logger.warning(f"Tool '{script_path.name}' emitted stderr: {stderr_str}")

            if process.returncode != 0:
                logger.error(f"Tool '{script_path.name}' failed with exit code {process.returncode}")
                return None
            
            # Find the JSON part of the output (assuming it prints other stuff too)
            json_output = None
            if '{\'imports\':' in stdout_str or '{\'type\':' in stdout_str:
                 # Try to find JSON block if analysis script prints other things
                 # A better approach is for scripts to ONLY print JSON if requested
                 try:
                     # Find first '{' and last '}' to crudely extract JSON
                     start_idx = stdout_str.find('{')
                     end_idx = stdout_str.rfind('}')
                     if start_idx != -1 and end_idx != -1:
                         json_str = stdout_str[start_idx:end_idx+1]
                         json_output = json.loads(json_str)
                     else:
                          logger.warning(f"Could not find JSON block in tool output:
{stdout_str}")
                 except json.JSONDecodeError as json_e:
                     logger.error(f"Failed to decode JSON from tool '{script_path.name}' output: {json_e}\nOutput was:\n{stdout_str}")
                     return None
            else:
                logger.warning(f"Tool '{script_path.name}' output doesn't look like expected JSON:\n{stdout_str}")

            return json_output

        except FileNotFoundError:
            logger.error(f"Tool script not found: {script_path}")
            return None
        except Exception as e:
            logger.error(f"Error running tool '{script_path.name}': {e}", exc_info=True)
            return None

    async def analyze_structure(self, target_file: Path) -> Optional[Dict]:
        """Use analyze_file_structure.py to get a component map."""
        args = [str(target_file), "--output-json"]
        return await self._run_tool_script(ANALYZE_SCRIPT, args)

    async def identify_candidates(self, target_file: Path, symbols: List[str]) -> Optional[Dict]:
        """Use identify_refactor_candidates.py to get line positions."""
        args = [str(target_file), "--symbols"] + symbols # Add symbols correctly
        # Assume the identify script also primarily outputs JSON
        return await self._run_tool_script(IDENTIFY_SCRIPT, args) 

    # --- Planning and Dispatch (Stubs) ---
    async def generate_refactor_plan(self, task: RefactorTask) -> Optional[List[Dict]]:
        """(Stub) Generate a sequence of refactoring steps based on analysis and criteria."""
        logger.info(f"Generating refactor plan for task: {task.task_id}")
        # --- TODO: Implement actual planning logic --- 
        # Example: If goal is "modularize" and file is large, plan to move classes/funcs
        plan = []
        if task.goal == "modularize" and task.analysis_result:
            # Simple plan: move each top-level class to its own file
            base_name = task.target_file.stem
            target_dir = task.target_file.parent / base_name # Put modules in subdir?
            for class_info in task.analysis_result.get("classes", []):
                class_name = class_info["name"]
                # Basic check to avoid moving very common/builtin-like names?
                if len(class_name) > 3 and class_name[0].isupper(): 
                     plan.append({
                         "action": "move_symbol",
                         "symbol": class_name,
                         "symbol_type": "class",
                         "source_file": str(task.target_file),
                         "target_file": str(target_dir / f"{class_name.lower()}.py")
                     })
            if not plan:
                 logger.warning("Could not generate any steps for modularization plan.")
                 return None
                 
        elif task.goal == "extract_class" and task.params.get("symbols_to_extract"):
             target_dir = task.target_file.parent
             for symbol_name in task.params["symbols_to_extract"]:
                 plan.append({
                         "action": "move_symbol",
                         "symbol": symbol_name,
                         "symbol_type": "class", # Assume class for now
                         "source_file": str(task.target_file),
                         "target_file": str(target_dir / f"{symbol_name.lower()}.py")
                     })
        else:
            logger.warning(f"Cannot generate plan for goal '{task.goal}' with current logic.")
            return None
            
        logger.info(f"Generated plan with {len(plan)} steps for task {task.task_id}")    
        return plan

    async def dispatch_refactor_plan(self, task: RefactorTask):
        """Execute the steps in the refactoring plan by calling tool scripts."""
        if not task.plan:
            logger.error(f"No plan to dispatch for task {task.task_id}")
            task.update_status("failed", "No plan generated.")
            return
            
        logger.info(f"Dispatching {len(task.plan)} refactor steps for task {task.task_id}")
        all_steps_succeeded = True
        step_errors = []

        for i, step in enumerate(task.plan):
            step_num = i + 1
            action = step.get("action")
            logger.info(f"Executing Step {step_num}/{len(task.plan)}: Action='{action}'")
            
            if action == "move_symbol":
                source = step.get("source_file")
                target = step.get("target_file")
                symbol = step.get("symbol")
                symbol_type = step.get("symbol_type")
                
                # Get location info (requires identify_candidates to have run and populated task)
                start_line, end_line = None, None
                if task.candidate_locations and symbol in task.candidate_locations:
                    loc = task.candidate_locations[symbol]
                    start_line = loc.get("start_line")
                    end_line = loc.get("end_line")
                    
                if not all([source, target, symbol, symbol_type, start_line, end_line]):
                     err = f"Missing parameters for move_symbol step {step_num}: {step}"
                     logger.error(err)
                     step_errors.append(err)
                     all_steps_succeeded = False
                     continue # Skip this step

                # --- Call refactor_move_symbol.py --- 
                tool_args = [
                     "--source", str(source),
                     "--target", str(target),
                     "--symbol", str(symbol),
                     "--type", str(symbol_type),
                     "--start-line", str(start_line),
                     "--end-line", str(end_line),
                     # "--dry-run" # Enable dry-run for testing?
                ]
                # Using _run_tool_script assumes JSON output, but move tool might not produce it
                # Let's call subprocess directly here for more control over success check
                command = [PYTHON_EXECUTABLE, str(MOVE_SCRIPT)] + tool_args
                logger.info(f"  Running command: {' '.join(command)}")
                try:
                    env = os.environ.copy()
                    project_root = Path(__file__).parent.parent.parent
                    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
                    
                    process = await asyncio.create_subprocess_exec(
                        *command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                        cwd=project_root
                    )
                    stdout, stderr = await process.communicate()
                    stdout_str = stdout.decode().strip()
                    stderr_str = stderr.decode().strip()
                    
                    logger.debug(f"  [Move Tool STDOUT]:\n{stdout_str}")
                    if stderr_str:
                         logger.warning(f"  [Move Tool STDERR]:\n{stderr_str}")
                    
                    if process.returncode != 0:
                        err = f"Move symbol step {step_num} failed (Exit Code: {process.returncode}). Symbol: '{symbol}'"
                        logger.error(err)
                        step_errors.append(err + f"\nSTDERR: {stderr_str}")
                        all_steps_succeeded = False
                        # Decide whether to stop plan execution on first failure
                        # break 
                    else:
                        logger.info(f"  Step {step_num} completed successfully.")
                        
                except Exception as e:
                     err = f"Exception running move symbol step {step_num} for '{symbol}': {e}"
                     logger.error(err, exc_info=True)
                     step_errors.append(err)
                     all_steps_succeeded = False
                     # break
                     
            else:
                logger.warning(f"  Skipping unknown plan action in step {step_num}: {action}")
                step_errors.append(f"Unknown action '{action}' in step {step_num}")
                all_steps_succeeded = False

        logger.info(f"Finished dispatching plan for task {task.task_id}")
        if not all_steps_succeeded:
             # Update task status to reflect partial or full failure
             final_error = "Refactor plan execution failed or had errors. Details: " + "; ".join(step_errors)
             task.update_status("failed", final_error)
             await self.report_progress(task, final_status="Failure", message=final_error)
             # Raise an exception to be caught by process_task? Or just log?
             # raise RuntimeError(final_error)
        # If loop completed without error, process_task will set status to complete

    # --- Reporting --- 
    async def report_progress(self, task: Optional[RefactorTask], final_status: str = "In Progress", message: Optional[str] = None):
        """(Stub) Report task progress or completion status."""
        task_id = task.task_id if task else "Unknown"
        log_msg = f"Refactor Task {task_id} | Status: {final_status}" 
        if message: log_msg += f" | Message: {message}"
        logger.info(log_msg)
        # Define the actual agent ID here if applicable, or remove/modify the event dispatch
        # Example: If this coordinator should have a fixed ID:
        # coordinator_agent_id = "refactor_coordinator"
        # await agent_bus._dispatcher.dispatch_event(Event(type=EventType.SYSTEM, source_id=coordinator_agent_id, data=event_data))


# --- Standalone Demo / Simulation Block --- 
if __name__ == "__main__":
    print("--- AgentRefactorCoordinator Standalone Demo ---")
    
    coordinator = AgentRefactorCoordinator()
    
    # Example Task: Modularize the agent_bus.py file (if it exists)
    # NOTE: This requires agent_bus.py to be in the expected location relative to this script
    project_root = Path(__file__).parent.parent.parent
    agent_bus_file = project_root / "core" / "agent_bus.py"
    
    if not agent_bus_file.exists():
        print(f"Error: Cannot run demo. Agent bus file not found at: {agent_bus_file}")
        sys.exit(1)
        
    demo_task_data = {
       "goal": "modularize",
       "target_file": str(agent_bus_file),
       "criteria": ["group by responsibility"],
       "task_id": "demo_modularize_bus"
    }
    
    print(f"\nSubmitting demo task: {demo_task_data['goal']} on {demo_task_data['target_file']}")
    task_id = coordinator.receive_task(demo_task_data)
    
    async def wait_for_task(task_id):
         if not task_id: return
         print(f"\nWaiting for task {task_id} to complete (or fail)...")
         start_time = time.time()
         while task_id in coordinator.active_tasks and coordinator.active_tasks[task_id].status not in ["complete", "failed"]:
             await asyncio.sleep(0.5)
             if time.time() - start_time > 30: # Timeout
                 print("Demo task timed out after 30s.")
                 break
         if task_id in coordinator.active_tasks:
             final_task = coordinator.active_tasks[task_id]
             print(f"\n--- Task {task_id} Final Status: {final_task.status} ---")
             if final_task.plan:
                 print("Generated Plan:")
                 print(json.dumps(final_task.plan, indent=2))
             if final_task.error:
                 print(f"Error: {final_task.error}")
         else:
             print(f"Task {task_id} finished but not found in active list?")

    # Run the main task processing
    try:
        asyncio.run(wait_for_task(task_id))
    except KeyboardInterrupt:
        print("\nDemo interrupted.")
        
    print("\n--- Demo Finished ---") 