# DreamForge Agents - Development Task List

## Onboarding Instructions

**Purpose:** This task list tracks development, testing, and refinement tasks specifically for the core system agents (e.g., `PlannerAgent`, `CalendarAgent`, `WorkflowAgent`, `ArchitectsEdgeAgent`) primarily located within the `agents/` directory and related core components (`core/`). Your primary focus is implementing and testing the core logic and interactions of these agents.

**Core Coordination Documents:**
*   **Rulebook:** `/d:/Dream.os/_agent_coordination/rulebook.md`
*   **Agent Stop Protocol:** `/d:/Dream.os/_agent_coordination/agent_stop_protocol.md`
*   **Main Task List:** `/d:/Dream.os/tasks/task_list.md`
*   **ACTION:** Review these core documents thoroughly before starting any tasks.

**Communication & Mailbox:**
*   Core inter-agent communication uses the central `AgentBus` (`core/coordination/agent_bus.py`).
*   Tasks in this list are primarily for development/refinement and will be assigned conceptually. Direct mailbox interaction is generally not expected for these internal development tasks unless specified in the task details.

---

## Agent Development Tasks

*(Tasks related to implementing and refining agent logic, models, and tests will be listed here)*

### Data Model Refinement

- **DF-MODEL-001:** Refine `Task` data model in `core/models/task.py`.
  - Add validation (e.g., using Pydantic if integrated later, or custom checks).
  - Implement timestamp updates in `update_status`.
  - Replace `print` with proper logging.
  - Add comprehensive docstrings and type hints.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

- **DF-MODEL-002:** Refine `Plan` data model in `core/models/plan.py`.
  - Add validation.
  - Implement methods for plan manipulation (e.g., reordering tasks, calculating total estimated time).
  - Add comprehensive docstrings and type hints.
  - Status: Completed
  - Priority: Low
  - Assigned To: DevAgent (Hypothetical)

- **DF-MODEL-003:** Refine `WorkflowDefinition` and `WorkflowStep` models in `core/models/workflow.py`.
  - Add validation (e.g., step ID uniqueness, parameter structure).
  - Consider adding error handling/retry configuration per step.
  - Add comprehensive docstrings and type hints.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

### Testing Implementation

- **DF-TEST-001:** Implement tests for `ArchitectsEdgeAgent` in `agents/tests/test_architects_edge_agent.py`.
  - Test `interpret_directive` with various inputs.
  - Test `dispatch_to_dreamforge` using mock AgentBus.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

- **DF-TEST-002:** Implement tests for `PlannerAgent` in `agents/tests/test_planner_agent.py`.
  - Test `plan_from_goal` response structure.
  - Test `refine_plan` with sample plans and instructions.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

- **DF-TEST-003:** Implement tests for `CalendarAgent` in `agents/tests/test_calendar_agent.py`.
  - Test `schedule_tasks` merging logic.
  - Test `find_available_slots` with constraints.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

- **DF-TEST-004:** Implement tests for `WorkflowAgent` in `agents/tests/test_workflow_agent.py`.
  - Test `generate_workflow` parsing and saving.
  - Test `execute_workflow` step execution and context passing (mock AgentBus).
  - Test `_interpolate_params` edge cases.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)
  - Notes: Test suite now passes after fixing core dependencies and interpolation logic.

- **DF-TEST-005:** Implement tests for `AgentBus` in `core/tests/test_agent_bus.py`.
  - Test Singleton pattern.
  - Test agent registration/unregistration.
  - Test dispatch success and failure modes.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

- **DF-TEST-006:** Implement tests for data models in `core/tests/test_models.py`.
  - Test Task, Plan, WorkflowDefinition creation and basic methods.
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

