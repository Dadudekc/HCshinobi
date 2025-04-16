#!/usr/bin/env python3
"""Dream.OS Main Entry Point."""

import sys
import os
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from core.gui.main_window import DreamOSMainWindow
# Assuming logger setup will now be configured via LogManager
# Potentially remove direct setup_logging import if LogManager handles it
# from core.utils.logger import setup_logging, get_logger 
# Assuming LogManager is accessible or configured elsewhere
from _agent_coordination.core.utils.logging import get_logger 

def setup_environment():
    """Setup the application environment."""
    try:
        # Ensure required directories exist
        # Use relative paths from project root
        root_dir = Path(__file__).parent
        dirs = [
            root_dir / "agent_directory",
            root_dir / "logs",
            root_dir / "config",
            root_dir / "memory",
            root_dir / "runtime" # Added runtime dir
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Configure logging via LogManager (assuming it's available)
        # This might need adjustment depending on how LogManager is initialized
        from _agent_coordination.core.utils.logging import LogManager
        log_dir = root_dir / "logs"
        LogManager().configure(log_dir=log_dir)
        
        logger = get_logger(__name__)
        logger.info("Environment setup complete using LogManager")
        return True

    except Exception as e:
        # Use basic print before logger is fully configured
        print(f"Error setting up environment: {e}", file=sys.stderr)
        # Optionally try basic logging config as fallback
        # logging.basicConfig(level=logging.WARNING) 
        # logging.warning(f"Error setting up environment: {e}")
        return False

def main(test_mode=False):
    """Main application entry point."""
    logger = None # Initialize logger variable
    try:
        # Setup environment FIRST
        if not setup_environment():
             print("❌ Critical error during initial environment setup. Exiting.", file=sys.stderr)
             sys.exit(1)

        # Now get the configured logger
        logger = get_logger(__name__, component="MainApp") 

        # Enable debug logging if DEBUG environment variable is set
        if os.getenv("DEBUG"):
            import logging
            LogManager().set_level(logging.DEBUG) # Use LogManager method
            logger.info("🔍 Debug mode enabled - verbose logging active")

        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Dream.OS")
        app.setApplicationVersion("1.0.0") # Consider moving version to config

        # Set application style (optional)
        app.setStyle("Fusion")

        # Create main window
        logger.info("Initializing DreamOSMainWindow...")
        window = DreamOSMainWindow() # Assumes MainWindow gets its own logger
        logger.info("✓ DreamOSMainWindow initialized.")
        
        if test_mode:
            logger.info("🧪 Running in Test & Simulation Mode (--test)")
            # 🔍 Example usage — Standalone run for debugging, onboarding, agentic simulation
            print("🧪 Running Autonomous Test Sequence & Agentic Coordination Kickoff...")
            
            # Test 1: Agent Interface - Tab System Check
            print("📋 [Agent Test] Verifying Core Interface (Tab System):")
            tab_names = window.get_tab_names()
            if tab_names:
                 for tab_name in tab_names:
                    print(f"  ✓ Found interface component: {tab_name}")
            else:
                print("  ⚠️ No tabs found in the main window.")
            
            # Test 2: Agent Action - Task Management & Logging
            print("📝 [Agent Test] Simulating Task Creation & Logging:")
            test_task = {
                "id": f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "name": "Autonomous Test Task",
                "description": "Task created during automated agentic simulation.",
                "priority": "High",
                "status": "Pending"
            }
            try:
                window.task_manager.add_task(test_task)
                print(f"  ✓ Task '{test_task['name']}' added to local Task Manager.")
                # Simulate logging to a central task board
                print(f"  📡 Syncing Task {test_task['id']} with Central Agent Board...") 
                # Assume window.log_task_to_board(test_task) or similar exists
            except Exception as e:
                print(f"  ❌ Failed to add or log task: {e}")

            # Test 3: Agent Perception - Event Logging & Mailbox Update
            print("📊 [Agent Test] Simulating Event Perception & Mailbox Update:")
            event_name = "agent_simulation_event"
            event_data = {"timestamp": datetime.now().isoformat(), "source": "main.py test"}
            try:
                window.log_event(event_name, event_data)
                print(f"  ✓ Event '{event_name}' logged locally.")
                # Simulate sending a message/notification to an agent mailbox
                print(f"  📬 Sending notification to Agent Mailbox: Event '{event_name}' occurred.")
                # Assume window.notify_mailbox(event_name, event_data) or similar exists
            except Exception as e:
                print(f"  ❌ Failed to log event or notify mailbox: {e}")

            # Test 4: Agent State - Persistence & Board Sync
            print("💾 [Agent Test] Simulating State Persistence & Board Sync:")
            try:
                window.save_state()
                print("  ✓ Local agent state saved successfully.")
                # Simulate syncing state changes with the central board
                print("  🔄 Syncing local state changes with Central Agent Board...")
                # Assume window.sync_state_with_board() or similar exists
            except Exception as e:
                print(f"  ❌ Failed to save state or sync with board: {e}")

            print("✨ Autonomous Test Sequence Completed!")
            
            # Cleanup
            print("🧹 Cleaning up resources...")
            window.close()
            print("✓ Resources released.")
            return
            
        # Normal Mode: Show the GUI
        logger.info("🚀 Launching Dream.OS GUI...")
        window.show()
        
        # Start event loop
        exit_code = app.exec_()
        logger.info(f"Application exited with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        critical_error_msg = f"❌ CRITICAL ERROR in main execution: {e}"
        print(critical_error_msg, file=sys.stderr)
        if logger:
             # Log with traceback if logger is available
             logger.critical(critical_error_msg, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    """
    Dream.OS: Autonomous Usage Block & Agentic Coordination Kickoff
    -------------------------------------------------------------
    
    This block serves multiple purposes:
    1. Standalone Execution: Runs the module directly for testing/debugging.
    2. Capability Demonstration: Shows the core features in action.
    3. Onboarding Aid: Helps developers and AI understand the module's role.
    4. Agentic Simulation: Kicks off a test sequence demonstrating autonomous coordination.
    
    Running Modes:
    -------------
    1. Normal Mode (GUI):
       ```bash
       python main.py
       ```
       Launches the full Dream.OS graphical user interface.
    
    2. Test & Simulation Mode (Agentic Kickoff):
       ```bash
       python main.py --test
       ```
       Executes an automated sequence simulating agent actions and coordination:
       - Initializes the core `DreamOSMainWindow` (acting as the agent's interface).
       - Verifies interface components (Tab System).
       - Simulates agent actions like creating tasks (`task_manager.add_task`).
       - **Logs tasks to a simulated central Agent Board.** 
       - Simulates agent perception by logging events (`log_event`).
       - **Sends notifications to a simulated Agent Mailbox.**
       - Handles agent state persistence (`save_state`).
       - **Syncs state changes with the simulated Agent Board.**
       - Performs resource cleanup (`window.close`).
    
    3. Debug Mode (Verbose Logging):
       ```bash
       # Windows: set DEBUG=1 && python main.py [--test]
       # Unix/Mac:  DEBUG=1 python main.py [--test]
       ```
       Enables detailed logging for deeper analysis in either mode.
    
    Agentic Coordination Points (Simulated in --test mode):
    -------------------------------------------------------
    - **Task Logging:** `print("📡 Syncing Task ... with Central Agent Board...")`
    - **Mailbox Update:** `print("📬 Sending notification to Agent Mailbox...")`
    - **Board Sync:** `print("🔄 Syncing local state changes with Central Agent Board...")`
    
    This simulation helps validate the module's readiness for integration into
    autonomous workflows within Dream.OS or similar agentic frameworks.
    """
    
    # Parse command line arguments
    test_mode = "--test" in sys.argv
    
    # Setup logging FIRST, so even argument parsing issues are logged if possible
    try:
        if not setup_environment():
            print("❌ Critical error during initial environment setup. Exiting.")
            sys.exit(1)
        logger = get_logger(__name__)
    except Exception as e:
        print(f"❌ Failed to setup environment/logging early: {e}")
        # Continue without logger if setup failed, but flag the issue
        logger = None 

    # Enable debug logging if DEBUG environment variable is set
    if os.getenv("DEBUG"):
        import logging
        # Ensure logging was set up
        if logger:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("🔍 Debug mode enabled - verbose logging active")
        else:
            print("⚠️ Logging setup failed, cannot enable DEBUG level via logger.")
        # Also print to console for visibility if logger failed
        print("🔍 Debug mode requested via environment variable.")
    
    # Display startup banner
    print("=" * 60)
    print("🚀 Initializing Dream.OS Entry Point")
    print(f"📂 Working Directory: {os.getcwd()}")
    print(f"🔧 Python Version: {sys.version.split()[0]}")
    try:
        # Attempt to get Qt version only if not in test mode or if absolutely needed
        # This avoids unnecessary QApplication instantiation just for the version string
        qt_version = "N/A (GUI not loaded)"
        if not test_mode or os.getenv("DEBUG"): # Show Qt version in debug or normal mode
             # Need an app instance to get Qt version
             temp_app_instance_for_version = QApplication.instance() or QApplication(sys.argv)
             qt_version = temp_app_instance_for_version.qt_version()
             # Clean up temporary instance if we created it and are in test mode
             if test_mode and not QApplication.instance():
                 del temp_app_instance_for_version 

        print(f"📦 Qt Version: {qt_version}")
    except Exception as e:
         print(f"📦 Qt Version: Error retrieving - {e}")
    print(f"🔬 Mode: {'Agentic Simulation (--test)' if test_mode else 'Normal GUI'}")
    print("=" * 60)
    
    # Launch application in the chosen mode
    main(test_mode=test_mode) 