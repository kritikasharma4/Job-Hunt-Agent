"""
Configuration settings for the AI Job Hunting Agent.

Handles environment variables, configuration loading, and default settings.
Follows the Single Responsibility Principle by centralizing all configuration.
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class LLMConfig:
    """Configuration for LLM provider settings."""

    provider: str = "anthropic"  # 'anthropic', 'openai', 'local', etc.
    model: str = "claude-3-sonnet-20240229"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30


@dataclass
class JobFetcherConfig:
    """Configuration for job fetching behavior."""

    enabled_sources: list = None  # e.g., ['linkedin', 'indeed', 'builtin']
    max_results_per_source: int = 50
    timeout: int = 30
    rate_limit_delay: float = 1.0

    def __post_init__(self):
        if self.enabled_sources is None:
            self.enabled_sources = ['linkedin']


@dataclass
class RelevanceConfig:
    """Configuration for relevance matching settings."""

    min_relevance_score: float = 0.6
    weight_skills: float = 0.3
    weight_experience: float = 0.3
    weight_location: float = 0.2
    weight_salary: float = 0.2


@dataclass
class FilterConfig:
    """Configuration for job filtering rules."""

    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    required_locations: list = None
    excluded_keywords: list = None
    min_experience_years: int = 0

    def __post_init__(self):
        if self.required_locations is None:
            self.required_locations = []
        if self.excluded_keywords is None:
            self.excluded_keywords = []


@dataclass
class AppSettings:
    """Main application settings aggregating all configurations."""

    llm: LLMConfig = None
    job_fetcher: JobFetcherConfig = None
    relevance: RelevanceConfig = None
    filter: FilterConfig = None
    debug: bool = False
    log_level: str = "INFO"

    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()
        if self.job_fetcher is None:
            self.job_fetcher = JobFetcherConfig()
        if self.relevance is None:
            self.relevance = RelevanceConfig()
        if self.filter is None:
            self.filter = FilterConfig()

    @classmethod
    def from_env(cls) -> "AppSettings":
        """Load settings from environment variables."""
        llm_config = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "anthropic"),
            model=os.getenv("LLM_MODEL", "claude-3-sonnet-20240229"),
            api_key=os.getenv("LLM_API_KEY"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        )

        return cls(
            llm=llm_config,
            debug=os.getenv("DEBUG", "False").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
