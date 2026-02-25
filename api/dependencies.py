"""
FastAPI dependency injection providers.

Provides database sessions and agent instances to route handlers.
"""

import logging
from config.settings import AppSettings
from core.agent import AgentBuilder

logger = logging.getLogger(__name__)


def get_settings() -> AppSettings:
    return AppSettings.from_env()


def build_agent(settings: AppSettings, use_llm: bool = False):
    """Build a JobHuntingAgent with configured components.

    LLM matching is off by default for API use — it's too slow for
    interactive searches (one Ollama call per job). The skill-based +
    experience matchers are instant and produce good results.
    """
    builder = AgentBuilder(settings)

    if use_llm:
        llm_provider = _try_setup_llm(settings)
        if llm_provider:
            builder.with_llm(llm_provider)

    builder.with_fetchers(settings.job_fetcher.enabled_sources)
    return builder.build()


def _try_setup_llm(settings: AppSettings):
    """Try to initialize the LLM provider. Returns None if unavailable."""
    if settings.llm.provider.lower() == "ollama":
        try:
            from llm.ollama_provider import OllamaProvider
            provider = OllamaProvider(settings.llm)
            if provider.validate_credentials():
                logger.info("Ollama LLM provider connected")
                return provider
            else:
                logger.warning("Ollama not available — running without LLM")
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama: {e}")
            return None
    return None
