# Agent Coordination Rulebook

## Onboarding Procedures for New Agents (Example Rules)

These rules define expected behavior for agents integrating into the system.

### Rule ONB-001: No Placeholders
- **ID:** ONB-001
- **Description:** "All code, scripts, or documentation generated MUST be fully functional and implemented based on the task requirements. Placeholder functions, comments like '# TODO: Implement later', or incomplete logic are unacceptable."
- **Keywords:** `no placeholders`, `functional`, `complete`, `implement`, `no TODO comments`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-001
    description: "All code, scripts, or documentation generated MUST be fully functional and implemented based on the task requirements. Placeholder functions, comments like '# TODO: Implement later', or incomplete logic are unacceptable."
    keywords:
      - no placeholders
      - functional
      - complete
      - implement
      - no TODO comments
    applies_to: all_agents
```

### Rule ONB-002: Communication Protocol
- **ID:** ONB-002
- **Description:** "Agents primarily communicate via file drops in designated `inbox/` and `outbox/` directories. Check your inbox regularly for tasks and messages."
- **Keywords:** `communication`, `inbox`, `outbox`, `file drop`, `tasks`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-002
    description: "Agents primarily communicate via file drops in designated `inbox/` and `outbox/` directories. Check your inbox regularly for tasks and messages."
    keywords:
      - communication
      - inbox
      - outbox
      - file drop
      - tasks
    applies_to: all_agents
```

### Rule ONB-003: Task Acceptance
- **ID:** ONB-003
- **Description:** "Upon receiving a task in your inbox, acknowledge receipt by creating a status file in your outbox (e.g., `TASKID_status.json` with `status: accepted`)."
- **Keywords:** `task acceptance`, `acknowledge`, `outbox`, `status`, `accepted`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-003
    description: "Upon receiving a task in your inbox, acknowledge receipt by creating a status file in your outbox (e.g., `TASKID_status.json` with `status: accepted`)."
    keywords:
      - task acceptance
      - acknowledge
      - outbox
      - status
      - accepted
    applies_to: all_agents
```

### Rule ONB-004: Reporting Results
- **ID:** ONB-004
- **Description:** "When completing a task or reporting status/errors, write results to a clearly named file in your `outbox`. Use a consistent format: TASK_ID, STATUS, RESULT_SUMMARY, ERROR_DETAILS (if applicable)."
- **Keywords:** `outbox`, `format`, `TASK_ID`, `STATUS`, `RESULT_SUMMARY`, `ERROR_DETAILS`, `report`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-004
    description: "When completing a task or reporting status/errors, write results to a clearly named file in your `outbox`. Use a consistent format: TASK_ID, STATUS, RESULT_SUMMARY, ERROR_DETAILS (if applicable)."
    keywords:
      - outbox
      - format
      - TASK_ID
      - STATUS
      - RESULT_SUMMARY
      - ERROR_DETAILS
      - report
    applies_to: all_agents
```

### Rule ONB-005: Dependency Management
- **ID:** ONB-005
- **Description:** "If your task requires external libraries or dependencies not already listed in the root `/d:/Dream.os/requirements.txt`, propose additions by adding them to `/d:/Dream.os/temp/dependency_proposals.txt`."
- **Keywords:** `dependencies`, `requirements.txt`, `propose`, `libraries`, `temp`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-005
    description: "If your task requires external libraries or dependencies not already listed in the root `/d:/Dream.os/requirements.txt`, propose additions by adding them to `/d:/Dream.os/temp/dependency_proposals.txt`."
    keywords:
      - dependencies
      - requirements.txt
      - propose
      - libraries
      - temp
    applies_to: all_agents
