import sys # Import sys for path manipulation
import os # Import os for path manipulation

# Add project root for imports
script_dir = os.path.dirname(__file__) # execution/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Go up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .prompt_executor_chatgpt import ChatGPTExecutor
from .prompt_executor_cursor import CursorExecutor

# --- Service Imports ---
try:
    from governance_memory_engine import log_event # Import log_event
    _core_imports_ok = True
except ImportError as e:
    print(f"[PromptExecutor Error ❌] Failed to import governance_memory_engine: {e}")
    _core_imports_ok = False
    # Define dummy log_event
    def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")

# Configuration
_SOURCE = "PromptExecutor" # Define logging source

class PromptExecutor:
    """Unified interface to execute prompts using different backends (Cursor, ChatGPT)."""

    def __init__(self, preferred_backend='cursor', chatgpt_executor=None, cursor_executor=None):
        """Initializes the PromptExecutor.

        Args:
            preferred_backend (str): 'cursor' or 'chatgpt'. Default backend to try first.
            chatgpt_executor (ChatGPTExecutor, optional): Pre-configured instance.
            cursor_executor (CursorExecutor, optional): Pre-configured instance.
        """
        # Initialize executors only if core imports are okay, otherwise use None/defaults
        # Note: The executor classes themselves might have fallbacks or print warnings.
        self.chatgpt_executor = chatgpt_executor if chatgpt_executor else ChatGPTExecutor()
        self.cursor_executor = cursor_executor if cursor_executor else CursorExecutor()
        
        if preferred_backend not in ['cursor', 'chatgpt']:
            log_event("EXECUTOR_CRITICAL", _SOURCE, {"error": "Invalid preferred_backend", "value": preferred_backend})
            raise ValueError("preferred_backend must be 'cursor' or 'chatgpt'")
        self.preferred_backend = preferred_backend
        # print(f"PromptExecutor initialized. Preferred backend: {self.preferred_backend}")
        log_event("EXECUTOR_INIT", _SOURCE, {"preferred_backend": self.preferred_backend})

    def execute(self, prompt, backend='auto', **kwargs):
        """Executes a prompt using the specified or preferred backend.

        Args:
            prompt (str or list): The prompt content. String for Cursor, list of strings for ChatGPT.
            backend (str): 'cursor', 'chatgpt', or 'auto'. 
                         'auto' uses the preferred_backend.
            **kwargs: Additional arguments specific to the backend executor 
                      (e.g., chat_title_keyword for chatgpt, timeout).

        Returns:
            str or None: The response content from the backend, or None on failure.
        """
        target_backend = self.preferred_backend if backend == 'auto' else backend
        log_context = {"target_backend": target_backend, "requested_backend": backend}

        # print(f"Executing prompt via: {target_backend}")
        log_event("EXECUTE_PROMPT_START", _SOURCE, log_context)

        if target_backend == 'cursor':
            if not isinstance(prompt, str):
                 # print("Warning: Cursor backend expects a single string prompt. Joining list.")
                 log_event("EXECUTOR_WARNING", _SOURCE, {**log_context, "warning": "Cursor backend expects string prompt, joining list", "prompt_type": type(prompt).__name__})
                 prompt = "\n".join(prompt)
            # Add executor existence check
            if not self.cursor_executor:
                log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "CursorExecutor instance not available"})
                return None
            return self.cursor_executor.execute_prompt(prompt, **kwargs)
        
        elif target_backend == 'chatgpt':
            if isinstance(prompt, str):
                 # Assume single message if string is passed
                 messages = [prompt]
            elif isinstance(prompt, list):
                 messages = prompt
            else:
                 # print("Error: ChatGPT backend expects a string or list of strings for prompt.")
                 log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Invalid prompt type for ChatGPT", "prompt_type": type(prompt).__name__})
                 return None
            
            # Extract relevant kwargs for ChatGPTExecutor
            chatgpt_kwargs = {}
            if 'chat_title_keyword' in kwargs:
                chatgpt_kwargs['chat_title_keyword'] = kwargs['chat_title_keyword']
            if 'timeout' in kwargs:
                 chatgpt_kwargs['timeout'] = kwargs['timeout']
            
            # Add executor existence check
            if not self.chatgpt_executor:
                log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "ChatGPTExecutor instance not available"})
                return None
            return self.chatgpt_executor.execute_prompt(messages, **chatgpt_kwargs)
        
        else:
            # print(f"Error: Unknown backend specified: {target_backend}")
            log_event("EXECUTOR_ERROR", _SOURCE, {**log_context, "error": "Unknown backend specified"})
            return None

# Example Usage
if __name__ == '__main__':
    # Assumes chatgpt_commander_agent is running for ChatGPT tests
    # Assumes manual interaction or working CLI for Cursor tests

    # Initialize preferring Cursor
    executor = PromptExecutor(preferred_backend='cursor')

    print("\n--- Test 1: Execute via preferred backend (Cursor) ---")
    cursor_prompt = "Write a python function that returns 'Hello Cursor'"
    response1 = executor.execute(cursor_prompt) # backend='auto' implies preferred
    if response1:
        print(f"Cursor Response:\n{response1}")
    else:
        print("Cursor execution failed or timed out.")

    print("\n--- Test 2: Explicitly execute via ChatGPT backend ---")
    chatgpt_prompt = ["Write a python function that returns 'Hello ChatGPT'"]
    response2 = executor.execute(chatgpt_prompt, backend='chatgpt', chat_title_keyword="Test Chat")
    if response2:
        print(f"ChatGPT Response:\n{response2}")
    else:
        print("ChatGPT execution failed or timed out.")
        
    print("\n--- Test 3: Execute list prompt via preferred backend (Cursor) ---")
    # Demonstrates type conversion warning
    list_prompt = ["Line 1", "Line 2 for Cursor"]
    response3 = executor.execute(list_prompt, backend='cursor') 
    if response3:
        print(f"Cursor Response (from list):\n{response3}")
    else:
        print("Cursor execution failed or timed out.")

    print("\n--- Test 4: Execute string prompt via ChatGPT backend ---")
    string_prompt_gpt = "Explain lazy loading."
    response4 = executor.execute(string_prompt_gpt, backend='chatgpt', chat_title_keyword="Test Chat")
    if response4:
         print(f"ChatGPT Response (from string):\n{response4}")
    else:
        print("ChatGPT execution failed or timed out.") 