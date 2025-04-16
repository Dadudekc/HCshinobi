# Task List: social Module (`/d:/Dream.os/social/`)

Tasks related to social agents, interactions, and integration with the core system.

## I. AgentBus Integration

-   [ ] **Review Agent Registration:** Ensure all social agents are correctly registered with the `AgentBus` (likely defined in `/d:/Dream.os/_agent_coordination/core/agent_bus.py`).
-   [ ] **Define Social EventTypes:** Define specific `EventType` values for social interactions (e.g., `CHAT_MESSAGE`, `RELATIONSHIP_UPDATE`) within the `AgentBus` event definitions.
-   [ ] **Implement Event Handling:** Ensure social agents subscribe to and correctly handle relevant events from the `AgentBus`.
-   [ ] **Task Dispatch Compatibility:** Verify if social agents need to receive tasks via the `TaskDispatcherAgent`. If so, ensure they handle `EventType.TASK` events and parse the payload correctly.
    -   [ ] Add relevant `task_type` mappings to `_infer_target_agent` in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` if needed.

## II. Social Protocols & Logic

-   [ ] **Review Communication Protocols:** Ensure protocols for inter-agent social communication are robust and well-defined.
-   [ ] **State Management:** Verify the handling of social states (e.g., relationships, ongoing conversations) is correct and persists appropriately.
-   [ ] **Integration with Core:** Confirm social interactions can correctly trigger core system tasks if needed (e.g., a chat command triggering a `CursorControlAgent` task).

## III. Testing & Validation

-   [ ] **Test Social Event Flows:** Simulate social events on the `AgentBus` and verify correct agent responses.
-   [ ] **Test Social Task Handling:** If applicable, inject social-related tasks via `/d:/Dream.os/runtime/task_list.json` and monitor using `/d:/Dream.os/tools/task_list_visualizer.py`.
-   [ ] **Integration Tests:** Add tests covering interactions between social agents and core agents via the `AgentBus`.

## IV. Documentation & Logging

-   [ ] **Document Social Agents:** Ensure clear documentation for each social agent's purpose, capabilities, and handled events/tasks.
-   [ ] **Document Social Protocols:** Explain the communication protocols used.
-   [ ] **Improve Logging:** Enhance logging within social agents for better debugging of interactions.

## V. Finalization

-   [ ] Commit all code changes related to this module.
-   [ ] Resolve any outstanding issues or TODOs specific to social features. 