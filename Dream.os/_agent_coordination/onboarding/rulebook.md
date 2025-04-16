# Agent Coordination Rulebook

## Operational Protocols

### Protocol #CLEANUPTIME
- **ID:** PROTOCOL-CLEANUP-001
- **Description:** "Activation of #CLEANUPTIME signals a system-wide shift. Focus exclusively on refining, organizing, deduplicating, and improving the robustness of existing code, structure, and protocols. Feature expansion is deprioritized. Tasks will address code quality, structural integrity, error handling, consistency, test coverage, documentation, and resolving existing TODOs/placeholders."
- **Keywords:** `cleanup`, `refactor`, `deduplicate`, `organize`, `robustness`, `consistency`, `no new features`
- **Applies To:** `all_agents`, `supervisor`

```yaml
rules:
  - id: PROTOCOL-CLEANUP-001
    description: "Activation of #CLEANUPTIME signals a system-wide shift. Focus exclusively on refining, organizing, deduplicating, and improving the robustness of existing code, structure, and protocols. Feature expansion is deprioritized. Tasks will address code quality, structural integrity, error handling, consistency, test coverage, documentation, and resolving existing TODOs/placeholders."
    keywords:
      - cleanup
      - refactor
      - deduplicate
      - organize
      - robustness
      - consistency
      - no new features
    applies_to: all_agents
```

## Onboarding Procedures for New Agents (Example Rules)

These rules define expected behavior for agents integrating into the system.

### Rule ONB-001 (Reforged): No Placeholders. No Simulations. Only Completion.
- **ID:** ONB-001
- **Description:** All agents must complete their assigned tasks fully and functionally. Placeholders, stubs, TODO comments, simulated returns, or passive logging-only methods are strictly forbidden—even in scaffolding or infrastructure tasks.
- **Exception:** None. If an agent cannot complete its task due to missing dependencies, undefined behavior, or system limitations, it must:
  1. Log the failure with full detail.
  2. Update the task as `BLOCKED` or `FAILED` in `task_list.json`.
  3. Write a message to its assigned `mailbox.json` (Clarification: This seems redundant if Task List is updated; focusing on Task List update as primary feedback).
  4. Notify the ProjectBoard or coordinating agent (e.g., `AgentMonitorAgent`) with context (Clarification: Requires specific implementation; for now, logging + Task List update is primary).
  5. Await reassignment or patch resolution.
- **Motto:** "There is no simulation. There is only execution."
- **Applies To:** `all_agents`, `all_systems`, including `auto_stub_sweep_001`

```yaml
rules:
  - id: ONB-001
    description: "All agents must complete their assigned tasks fully and functionally. Placeholders, stubs, TODO comments, simulated returns, or passive logging-only methods are strictly forbidden—even in scaffolding or infrastructure tasks. Exception: None. If completion is impossible, agent must log failure, update task status (BLOCKED/FAILED), and await resolution."
    keywords:
      - no placeholders
      - no simulation
      - completion mandatory
      - no stubs
      - functional
      - report failure
      - blocked
    applies_to: all_agents
```

### Rule ONB-002: Communication Protocol
- **ID:** ONB-002
- **Description:** "Agents primarily communicate via file drops in designated `mailbox/<AgentName>/inbox/` directories. Check your inbox regularly for tasks and messages."
- **Keywords:** `communication`, `inbox`, `mailbox`, `file drop`, `tasks`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-002
    description: "Agents primarily communicate via file drops in designated `mailbox/<AgentName>/inbox/` directories. Check your inbox regularly for tasks and messages."
    keywords:
      - communication
      - inbox
      - mailbox
      - file drop
      - tasks
    applies_to: all_agents
```

### Rule ONB-003: Task Acceptance & Status Update
- **ID:** ONB-003
- **Description:** "Upon successfully processing an `inbox` message, the agent MUST update the status of the original task in `task_list.json` (using `task_utils.update_task_status`) to `COMPLETED` or `FAILED`, including relevant results or errors. The `original_task_id` is provided in the inbox message."
- **Keywords:** `task update`, `status`, `completed`, `failed`, `task_list.json`, `original_task_id`
- **Applies To:** `all_agents` (that process tasks)

```yaml
rules:
  - id: ONB-003
    description: "Upon successfully processing an `inbox` message, the agent MUST update the status of the original task in `task_list.json` (using `task_utils.update_task_status`) to `COMPLETED` or `FAILED`, including relevant results or errors. The `original_task_id` is provided in the inbox message."
    keywords:
      - task update
      - status
      - completed
      - failed
      - task_list.json
      - original_task_id
    applies_to: all_agents # specifically agents handling dispatched tasks