- **DF-TEST-007:** Implement tests for core services in `core/tests/test_core_services.py`.
  - Test `template_engine.render_template` (assuming it's in `core/template_engine.py`).
  - Test `prompt_staging_service.stage_and_execute_prompt` (assuming it's in `core/prompt_staging_service.py`, requires mocking LLM/bridge).
  - Status: Completed
  - Priority: Medium
  - Assigned To: DevAgent (Hypothetical)

# Task List: agents Module (`/d:/Dream.os/agents/`)

Tasks related to the definition, implementation, and integration of individual agents.

## I. AgentBus Integration (General)

-   [ ] **Review Agent Registration:** Ensure all agents within this directory are correctly registered with the `AgentBus` (`/d:/Dream.os/_agent_coordination/core/agent_bus.py`).
-   [ ] **Standardize Event Handling:** Ensure agents consistently subscribe to and handle events using `AgentBus` methods.
-   [ ] **Task Reception (`EventType.TASK`):**
    -   [ ] Verify all agents intended to receive tasks from `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` correctly handle the `EventType.TASK` event.
    -   [ ] Ensure robust parsing of the task payload (`action`, `params`, etc.).
-   [ ] **Task Status Updates:**
    -   [ ] Standardize how agents report `COMPLETED`/`FAILED` status for tasks originating from the task list (e.g., direct update to `/d:/Dream.os/runtime/task_list.json` via utility, `AgentBus` status event).
    -   [ ] Ensure the chosen mechanism is reliable and handles potential errors (e.g., uses file locking if writing directly).

## II. Specific Agent Reviews

-   [ ] **`CursorControlAgent`:**
    -   [ ] Review handled `task_type`s and ensure they align with the inference map in `TaskDispatcherAgent`.
    -   [ ] Verify interaction logic with VS Code or other target IDEs.
    -   [ ] Test robustness of terminal command execution and output handling.
-   [ ] **`MeredithResonanceScanner`:**
    -   [ ] Define tasks/events handled by this agent.
    -   [ ] Verify integration with relevant data sources or systems.
-   [ ] **`FeedbackEngine`:**
    -   [ ] Define tasks/events handled by this agent.
    -   [ ] Verify feedback processing logic.
-   [ ] **`AgentMonitorAgent`:**
    -   [ ] Define tasks/events handled by this agent.
    -   [ ] Verify system status reporting mechanisms.
-   [ ] **Other Agents:** Review any other agents in `/d:/Dream.os/agents/` for AgentBus integration, task handling, and specific logic.

## III. Testing

-   [ ] Add/update unit tests for individual agent logic.
-   [ ] Add/update integration tests (using mocked `AgentBus`) for agent event handling and task processing (as outlined in `/d:/Dream.os/tests/task_list.md`).

## IV. Documentation & Logging

-   [ ] Ensure each agent file has a clear module/class docstring explaining its purpose.
-   [ ] Document the specific tasks/events handled by each agent.
-   [ ] Enhance logging within agents for better traceability of actions and decisions.

## V. Finalization

-   [ ] Commit all changes to agent code.
-   [ ] Resolve any outstanding TODOs or issues within agent implementations.

## Core Agents

### CalendarAgent (`/d:/Dream.os/agents/calendar_agent.py`)
-   [x] Basic functionality: Read calendar events.
-   [ ] Add new events.
-   [ ] Edit existing events.
-   [ ] Integrate with Google Calendar API.
-   [ ] AgentBus Integration: Handle relevant scheduling tasks/events.

### ArchitectsEdgeAgent (`/d:/Dream.os/agents/architects_edge_agent.py`)
-   [x] Initial setup.
-   [ ] Define core architectural analysis tasks.
-   [ ] Integrate with project structure analysis tools.
-   [ ] AgentBus Integration: Subscribe to code change events, report architectural violations.

### ChatGPTCommanderAgent (`/d:/Dream.os/agents/chatgpt_commander_agent.py`)
-   [x] Basic interaction loop.
-   [ ] Command parsing refinement.
-   [ ] State management for conversations.
-   [ ] Error handling for API calls.
-   [ ] AgentBus Integration: Receive commands, dispatch resulting tasks/events.

## Reflection Agent (`/d:/Dream.os/agents/reflection_agent/`)
-   [ ] Define reflection process steps.
-   [ ] Implement data gathering for reflection.
-   [ ] Develop reflection analysis algorithms.
-   [ ] AgentBus Integration: Trigger reflection cycles, report insights.

## AgentBus Integration & Task Handling (System-Wide Agent Tasks)

*Tasks related to ensuring agents correctly interact with the core coordination system (`AgentBus`, `TaskDispatcherAgent`).*

-   [ ] **Review Agent Registration:** Ensure all agents within `/d:/Dream.os/agents/` are correctly registered with the `AgentBus` (`/d:/Dream.os/_agent_coordination/core/agent_bus.py`).
-   [ ] **Standardize Event Handling:** Ensure agents consistently subscribe to and handle events using `AgentBus` methods.
-   [ ] **Task Reception (`EventType.TASK`):**
    -   [ ] Verify all agents intended to receive tasks from `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` correctly handle the `EventType.TASK` event.
    -   [ ] Ensure robust parsing of the task payload (`action`, `params`, etc.).
-   [ ] **Task Status Updates:**
    -   [ ] Standardize how agents report `COMPLETED`/`FAILED` status for tasks originating from the task list (e.g., direct update to `/d:/Dream.os/runtime/task_list.json` via utility, `AgentBus` status event).
    -   [ ] Ensure the chosen mechanism is reliable and handles potential errors (e.g., uses file locking if writing directly).

## Specific Agent Reviews (Post-Refactor)

-   [ ] **`CursorControlAgent`:**
    -   [ ] Review handled `task_type`s and ensure they align with the inference map in `TaskDispatcherAgent`.
    -   [ ] Verify interaction logic with VS Code or other target IDEs.
    -   [ ] Test robustness of terminal command execution and output handling.
-   [ ] **`MeredithResonanceScanner`:**
    -   [ ] Define tasks/events handled by this agent.
    -   [ ] Verify integration with relevant data sources or systems.
-   [ ] **`FeedbackEngine`:**
    -   [ ] Define tasks/events handled by this agent.
    -   [ ] Verify feedback processing logic.
-   [ ] **`AgentMonitorAgent`:**
    -   [ ] Define tasks/events handled by this agent.
    -   [ ] Verify system status reporting mechanisms.
-   [ ] **Other Agents:** Review any other agents in `/d:/Dream.os/agents/` for AgentBus integration, task handling, and specific logic post-coordination refactor.

## Testing (Agent Specific)

-   [ ] Add/update unit tests for individual agent logic.
-   [ ] Add/update integration tests (using mocked `AgentBus`) for agent event handling and task processing (as outlined in `/d:/Dream.os/tests/task_list.md`).

## Documentation & Logging (Agent Specific)

-   [ ] Ensure each agent file has a clear module/class docstring explaining its purpose.
-   [ ] Document the specific tasks/events handled by each agent.
-   [ ] Enhance logging within agents for better traceability of actions and decisions.

## General Agent Development

-   [ ] Develop template/boilerplate for new agents.
-   [ ] Define standard agent lifecycle methods (start, stop, handle_message).
-   [ ] Improve error handling and resilience framework for agents.

## V. Finalization (Agents Module)

-   [ ] Commit all changes to agent code.
-   [ ] Resolve any outstanding TODOs or issues within agent implementations. 