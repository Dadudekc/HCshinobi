# Dream.OS ScreenshotTrainer - User Guide

## 1. Overview

Welcome to the Dream.OS ScreenshotTrainer module! This application helps you manage and monitor tasks related to training UI element recognition, particularly within the context of the Dream.OS ecosystem. It provides a tabbed interface for executing task cycles, monitoring progress, and viewing system feedback.

A key feature is its ability to save its state automatically and when you shut it down, allowing you to resume your work later without losing context.

## 2. Interface Overview

The main window consists of:

*   **Tab Bar:** Allows switching between different functional views.
*   **Control Bar:** Contains buttons for manually saving the application state and initiating a graceful shutdown.
*   **Status Bar:** Displays real-time information like the number of active tasks, logged events, and the current system status (Ready, Saving, Loading, Shutting Down, Error).

### Tabs

*   **Task Monitor:**
    *   Displays a list of all known tasks managed by the system.
    *   Allows filtering tasks by status (Pending, Running, Completed, Failed, Cancelled).
    *   Allows searching for tasks by ID or name.
    *   Provides controls (buttons and context menu) to cancel or retry selected tasks.
    *   Shows details for the currently selected task.
*   **Cycle Execution:**
    *   Allows selecting a predefined task template.
    *   Allows setting the number of times (cycles) the template should be executed.
    *   Provides buttons to start and stop the execution cycle.
    *   Displays overall progress for the current cycle.
    *   Shows detailed statistics (start/end time, task counts, success rate) for the last or current cycle.
    *   Lists the individual tasks within the currently running or selected template cycle.
*   **Feedback:**
    *   Displays a chronological log of system events and feedback messages.
    *   Allows filtering events by source component (e.g., MainWindow, TaskMonitorTab) or severity (Info, Warning, Error, Success).
    *   Allows searching for specific event messages or types.
    *   Shows detailed information for the selected event, including any associated data.
    *   Provides actions like copying event details.

## 3. State Persistence

The application automatically saves the state of all open tabs every 5 minutes. It also saves the state when you initiate a graceful shutdown. This includes:

*   Filter settings and search text in Task Monitor and Feedback tabs.
*   Selected items (tasks or events) in the tables.
*   Scroll positions within tables.
*   Splitter positions (in the Feedback tab).
*   The last selected template and cycle count in the Cycle Execution tab (Note: running cycles are *not* automatically resumed on startup).

When you restart the application, it will attempt to load this saved state, restoring the UI to how you left it.

## 4. Shutdown Procedures

*   **Graceful Shutdown:** Use the "Shutdown" button in the control bar or close the main window (using the X button). This initiates a process where:
    1.  Each tab prepares for shutdown (stops timers, logs final stats).
    2.  The state of each tab is saved to `agent_directory/tab_states.json`.
    3.  The application closes.
*   **Status Indicator:** During shutdown, the main status label will indicate "System Status: Shutting Down...".

## 5. Error Handling & Known Limitations

*   **Error Indicator:** If a significant error occurs (e.g., failure to save/load state), the main status label will turn red and display an error message. Check the Feedback tab or the log files for more details.
*   **State Restoration Failures:** If the `tab_states.json` file is corrupted or unreadable, the application will start with a default state. A warning message will be shown. If only specific tabs fail to restore, a warning listing those tabs will appear.
*   **Running Cycles:** Active execution cycles in the "Cycle Execution" tab are stopped during shutdown and are *not* automatically restarted when the application loads its state. You will need to manually restart the cycle if desired.

---
*This document provides a basic overview. Refer to specific module documentation or developer notes for more technical details.* 