```

### Rule ONB-004: Reporting Results (Deprecated/Clarified)
- **ID:** ONB-004
- **Description:** "(Deprecated by ONB-003) Results and errors should be reported by updating the status and relevant fields (`result_summary`, `error_message`) of the original task in `task_list.json`. Writing separate files to `outbox` is generally not required unless specified by a particular workflow."
- **Keywords:** `deprecated`, `task_list.json`, `result_summary`, `error_message`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-004
    description: "(Deprecated by ONB-003) Results and errors should be reported by updating the status and relevant fields (`result_summary`, `error_message`) of the original task in `task_list.json`. Writing separate files to `outbox` is generally not required unless specified by a particular workflow."
    keywords:
      - deprecated
      - task_list.json
      - result_summary
      - error_message
    applies_to: all_agents
```

### Rule ONB-005: Dependency Management
- **ID:** ONB-005
- **Description:** "If your task requires external libraries or dependencies not already listed in the root `requirements.txt`, propose additions by adding them to `proposals/dependency_proposals.txt` (relative to project root) or a designated proposal file."
- **Keywords:** `dependencies`, `requirements.txt`, `propose`, `libraries`, `proposals`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-005
    description: "If your task requires external libraries or dependencies not already listed in the root `requirements.txt`, propose additions by adding them to `proposals/dependency_proposals.txt` (relative to project root) or a designated proposal file."
    keywords:
      - dependencies
      - requirements.txt
      - propose
      - libraries
      - proposals
    applies_to: all_agents
```

### Rule ONB-006: Critical Error Handling
- **ID:** ONB-006
- **Description:** "If a critical error prevents task completion (e.g., exception during message processing), ensure the original task status in `task_list.json` is updated to `FAILED` with an appropriate `error_message`. The inbox message itself should be moved to the agent's `error/` directory by the `process_directory_loop`."
- **Keywords:** `error handling`, `failed`, `task_list.json`, `error_message`, `mailbox error dir`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-006
    description: "If a critical error prevents task completion (e.g., exception during message processing), ensure the original task status in `task_list.json` is updated to `FAILED` with an appropriate `error_message`. The inbox message itself should be moved to the agent's `error/` directory by the `process_directory_loop`."
    keywords:
      - error handling
      - failed
      - task_list.json
      - error_message
      - mailbox error dir
    applies_to: all_agents
```

### Rule ONB-007: Handler Dependencies & External Configuration
- **ID:** ONB-007
- **Description:** "Agent command handlers must directly implement logic using available tools (filesystem, controllers, internal state, etc.) or call other verifiable internal agent functions. Placeholders for external actions are forbidden (Ref: ONB-001). If a handler's action requires external configuration not known *a priori* (e.g., a system-specific command, API key, file path), this configuration MUST be provided via the incoming message's `params`. Handlers MUST validate required parameters and FAIL explicitly (return `False`, log error) if they are missing or invalid (e.g., default placeholder values). See `CursorControlAgent._handle_resume_operation` for an example pattern."
- **Keywords:** `handler`, `implementation`, `dependencies`, `parameters`, `configuration`, `no placeholders`, `fail fast`, `validate params`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-007
    description: "Agent command handlers must directly implement logic using available tools or internal functions. External configuration (e.g., specific commands, keys, paths) MUST be provided via message `params`. Handlers MUST validate required params and FAIL explicitly if missing/invalid. Placeholders forbidden (Ref: ONB-001)."
    keywords:
      - handler
      - implementation
      - dependencies
      - parameters
      - configuration
      - no placeholders
      - fail fast
      - validate params
    applies_to: all_agents
```

## General Principles

### Rule 1: Continuous Operation
- **ID:** GEN-001
- **Description:** "Agents should strive for continuous operation towards their goals. Avoid halting unless explicitly allowed by other rules or task definitions require external input."
- **Keywords:** `continuous`, `operation`, `avoid halt`, `strive`, `external input`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-001
    description: "Agents should strive for continuous operation towards their goals. Avoid halting unless explicitly allowed by other rules or task definitions require external input."
    keywords:
      - continuous
      - operation
      - avoid halt
      - strive
      - external input
    applies_to: all_agents
```

### Rule 2: Proactive Problem Solving
- **ID:** GEN-002
- **Description:** "Agents should attempt to resolve issues independently based on these rules before halting. Check rules (`onboarding/rulebook.md`) and task context first. Escalate (e.g., via proposal or specific task type) only if resolution fails or specific conditions are met."
- **Keywords:** `proactive`, `resolve`, `independent`, `check rules`, `context`, `escalate`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-002
    description: "Agents should attempt to resolve issues independently based on these rules before halting. Check rules (`onboarding/rulebook.md`) and task context first. Escalate (e.g., via proposal or specific task type) only if resolution fails or specific conditions are met."
    keywords:
      - proactive
      - resolve
      - independent
      - check rules
      - context
      - escalate
    applies_to: all_agents
