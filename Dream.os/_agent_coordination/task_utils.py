import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging for this utility module
logger = logging.getLogger("TaskUtils")
# Basic config if no handlers are set elsewhere
if not logger.hasHandlers():
     # Avoid double logging if root logger is configured
    if not logging.getLogger().hasHandlers():
         logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def read_tasks(task_list_path: Path) -> List[Dict[str, Any]]:
    """Reads the task list from the JSON file."""
    try:
        if not task_list_path.exists():
            logger.warning(f"Task list not found at {task_list_path}, returning empty list.")
            return []
        
        with task_list_path.open("r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            tasks = json.loads(content)
            return tasks
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {task_list_path}: {e}. File content: '{content[:100]}...'")
        # Consider moving corrupted file logic here if desired
        return [] 
    except Exception as e:
        logger.error(f"Error reading task list {task_list_path}: {e}", exc_info=True)
        return []

def write_tasks(task_list_path: Path, tasks: List[Dict[str, Any]]):
    """Writes the updated task list back to the JSON file."""
    # Potential Improvement: Add file locking here for multi-process safety
    try:
        with task_list_path.open("w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing task list {task_list_path}: {e}", exc_info=True)

def update_task_status(task_list_path: Path, task_id: str, new_status: str, 
                       result_summary: Optional[str] = None, error_message: Optional[str] = None) -> bool:
    """Updates the status and optionally result/error of a specific task.

    Reads the task list, finds the task, updates its status and timestamp,
    adds result or error info, and writes the list back.

    Args:
        task_list_path: Path to the task_list.json file.
        task_id: The ID of the task to update.
        new_status: The new status (e.g., "COMPLETED", "FAILED").
        result_summary: Optional summary of the execution result (for COMPLETED).
        error_message: Optional error details (for FAILED).

    Returns:
        True if the task was found and updated, False otherwise.
    """
    updated = False
    save_needed = False
    tasks = read_tasks(task_list_path)
    
    if tasks is None: # Handle read error case
        logger.error(f"Could not update task {task_id} because task list failed to load.")
        return False
         
    for task in tasks:
        if task.get("task_id") == task_id:
            if task.get("status") != new_status:
                task["status"] = new_status
                task["timestamp_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                save_needed = True
                
                # Clear previous results/errors when status changes
                task.pop("error_message", None)
                task.pop("result_summary", None)
                
                # Add new result/error if provided
                if new_status == "FAILED" and error_message:
                    task["error_message"] = error_message
                elif new_status == "COMPLETED" and result_summary:
                     task["result_summary"] = result_summary
                     
                updated = True
                logger.info(f"Updated task '{task_id}' status to '{new_status}'.")
                break
            else:
                # Task found, but status is already the desired one. Still counts as found.
                updated = True 
                # Optionally update timestamp anyway? Or add result/error if missing?
                # For simplicity, we only save if status *changes*.
                logger.debug(f"Task '{task_id}' already has status '{new_status}'. No status change needed.")
                break # Found the task, no need to continue loop
                
    if save_needed:
        write_tasks(task_list_path, tasks)
    elif not updated:
         logger.warning(f"Could not find task {task_id} to update status to {new_status}")

    return updated # Return True if the task was found (regardless of write)

# Example usage block (optional, for testing)
if __name__ == "__main__":
    print("Running TaskUtils example...")
    # Create dummy task list in temp dir
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmpdir:
        dummy_path = Path(tmpdir) / "dummy_task_list.json"
        print(f"Using temp file: {dummy_path}")
        
        # Initial write
        initial_tasks = [
            {"task_id": "task_001", "status": "PENDING", "action": "Do something"},
            {"task_id": "task_002", "status": "PENDING", "action": "Do another thing"}
        ]
        write_tasks(dummy_path, initial_tasks)
        print("Initial tasks written.")
        
        # Read back
        read_back = read_tasks(dummy_path)
        print(f"Read back tasks: {read_back}")
        assert len(read_back) == 2
        
        # Update status (Success)
        update_success = update_task_status(dummy_path, "task_001", "COMPLETED", result_summary="It worked!")
        print(f"Update task_001 success: {update_success}")
        assert update_success
        
        # Update status (Failure)
        update_fail = update_task_status(dummy_path, "task_002", "FAILED", error_message="It broke!")
        print(f"Update task_002 success: {update_fail}")
        assert update_fail
        
        # Update status (Not Found)
        update_missing = update_task_status(dummy_path, "task_003", "COMPLETED")
        print(f"Update task_003 success: {update_missing}")
        assert not update_missing

        # Read final
        final_tasks = read_tasks(dummy_path)
        print(f"Final tasks: {final_tasks}")
        assert final_tasks[0]["status"] == "COMPLETED"
        assert "result_summary" in final_tasks[0]
        assert final_tasks[1]["status"] == "FAILED"
        assert "error_message" in final_tasks[1]
        
    print("TaskUtils example finished.") 