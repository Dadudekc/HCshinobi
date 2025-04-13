# Agent Coordination Hub

This directory serves as a central point for coordinating tasks, messages, and status between different agents working on this project.

## Hierarchy

- **Agent1 (Supervisor):** Represents the top-level coordinating agent (this AI assistant).
    - `Agent1/inbox`: Messages intended for the supervisor.
    - `Agent1/outbox`: Messages sent by the supervisor.
    - `Agent1/onboarding`: Information and procedures for new agents joining the project.
    - `Agent1/project_board`: High-level view of ongoing projects, tasks, and statuses (e.g., Kanban-style notes).
    - `Agent1/supervisor_tools`: Notes, configurations, or scripts specific to the supervisor's role.

- **Other Agents:** Each subsequent agent working on the project should have its own subdirectory (e.g., `src_agent`, `docs_agent`).
    - `<agent_name>/inbox/`: Tasks and messages assigned TO this agent.
    - `<agent_name>/outbox/`: Status updates and results FROM this agent.

## Portability

This `_agent_coordination` directory is designed to be self-contained within `src/`. You can potentially copy or link this directory into other projects to replicate the coordination structure. 