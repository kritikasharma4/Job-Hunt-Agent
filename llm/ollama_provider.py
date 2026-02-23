"""
Ollama Local LLM provider implementation.

Integrates with Ollama for running local language models like Llama 3.
Handles HTTP communication with Ollama service and includes error handling and health checks.
"""

import json
import logging
from typing import Optional, Dict, Any
import requests

from .base import LLMProvider
from config.settings import LLMConfig

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama Local LLM provider.

    Responsibility: Implements LLMProvider interface specifically for Ollama's local models,
    enabling support for models like Llama 3 8B Q4, Mistral, and other open-source models.
    Handles communication with local Ollama service via HTTP with production-ready error handling.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize Ollama provider.

        Args:
            config: LLM configuration with Ollama-specific settings.
                   Expected: provider='ollama', model='llama3' (or other Ollama model)
                   api_key is not required for local Ollama
        """
        super().__init__(config)
        self.base_url = "http://localhost:11434"
        self.generate_endpoint = f"{self.base_url}/api/generate"
        self.tags_endpoint = f"{self.base_url}/api/tags"
        self.pull_endpoint = f"{self.base_url}/api/pull"
        self.session = requests.Session()

        logger.info(
            f"Initialized OllamaProvider with model={config.model}, "
            f"temperature={config.temperature}, max_tokens={config.max_tokens}"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Ollama local model.

        Args:
            prompt: User input prompt
            system_prompt: Optional system context/instruction to prepend to prompt
            **kwargs: Additional parameters:
                - temperature: Override config temperature (0-1)
                - max_tokens: Override config max_tokens
                - top_p: Nucleus sampling parameter

        Returns:
            Generated text response (stripped of whitespace)

        Raises:
            ConnectionError: If Ollama service is not running
            ValueError: If prompt is empty
            RuntimeError: If generation fails after timeout
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Get temperature and max_tokens from kwargs or config
        temperature = kwargs.get("temperature", self.config.temperature)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        timeout = kwargs.get("timeout", self.config.timeout)

        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "temperature": temperature,
            "num_predict": max_tokens,
            "stream": False,
        }

        try:
            logger.debug(f"Calling Ollama generate with model={self.config.model}")
            response = self.session.post(
                self.generate_endpoint,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()

            data = response.json()
            generated_text = data.get("response", "").strip()

            if not generated_text:
                raise RuntimeError("Model returned empty response")

            logger.debug(f"Generated {len(generated_text)} characters")
            return generated_text

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Ollama service at {self.base_url}: {e}")
            raise ConnectionError(
                f"Ollama service not running at {self.base_url}. "
                f"Start with: ollama serve"
            ) from e

        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama request timed out after {timeout}s")
            raise RuntimeError(
                f"Ollama generation timed out after {timeout} seconds. "
                f"Try increasing timeout or reducing max_tokens."
            ) from e

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise RuntimeError(f"Ollama API error: {e}") from e

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            raise RuntimeError(f"Invalid response from Ollama: {e}") from e

    def generate_with_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response from Ollama model.

        Forces the model to return valid JSON by embedding schema instructions
        in the prompt and parsing the response carefully.

        Args:
            prompt: User input prompt
            output_schema: JSON schema describing expected output format.
                          Used to guide model and for basic validation.
                          Example: {"task": "string", "score": "float", "reasoning": "string"}
            system_prompt: Optional system context
            **kwargs: Additional parameters (temperature, timeout, etc.)

        Returns:
            Parsed JSON response as dictionary

        Raises:
            ValueError: If output doesn't appear to be valid JSON
            ConnectionError: If Ollama service is not running
            RuntimeError: If generation fails or response can't be parsed
        """
        if not output_schema or not isinstance(output_schema, dict):
            raise ValueError("output_schema must be a non-empty dictionary")

        # Build schema description for the model
        schema_description = json.dumps(output_schema, indent=2)

        # Create instruction to force JSON output
        json_instruction = (
            f"\n\nYou MUST respond with ONLY valid JSON matching this schema:\n"
            f"{schema_description}\n\n"
            f"Respond with JSON object only, no other text."
        )

        full_prompt = prompt + json_instruction

        try:
            # Generate text with slightly higher timeout for structured output
            timeout = kwargs.get("timeout", self.config.timeout + 5)
            response_text = self.generate(
                full_prompt,
                system_prompt=system_prompt,
                timeout=timeout,
                **{k: v for k, v in kwargs.items() if k not in ["timeout"]},
            )

            # Extract JSON from response (handle cases where model adds extra text)
            parsed_json = self._extract_json_from_response(response_text)

            logger.debug(f"Successfully parsed structured output: {list(parsed_json.keys())}")
            return parsed_json

        except ConnectionError:
            raise
        except RuntimeError as e:
            logger.error(f"Failed to generate structured output: {e}")
            raise

    def validate_credentials(self) -> bool:
        """
        Validate Ollama service is running and model is available.

        Checks both that:
        1. Ollama service is reachable
        2. The specified model is available locally

        Returns:
            True if Ollama service is accessible and model is loaded

        Logs warnings if service is not ready but doesn't raise exceptions.
        """
        try:
            # Check if Ollama service is running
            response = self.session.get(self.tags_endpoint, timeout=5)
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])

            # Extract model names
            available_models = [m.get("name", "").split(":")[0] for m in models]

            # Check if our configured model is available
            model_name = self.config.model.split(":")[0]  # Handle version tags

            if any(m.startswith(model_name) for m in available_models):
                logger.info(f"✓ Ollama service verified with model {self.config.model}")
                return True
            else:
                logger.warning(
                    f"Model '{self.config.model}' not found in Ollama. "
                    f"Available: {', '.join(available_models)}. "
                    f"Pull with: ollama pull {self.config.model}"
                )
                return False

        except requests.exceptions.ConnectionError:
            logger.warning(
                f"✗ Cannot connect to Ollama at {self.base_url}. "
                f"Start with: ollama serve"
            )
            return False

        except requests.exceptions.Timeout:
            logger.warning(f"✗ Ollama connection timed out at {self.base_url}")
            return False

        except Exception as e:
            logger.warning(f"✗ Error validating Ollama credentials: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of Ollama service and model.

        Returns:
            Dictionary with health status containing:
            - service_running: bool - Whether Ollama service is accessible
            - model_available: bool - Whether configured model is loaded
            - model_name: str - Configured model name
            - available_models: list - List of available models
            - error: str or None - Error message if health check failed

        Example:
            >>> provider = OllamaProvider(config)
            >>> health = provider.health_check()
            >>> if health['service_running'] and health['model_available']:
            ...     print("Ready to generate")
        """
        health = {
            "service_running": False,
            "model_available": False,
            "model_name": self.config.model,
            "available_models": [],
            "error": None,
        }

        try:
            response = self.session.get(self.tags_endpoint, timeout=5)
            response.raise_for_status()

            data = response.json()
            models = data.get("models", [])
            health["available_models"] = [m.get("name", "") for m in models]
            health["service_running"] = True

            # Check if our model is available
            model_name = self.config.model.split(":")[0]
            for model in health["available_models"]:
                if model.startswith(model_name):
                    health["model_available"] = True
                    break

        except requests.exceptions.ConnectionError as e:
            health["error"] = f"Cannot connect to Ollama at {self.base_url}"
            logger.error(health["error"])

        except requests.exceptions.Timeout as e:
            health["error"] = f"Ollama connection timed out"
            logger.error(health["error"])

        except Exception as e:
            health["error"] = f"Health check failed: {str(e)}"
            logger.error(health["error"])

        return health

    def pull_model(self, model_name: str) -> bool:
        """
        Download/pull a model from Ollama library if not present.

        This is a convenience method but doesn't wait for the pull to complete.
        For a production system, you'd want to check status periodically.

        Args:
            model_name: Name of model to pull (e.g., 'llama3', 'mistral')

        Returns:
            True if pull was initiated, False if it failed

        Note:
            This initiates the pull but doesn't wait for completion.
            Model download can take several minutes.
        """
        if not model_name or not model_name.strip():
            raise ValueError("Model name cannot be empty")

        try:
            logger.info(f"Initiating pull for model: {model_name}")
            payload = {"name": model_name}

            response = self.session.post(
                self.pull_endpoint,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            logger.info(f"Successfully initiated pull for {model_name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    @staticmethod
    def _extract_json_from_response(response_text: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from model response text.

        Models sometimes add extra text before/after JSON. This method:
        1. Tries direct JSON parsing
        2. If that fails, looks for JSON-like patterns (text between { and })
        3. Handles various edge cases

        Args:
            response_text: Raw text from model

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If no valid JSON can be extracted
            json.JSONDecodeError: If extracted text is not valid JSON
        """
        if not response_text or not response_text.strip():
            raise ValueError("Response text is empty")

        response_text = response_text.strip()

        # Try direct parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object (text between { and })
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            try:
                json_str = response_text[start_idx : end_idx + 1]
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try to find JSON array (text between [ and ])
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]")

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            try:
                json_str = response_text[start_idx : end_idx + 1]
                parsed = json.loads(json_str)
                # Wrap array in object if needed
                if isinstance(parsed, list):
                    return {"results": parsed}
                return parsed
            except json.JSONDecodeError:
                pass

        # If all else fails, raise error with the problematic text
        raise ValueError(
            f"Could not extract valid JSON from response. "
            f"First 200 chars: {response_text[:200]}"
        )