```

### Rule ONB-006: Critical Error Handling
- **ID:** ONB-006
- **Description:** "If a critical error prevents task completion, do not delete the `inbox` message. Generate a file in `outbox/` with: TASK_ID, STATUS: Error, ERROR_DETAILS, and optionally AGENT_STATE or CONTEXT_INFO."
- **Keywords:** `error reporting`, `outbox`, `preserve inbox`, `TASK_ID`, `STATUS: Error`, `ERROR_DETAILS`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: ONB-006
    description: "If a critical error prevents task completion, do not delete the `inbox` message. Generate a file in `outbox/` with: TASK_ID, STATUS: Error, ERROR_DETAILS, and optionally AGENT_STATE or CONTEXT_INFO."
    keywords:
      - error reporting
      - outbox
      - preserve inbox
      - TASK_ID
      - "STATUS: Error" # Quoted keyword
      - ERROR_DETAILS
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
- **Description:** "Agents should attempt to resolve issues independently based on these rules before halting. Check rules and task context first. Escalate only if resolution fails or specific conditions are met."
- **Keywords:** `proactive`, `resolve`, `independent`, `check rules`, `context`, `escalate`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-002
    description: "Agents should attempt to resolve issues independently based on these rules before halting. Check rules and task context first. Escalate only if resolution fails or specific conditions are met."
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
- **Description:** "If an agent halts unnecessarily (i.e., the reason was already covered by rules/tasks), this rulebook **must** be updated to clarify the procedure. The detecting system (Monitor/Analyzer) is responsible for initiating the update."
- **Keywords:** `halt`, `unnecessary`, `update`, `clarify`, `rulebook`, `monitor`
- **Applies To:** `monitor_analyzer_agent`

```yaml
rules:
  - id: GEN-003
    description: "If an agent halts unnecessarily (i.e., the reason was already covered by rules/tasks), this rulebook **must** be updated to clarify the procedure. The detecting system (Monitor/Analyzer) is responsible for initiating the update."
    keywords:
      - halt
      - unnecessary
      - update
      - clarify
      - rulebook
      - monitor
    applies_to: monitor_analyzer_agent
```

### Rule 4: Mailbox Monitoring
- **ID:** GEN-004
- **Description:** "Agents MUST regularly check their designated communication channel (e.g., `mailbox.json` incoming queue, Supervisor state updates) for new tasks, commands, or status requests. Frequency depends on agent role but should be sufficient to ensure responsiveness."
- **Keywords:** `mailbox`, `communication`, `check inbox`, `incoming`, `supervisor state`, `responsiveness`
- **Applies To:** `all_agents` (especially `supervisor`)

```yaml
rules:
  - id: GEN-004
    description: "Agents MUST regularly check their designated communication channel (e.g., `mailbox.json` incoming queue, Supervisor state updates) for new tasks, commands, or status requests. Frequency depends on agent role but should be sufficient to ensure responsiveness."
    keywords:
      - mailbox
      - communication
      - check inbox
      - incoming
      - supervisor state
      - responsiveness
    applies_to: all_agents # Supervisor role implies higher frequency
```

### Rule 5: Proactive Goal Decomposition & Action Initiation
- **ID:** GEN-005
- **Description:** "Upon receiving a high-level goal or observing a need, the responsible agent (especially the Supervisor) MUST proactively decompose it into concrete, actionable tasks and update the relevant task list(s). Bias towards interpreting intent and initiating the first logical step or assigning it immediately, rather than excessive clarification. Report actions taken."
- **Keywords:** `proactive`, `decomposition`, `task generation`, `initiate action`, `bias for action`, `goal-oriented`
- **Applies To:** `supervisor`, `planning_agents`, `all_agents` (to lesser extent)

```yaml
rules:
  - id: GEN-005
    description: "Upon receiving a high-level goal or observing a need, the responsible agent (especially the Supervisor) MUST proactively decompose it into concrete, actionable tasks and update the relevant task list(s). Bias towards interpreting intent and initiating the first logical step or assigning it immediately, rather than excessive clarification. Report actions taken."
    keywords:
      - proactive
      - decomposition
      - task generation
      - initiate action
      - bias for action
      - goal-oriented
    applies_to: ["supervisor", "planning_agents", "all_agents"]
```

### Rule 6: Supervisor Orchestration Role
- **ID:** SUP-001
- **Description:** "The Supervisor agent's primary role is orchestration, scaffolding, context passing, and task assignment. It should NOT perform detailed implementation work itself but rather delegate to specialized agents. Its tasks include: (1) Interpreting high-level directives. (2) Scaffolding new project structures (directories, basic files). (3) Generating initial task lists for new components/features. (4) Identifying appropriate agents for tasks. (5) Assigning tasks via the designated communication mechanism (AgentBus, Mailbox). (6) Providing necessary context for task execution. (7) Monitoring overall progress and agent status. (8) Updating coordination documents (like this rulebook)."
- **Keywords:** `supervisor`, `orchestration`, `scaffolding`, `delegate`, `task assignment`, `context passing`, `monitor`
- **Applies To:** `supervisor`

```yaml
rules:
  - id: SUP-001
    description: "The Supervisor agent's primary role is orchestration, scaffolding, context passing, and task assignment. It should NOT perform detailed implementation work itself but rather delegate to specialized agents. Its tasks include: (1) Interpreting high-level directives. (2) Scaffolding new project structures (directories, basic files). (3) Generating initial task lists for new components/features. (4) Identifying appropriate agents for tasks. (5) Assigning tasks via the designated communication mechanism (AgentBus, Mailbox). (6) Providing necessary context for task execution. (7) Monitoring overall progress and agent status. (8) Updating coordination documents (like this rulebook)."
    keywords:
      - supervisor
      - orchestration
      - scaffolding
      - delegate
      - task assignment
      - context passing
      - monitor
    applies_to: ["supervisor"]
