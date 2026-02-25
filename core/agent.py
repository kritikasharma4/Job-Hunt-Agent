"""
Main AI Job Hunting Agent orchestration.

Coordinates profile parsing, job fetching, relevance matching, and filtering
into a single end-to-end pipeline.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from models.schemas import UserProfile, Job, JobMatch, RelevanceScore
from profile.parser import ProfileParserFactory, ProfileValidator
from jobs.fetchers.base import JobFetcher, LinkedInJobFetcher, IndeedJobFetcher
from jobs.fetchers.demo import DemoJobFetcher
from jobs.fetchers.jsearch import JSearchFetcher
from relevance.matcher import (
    RelevanceMatcher, RelevanceScorer, HybridMatcher,
    SkillBasedMatcher, ExperienceMatcher, LLMBasedMatcher,
)
from filters.job_filters import (
    JobFilter, JobFilterPipeline, DuplicateFilter,
    SalaryFilter, LocationFilter, ExperienceLevelFilter, KeywordFilter,
)
from config.settings import AppSettings

logger = logging.getLogger(__name__)


class JobHuntingAgent:
    """
    Main agent orchestrating the job hunting workflow.

    Responsibility: Acts as the primary facade coordinating all subsystems:
    profile parsing, job fetching, relevance matching, and filtering.
    """

    def __init__(
        self,
        job_fetchers: List[JobFetcher],
        relevance_scorer: RelevanceScorer,
        filter_pipeline: JobFilterPipeline,
        settings: AppSettings,
        llm_provider=None,
    ):
        """
        Initialize the job hunting agent.

        Args:
            job_fetchers: List of job fetchers for different sources
            relevance_scorer: Scorer for matching profiles with jobs
            filter_pipeline: Pipeline for filtering jobs
            settings: Application configuration
            llm_provider: Optional LLM provider for PDF/text parsing
        """
        self.job_fetchers = {f.source_name: f for f in job_fetchers}
        self.relevance_scorer = relevance_scorer
        self.filter_pipeline = filter_pipeline
        self.settings = settings
        self.llm_provider = llm_provider
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
        logger.info(f"Loading profile from: {profile_path}")

        # Register parsers with LLM if available (needed for PDF/text)
        if self.llm_provider:
            ProfileParserFactory.create_with_llm(self.llm_provider)

        profile = ProfileParserFactory.parse_profile(profile_path)

        # Validate
        ProfileValidator.validate(profile)
        completeness = ProfileValidator.validate_completeness(profile)
        logger.info(
            f"Profile loaded: {profile.full_name} "
            f"(completeness: {completeness['completeness_score']:.0%}, "
            f"skills: {len(profile.skills)}, "
            f"experience: {profile.get_years_of_experience()} years)"
        )

        if completeness["missing_fields"]:
            logger.warning(
                f"Profile missing: {', '.join(completeness['missing_fields'])}"
            )

        self.user_profile = profile
        return profile

    def fetch_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        sources: Optional[List[str]] = None,
        **filters,
    ) -> List[Job]:
        """
        Fetch jobs from configured sources.

        Args:
            query: Job search query
            location: Optional location filter
            sources: Optional list of sources to fetch from (default: all)
            **filters: Additional filters passed to fetchers
                       (employment_type, date_posted, remote_only, etc.)

        Returns:
            List of Job objects from all sources
        """
        if not self.job_fetchers:
            logger.warning("No job fetchers configured")
            return []

        # Determine which fetchers to use
        if sources:
            fetchers_to_use = {
                name: f for name, f in self.job_fetchers.items()
                if name in [s.lower() for s in sources]
            }
            unknown = set(s.lower() for s in sources) - set(self.job_fetchers.keys())
            if unknown:
                logger.warning(f"Unknown sources ignored: {unknown}")
        else:
            fetchers_to_use = self.job_fetchers

        max_per_source = self.settings.job_fetcher.max_results_per_source
        all_jobs = []

        for source_name, fetcher in fetchers_to_use.items():
            try:
                logger.info(f"Fetching from {source_name}...")
                jobs = fetcher.fetch(
                    query=query,
                    location=location,
                    max_results=max_per_source,
                    **filters,
                )
                all_jobs.extend(jobs)
                logger.info(f"  {source_name}: {len(jobs)} jobs")
            except Exception as e:
                logger.error(f"Failed to fetch from {source_name}: {e}")
                continue

        logger.info(f"Total jobs fetched: {len(all_jobs)}")
        return all_jobs

    def match_and_rank_jobs(self, jobs: List[Job]) -> List[JobMatch]:
        """
        Match jobs against profile, filter, and rank by relevance.

        Args:
            jobs: Jobs to match

        Returns:
            Ranked list of JobMatch objects (highest score first)

        Raises:
            ValueError: If profile not loaded
        """
        if not self.user_profile:
            raise ValueError(
                "Profile not loaded. Call load_profile() first."
            )

        if not jobs:
            logger.warning("No jobs to match")
            return []

        # Step 1: Score all jobs
        logger.info(f"Scoring {len(jobs)} jobs against profile...")
        scores = self.relevance_scorer.score_jobs(self.user_profile, jobs)

        # Step 2: Filter
        logger.info("Applying filters...")
        filtered_jobs, report = self.filter_pipeline.apply(
            jobs, self.user_profile
        )
        filtered_ids = {j.job_id for j in filtered_jobs}

        # Step 3: Build JobMatch objects
        min_score = self.settings.relevance.min_relevance_score
        matches = []

        for job, score in zip(jobs, scores):
            passed_filters = job.job_id in filtered_ids

            # Find filter reasons for this job
            filter_reasons = [
                r for r in report.get("reasons", [])
                if job.title in r and job.company in r
            ]

            match = JobMatch(
                job=job,
                relevance_score=score,
                passed_filters=passed_filters,
                filter_reasons=filter_reasons,
            )

            # Keep if passed filters AND meets minimum score
            if passed_filters and score.overall_score >= min_score:
                matches.append(match)

        # Step 4: Sort by overall score descending
        matches.sort(key=lambda m: m.relevance_score.overall_score, reverse=True)

        logger.info(
            f"Matching complete: {len(matches)} jobs passed "
            f"(min_score={min_score}, filtered={report.get('total_removed', 0)})"
        )

        return matches

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
        """
        logger.info("=" * 60)
        logger.info("Starting Job Hunting Pipeline")
        logger.info("=" * 60)

        # 1. Load profile
        self.load_profile(profile_path)

        # 2. Fetch jobs
        jobs = self.fetch_jobs(query, location, sources)
        if not jobs:
            logger.warning("No jobs found. Try broadening your search.")
            return []

        # 3. Match, filter, rank
        matches = self.match_and_rank_jobs(jobs)

        logger.info("=" * 60)
        logger.info(f"Pipeline complete: {len(matches)} matched jobs")
        if matches:
            top = matches[0]
            logger.info(
                f"Top match: '{top.job.title}' at {top.job.company} "
                f"(score: {top.relevance_score.overall_score:.3f})"
            )
        logger.info("=" * 60)

        return matches

    def save_results(self, matches: List[JobMatch], output_path: str) -> None:
        """
        Save matching results to JSON file.

        Args:
            matches: JobMatch results to save
            output_path: Path to save results
        """
        results = []
        for match in matches:
            job = match.job
            score = match.relevance_score

            results.append({
                "rank": len(results) + 1,
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "location": str(job.location) if job.location else "N/A",
                "url": job.url,
                "source": job.source,
                "salary": {
                    "min": job.salary.min_amount,
                    "max": job.salary.max_amount,
                    "currency": job.salary.currency,
                    "period": job.salary.period,
                } if job.salary else None,
                "scores": {
                    "overall": round(score.overall_score, 3),
                    "skills": round(score.skills_score, 3),
                    "experience": round(score.experience_score, 3),
                    "location": round(score.location_score, 3),
                    "salary": round(score.salary_score, 3),
                    "level": round(score.level_score, 3),
                },
                "matching_skills": score.matching_skills,
                "missing_skills": score.missing_skills,
                "reasoning": score.reasoning,
            })

        output = {
            "generated_at": datetime.now().isoformat(),
            "profile": self.user_profile.full_name if self.user_profile else "Unknown",
            "total_matches": len(results),
            "results": results,
        }

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, default=str)
            logger.info(f"Results saved to: {output_path} ({len(results)} matches)")
        except Exception as e:
            logger.error(f"Failed to save results to {output_path}: {e}")
            raise


