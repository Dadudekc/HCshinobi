# DreamForge Agent Development Task List

## Onboarding & Coordination

**Purpose:** This document tracks specific development, testing, and refinement tasks for the core agents within the DreamForge system (Planner, Calendar, Workflow, etc.). Focus is on building and integrating the capabilities of these internal agents.

**Core Coordination Documents:**
*   **Rulebook:** `/d:/Dream.os/_agent_coordination/rulebook.md` (Defines operational rules and protocols)
*   **Main Task List:** `/d:/Dream.os/dreamforge/tasks/task_list.md` (Tracks higher-level DreamForge features and integrations)

**Communication & Mailbox:**
*   Inter-agent communication within DreamForge typically occurs via the `AgentBus` (defined in `dreamforge/core/coordination/agent_bus.py`).
*   Task assignments and status updates related *specifically* to the development work listed here are managed within this file.
*   Agents performing development tasks do not typically require a separate `mailbox.json` for *these* internal development tracking purposes. Communication regarding these tasks happens via direct updates to this file or through assigned issue trackers (if applicable).

---

## Tasks

### Models & Core Logic (`DF-MODEL-*`)

*   **DF-MODEL-001:** Implement `PlannerAgent.refine_plan` Method
    *   **Description:** Implement the logic for the `refine_plan` method in `dreamforge/agents/planner_agent.py`. This includes creating a suitable prompt template (`planner/refine_plan.j2`), rendering it with the existing plan and feedback, calling the `stage_and_execute_prompt` service, and parsing the LLM response to return the refined plan.
    *   **Status:** completed
    *   **Priority:** 2
    *   **Assigned:** Developer
    *   **Dependencies:** DF-MODEL-000 (PlannerAgent plan_from_goal - assumed complete), CoreServicesReady
*   **DF-MODEL-002:** Implement `CalendarAgent.schedule_tasks` Method
    *   **Description:** Implement the core logic for `schedule_tasks` in `dreamforge/agents/calendar_agent.py`. This involves rendering the `calendar/schedule_tasks.j2` template, calling `stage_and_execute_prompt`, and implementing a robust parser (`_parse_llm_schedule_response`) for the LLM's JSON output containing start/end times and scheduling statuses.
    *   **Status:** completed
    *   **Priority:** 2
    *   **Assigned:** Developer
    *   **Dependencies:** DF-MODEL-000 (PlannerAgent plan_from_goal - assumed complete), CoreServicesReady
*   **DF-MODEL-003:** Implement `WorkflowAgent` Core Methods
    *   **Description:** Implement the placeholder methods (`execute_task`, `monitor_progress`, `handle_completion`) in `dreamforge/agents/workflow_agent.py`. Define basic logic structure and interaction points (e.g., calling other agents via AgentBus, updating task status).
    *   **Status:** completed
    *   **Priority:** 3
    *   **Assigned:** Developer
    *   **Dependencies:** CoreServicesReady, AgentBusReady

### Testing (`DF-TEST-*`)

*   **DF-TEST-001:** Unit Tests for `PlannerAgent._parse_llm_plan_response`
    *   **Description:** Create unit tests in `dreamforge/tests/test_planner_agent.py` specifically for the `_parse_llm_plan_response` method. Test various valid and invalid LLM response formats (correct JSON, JSON in ``` block, dict with 'tasks' key, invalid JSON, non-JSON text).
    *   **Status:** completed
    *   **Priority:** 2
    *   **Assigned:** Developer
    *   **Dependencies:** DF-MODEL-000 (PlannerAgent structure)
*   **DF-TEST-002:** Unit Tests for `CalendarAgent._parse_llm_schedule_response` (Requires Parser Implementation)
    *   **Description:** Create unit tests in `dreamforge/tests/test_calendar_agent.py` for the (yet to be implemented) LLM response parser for scheduling. Test various valid and invalid schedule formats returned by the LLM.
    *   **Status:** completed
    *   **Priority:** 3
    *   **Assigned:** Developer
    *   **Dependencies:** DF-MODEL-000 (PlannerAgent structure)
*   **DF-TEST-003:** Integration Test: `PlannerAgent.plan_from_goal` with Mock LLM
    *   **Description:** Create an integration test in `dreamforge/tests/test_planner_agent.py` that calls `plan_from_goal`. Mock the `stage_and_execute_prompt` service to return predefined successful and failing LLM responses. Verify the output or error handling.
    *   **Status:** completed
    *   **Priority:** 2
    *   **Assigned:** Developer
    *   **Dependencies:** DF-MODEL-000, CoreServicesReady (Mockable)
*   **DF-TEST-004:** Unit Tests for `AgentBus` Registration and Message Sending
    *   **Description:** Create unit tests in `dreamforge/tests/test_agent_bus.py` for the `AgentBus` class. Test agent registration, retrieval, and the `send_message` functionality (ensure it calls the target agent's `receive_message` method).
    *   **Status:** completed
    *   **Priority:** 3
    *   **Assigned:** Developer
    *   **Dependencies:** AgentBusReady
*   **DF-TEST-005:** Unit Tests for Data Models (`Task`, `Event`)
    *   **Description:** Create unit tests in `dreamforge/tests/test_data_models.py` for any defined data models (e.g., Task, Event Pydantic models if implemented). Test validation and serialization.
    *   **Status:** pending
    *   **Priority:** 4
    *   **Assigned:** Developer
    *   **Dependencies:** DataModelsDefined
*   **DF-TEST-006:** Unit Tests for `PromptStagingService` (Core Logic)
    *   **Description:** Create unit tests in `dreamforge/tests/test_prompt_staging_service.py` for the core logic within `stage_and_execute_prompt` (excluding the actual LLM call). Test prompt formatting, context assembly, and logging.
    *   **Status:** completed
    *   **Priority:** 3
    *   **Assigned:** Developer
    *   **Dependencies:** DataModelsDefined
*   **DF-TEST-007:** Unit Tests for `TemplateEngine`
    *   **Description:** Create unit tests in `dreamforge/tests/test_template_engine.py` for the `render_template` function. Test rendering with valid context, handling of missing templates, and potential rendering errors.
    *   **Status:** completed
    *   **Priority:** 4
    *   **Assigned:** Developer
    *   **Dependencies:** DataModelsDefined