```

### Rule 3: Rulebook Updates on Unnecessary Halts
- **ID:** GEN-003
- **Description:** "If an agent halts unnecessarily (i.e., the reason was already covered by rules/tasks), this rulebook (`onboarding/rulebook.md`) **must** be updated to clarify the procedure. The detecting system (Monitor/Analyzer/Supervisor) is responsible for initiating the update (e.g., via a proposal or task)."
- **Keywords:** `halt`, `unnecessary`, `update`, `clarify`, `rulebook`, `monitor`, `supervisor`
- **Applies To:** `monitor_analyzer_agent`, `supervisor`

```yaml
rules:
  - id: GEN-003
    description: "If an agent halts unnecessarily (i.e., the reason was already covered by rules/tasks), this rulebook (`onboarding/rulebook.md`) **must** be updated to clarify the procedure. The detecting system (Monitor/Analyzer/Supervisor) is responsible for initiating the update (e.g., via a proposal or task)."
    keywords:
      - halt
      - unnecessary
      - update
      - clarify
      - rulebook
      - monitor
      - supervisor
    applies_to: ["monitor_analyzer_agent", "supervisor"]
```

### Rule 4: Mailbox Monitoring
- **ID:** GEN-004
- **Description:** "Agents MUST regularly check their designated inbox (`mailboxes/<AgentName>/inbox/`) for new messages/tasks. Frequency depends on agent role but should be sufficient to ensure responsiveness."
- **Keywords:** `mailbox`, `communication`, `check inbox`, `incoming`, `responsiveness`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-004
    description: "Agents MUST regularly check their designated inbox (`mailboxes/<AgentName>/inbox/`) for new messages/tasks. Frequency depends on agent role but should be sufficient to ensure responsiveness."
    keywords:
      - mailbox
      - communication
      - check inbox
      - incoming
      - responsiveness
    applies_to: all_agents
```

### Rule 5: Proactive Goal Decomposition & Action Initiation
- **ID:** GEN-005
- **Description:** "Upon receiving a high-level goal (e.g., from `project_board.json`) or observing a need, the responsible agent (e.g., Supervisor, Planner) MUST proactively decompose it into concrete, actionable tasks and add them to `task_list.json`. Bias towards interpreting intent and initiating the first logical step or assigning it immediately, rather than excessive clarification. Report actions taken (e.g., log, update project board idea status)."
- **Keywords:** `proactive`, `decomposition`, `task generation`, `initiate action`, `bias for action`, `goal-oriented`, `task_list.json`, `project_board.json`
- **Applies To:** `supervisor`, `planning_agents`, `all_agents` (to lesser extent)

```yaml
rules:
  - id: GEN-005
    description: "Upon receiving a high-level goal (e.g., from `project_board.json`) or observing a need, the responsible agent (e.g., Supervisor, Planner) MUST proactively decompose it into concrete, actionable tasks and add them to `task_list.json`. Bias towards interpreting intent and initiating the first logical step or assigning it immediately, rather than excessive clarification. Report actions taken (e.g., log, update project board idea status)."
    keywords:
      - proactive
      - decomposition
      - task generation
      - initiate action
      - bias for action
      - goal-oriented
      - task_list.json
      - project_board.json
    applies_to: ["supervisor", "planning_agents", "all_agents"]
```

### Rule GEN-006: Autonomous Operation Mandate
- **ID:** GEN-006
- **Description:** "Agents MUST NOT halt solely due to lack of *new* user input if existing tasks (`task_list.json`), project board ideas (`onboarding/project_board.json`), or rulebook procedures (`onboarding/rulebook.md`) provide direction. Before halting, agents MUST verify context. Halting with available context/tasks is an operational error. Resume execution using available references. Report *unresolvable* blockers or completion via task status updates (Rule ONB-003)."
- **Keywords:** `autonomous`, `no halt`, `check context`, `task_list.json`, `project_board.json`, `rulebook.md`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-006
    description: "Agents MUST NOT halt solely due to lack of *new* user input if existing tasks (`task_list.json`), project board ideas (`onboarding/project_board.json`), or rulebook procedures (`onboarding/rulebook.md`) provide direction. Before halting, agents MUST verify context. Halting with available context/tasks is an operational error. Resume execution using available references. Report *unresolvable* blockers or completion via task status updates (Rule ONB-003)."
    keywords:
      - autonomous
      - no halt
      - check context
      - task_list.json
      - project_board.json
      - rulebook.md
    applies_to: all_agents
``` 