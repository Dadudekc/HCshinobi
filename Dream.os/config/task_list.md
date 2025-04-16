# Task List: config Module (`/d:/Dream.os/config/`)

Tasks related to system configuration files and parameters.

## I. Configuration Structure

-   [ ] **Review Config Files:** Identify all configuration files used by the system (e.g., `config.yaml`, `.env`, specific agent configs).
-   [ ] **Standardize Format:** Ensure a consistent format (e.g., YAML, JSON, INI) is used where appropriate.
-   [ ] **Parameter Naming:** Verify consistent and clear naming conventions for configuration parameters.
-   [ ] **Environment Variables:** Clarify the use of environment variables versus config files.

## II. Core System Configuration

-   [ ] **AgentBus Config:** Document configuration options for `/d:/Dream.os/_agent_coordination/core/agent_bus.py` (if any).
-   [ ] **TaskDispatcher Config:** Document configuration options for `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` (e.g., `CHECK_INTERVAL_SECONDS`, task list path if configurable).
-   [ ] **Logging Configuration:** Review and document how logging levels and outputs are configured.

## III. Agent Configuration

-   [ ] **Review Agent Params:** Check if agents require specific configuration parameters (API keys, model names, resource limits).
-   [ ] **Consolidate Config:** Consider consolidating agent-specific configurations into a central file or structure.

## IV. Loading & Validation

-   [ ] **Review Loading Logic:** Examine how configuration is loaded (e.g., in `/d:/Dream.os/core/` or specific modules).
-   [ ] **Implement Validation:** Add validation for critical configuration parameters (e.g., required fields, value types/ranges).
-   [ ] **Default Values:** Define sensible default values for non-critical parameters.

## V. Documentation

-   [ ] **Document Config Files:** Create documentation (e.g., in `/d:/Dream.os/docs/task_list.md` or a dedicated config doc) explaining all configuration options, their purpose, and possible values.
-   [ ] **Provide Examples:** Include example configuration snippets.

## VI. Finalization

-   [ ] Commit any changes to configuration files or loading logic.
-   [ ] Ensure configuration is well-structured and documented. 