#!/usr/bin/env python
# Simplified script to test only the problematic import
import sys
import os
import logging

# --- Path Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Use INFO level
logging.info(f"DEBUG_PATH: SCRIPT_DIR = {SCRIPT_DIR}")
logging.info(f"DEBUG_PATH: Calculated WORKSPACE_ROOT = {WORKSPACE_ROOT}")
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)
    logging.info(f"DEBUG_PATH: Inserted WORKSPACE_ROOT into sys.path")
# Also add core dir for direct import test
CORE_DIR = os.path.join(WORKSPACE_ROOT, 'agents', 'core')
if CORE_DIR not in sys.path:
    sys.path.insert(1, CORE_DIR) # Add core dir after workspace root
logging.info(f"DEBUG_PATH: Added CORE_DIR to sys.path: {CORE_DIR}")
logging.info(f"DEBUG_PATH: Updated sys.path = {sys.path}")

# --- THE ONLY ACTION --- 
try:
    # logging.info("Attempting import: from agents.core.agent_command_handler import CommandHandler")
    # from agents.core.agent_command_handler import CommandHandler
    # logging.info("SUCCESS: Imported CommandHandler!")
    logging.info("Attempting direct import: import agent_command_handler")
    import agent_command_handler
    logging.info("SUCCESS: Imported agent_command_handler directly!")
except Exception as e:
    logging.exception("Direct import failed!") # Log full traceback
    print(f"ERROR: Direct import failed: {e}") # Print error to stdout as well
    sys.exit(1)

logging.info("Minimal direct import test script finished successfully.")
sys.exit(0)

# --- Original Code Below (Effectively Commented Out) ---
"""
import argparse
import json
# ... rest of original imports and code ...
""" 