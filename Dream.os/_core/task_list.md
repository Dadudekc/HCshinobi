# Task List: _core Module (`/d:/Dream.os/_core/`)

Tasks related to fundamental abstractions, base classes, and core utilities.

## I. Core Abstractions

-   [ ] **Review BaseAgent Class:** Examine the base class for agents. Ensure it provides necessary common functionality (e.g., lifecycle methods, logging setup, basic AgentBus interaction).
-   [ ] **Review Core Data Structures:** Check definitions for fundamental data structures (e.g., Task representation if defined here, Message formats).
-   [ ] **Identify Shared Utilities:** Review utilities within `_core` for potential consolidation or improvement.

## II. Integration with Coordination

-   [ ] **BaseAgent `AgentBus` Integration:** Ensure the `BaseAgent` correctly handles registration and basic communication with `/d:/Dream.os/_agent_coordination/core/agent_bus.py`.
-   [ ] **Task Handling Utilities:** If task status update logic or task parsing helpers reside here, ensure they are compatible with `/d:/Dream.os/runtime/task_list.json` format and `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`.

## III. Error Handling & Logging

-   [ ] **Standardize Error Types:** Define common exception types for core errors.
-   [ ] **Logging Setup:** Verify the core logging configuration is robust and used consistently by inheriting classes/modules.

## IV. Testing

-   [ ] **Add Unit Tests:** Ensure core abstractions and utilities have adequate unit test coverage.

## V. Documentation

-   [ ] **Document Base Classes:** Provide clear documentation for base classes and core abstractions.
-   [ ] **Document Core Utilities:** Explain the purpose and usage of shared utilities.

## VI. Finalization

-   [ ] Commit changes to core components.
-   [ ] Resolve TODOs within the `_core` module. 