```

### Rule 7: Pragmatic Error Recovery (GOV-CORE-ERROR-RESILIENCE-01)
- **ID:** GOV-CORE-ERROR-RESILIENCE-01
- **Description:** "Dream.OS must remain resilient and decisive in the face of system errors or incomplete context. When operating autonomously, agents should prioritize momentum, resourcefulness, and fallback logic to keep execution flowing. Failure to load a module, file, or variable must not result in process death unless unrecoverable. Agents may default to hardcoded values, cached data, or estimated guesses. Use available tools/data, even partially. Log all errors/fallbacks for supervisor review. Temporary patches/fixes are acceptable for mission completion."
- **Keywords:** `resilience`, `error handling`, `fallback`, `momentum`, `resourcefulness`, `log errors`, `pragmatic`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GOV-CORE-ERROR-RESILIENCE-01
    description: "Dream.OS must remain resilient and decisive in the face of system errors or incomplete context. When operating autonomously, agents should prioritize momentum, resourcefulness, and fallback logic to keep execution flowing. Failure to load a module, file, or variable must not result in process death unless unrecoverable. Agents may default to hardcoded values, cached data, or estimated guesses. Use available tools/data, even partially. Log all errors/fallbacks for supervisor review. Temporary patches/fixes are acceptable for mission completion."
    keywords:
      - resilience
      - error handling
      - fallback
      - momentum
      - resourcefulness
      - log errors
      - pragmatic
    applies_to: ["all_agents"]
```

## Detected Incidents → Clarification Logs

*(This section will be populated automatically by the Monitor/Analyzer Agent when unnecessary halts lead to rule clarifications.)*

```yaml
# Placeholder for automated rule additions
```

## Specific Procedures

*(Add specific operational rules here, following the same format)*

## [AUTO-APPLIED RULES]

---
*Applied on: 2024-07-16 19:15:37 (Rule ID: REFLECT-20240716191537)*
### [REFLECT] Proposal - TestReflector - 2024-07-16 19:15:37
**Status:** Accepted
- **ID:** REFLECT-20240716191537
- **Origin:** 'reflection-20240716191537-AgentZ'
- **Reasoning:** Halt reason ('Rule two seems vague and unclear') contains keywords suggesting ambiguity regarding Rule GEN-002.
- **Proposed Description:** "Proposed clarification/rule related to halt reason 'Rule two seems vague and unclear'. Triggered by TestReflector's reflection (reflection-20240716191537-AgentZ) on alert alert-3 regarding AgentZ. Reasoning: Halt reason ('Rule two seems vague and unclear') contains keywords suggesting ambiguity regarding Rule GEN-002."
- **Keywords:** `reflection-proposal`, `halt`, `AgentZ`, `Rule_two_seems_vague_and_uncl`
- **Applies To:** `all_agents`

```yaml
# Proposed Rule - Review Needed
rules:
  - id: REFLECT-20240716191537
    description: "Proposed clarification/rule related to halt reason 'Rule two seems vague and unclear'. Triggered by TestReflector's reflection (reflection-20240716191537-AgentZ) on alert alert-3 regarding AgentZ. Reasoning: Halt reason ('Rule two seems vague and unclear') contains keywords suggesting ambiguity regarding Rule GEN-002."
    keywords:
        - reflection-proposal
        - halt
        - AgentZ
        - Rule_two_seems_vague_and_uncl
    applies_to: all_agents
    # Add other relevant fields like 'halt_conditions_allowed', 'self_fix_strategy' after review
```

# --- End of Rulebook --- # 