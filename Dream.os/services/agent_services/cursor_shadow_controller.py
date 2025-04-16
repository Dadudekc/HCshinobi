# services/cursor_shadow_controller.py

import time
import uuid
import json # Added import
import logging # Added import
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class CursorShadowController:
    """
    Shadow controller that allows background execution of prompts in Cursor
    without requiring visible GUI interaction, using a file-based inbox/outbox.
    """

    def __init__(self, prompt_dir="cursor_inbox", output_dir="cursor_outbox"):
        self.prompt_dir = Path(prompt_dir)
        self.output_dir = Path(output_dir)
        try:
            self.prompt_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"CursorShadowController initialized. Inbox: {self.prompt_dir.resolve()}, Outbox: {self.output_dir.resolve()}")
        except Exception as e:
            logger.error(f"Failed to create controller directories: {e}", exc_info=True)
            raise

    def send_prompt_to_cursor(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        Writes the prompt to a file in the inbox for Cursor to pick up.

        Returns:
            prompt_id (str): Unique ID for the prompt (used for result tracking).
        """
        prompt_id = str(uuid.uuid4())[:8]
        file_path = self.prompt_dir / f"{prompt_id}.prompt.txt"
        logger.debug(f"Writing prompt {prompt_id} to {file_path}")

        payload = f"# Prompt ID: {prompt_id}\n"
        if context:
            # Serialize context safely
            try:
                context_str = json.dumps(context)
                payload += f"# Context: {context_str}\n\n"
            except Exception as e:
                logger.warning(f"Could not serialize context for prompt {prompt_id}: {e}")
                payload += f"# Context: [Serialization Error]\n\n"

        payload += prompt

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(payload)
            logger.info(f"Prompt {prompt_id} sent successfully to inbox.")
            return prompt_id
        except Exception as e:
            logger.error(f"Failed to write prompt file {file_path}: {e}", exc_info=True)
            raise # Re-raise exception to signal failure

    def monitor_output(self, prompt_id: str, timeout=60, poll_interval=1) -> Dict:
        """
        Watches the output directory for the result file from Cursor.

        Returns:
            Dict with `success`, `response`, or `error`.
        """
        result_file = self.output_dir / f"{prompt_id}.result.json"
        start_time = time.time()
        logger.debug(f"Monitoring for result file: {result_file} (Timeout: {timeout}s)")

        while time.time() - start_time < timeout:
            if result_file.exists():
                logger.debug(f"Result file {result_file} found.")
                try:
                    # Add slight delay to ensure file write is complete
                    time.sleep(0.1)
                    with open(result_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if not content.strip():
                             logger.warning(f"Result file {result_file} is empty. Retrying read.")
                             time.sleep(poll_interval) # Wait before retrying empty file
                             continue # Retry reading the file
                        result = json.loads(content)
                    # Clean up the result file after reading
                    try:
                        result_file.unlink()
                        logger.debug(f"Removed result file {result_file}")
                    except Exception as del_e:
                        logger.warning(f"Failed to remove result file {result_file}: {del_e}")
                    logger.info(f"Successfully processed result for prompt {prompt_id}.")
                    # Ensure result has a 'success' key for consistency downstream
                    if 'success' not in result:
                         logger.warning(f"Result for {prompt_id} missing 'success' key. Assuming success based on presence of file.")
                         result['success'] = True # Or infer based on other keys?
                    return result # Expected format: {"success": bool, "response": str|None, "error": str|None}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON result file {result_file}: {e}. Content: '{content[:100]}...'")
                    return {"success": False, "error": f"Failed to parse result JSON: {e}"}
                except Exception as e:
                    logger.error(f"Failed to read or process result file {result_file}: {e}", exc_info=True)
                    return {"success": False, "error": f"Failed to read/process result: {e}"}
            time.sleep(poll_interval)

        logger.warning(f"Timeout waiting for Cursor response for prompt {prompt_id}.")
        return {"success": False, "error": f"Timeout waiting for Cursor response for prompt {prompt_id}"}

    def run_prompt_cycle(self, prompt: str, context: Optional[Dict] = None, timeout=60) -> Dict:
        """
        Sends a prompt and waits for output, encapsulating the full cycle.
        """
        prompt_id = "error"
        try:
            prompt_id = self.send_prompt_to_cursor(prompt, context)
            result = self.monitor_output(prompt_id, timeout=timeout)
        except Exception as e:
            # Catch errors during sending itself
            logger.error(f"Error during prompt cycle (sending phase) for prompt ID '{prompt_id}': {e}", exc_info=True)
            result = {"success": False, "error": f"Failed during prompt sending: {e}"}

        # Ensure prompt_id is added even if monitoring failed
        if isinstance(result, dict):
             result["prompt_id"] = prompt_id # Add prompt_id for tracking
        else: # Should not happen, but safeguard
             result = {"success": False, "error": "Invalid result format from monitor", "prompt_id": prompt_id}

        return result

if __name__ == "__main__":
    # 🔍 Example usage — Standalone test for the controller
    import sys
    import shutil
    print(f">>> Running module: {__file__}")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Test Setup ---
    test_inbox = Path("temp_cursor_inbox")
    test_outbox = Path("temp_cursor_outbox")
    print(f"Using temporary directories: Inbox='{test_inbox.resolve()}', Outbox='{test_outbox.resolve()}'")

    controller = CursorShadowController(prompt_dir=str(test_inbox), output_dir=str(test_outbox))

    # --- Test Scenario --- #
    test_prompt = "Analyze the sentiment of this text: 'DreamOS is amazing!'"
    test_context = {"user_id": "test_user", "session_id": "demo_session"}

    print(f"\n>>> Sending test prompt: \n{test_prompt}")
    prompt_id_sent = ""
    try:
        # Simulate sending
        prompt_id_sent = controller.send_prompt_to_cursor(test_prompt, test_context)
        print(f"Prompt sent with ID: {prompt_id_sent}")
        prompt_file = test_inbox / f"{prompt_id_sent}.prompt.txt"
        print(f"Check inbox file: {prompt_file}")
        assert prompt_file.exists(), "Prompt file was not created!"
        print("✓ Prompt file created.")

        # Simulate Cursor processing and writing response
        print("\n>>> Simulating Cursor processing... (Will write result file shortly)")
        async def simulate_cursor_response(p_id, out_dir):
            await asyncio.sleep(3)
            result_data = {
                "success": True,
                "response": "Positive sentiment detected.",
                "raw": "[SentimentAnalysis] Score: 0.95, Label: POSITIVE",
                "prompt_id": p_id # Cursor should echo the ID
            }
            result_file_path = out_dir / f"{p_id}.result.json"
            try:
                with open(result_file_path, "w", encoding="utf-8") as f:
                    json.dump(result_data, f)
                print(f"[SIM] Cursor wrote result to: {result_file_path}")
            except Exception as write_e:
                print(f"[SIM] Error writing result file: {write_e}")

        # Run simulation concurrently with monitoring (for demo purposes)
        async def monitor_and_simulate():
             await asyncio.gather(
                 asyncio.to_thread(controller.monitor_output, prompt_id_sent, timeout=10),
                 simulate_cursor_response(prompt_id_sent, test_outbox)
             )

        # This part needs asyncio.run or equivalent if not in an async context already
        # Let's simplify for basic __main__ test: write file THEN monitor
        # (The gather approach is better for true async testing)
        print("\n>>> Simulating Cursor writing response file...")
        simulated_result_data = {
                "success": True,
                "response": "Positive sentiment detected.",
                "raw": "[SentimentAnalysis] Score: 0.95, Label: POSITIVE",
                "prompt_id": prompt_id_sent
            }
        simulated_result_file = test_outbox / f"{prompt_id_sent}.result.json"
        with open(simulated_result_file, "w", encoding="utf-8") as f_sim:
             json.dump(simulated_result_data, f_sim)
        print(f"✓ Simulated result file written: {simulated_result_file}")

        # Monitor for the result
        print(f"\n>>> Monitoring for result (ID: {prompt_id_sent})...")
        final_result = controller.monitor_output(prompt_id_sent, timeout=10)

        print(f"\n>>> Final Result Received:")
        print(json.dumps(final_result, indent=2))

        assert final_result.get("success") is True, "Test failed: Success not True."
        assert not simulated_result_file.exists(), "Test failed: Result file was not cleaned up."
        print("\n✓ Basic send/monitor cycle successful.")

    except Exception as e:
        print(f"\n>>> Test Error: {e}")
        sys.exit(1)
    finally:
        # Clean up temporary directories
        print("\n>>> Cleaning up test directories...")
        shutil.rmtree(test_inbox, ignore_errors=True)
        shutil.rmtree(test_outbox, ignore_errors=True)
        print("✓ Cleanup complete.")

    print(f"\n>>> Module {__file__} execution finished.") 