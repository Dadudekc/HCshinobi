"""
Mistral AI client service for handling API interactions.
"""

import os
from typing import List, Dict, Optional
from mistralai import Mistral as BaseMistralClient
import logging


class MistralClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Mistral client with API key.

        Args:
            api_key: Optional API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Mistral API key is required. Set MISTRAL_API_KEY environment variable or pass api_key parameter."
            )

        self.client = BaseMistralClient(api_key=self.api_key)
        logging.info("Mistral client initialized successfully.")

    def chat(self, messages: List[Dict[str, str]], model: str = "mistral-tiny") -> str:
        """
        Send a chat request to Mistral AI.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: The model to use for generation

        Returns:
            The generated response text
        """
        try:
            response = self.client.chat(model=model, messages=messages)
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error in Mistral chat request: {e}")
            raise

    def generate_text(
        self, prompt: str, model: str = "mistral-tiny", max_tokens: int = 1000
    ) -> str:
        """
        Generate text using Mistral AI.

        Args:
            prompt: The input prompt
            model: The model to use for generation
            max_tokens: Maximum number of tokens to generate

        Returns:
            The generated text
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.client.chat(
                model=model, messages=messages, max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error in Mistral text generation: {e}")
            raise