class AgentBuilder:
    """
    Builder for constructing JobHuntingAgent instances.

    Responsibility: Simplifies agent construction with default components
    while allowing customization. Implements Builder Pattern.
    """

    def __init__(self, settings: Optional[AppSettings] = None):
        """
        Initialize builder with settings.

        Args:
            settings: Application settings (defaults to AppSettings() if None)
        """
        self.settings = settings or AppSettings()
        self.job_fetchers: List[JobFetcher] = []
        self.relevance_scorer: Optional[RelevanceScorer] = None
        self.filter_pipeline: Optional[JobFilterPipeline] = None
        self.llm_provider = None
        self.filters: List[JobFilter] = []

    def with_llm(self, llm_provider) -> "AgentBuilder":
        """Set LLM provider (used for PDF/text parsing and LLM-based matching)."""
        self.llm_provider = llm_provider
        return self

    def with_job_fetcher(self, fetcher: JobFetcher) -> "AgentBuilder":
        """Add a job fetcher."""
        self.job_fetchers.append(fetcher)
        return self

    def with_fetchers(self, sources: List[str]) -> "AgentBuilder":
        """Add fetchers by source name (convenience method)."""
        source_map = {
            "linkedin": LinkedInJobFetcher,
            "indeed": IndeedJobFetcher,
            "demo": DemoJobFetcher,
            "jsearch": JSearchFetcher,
        }
        for source in sources:
            cls = source_map.get(source.lower())
            if cls:
                self.job_fetchers.append(cls())
            else:
                logger.warning(f"Unknown source: {source}")
        return self

    def with_relevance_scorer(self, scorer: RelevanceScorer) -> "AgentBuilder":
        """Set a custom relevance scorer."""
        self.relevance_scorer = scorer
        return self

    def with_filter(self, job_filter: JobFilter) -> "AgentBuilder":
        """Add a filter to the pipeline."""
        self.filters.append(job_filter)
        return self

    def with_filter_pipeline(self, pipeline: JobFilterPipeline) -> "AgentBuilder":
        """Set a complete custom filter pipeline."""
        self.filter_pipeline = pipeline
        return self

    def build(self) -> JobHuntingAgent:
        """
        Build the agent with configured components.
        Uses sensible defaults for any component not explicitly set.

        Returns:
            Configured JobHuntingAgent
        """
        # Default fetchers: LinkedIn
        if not self.job_fetchers:
            self.job_fetchers = [LinkedInJobFetcher()]
            logger.info("Using default fetcher: LinkedIn")

        # Default scorer: Hybrid (Skill + Experience), add LLM if available
        if not self.relevance_scorer:
            matchers = [SkillBasedMatcher(), ExperienceMatcher()]
            weights = {"skill_based": 0.5, "experience": 0.5}

            if self.llm_provider:
                matchers.append(LLMBasedMatcher(self.llm_provider))
                weights = {"skill_based": 0.3, "experience": 0.3, "llm_based": 0.4}
                logger.info("Using hybrid scorer: Skill + Experience + LLM")
            else:
                logger.info("Using hybrid scorer: Skill + Experience (no LLM)")

            self.relevance_scorer = RelevanceScorer(
                HybridMatcher(matchers=matchers, weights=weights)
            )

        # Default filter pipeline
        if not self.filter_pipeline:
            if not self.filters:
                # Sensible defaults
                self.filters = [
                    DuplicateFilter(),
                    SalaryFilter(),  # Uses profile preferences
                    ExperienceLevelFilter(),  # Uses profile preferences
                ]
            self.filter_pipeline = JobFilterPipeline(self.filters)

        agent = JobHuntingAgent(
            job_fetchers=self.job_fetchers,
            relevance_scorer=self.relevance_scorer,
            filter_pipeline=self.filter_pipeline,
            settings=self.settings,
            llm_provider=self.llm_provider,
        )

        logger.info(
            f"Agent built: {len(self.job_fetchers)} fetchers, "
            f"{len(self.filter_pipeline.filters)} filters"
        )

        return agent
