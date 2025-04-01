"""
Utility class for interacting with the Ollama API asynchronously.
"""

import aiohttp
import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)

class OllamaError(Exception):
    """Custom exception for Ollama client errors."""
    pass

class OllamaClient:
    """Handles asynchronous communication with an Ollama API endpoint."""

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "mistral:latest"):
        """
        Initializes the OllamaClient.

        Args:
            base_url: The base URL of the Ollama API (e.g., http://localhost:11434).
            default_model: The default Ollama model to use if not specified per request.
        """
        if not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url
        self.api_url = f"{self.base_url}api/generate"
        self.default_model = default_model
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"OllamaClient initialized. API endpoint: {self.api_url}, Default model: {self.default_model}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Creates or returns the existing aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp ClientSession for OllamaClient.")
        return self._session

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_message: Optional[str] = None,
        context: Optional[Any] = None, # Previous conversation context (optional)
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None # Ollama generation options (e.g., temperature)
    ) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]: # Return type depends on stream
        """
        Sends a prompt to the Ollama /api/generate endpoint.

        Args:
            prompt: The main user prompt.
            model: The specific model to use (overrides default_model).
            system_message: An optional system-level instruction for the model.
            context: Optional context from previous interactions for conversational continuity.
            stream: If True, returns an async generator yielding partial responses.
                    If False (default), returns the complete final response dictionary.
            options: Optional dictionary of Ollama generation parameters
                     (e.g., {"temperature": 0.7, "top_p": 0.9}).

        Returns:
            If stream is False: A dictionary containing the full response from Ollama.
            If stream is True: An async generator yielding response chunk dictionaries.

        Raises:
            OllamaError: If the request fails or returns an error status.
        """
        session = await self._get_session()
        target_model = model or self.default_model

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": stream
        }
        if system_message:
            payload["system"] = system_message
        if context:
            payload["context"] = context
        if options:
            payload["options"] = options

        logger.debug(f"Sending request to Ollama ({target_model}): Prompt starting with '{prompt[:50]}...'")
        try:
            async with session.post(self.api_url, json=payload) as response:
                if response.status == 200:
                    logger.debug(f"Ollama request successful (Status: {response.status})")
                    if stream:
                        return self._stream_response(response)
                    else:
                        result = await response.json()
                        if result.get('error'):
                            logger.error(f"Ollama API returned an error: {result['error']}")
                            raise OllamaError(f"Ollama API error: {result['error']}")
                        logger.debug(f"Received Ollama response: {str(result)[:100]}...")
                        return result
                else:
                    error_text = await response.text()
                    log_message = f"Ollama API request failed. Status: {response.status}. Response: {error_text}"
                    logger.error(log_message)
                    raise OllamaError(log_message)

        except aiohttp.ClientConnectorError as e:
            log_message = f"Could not connect to Ollama API at {self.api_url}. Is Ollama running? Error: {e}"
            logger.error(log_message)
            raise OllamaError(log_message) from e
        except aiohttp.ClientError as e:
            log_message = f"An unexpected error occurred during Ollama request: {e}"
            logger.error(log_message)
            raise OllamaError(log_message) from e
        except json.JSONDecodeError as e:
            log_message = f"Failed to decode JSON response from Ollama: {e}"
            logger.error(log_message)
            raise OllamaError(log_message) from e

    async def _stream_response(self, response: aiohttp.ClientResponse) -> AsyncGenerator[Dict[str, Any], None]:
        """Helper to stream and parse line-delimited JSON responses."""
        buffer = ""
        try:
            async for line_bytes in response.content.iter_any(): # Read whatever chunk is available
                buffer += line_bytes.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip(): # Ensure line is not empty
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning(f"Could not decode JSON line from stream: {line}")
            # Process any remaining buffer content after the loop finishes
            if buffer.strip():
                try:
                    yield json.loads(buffer)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode final JSON buffer from stream: {buffer}")

        except aiohttp.ClientError as e:
            logger.error(f"Error reading Ollama stream: {e}")
            raise OllamaError(f"Error reading Ollama stream: {e}") from e
        finally:
            logger.debug("Finished processing Ollama stream.")


    async def close(self):
        """Closes the underlying aiohttp ClientSession."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Closed OllamaClient's aiohttp session.")
            self._session = None

    async def __aenter__(self):
        await self._get_session() # Ensure session exists
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Example usage (if run directly)
async def main():
    # Configure basic logging for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Ollama Client Test --- ")

    # Ensure Ollama is running locally with the 'mistral' model pulled
    client = OllamaClient(default_model="mistral:latest")
    # Or use context manager:
    # async with OllamaClient(default_model="mistral:latest") as client:

    try:
        # --- Test Non-Streaming Generate ---
        print("\n--- Testing Non-Streaming Generate ---")
        prompt = "Why is the sky blue? Keep it brief."
        print(f"Sending prompt: {prompt}")
        response = await client.generate(prompt)
        print(f"Received response:")
        print(response.get('response', 'No response field found.'))
        # print(f"Full response dict: {response}") # Uncomment for full details

        # --- Test Streaming Generate ---
        print("\n--- Testing Streaming Generate ---")
        prompt_stream = "Tell me a short story about a robot learning to paint."
        print(f"Sending streaming prompt: {prompt_stream}")
        print("Streaming response:")
        full_streamed_response = ""
        async for chunk in await client.generate(prompt_stream, stream=True):
            response_part = chunk.get('response', '')
            print(response_part, end='', flush=True)
            full_streamed_response += response_part
            if chunk.get('done'):
                 print("\nStream finished.")
                 # print(f"Final stream chunk: {chunk}") # Uncomment for details like context
                 break # Exit loop once done is True
        # print(f"\nFull streamed content: {full_streamed_response}") # Uncomment if needed

        # --- Test with System Message and Options ---
        print("\n--- Testing with System Message and Options ---")
        system = "You are a pirate planning a voyage."
        prompt_options = "List 3 essential items for the journey."
        options = {"temperature": 0.2} # Low temperature for more predictable output
        print(f"System: {system}")
        print(f"Prompt: {prompt_options}")
        print(f"Options: {options}")
        response_options = await client.generate(prompt_options, system_message=system, options=options)
        print(f"Received response:")
        print(response_options.get('response', 'No response field found.'))

        # --- Test Error Handling (Example: Bad Model Name) ---
        # print("\n--- Testing Error Handling (Bad Model) ---")
        # try:
        #     await client.generate("Hello", model="non_existent_model:latest")
        # except OllamaError as e:
        #     print(f"Caught expected error: {e}")

    except OllamaError as e:
        print(f"\nERROR: An Ollama interaction failed: {e}")
        print("Please ensure Ollama is running and the model (e.g., 'mistral:latest') is available ('ollama list').")
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred: {e}")
    finally:
        await client.close() # Explicitly close if not using context manager
        print("\n--- Ollama Client Test Complete --- ")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 