# Agent Autonomous Pause Logging Protocol

## 1. Purpose

This protocol defines the standardized method for agents to log instances where they pause autonomous operation specifically due to adherence to meta-rules (like the "clear backlog before new features" directive) or when awaiting explicit user confirmation/review before proceeding with the next logical step in autonomous development.

The goal is to gather data on these pauses to understand their frequency and context, enabling future refinement of rules, prompts, or agent logic to improve continuous autonomous operation.

## 2. Trigger Conditions

This log event should be generated **only** when:

*   The agent has successfully completed its previous action or task.
*   The agent is capable of identifying the next logical step (e.g., checking a task list, checking a mailbox, selecting the next task).
*   The **primary reason** for pausing before taking that next step is adherence to a system-level rule (e.g., "clear backlog") or an implicit understanding that review/confirmation is required before proceeding autonomously.

This log should **NOT** be used for pauses caused by:

*   Technical errors (e.g., code exceptions, API failures).
*   Waiting for a dependency (e.g., another agent's response to a direct request).
*   Inability to parse information or understand the next step.
*   Explicit user interrupt/directive.

## 3. Logging Mechanism

Agents MUST use the standard `governance_memory_engine.log_event` function.

## 4. Log Event Details

*   **Event Type:** `AUTONOMOUS_PAUSE_FOR_REVIEW`
*   **Source (`src`):** The `agent_id` of the agent pausing.
*   **Details (`dtls`):** A dictionary containing:
    *   `reason_code` (str): A standardized code indicating the primary reason. Initial codes:
        *   `BACKLOG_CLEARANCE_RULE`: Pause due to the rule requiring backlog clearance before new features.
        *   `AWAITING_CONFIRMATION`: General pause awaiting implicit or explicit confirmation before proceeding autonomously (use if `BACKLOG_CLEARANCE_RULE` isn't specific enough).
    *   `last_completed_task` (str | None): The Task ID of the most recently completed task, if applicable.
    *   `next_intended_action` (str): Brief description of the action the agent was about to take (e.g., "Read agents/task_list.md", "Check social/runtime/SocialAgent/inbox", "Select next priority task from agents/task_list.md").
    *   `rule_reference` (str | None): Optional reference to a specific rule ID from `rulebook.md` or a description of the implicit rule.

## 5. Example Log Entry

```json
{
  "event_type": "AUTONOMOUS_PAUSE_FOR_REVIEW",
  "timestamp": "2025-04-14T10:30:00.123Z",
  "source": "PlannerAgent",
  "details": {
    "reason_code": "BACKLOG_CLEARANCE_RULE",
    "last_completed_task": "DF-PLAN-015",
    "next_intended_action": "Review agents/task_list.md for next task",
    "rule_reference": "Implicit rule: Clear Backlog"
  }
}
```

## 6. Implementation Notes

*   Agents should be designed to recognize these specific pause conditions and generate this log event just before entering the waiting state.
*   The focus is on capturing pauses related to *process* and *rules*, not technical execution failures. 