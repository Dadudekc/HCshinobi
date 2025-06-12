"""
Utility class for interacting with the Ollama API asynchronously.
"""

import aiohttp
import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator

# Assuming constants are accessible or loaded elsewhere
# If not, they need to be imported or passed
from HCshinobi.core.constants import (
    OLLAMA_API_URL,
    OLLAMA_MODEL,
    OLLAMA_REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

class OllamaError(Exception):
    """Custom exception for Ollama client errors."""
    pass

class OllamaClient:
    """Handles asynchronous communication with an Ollama API endpoint."""

    def __init__(
        self,
        model: str = OLLAMA_MODEL,
        host: str = OLLAMA_API_URL,
        context_size: int = 4096,
        temperature: float = 0.7
    ):
        """Initialize the Ollama client.
        
        Args:
            model: Name of the model to use
            host: Ollama API host address
            context_size: Maximum context size
            temperature: Generation temperature (0.0 to 1.0)
        """
        self.model = model
        self.host = host.rstrip("/")
        self.context_size = context_size
        self.temperature = temperature
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"OllamaClient initialized. API endpoint: {self.host}, Default model: {self.model}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Creates or returns the existing aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp ClientSession for OllamaClient.")
        return self._session

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate a response using Ollama.
        
        Args:
            prompt: The prompt to generate from
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
            
        Raises:
            OllamaError: If generation fails
        """
        try:
            session = await self._get_session()
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature or self.temperature,
                "context_size": self.context_size
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            logger.debug(f"Sending request to Ollama ({self.model}): Prompt starting with '{prompt[:50]}...'")
            async with session.post(
                f"{self.host}/api/generate",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_message = f"Ollama API request failed. Status: {response.status}. Response: {error_text}"
                    logger.error(log_message)
                    raise OllamaError(log_message)
                    
                data = await response.json()
                logger.debug(f"Received Ollama response: {str(data)[:100]}...")
                return data["response"]
                    
        except aiohttp.ClientConnectorError as e:
            log_message = f"Could not connect to Ollama API at {self.host}. Is Ollama running? Error: {e}"
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
        except Exception as e:
            log_message = f"Unexpected error during generation: {e}"
            logger.error(log_message)
            raise OllamaError(log_message)

    async def chat(
        self,
        messages: list[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Have a chat conversation using Ollama.
        
        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: Optional system prompt
            temperature: Override default temperature
            
        Returns:
            Generated response
            
        Raises:
            OllamaError: If chat fails
        """
        try:
            session = await self._get_session()
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            logger.debug(f"Sending request to Ollama ({self.model}): Chat starting with '{messages[0]['content'][:50]}...'")
            async with session.post(
                f"{self.host}/api/chat",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_message = f"Ollama API request failed. Status: {response.status}. Response: {error_text}"
                    logger.error(log_message)
                    raise OllamaError(log_message)
                    
                data = await response.json()
                logger.debug(f"Received Ollama response: {str(data['message']['content'])[:100]}...")
                return data["message"]["content"]
                    
        except aiohttp.ClientConnectorError as e:
            log_message = f"Could not connect to Ollama API at {self.host}. Is Ollama running? Error: {e}"
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
        except Exception as e:
            log_message = f"Unexpected error during chat: {e}"
            logger.error(log_message)
            raise OllamaError(log_message)

    async def embed(self, text: str) -> list[float]:
        """Get embeddings for text using Ollama.
        
        Args:
            text: Text to get embeddings for
            
        Returns:
            List of embedding values
            
        Raises:
            OllamaError: If embedding fails
        """
        try:
            session = await self._get_session()
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            logger.debug(f"Sending request to Ollama ({self.model}): Embedding for text starting with '{text[:50]}...'")
            async with session.post(
                f"{self.host}/api/embeddings",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_message = f"Ollama API request failed. Status: {response.status}. Response: {error_text}"
                    logger.error(log_message)
                    raise OllamaError(log_message)
                    
                data = await response.json()
                logger.debug(f"Received Ollama response: {str(data['embedding'])[:100]}...")
                return data["embedding"]
                    
        except aiohttp.ClientConnectorError as e:
            log_message = f"Could not connect to Ollama API at {self.host}. Is Ollama running? Error: {e}"
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
        except Exception as e:
            log_message = f"Unexpected error getting embeddings: {e}"
            logger.error(log_message)
            raise OllamaError(log_message)

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

    # Ensure Ollama is running locally with the 'ninja' model pulled
    client = OllamaClient(model="ninja:latest")
    # Or use context manager:
    # async with OllamaClient(model="ninja:latest") as client:

    try:
        # --- Test Non-Streaming Generate ---
        print("\n--- Testing Non-Streaming Generate ---")
        prompt = "Why is the sky blue? Keep it brief."
        print(f"Sending prompt: {prompt}")
        response = await client.generate(prompt)
        print(f"Received response:")
        print(response)
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
        response_options = await client.generate(prompt_options, system_prompt=system, options=options)
        print(f"Received response:")
        print(response_options)

        # --- Test Error Handling (Example: Bad Model Name) ---
        # print("\n--- Testing Error Handling (Bad Model) ---")
        # try:
        #     await client.generate("Hello", model="non_existent_model:latest")
        # except OllamaError as e:
        #     print(f"Caught expected error: {e}")

    except OllamaError as e:
        print(f"\nERROR: An Ollama interaction failed: {e}")
        print("Please ensure Ollama is running and the model (e.g., 'ninja:latest') is available ('ollama list').")
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred: {e}")
    finally:
        await client.close() # Explicitly close if not using context manager
        print("\n--- Ollama Client Test Complete --- ")

async def generate_ollama_response(
    prompt: str,
    model: str = OLLAMA_MODEL,
    api_url: str = OLLAMA_API_URL,
    timeout: int = OLLAMA_REQUEST_TIMEOUT
) -> Optional[str]:
    """
    Sends a prompt to the Ollama API and returns the generated text content.

    Args:
        prompt: The input prompt for the Ollama model.
        model: The specific Ollama model to use (defaults to constant).
        api_url: The Ollama API endpoint (defaults to constant).
        timeout: Request timeout in seconds (defaults to constant).

    Returns:
        The generated text content as a string, or None if an error occurs.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False, # We want the full response at once
        "format": "json" # Request JSON output for easier parsing
    }

    logger.debug(f"Sending prompt to Ollama ({model}) at {api_url}:")
    # logger.debug(f"Prompt: {prompt[:500]}...") # Log truncated prompt

    try:
        async with aiohttp.ClientSession() as session:
            request_timeout = aiohttp.ClientTimeout(total=timeout)
            async with session.post(api_url, json=payload, timeout=request_timeout) as response:
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                
                response_text = await response.text()
                logger.debug(f"Received Ollama response (status {response.status})")
                # logger.debug(f"Raw Response: {response_text[:500]}...")
                
                # Parse the JSON response
                try:
                    data = json.loads(response_text)
                    # The actual generated text is often nested, commonly under 'response'
                    # within another JSON object if format='json' was used.
                    # Check for standard 'response' key first
                    if 'response' in data and isinstance(data['response'], str):
                         # If the 'response' field itself contains a JSON string, parse *that*
                         try:
                             inner_data = json.loads(data['response'])
                             # Assuming the desired text is in a specific key within the inner JSON
                             # Adjust 'generated_text_key' based on your model's typical output format
                             generated_text = inner_data.get("narrative", inner_data.get("dialogue", str(inner_data))) # Example keys
                             logger.debug("Successfully parsed nested JSON response.")
                             return generated_text
                         except json.JSONDecodeError:
                             # If parsing inner JSON fails, maybe 'response' *was* the final text
                             logger.debug("'response' field was not nested JSON, returning as is.")
                             return data['response']
                    # Fallback if 'response' key isn't found or isn't a string
                    else:
                         logger.warning(f"Could not find expected 'response' key in Ollama JSON data: {data}")
                         # Attempt to return the whole structure as string if desperate
                         return json.dumps(data)
                         
                except json.JSONDecodeError as json_err:
                     logger.error(f"Failed to decode Ollama JSON response: {json_err}")
                     logger.error(f"Response text was: {response_text}")
                     return None
                     
    except aiohttp.ClientError as client_err:
        logger.error(f"Ollama API request failed (Client Error): {client_err}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Ollama API request timed out after {timeout} seconds.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred calling Ollama API: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 