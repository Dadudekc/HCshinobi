# DreamForge - Initial Task List

## Phase 1: Core Agent Scaffolding

- **DF-AGENT-000:** Create initial `ArchitectsEdgeAgent` class structure in `dreamforge/agents/architects_edge_agent.py`.
  - Define `__init__` method.
  - Define placeholder method for `interpret_directive(directive: str) -> dict` (to translate user intent).
  - Define placeholder method for `dispatch_to_dreamforge(action: dict)` (to send command to specific DreamForge agents).
  - Status: Completed
  - Priority: Critical

- **DF-AGENT-001:** Create initial `PlannerAgent` class structure in `dreamforge/agents/planner_agent.py`. 
  - Define `__init__` method.
  - Define placeholder methods for `plan_from_goal(goal: str) -> list[dict]` and `refine_plan(plan: list[dict]) -> list[dict]`.
  - Status: Completed
  - Priority: High

- **DF-AGENT-002:** Create initial `CalendarAgent` class structure in `dreamforge/agents/calendar_agent.py`.
  - Define `__init__` method.
  - Define placeholder methods for `schedule_tasks(tasks: list[dict]) -> list[dict]` and `find_available_slots(duration_minutes: int, constraints: dict) -> list[dict]`.
  - Status: Completed
  - Priority: High

- **DF-AGENT-003:** Create initial `WorkflowAgent` class structure in `dreamforge/agents/workflow_agent.py`.
  - Define `__init__` method.
  - Define placeholder methods for `generate_workflow(prompt: str) -> dict` and `execute_workflow(workflow_id: str, inputs: dict)`.
  - Status: Completed
  - Priority: High

- **DF-AGENT-004:** Implement `dispatch_to_dreamforge` method in `ArchitectsEdgeAgent`.
  - Import and use `AgentBus`.
  - Map parsed action (from `interpret_directive`) to `AgentBus.dispatch` calls.
  - Status: Completed
  - Priority: High

- **DF-AGENT-005:** Implement `refine_plan` method in `PlannerAgent`.
  - Create and use `refine_plan.j2` prompt template.
  - Take an existing plan and refinement instructions/feedback as input.
  - Output the refined plan list.
  - Status: Completed
  - Priority: Medium

- **DF-AGENT-006:** Implement `find_available_slots` method in `CalendarAgent`.
  - Create and use `find_available_slots.j2` prompt template.
  - Take duration and constraints as input.
  - Load existing schedule.
  - Output a list of available time slots.
  - Status: Completed
  - Priority: Medium

- **DF-AGENT-007:** Implement `generate_workflow` method in `WorkflowAgent`.
  - Create and use `generate_workflow.j2` prompt template.
  - Take a natural language prompt as input.
  - Output a structured workflow definition dictionary.
  - Save the generated workflow definition.
  - Status: Completed
  - Priority: Medium

- **DF-AGENT-008:** Implement `execute_workflow` method in `WorkflowAgent`.
  - Load workflow definition.
  - Iterate through steps.
  - Interpolate parameters using context.
  - Dispatch step commands via AgentBus.
  - Handle step outputs and failures.
  - Status: Completed
  - Priority: High # Crucial for making workflows functional

- **DF-AGENT-009:** Improve parameter interpolation in `WorkflowAgent._interpolate_params`.
  - Handle nested dictionary access (e.g., `{{step_1.result.key}}`).
  - Add basic list index access (e.g., `{{step_2.items[0]}}`) if feasible.
  - Improve error handling and logging for missing keys/indices.
  - Status: Completed
  - Priority: Medium

## Phase 2: Agent Integration & Core Logic (TBD)

- **DF-COORD-001:** Implement initial `AgentBus` class in `dreamforge/coordination/agent_bus.py`.
  - Use Singleton pattern.
  - Implement `register_agent`, `unregister_agent`, and `dispatch` methods.
  - Status: Completed
  - Priority: Critical

- **DF-SOCIAL-001:** Implement GPT context analysis in `social/post_context_generator.py`.
  - Create `prompts/social/analyze_context.j2` template.
  - Call LLM via prompt staging service to analyze governance context.
  - Populate `gpt_decision` field in the returned context.
  - Status: Completed
  - Priority: Medium

- **DF-DEV-001:** Implement Sentiment Analysis for SocialAgent (Ref: social-new-003).
  - Modify `SocialMediaAgent` or relevant strategies (Twitter/Reddit).
  - Integrate NLTK/VADER library for sentiment scoring of scraped mentions.
  - Add results (e.g., sentiment score/label) to mention data.
  - Log sentiment outcomes using `governance_memory_engine.log_event`.
  - Add necessary dependency to requirements.txt (e.g., `nltk`).
  - Status: Pending
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

## Phase 3: UI Development (TBD)

# Task List: tasks Module (`/d:/Dream.os/tasks/`)

Tasks related to predefined task instances, templates, or high-level project goals.

**Note:** Review if this overlaps significantly with `/d:/Dream.os/agent_tasks/task_list.md` (for schema/types) or `/d:/Dream.os/PROJECT_TASKS.md` (for project management). Consolidate if necessary.

## I. Predefined Task Templates/Instances

-   [ ] **Review Purpose:** Clarify the role of this directory. Does it hold example task JSON files? Templates for generating tasks? High-level goal definitions?
-   [ ] **Update Existing Tasks:** If this holds predefined task instances (e.g., for testing, common workflows), ensure they conform to the latest schema defined in `/d:/Dream.os/agent_tasks/task_list.md`.
-   [ ] **Task Template Engine (If Applicable):** If tasks are generated from templates here, review the templating logic.

## II. High-Level Goal Tracking

-   [ ] **Link to Project Tasks:** If this tracks high-level goals, ensure it aligns with `/d:/Dream.os/PROJECT_TASKS.md`.
-   [ ] **Breakdown:** Ensure high-level goals here are broken down into actionable agent tasks tracked in `/d:/Dream.os/runtime/task_list.json`.

## III. Consistency & Maintenance

-   [ ] **Schema Compliance:** Ensure all task definitions or instances here use the standard schema.
-   [ ] **Remove Obsolete Tasks:** Clean up any outdated templates or definitions.

## IV. Documentation

-   [ ] **Document Purpose:** Clearly explain the purpose of this directory and its contents in a README or within `/d:/Dream.os/docs/task_list.md`.
-   [ ] **Document Templates/Goals:** Explain any predefined task templates or high-level goals stored here.

## V. Finalization

-   [ ] Commit changes to task definitions/templates.
-   [ ] Ensure clarity on the role of this directory vs. other task-related locations. 