import os
import sys
import random
import time
import logging
from functools import wraps
import json # Added for JSON parsing

# Add project root to sys.path
script_dir = os.path.dirname(__file__) # social/utils
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Example imports
try:
    from social.log_writer import get_social_logger
    # from some_module import some_function
    pass
except ImportError as e:
    print(f"[CommonUtils] Warning: Failed to import dependencies: {e}")
    # Fallback logger if import fails
    def get_social_logger():
        logger = logging.getLogger("DummySocialLogger")
        logger.setLevel(logging.WARNING)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not logger.hasHandlers():
             logger.addHandler(handler)
        return logger


logger = get_social_logger() # Initialize logger

def random_delay(min_delay=0.5, max_delay=1.5):
    # ... existing code ...
    pass

# --- Added Utility Functions ---

MAX_ATTEMPTS = 3 # Default max attempts, can be overridden

def retry_on_failure(max_attempts=MAX_ATTEMPTS, delay=2):
    """
    Decorator to retry a function on failure with a delay between attempts.
    Logs warnings on failure and error after max attempts.
    """
    def decorator_retry(func):
        @wraps(func)
        def wrapper_retry(*args, **kwargs):
            attempts = 0
            last_exception = None
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    last_exception = e
                    logger.warning(f"Attempt {attempts}/{max_attempts} failed in {func.__name__} due to: {type(e).__name__} - {e}")
                    time.sleep(delay * attempts) # Exponential backoff based on attempt number
            error_msg = f"All {max_attempts} attempts failed in {func.__name__}. Last exception: {type(last_exception).__name__} - {last_exception}"
            logger.error(error_msg)
            # Re-raise the last exception to allow calling code to handle it if needed
            raise Exception(error_msg) from last_exception
        return wrapper_retry
    return decorator_retry

def get_random_user_agent():
    """
    Returns a random user agent string from a predefined list.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    return random.choice(user_agents)

# --- End Added Utility Functions --- 

# --- Cursor Result Parsing ---

# Define expected output directory (relative to project root)
# This might be better placed in constants or agent config
CURSOR_OUTPUT_DIR = os.path.join(project_root, "outputs", "social_cursor")

def parse_cursor_result_file(result_filepath: str) -> dict | None:
    """
    Parses a Cursor result JSON file.

    Args:
        result_filepath: The full path to the JSON result file.

    Returns:
        A dictionary containing the parsed result data, or None if parsing fails.
    """
    log_context = {"filepath": result_filepath}
    logger.info(f"Attempting to parse Cursor result file: {os.path.basename(result_filepath)}")

    if not os.path.exists(result_filepath):
        logger.error(f"Cursor result file not found: {result_filepath}")
        log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": "File not found"})
        return None

    try:
        with open(result_filepath, 'r', encoding='utf-8') as f:
            result_data = json.load(f)

        # Basic validation (adapt based on the actual Cursor output schema)
        required_keys = ["result_id", "original_prompt_id", "status", "output"]
        missing_keys = [key for key in required_keys if key not in result_data]
        if missing_keys:
            error_msg = f"Missing required keys in result file: {missing_keys}"
            logger.error(f"{error_msg} in file: {result_filepath}")
            log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": error_msg})
            return None

        # Optional: Deeper validation of sub-structures (e.g., result_data['output'])

        logger.info(f"Successfully parsed Cursor result file: {result_filepath}")
        log_event("CURSOR_RESULT_PARSE_SUCCESS", "CommonUtils", {**log_context, "result_id": result_data.get("result_id")})
        return result_data

    except json.JSONDecodeError as json_e:
        error_msg = f"Invalid JSON in result file: {json_e}"
        logger.error(f"{error_msg} in file: {result_filepath}")
        log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": error_msg})
        return None
    except Exception as e:
        error_msg = f"Failed to read or parse result file: {e}"
        logger.exception(f"{error_msg} - File: {result_filepath}") # Use logger.exception for traceback
        log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": error_msg, "details": str(e)})
        return None

# --- End Cursor Result Parsing ---

# Example usage (can be uncommented for direct testing)
# if __name__ == "__main__":
#     print("Testing Cursor Result Parser...")
#     # Create dummy output dir and file
#     os.makedirs(CURSOR_OUTPUT_DIR, exist_ok=True)
#     dummy_result_filename = f"result_test_{int(time.time())}.json"
#     dummy_result_filepath = os.path.join(CURSOR_OUTPUT_DIR, dummy_result_filename)
#     dummy_result_payload = {
#         "result_id": str(uuid.uuid4()),
#         "original_prompt_id": str(uuid.uuid4()),
#         "timestamp_utc": datetime.now(timezone.utc).isoformat(),
#         "status": "success",
#         "output": {
#             "type": "code_edit_result",
#             "content": "+// Added a new line\n-// Removed a line",
#             "target_file": "test.py"
#         },
#         "metadata": {"execution_time_ms": 123}
#     }
#     try:
#         with open(dummy_result_filepath, 'w') as f:
#             json.dump(dummy_result_payload, f, indent=2)
#         print(f"Created dummy result file: {dummy_result_filepath}")
#         parsed_data = parse_cursor_result_file(dummy_result_filepath)
#         if parsed_data:
#             print("Parsing successful:")
#             print(json.dumps(parsed_data, indent=2))
#         else:
#             print("Parsing failed.")
#     except Exception as e:
#         print(f"Error during test: {e}")
#     finally:
#         # Clean up dummy file
#         if os.path.exists(dummy_result_filepath):
#             try: os.remove(dummy_result_filepath)
#             except: pass
#     print("Test finished.") 