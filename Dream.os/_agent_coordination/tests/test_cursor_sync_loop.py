import os
import sys
import json
import time
import uuid
import shutil
import subprocess
import threading
import pytest
from datetime import datetime, timezone

# --- Test Configuration ---
# Add project root to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Listener script path
LISTENER_SCRIPT = os.path.join(project_root, "_agent_coordination", "tools", "cursor_result_listener.py")

# Queue Directories (relative to project root)
BASE_QUEUE_DIR = os.path.join(project_root, "_agent_coordination", "test_queue_sync_loop")
PENDING_DIR = os.path.join(BASE_QUEUE_DIR, "cursor_pending")
PROCESSING_DIR = os.path.join(BASE_QUEUE_DIR, "cursor_processing")
ARCHIVE_DIR = os.path.join(BASE_QUEUE_DIR, "cursor_archive")
ERROR_DIR = os.path.join(BASE_QUEUE_DIR, "cursor_error")
FEEDBACK_DIR = os.path.join(BASE_QUEUE_DIR, "feedback_queue", "chatgpt_pending")
CONTEXT_FILE = os.path.join(BASE_QUEUE_DIR, "chatgpt_project_context.json")
LOG_FILE = os.path.join(BASE_QUEUE_DIR, "cursor_listener_test.log")

# --- Test Fixture --- 

@pytest.fixture(scope="function") # Use function scope for clean directories each test
def setup_test_environment():
    """Creates clean queue directories and context file for a test run."""
    print(f"\nSetting up test environment in: {BASE_QUEUE_DIR}")
    # Clean up old directories if they exist
    if os.path.exists(BASE_QUEUE_DIR):
        shutil.rmtree(BASE_QUEUE_DIR)
        
    # Create all necessary directories
    os.makedirs(PENDING_DIR)
    os.makedirs(PROCESSING_DIR)
    os.makedirs(ARCHIVE_DIR)
    os.makedirs(ERROR_DIR)
    os.makedirs(FEEDBACK_DIR)
    
    # Create an empty initial context file
    with open(CONTEXT_FILE, 'w') as f:
        json.dump({"last_updated": None, "cursor_results": {}}, f)
        
    yield # Test runs here
    
    # Teardown: Clean up directories after test
    print(f"\nTearing down test environment: {BASE_QUEUE_DIR}")
    if os.path.exists(BASE_QUEUE_DIR):
         try:
            # Add slight delay for file handles to release if listener process was just killed
            time.sleep(0.5)
            shutil.rmtree(BASE_QUEUE_DIR)
         except OSError as e:
             print(f"Warning: Error during teardown cleanup: {e}")

# --- Helper Functions --- 

def create_test_prompt(prompt_id: str, content: str = "Test prompt content") -> str:
    """Creates a prompt file in the pending directory."""
    payload = {
        "prompt_id": prompt_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_agent": "TestAgent",
        "prompt_text": content,
        "target_context": {"file_path": "/test/file.py"},
        "metadata": {"originating_request_id": f"test_{prompt_id}"}
    }
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{prompt_id}.json"
    filepath = os.path.join(PENDING_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(payload, f)
    print(f"Created test prompt: {filepath}")
    return filename

def start_listener_subprocess(timeout=15):
    """Starts the listener script as a subprocess."""
    env = os.environ.copy()
    # Override paths for the listener process to use the test directories
    env["CURSOR_PENDING_DIR"] = PENDING_DIR
    env["CURSOR_PROCESSING_DIR"] = PROCESSING_DIR
    env["CURSOR_ARCHIVE_DIR"] = ARCHIVE_DIR
    env["CURSOR_ERROR_DIR"] = ERROR_DIR
    env["FEEDBACK_DIR"] = FEEDBACK_DIR
    env["CONTEXT_FILE"] = CONTEXT_FILE
    env["LISTENER_LOG_FILE"] = LOG_FILE
    env["PYTHONUNBUFFERED"] = "1" # Ensure logs are written immediately
    
    print(f"Starting listener subprocess: {LISTENER_SCRIPT}")
    # Use CREATE_NEW_PROCESS_GROUP on Windows to allow killing the process tree later
    process_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    process = subprocess.Popen(
        [sys.executable, LISTENER_SCRIPT], 
        env=env, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=process_flags
    )
    return process

def stop_listener_subprocess(process):
    """Stops the listener subprocess gracefully, then forcefully."""
    if process and process.poll() is None:
        print("Stopping listener subprocess...")
        try:
            if sys.platform == "win32":
                # Send Ctrl+C equivalent on Windows
                # process.send_signal(subprocess.signal.CTRL_C_EVENT) # Doesn't always work reliably
                # Use taskkill on the process group
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], check=True, capture_output=True)
                print(f"Sent taskkill to PID {process.pid}")
            else:
                # Send SIGINT (Ctrl+C) on Unix-like systems
                process.send_signal(subprocess.signal.SIGINT)
            
            # Wait briefly for graceful shutdown
            process.wait(timeout=5)
            print("Listener process terminated gracefully.")
        except subprocess.TimeoutExpired:
            print("Listener did not stop gracefully, killing forcefully.")
            process.kill()
            process.wait()
        except Exception as e:
            print(f"Error stopping listener process: {e}. Attempting kill.")
            try:
                process.kill()
                process.wait()
            except Exception as ke:
                 print(f"Error killing listener process: {ke}")
        finally:
             # Capture remaining output after trying to stop
            stdout, stderr = process.communicate()
            if stdout:
                 print(f"Listener STDOUT:\n{stdout.decode(errors='ignore')}")
            if stderr:
                 print(f"Listener STDERR:\n{stderr.decode(errors='ignore')}")

