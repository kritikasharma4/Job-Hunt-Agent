"""
Abstract base classes for LLM providers.

Follows the Dependency Inversion Principle - depends on abstractions, not concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from config.settings import LLMConfig


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Responsibility: Defines the interface that all LLM providers must implement,
    enabling easy swapping between different LLM services (OpenAI, Anthropic, local, etc.).
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM provider.

        Args:
            config: LLM configuration settings
        """
        self.config = config

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: The user prompt/input
            system_prompt: Optional system context
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def generate_with_structured_output(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response formatted according to schema.

        Args:
            prompt: The user prompt/input
            output_schema: JSON schema for expected output format
            system_prompt: Optional system context
            **kwargs: Additional provider-specific parameters

        Returns:
            Structured response matching the schema
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Validate that provider credentials are valid.

        Returns:
            True if credentials are valid, False otherwise
        """
        pass


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.

    Responsibility: Encapsulates provider instantiation logic following the Factory Pattern,
    allowing easy addition of new providers without modifying existing code.
    """

    _providers: Dict[str, type] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """
        Register a new LLM provider.

        Args:
            name: Provider name identifier
            provider_class: Provider class (must inherit from LLMProvider)
        """
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create_provider(cls, config: LLMConfig) -> LLMProvider:
        """
        Create an LLM provider instance based on configuration.

        Args:
            config: LLM configuration

        Returns:
            Instantiated LLM provider

        Raises:
            ValueError: If provider is not registered
        """
        provider_name = config.provider.lower()
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown LLM provider: {config.provider}")

        provider_class = cls._providers[provider_name]
        return provider_class(config)
