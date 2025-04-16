import os
import sys
import json

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(__file__) # dreamforge/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

# --- Core Imports --- 
try:
    from dreamforge.core.governance_memory_engine import log_event
    from dreamforge.core.coordination.agent_bus import AgentBus
    from dreamforge.agents.planner_agent import PlannerAgent
    from dreamforge.agents.calendar_agent import CalendarAgent
    # Import other agents as needed (e.g., WorkflowAgent)
except ImportError as e:
    print(f"[Main] Critical error importing core components: {e}")
    sys.exit(1)
# ------------------

_SOURCE_ID = "DreamForgeMain"

def main():
    log_event("SYSTEM_START", _SOURCE_ID, {"message": "DreamForge main execution started."})    

    # 1. Initialize AgentBus (Singleton)
    log_event("SYSTEM_STEP", _SOURCE_ID, {"step": "Initializing AgentBus"})
    agent_bus = AgentBus()

    # 2. Initialize Agents
    log_event("SYSTEM_STEP", _SOURCE_ID, {"step": "Initializing Agents"})
    try:
        # LLM config can be loaded from a central config file later
        planner = PlannerAgent(llm_config={"model": "simulated-default"})
        calendar = CalendarAgent(llm_config={"model": "simulated-default"})
        # workflow_agent = WorkflowAgent(agent_bus)
    except Exception as e:
        log_event("SYSTEM_CRITICAL", _SOURCE_ID, {"error": "Failed to initialize agents", "details": str(e)})
        return # Cannot proceed

    # 3. Register Agents with the Bus
    log_event("SYSTEM_STEP", _SOURCE_ID, {"step": "Registering Agents"})
    registration_success = True
    if not agent_bus.register_agent(planner.agent_id, planner):
        log_event("SYSTEM_ERROR", _SOURCE_ID, {"error": f"Failed to register {planner.agent_id}"})
        registration_success = False
    if not agent_bus.register_agent(calendar.agent_id, calendar):
        log_event("SYSTEM_ERROR", _SOURCE_ID, {"error": f"Failed to register {calendar.agent_id}"})
        registration_success = False
    # if not agent_bus.register_agent(workflow_agent.agent_id, workflow_agent):
    #     log_event("SYSTEM_ERROR", _SOURCE_ID, {"error": f"Failed to register WorkflowAgent"})
    #     registration_success = False
        
    if not registration_success:
        log_event("SYSTEM_CRITICAL", _SOURCE_ID, {"error": "Agent registration failed. Aborting."})    
        return
        
    log_event("SYSTEM_INFO", _SOURCE_ID, {"message": "Agents initialized and registered", "registered_agents": agent_bus.list_agents()})

    # 4. Example Workflow: Plan & Schedule
    log_event("SYSTEM_STEP", _SOURCE_ID, {"step": "Starting example workflow: Plan & Schedule"})
    user_goal = "Create a comprehensive tutorial for the new AgentBus system."
    log_event("USER_INPUT", _SOURCE_ID, {"goal": user_goal})

    try:
        # --- Planning --- 
        log_event("WORKFLOW_STEP", _SOURCE_ID, {"agent": planner.agent_id, "action": "plan_from_goal"})
        initial_plan = planner.plan_from_goal(user_goal)

        if not initial_plan:
            log_event("WORKFLOW_FAIL", _SOURCE_ID, {"reason": "Planning failed.", "goal": user_goal})
            return # Cannot proceed without a plan

        log_event("WORKFLOW_INFO", _SOURCE_ID, {"message": "Plan generated", "task_count": len(initial_plan)})
        # Optional: print plan details
        # print("--- Initial Plan ---")
        # print(json.dumps(initial_plan, indent=2))
        # print("--------------------")

        # --- Scheduling --- 
        # Define dummy existing events for now
        existing_calendar_events = [
            {"summary": "Daily Standup", "start": "2025-01-01T09:00:00Z", "end": "2025-01-01T09:15:00Z"}
        ]
        log_event("WORKFLOW_STEP", _SOURCE_ID, {"agent": calendar.agent_id, "action": "schedule_tasks"})
        scheduled_plan = calendar.schedule_tasks(initial_plan, existing_calendar_events)

        if not scheduled_plan:
             log_event("WORKFLOW_FAIL", _SOURCE_ID, {"reason": "Scheduling failed.", "plan_task_count": len(initial_plan)})
        else:
            log_event("WORKFLOW_COMPLETE", _SOURCE_ID, {"message": "Plan generated and scheduled (simulated)", "final_plan_task_count": len(scheduled_plan)})
            # Optional: print scheduled plan details
            print("--- Scheduled Plan (Simulated) ---")
            print(json.dumps(scheduled_plan, indent=2))
            print("---------------------------------")
            
    except Exception as e:
        log_event("WORKFLOW_ERROR", _SOURCE_ID, {"error": "Error during Plan & Schedule workflow", "details": str(e)})

    # --- End Example Workflow ---
    
    log_event("SYSTEM_STOP", _SOURCE_ID, {"message": "DreamForge main execution finished."})

if __name__ == "__main__":
    main() 