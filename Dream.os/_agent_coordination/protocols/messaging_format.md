# Dream.OS Messaging & Format Protocols

This document outlines the standard formats and locations for communication between agents, core services, and external interfaces (like Cursor/ChatGPT bridges) within Dream.OS.

**Version:** 1.0
**Last Updated:** $(date --iso-8601=seconds) # Placeholder - Should be updated manually or via script

## Core Principles:

- **Structured Data:** Use JSON for machine-to-machine communication (agent commands, task lists, structured results).
- **Human Readability:** Use Markdown for reports, logs, and summaries intended for human review.
- **Dynamic Generation:** Use Jinja2 templates (`.j2`) for constructing complex prompts or messages.
- **Clear Channels:** Utilize designated **absolute file paths** for specific communication flows, rooted at the project base (e.g., `/d:/Dream.os/`).

## Standard File Formats & Usage:

| Direction/Purpose                  | Format   | Extension | Canonical Path Pattern                               | Reason                                                  |
|-----------------------------------|----------|-----------|----------------------------------------------------|---------------------------------------------------------|
| Agent ↔ Agent (Task/Status)     | `JSON`   | `.json`   | `/d:/Dream.os/runtime/AgentX/inbox/task_*.json`    | Machine-readable task/command structure                 |
| Agent → Agent (Message/Result)    | `JSON`   | `.json`   | `/d:/Dream.os/runtime/AgentX/outbox/msg_*.json`    | Structured output/status updates                        |
| Prompt Template                   | `Jinja`  | `.j2`     | `/d:/Dream.os/templates/*.j2`                      | Allows structured + dynamic prompt templating           |
| Rendered Prompt → Cursor          | `Text`   | `.txt`    | `/d:/Dream.os/temp/cursor_input.txt`               | Final rendered text ready for processing by Cursor/LLM |
| Cursor → System (Result/Command) | `JSON`   | `.json`   | `/d:/Dream.os/temp/cursor_output.json`             | Enables structured feedback/commands from Cursor bridge |
| System State (General)            | `JSON`   | `.json`   | `/d:/Dream.os/temp/*.json` or `/d:/Dream.os/runtime/AgentX/*.json` | General state persistence                         |
| Human-Facing Report/Log           | `Markdown`| `.md`     | `/d:/Dream.os/analysis/*.md` or `/d:/Dream.os/logs/*.md` | Human-readable summaries, proposals, decisions          |
| Governance Log                    | `JSONL`  | `.jsonl`  | `/d:/Dream.os/governance_memory.jsonl`             | Append-only log of significant system events          |
| Agent Reflection Log              | `Markdown`| `.md`     | `/d:/Dream.os/_agent_coordination/*/reflection/*.md` | Human-readable agent self-reflection logs             |
| Supervisor State                  | `JSON`   | `.json`   | `/d:/Dream.os/runtime/supervisor_state.json`       | Persistent state for the Supervisor                   |

## File-Based Message Bus (`/d:/Dream.os/temp/`):

The `/d:/Dream.os/temp/` directory serves as a primary low-level message bus, particularly for interfacing with external processes or the Cursor bridge.

- **`/d:/Dream.os/temp/cursor_input.txt`**: 
    - **Format:** Plain Text (often Jinja-rendered output).
    - **Written By:** `PromptStagingService` (or other components preparing prompts).
    - **Read By:** External process monitoring for Cursor/LLM input.
    - **Purpose:** Stage the exact text prompt for the next LLM interaction.
- **`/d:/Dream.os/temp/cursor_output.json`**: 
    - **Format:** JSON.
    - **Written By:** External process representing Cursor/LLM output.
    - **Read By:** `PromptStagingService` (`fetch_cursor_response`), dispatchers, routers.
    - **Purpose:** Receive structured commands, results, or data back from the LLM interaction.

## Agent Runtime Communication (`/d:/Dream.os/runtime/AgentX/`):

Each agent instance typically operates within its `/d:/Dream.os/runtime/AgentX/` directory.

- **`/d:/Dream.os/runtime/AgentX/inbox/`**: Contains incoming messages or task definitions, usually as `.json` files.
- **`/d:/Dream.os/runtime/AgentX/outbox/`**: Contains outgoing messages, results, or status updates, usually as `.json` files, ready for pickup by the supervisor or other agents.

## Notes:

- **Atomicity:** Assume file writes are generally atomic for simplicity, but be mindful of potential race conditions in high-concurrency scenarios (consider file locking or queueing systems if needed later).
- **Cleanup:** Processes reading from message files (e.g., `/d:/Dream.os/temp/cursor_output.json`, `/d:/Dream.os/runtime/AgentX/outbox/msg_*.json`) should ideally delete or archive the file after successful processing to prevent reprocessing.
- **Error Handling:** Implement robust error handling (e.g., `try...except` blocks) when reading/writing/parsing these files. 