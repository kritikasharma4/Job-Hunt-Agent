"""
Main AI Job Hunting Agent orchestration.

Coordinates profile parsing, job fetching, relevance matching, and filtering.
"""

from typing import List, Optional
from models.schemas import UserProfile, Job, JobMatch
from profile.parser import ProfileParser
from jobs.fetchers.base import JobFetcher
from relevance.matcher import RelevanceScorer
from filters.job_filters import JobFilterPipeline
from config.settings import AppSettings


class JobHuntingAgent:
    """
    Main agent orchestrating the job hunting workflow.

    Responsibility: Acts as the primary facade coordinating all subsystems:
    profile parsing, job fetching, relevance matching, and filtering.
    Follows the Single Responsibility Principle by delegating to specialized components.
    """

    def __init__(
        self,
        profile_parser: ProfileParser,
        job_fetchers: List[JobFetcher],
        relevance_scorer: RelevanceScorer,
        filter_pipeline: JobFilterPipeline,
        settings: AppSettings
    ):
        """
        Initialize the job hunting agent.

        Args:
            profile_parser: Parser for loading user profile
            job_fetchers: List of job fetchers for different sources
            relevance_scorer: Scorer for matching profiles with jobs
            filter_pipeline: Pipeline for filtering jobs
            settings: Application configuration
        """
        self.profile_parser = profile_parser
        self.job_fetchers = {f.source_name: f for f in job_fetchers}
        self.relevance_scorer = relevance_scorer
        self.filter_pipeline = filter_pipeline
        self.settings = settings
        self.user_profile: Optional[UserProfile] = None

    def load_profile(self, profile_path: str) -> UserProfile:
        """
        Load user profile from file.

        Args:
            profile_path: Path to profile/resume file

        Returns:
            Loaded UserProfile

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If profile parsing fails
        """
        pass

    def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> List[Job]:
        """
        Fetch jobs from configured sources.

        Args:
            query: Job search query
            location: Optional location filter
            sources: Optional list of sources to fetch from (default: all)

        Returns:
            List of Job objects from all sources

        Raises:
            Exception: If fetching fails
        """
        pass

    def match_and_rank_jobs(self, jobs: List[Job]) -> List[JobMatch]:
        """
        Match jobs against profile and apply filters.

        Args:
            jobs: Jobs to match

        Returns:
            Ranked list of JobMatch objects

        Raises:
            ValueError: If profile not loaded
        """
        pass

    def run_pipeline(
        self,
        profile_path: str,
        query: str,
        location: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> List[JobMatch]:
        """
        Run the complete job hunting pipeline.

        Executes: load profile -> fetch jobs -> match -> filter -> rank

        Args:
            profile_path: Path to user profile
            query: Job search query
            location: Optional location
            sources: Optional source list

        Returns:
            Ranked list of matched jobs

        Raises:
            Exception: If any step fails
        """
        pass

    def save_results(self, matches: List[JobMatch], output_path: str) -> None:
        """
        Save matching results to file.

        Args:
            matches: JobMatch results to save
            output_path: Path to save results

        Raises:
            IOError: If save fails
        """
        pass


class AgentBuilder:
    """
    Builder for constructing JobHuntingAgent instances.

    Responsibility: Simplifies agent construction with default components
    while allowing customization. Implements Builder Pattern.
    """

    def __init__(self, settings: AppSettings):
        """
        Initialize builder with settings.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.profile_parser: Optional[ProfileParser] = None
        self.job_fetchers: List[JobFetcher] = []
        self.relevance_scorer: Optional[RelevanceScorer] = None
        self.filter_pipeline: Optional[JobFilterPipeline] = None

    def with_profile_parser(self, parser: ProfileParser) -> "AgentBuilder":
        """Set profile parser."""
        self.profile_parser = parser
        return self

    def with_job_fetcher(self, fetcher: JobFetcher) -> "AgentBuilder":
        """Add a job fetcher."""
        self.job_fetchers.append(fetcher)
        return self

    def with_relevance_scorer(self, scorer: RelevanceScorer) -> "AgentBuilder":
        """Set relevance scorer."""
        self.relevance_scorer = scorer
        return self

    def with_filter_pipeline(self, pipeline: JobFilterPipeline) -> "AgentBuilder":
        """Set filter pipeline."""
        self.filter_pipeline = pipeline
        return self

    def build(self) -> JobHuntingAgent:
        """
        Build the agent with configured components.

        Returns:
            Configured JobHuntingAgent

        Raises:
            ValueError: If required components are missing
        """
        pass