# --- Test Case --- 

def test_full_sync_loop(setup_test_environment):
    """Simulates the full loop: prompt -> listener -> context -> feedback."""
    listener_proc = None
    try:
        # 1. Start the listener in the background
        # Need to modify listener to accept paths via env vars or args
        # For now, we assume the listener uses the paths configured in *this* test
        listener_proc = start_listener_subprocess()
        time.sleep(2) # Give listener time to start up
        assert listener_proc.poll() is None, "Listener process failed to start or exited prematurely."

        # 2. Create a test prompt file
        test_prompt_id = f"sync_test_{uuid.uuid4()}"
        prompt_filename = create_test_prompt(test_prompt_id)
        prompt_filepath = os.path.join(PENDING_DIR, prompt_filename)

        # 3. Wait for processing (listener poll interval is 5s, add buffer)
        max_wait = 15
        wait_start = time.time()
        feedback_file_found = None
        archived_file_path = os.path.join(ARCHIVE_DIR, prompt_filename)
        
        print(f"Waiting up to {max_wait}s for processing...")
        while time.time() - wait_start < max_wait:
            # Check if prompt file is archived
            if os.path.exists(archived_file_path):
                 print(f"Prompt file archived: {archived_file_path}")
                 # Check if a feedback file exists (name is dynamic)
                 feedback_files = os.listdir(FEEDBACK_DIR)
                 if feedback_files:
                     feedback_file_found = os.path.join(FEEDBACK_DIR, feedback_files[0])
                     print(f"Feedback file found: {feedback_file_found}")
                     break
            time.sleep(1)
            
        assert os.path.exists(archived_file_path), f"Prompt file {prompt_filename} was not archived."
        assert feedback_file_found, "Feedback file was not created."
        
        # 4. Validate Context File Update
        print("Validating context file...")
        context_data = {} 
        with open(CONTEXT_FILE, 'r') as f:
            context_data = json.load(f)
        assert "cursor_results" in context_data
        assert test_prompt_id in context_data["cursor_results"]
        result_entry = context_data["cursor_results"][test_prompt_id]
        assert result_entry["status"] in ["success", "error"] # Placeholder can be either
        assert result_entry["source_prompt_file"] == prompt_filename
        assert "timestamp_processed_utc" in result_entry
        print("Context file validation successful.")

        # 5. Validate Feedback File Content
        print("Validating feedback file...")
        feedback_data = {}
        with open(feedback_file_found, 'r') as f:
            feedback_data = json.load(f)
        assert feedback_data["prompt_id"] == test_prompt_id
        assert feedback_data["target_agent"] == "TestAgent"
        assert feedback_data["cursor_result_status"] == result_entry["status"]
        assert "cursor_result_summary" in feedback_data
        assert feedback_data["cursor_result_summary"] == result_entry # Summary should match context entry
        print("Feedback file validation successful.")

        # 6. Check Listener Log (Basic Check)
        # print("Checking listener log...")
        # assert os.path.exists(LOG_FILE)
        # with open(LOG_FILE, 'r') as f:
        #     log_content = f.read()
        # assert f"Processing prompt_id: {test_prompt_id}" in log_content
        # assert f"Feedback message" in log_content # Check if feedback sending was logged
        # print("Listener log check passed.")
        
    finally:
        # Ensure listener is stopped even if assertions fail
        stop_listener_subprocess(listener_proc) 