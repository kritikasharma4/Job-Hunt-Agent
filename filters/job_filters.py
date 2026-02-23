"""
Job filtering implementations.

Applies various filters to narrow down job opportunities based on salary,
location, experience level, keywords, and duplicates. Supports composite
filters (AND/OR) and sequential pipeline execution with removal tracking.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Set, Tuple

from models.schemas import Job, UserProfile, JobLevel

logger = logging.getLogger(__name__)


# Ordered levels for range comparison
_LEVEL_ORDER = [
    JobLevel.ENTRY, JobLevel.JUNIOR, JobLevel.MID,
    JobLevel.SENIOR, JobLevel.LEAD, JobLevel.EXECUTIVE,
]

_LEVEL_INDEX: Dict[str, int] = {
    level.value: idx for idx, level in enumerate(_LEVEL_ORDER)
}


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _job_text_blob(job: Job) -> str:
    """Combine all searchable text from a job into one lowercase string."""
    parts = [
        job.title or "",
        job.company or "",
        job.description or "",
    ]
    parts.extend(job.requirements)
    parts.extend(job.nice_to_haves)
    return _normalize(" ".join(parts))


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class JobFilter(ABC):
    """
    Abstract base class for job filters.

    Responsibility: Defines interface for filtering jobs based on various criteria.
    Implements Composite Pattern for combining multiple filters.
    """

    @abstractmethod
    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """
        Apply filter to jobs.

        Args:
            jobs: List of jobs to filter
            profile: User profile for context-aware filtering

        Returns:
            Tuple of (filtered_jobs, filter_reasons) where reasons explain removals
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get filter name."""
        pass


# ---------------------------------------------------------------------------
# Salary filter
# ---------------------------------------------------------------------------

class SalaryFilter(JobFilter):
    """
    Filters jobs based on salary requirements.

    Responsibility: Removes jobs outside acceptable salary range.
    Jobs with no salary data are kept (not penalized for missing info).
    """


    def __init__(self, min_salary: Optional[int] = None, max_salary: Optional[int] = None):
        """
        Initialize salary filter.

        Args:
            min_salary: Minimum acceptable salary (None = no minimum)
            max_salary: Maximum acceptable salary (None = no maximum)
        """
        self.min_salary = min_salary
        self.max_salary = max_salary

    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """Filter by salary range."""
        # No filter configured and no profile preference — pass everything
        min_sal = self.min_salary
        max_sal = self.max_salary

        # Fall back to profile preferences if no explicit bounds
        if min_sal is None and profile.preferred_salary_range:
            min_sal = profile.preferred_salary_range.min_amount
        if max_sal is None and profile.preferred_salary_range:
            max_sal = profile.preferred_salary_range.max_amount

        if min_sal is None and max_sal is None:
            return jobs, []

        filtered = []
        reasons = []

        for job in jobs:
            # No salary info — keep the job (benefit of the doubt)
            if not job.salary:
                filtered.append(job)
                continue

            job_min = job.salary.min_amount
            job_max = job.salary.max_amount

            # Both salary bounds are None — keep
            if job_min is None and job_max is None:
                filtered.append(job)
                continue

            # Normalize: use whichever bound exists
            job_highest = job_max or job_min
            job_lowest = job_min or job_max

            # Check minimum: job's highest offer must meet our minimum
            if min_sal is not None and job_highest is not None and job_highest < min_sal:
                reasons.append(
                    f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                    f"salary ${job_highest:,.0f} below minimum ${min_sal:,.0f}"
                )
                continue

            # Check maximum: job's lowest offer must not exceed our maximum
            if max_sal is not None and job_lowest is not None and job_lowest > max_sal:
                reasons.append(
                    f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                    f"salary ${job_lowest:,.0f} above maximum ${max_sal:,.0f}"
                )
                continue

            filtered.append(job)

        removed = len(jobs) - len(filtered)
        if removed:
            logger.info(f"SalaryFilter: removed {removed}/{len(jobs)} jobs")

        return filtered, reasons

    def get_name(self) -> str:
        return "salary_filter"


# ---------------------------------------------------------------------------
# Location filter
# ---------------------------------------------------------------------------

class LocationFilter(JobFilter):
    """
    Filters jobs based on location preferences.

    Responsibility: Filters jobs by geographic location and remote availability.
    Jobs with no location data are kept.
    """

    def __init__(self, allowed_locations: Optional[List[str]] = None, require_remote: bool = False):
        """
        Initialize location filter.

        Args:
            allowed_locations: List of acceptable locations (city or state names, case-insensitive)
            require_remote: If True, only accept remote jobs
        """
        self.allowed_locations = [_normalize(loc) for loc in (allowed_locations or [])]
        self.require_remote = require_remote

    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """Filter by location."""
        # Build location list from profile if none configured
        allowed = list(self.allowed_locations)
        if not allowed and profile.preferred_locations:
            for loc in profile.preferred_locations:
                if loc.city:
                    allowed.append(_normalize(loc.city))
                if loc.state:
                    allowed.append(_normalize(loc.state))

        require_remote = self.require_remote
        if not require_remote and profile.remote_preference == "required":
            require_remote = True

        # No constraints at all — pass everything
        if not allowed and not require_remote:
            return jobs, []

        filtered = []
        reasons = []

        for job in jobs:
            # No location info — keep
            if not job.location:
                filtered.append(job)
                continue

            # Remote check
            if require_remote:
                if job.location.remote:
                    filtered.append(job)
                    continue
                else:
                    reasons.append(
                        f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                        f"not remote ({job.location})"
                    )
                    continue

            # Remote jobs always pass location filter
            if job.location.remote:
                filtered.append(job)
                continue

            # Check if job location matches any allowed location
            job_city = _normalize(job.location.city)
            job_state = _normalize(job.location.state)
            job_country = _normalize(job.location.country)

            matched = False
            for loc in allowed:
                if loc and (loc == job_city or loc == job_state or loc == job_country
                            or loc in job_city or loc in job_state):
                    matched = True
                    break

            if matched:
                filtered.append(job)
            else:
                reasons.append(
                    f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                    f"location '{job.location}' not in allowed list"
                )

        removed = len(jobs) - len(filtered)
        if removed:
            logger.info(f"LocationFilter: removed {removed}/{len(jobs)} jobs")

        return filtered, reasons

    def get_name(self) -> str:
        return "location_filter"


# ---------------------------------------------------------------------------
# Experience level filter
# ---------------------------------------------------------------------------

class ExperienceLevelFilter(JobFilter):
    """
    Filters jobs by required experience level.

    Responsibility: Removes jobs requiring experience level mismatched with profile.
    Jobs with no level info are kept.
    """

    def __init__(self, min_level: Optional[str] = None, max_level: Optional[str] = None):
        """
        Initialize experience filter.

        Args:
            min_level: Minimum acceptable level (e.g. 'junior', 'mid')
            max_level: Maximum acceptable level (e.g. 'senior', 'lead')
        """
        self.min_level = min_level
        self.max_level = max_level

    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """Filter by experience level."""
        # Determine bounds
        min_idx = self._level_to_index(self.min_level)
        max_idx = self._level_to_index(self.max_level)

        # Fall back to profile preferences
        if min_idx is None and max_idx is None and profile.preferred_job_levels:
            indices = [
                _LEVEL_ORDER.index(lv) for lv in profile.preferred_job_levels
                if lv in _LEVEL_ORDER
            ]
            if indices:
                min_idx = min(indices)
                max_idx = max(indices)

        # No constraints — pass everything
        if min_idx is None and max_idx is None:
            return jobs, []

        filtered = []
        reasons = []

        for job in jobs:
            # No level info — keep
            if not job.level:
                filtered.append(job)
                continue

            job_idx = _LEVEL_ORDER.index(job.level) if job.level in _LEVEL_ORDER else None
            if job_idx is None:
                filtered.append(job)
                continue

            # Check minimum
            if min_idx is not None and job_idx < min_idx:
                reasons.append(
                    f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                    f"level '{job.level.value}' below minimum '{_LEVEL_ORDER[min_idx].value}'"
                )
                continue

            # Check maximum
            if max_idx is not None and job_idx > max_idx:
                reasons.append(
                    f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                    f"level '{job.level.value}' above maximum '{_LEVEL_ORDER[max_idx].value}'"
                )
                continue

            filtered.append(job)

        removed = len(jobs) - len(filtered)
        if removed:
            logger.info(f"ExperienceLevelFilter: removed {removed}/{len(jobs)} jobs")

        return filtered, reasons

    def get_name(self) -> str:
        return "experience_level_filter"

    @staticmethod
    def _level_to_index(level_str: Optional[str]) -> Optional[int]:
        """Convert a level string to its index, or None."""
        if not level_str:
            return None
        return _LEVEL_INDEX.get(level_str.lower())


# ---------------------------------------------------------------------------
# Keyword filter
# ---------------------------------------------------------------------------

class KeywordFilter(JobFilter):
    """
    Filters jobs based on excluded keywords.

    Responsibility: Removes jobs containing unwanted keywords or phrases
    in their title, description, or requirements.
    """

    def __init__(self, excluded_keywords: Optional[List[str]] = None):
        """
        Initialize keyword filter.

        Args:
            excluded_keywords: List of keywords/phrases to exclude (case-insensitive)
        """
        self.excluded_keywords = [_normalize(kw) for kw in (excluded_keywords or [])]

    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """Filter by excluded keywords."""
        if not self.excluded_keywords:
            return jobs, []

        filtered = []
        reasons = []

        for job in jobs:
            text = _job_text_blob(job)
            matched_keyword = None

            for keyword in self.excluded_keywords:
                if keyword in text:
                    matched_keyword = keyword
                    break

            if matched_keyword:
                reasons.append(
                    f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                    f"contains excluded keyword '{matched_keyword}'"
                )
            else:
                filtered.append(job)

        removed = len(jobs) - len(filtered)
        if removed:
            logger.info(f"KeywordFilter: removed {removed}/{len(jobs)} jobs")

        return filtered, reasons

    def get_name(self) -> str:
        return "keyword_filter"


# ---------------------------------------------------------------------------
# Duplicate filter
# ---------------------------------------------------------------------------

class DuplicateFilter(JobFilter):
    """
    Removes duplicate or very similar job postings.

    Responsibility: Deduplicates jobs from multiple sources using:
    1. Exact match on job_id
    2. Exact match on URL
    3. Title + company similarity comparison
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize duplicate filter.

        Args:
            similarity_threshold: Similarity score (0.0-1.0) for title+company match.
                                  0.85 means 85% of words must overlap.
        """
        self.similarity_threshold = similarity_threshold

    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """Filter duplicate jobs."""
        if len(jobs) <= 1:
            return jobs, []

        filtered = []
        reasons = []
        seen_ids: Set[str] = set()
        seen_urls: Set[str] = set()
        seen_signatures: List[str] = []  # normalized "title @ company" strings

        for job in jobs:
            # Check 1: Exact job_id match
            if job.job_id in seen_ids:
                reasons.append(
                    f"[{self.get_name()}] Removed duplicate '{job.title}' at {job.company}: "
                    f"same job_id '{job.job_id}'"
                )
                continue

            # Check 2: Exact URL match
            if job.url:
                # Normalize URL: strip query params and trailing slashes
                clean_url = job.url.split("?")[0].rstrip("/").lower()
                if clean_url in seen_urls:
                    reasons.append(
                        f"[{self.get_name()}] Removed duplicate '{job.title}' at {job.company}: "
                        f"same URL"
                    )
                    continue
                seen_urls.add(clean_url)

            # Check 3: Title + company similarity
            signature = _normalize(f"{job.title} @ {job.company}")
            is_duplicate = False

            for existing_sig in seen_signatures:
                similarity = self._compute_similarity(signature, existing_sig)
                if similarity >= self.similarity_threshold:
                    reasons.append(
                        f"[{self.get_name()}] Removed duplicate '{job.title}' at {job.company}: "
                        f"similar to existing posting ({similarity:.0%} match)"
                    )
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            # Not a duplicate — keep it
            seen_ids.add(job.job_id)
            seen_signatures.append(signature)
            filtered.append(job)

        removed = len(jobs) - len(filtered)
        if removed:
            logger.info(f"DuplicateFilter: removed {removed}/{len(jobs)} duplicates")

        return filtered, reasons

    def get_name(self) -> str:
        return "duplicate_filter"

    @staticmethod
    def _compute_similarity(text_a: str, text_b: str) -> float:
        """
        Compute word-level Jaccard similarity between two strings.

        Returns a float between 0.0 (no overlap) and 1.0 (identical).
        """
        words_a = set(text_a.split())
        words_b = set(text_b.split())

        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Composite filter (AND / OR)
# ---------------------------------------------------------------------------

class CompositeJobFilter(JobFilter):
    """
    Combines multiple filters with logical operators.

    Responsibility: Orchestrates multiple JobFilter instances with AND/OR logic.

    AND mode: A job must pass ALL filters to be kept.
    OR mode: A job is kept if it passes ANY filter.
    """

    def __init__(self, filters: Optional[List[JobFilter]] = None, logical_and: bool = True):
        """
        Initialize composite filter.

        Args:
            filters: List of filters to combine
            logical_and: If True, uses AND logic (all must pass), else OR (any passes)
        """
        self.filters = filters or []
        self.logical_and = logical_and

    def add_filter(self, job_filter: JobFilter) -> None:
        """Add a filter to this composite."""
        self.filters.append(job_filter)

    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """Apply all filters with AND/OR logic."""
        if not self.filters:
            return jobs, []

        if self.logical_and:
            return self._apply_and(jobs, profile)
        else:
            return self._apply_or(jobs, profile)

    def get_name(self) -> str:
        mode = "AND" if self.logical_and else "OR"
        child_names = [f.get_name() for f in self.filters]
        return f"composite_{mode}({', '.join(child_names)})"

    def _apply_and(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """AND: pipe jobs through each filter sequentially. Must pass all."""
        current_jobs = jobs
        all_reasons = []

        for filt in self.filters:
            current_jobs, reasons = filt.apply(current_jobs, profile)
            all_reasons.extend(reasons)

        return current_jobs, all_reasons

    def _apply_or(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], List[str]]:
        """OR: a job is kept if ANY filter accepts it."""
        all_reasons = []
        kept_ids: Set[str] = set()

        for filt in self.filters:
            passed, reasons = filt.apply(jobs, profile)
            for job in passed:
                kept_ids.add(job.job_id)
            all_reasons.extend(reasons)

        # Keep jobs that passed at least one filter
        filtered = [job for job in jobs if job.job_id in kept_ids]

        # Only report reasons for jobs that were removed by ALL filters
        removed_ids = {job.job_id for job in jobs} - kept_ids
        final_reasons = []
        for job in jobs:
            if job.job_id in removed_ids:
                final_reasons.append(
                    f"[{self.get_name()}] Removed '{job.title}' at {job.company}: "
                    f"failed all OR filters"
                )

        return filtered, final_reasons


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class JobFilterPipeline:
    """
    Applies filters in sequence.

    Responsibility: Manages sequential execution of filters with tracking
    of which filter removed each job.
    """

    def __init__(self, filters: Optional[List[JobFilter]] = None):
        """
        Initialize filter pipeline.

        Args:
            filters: List of filters to apply in sequence
        """
        self.filters = filters or []

    def add_filter(self, job_filter: JobFilter) -> None:
        """Add a filter to the pipeline."""
        self.filters.append(job_filter)

    def apply(self, jobs: List[Job], profile: UserProfile) -> Tuple[List[Job], dict]:
        """
        Apply filters sequentially.

        Args:
            jobs: Jobs to filter
            profile: User profile for context

        Returns:
            Tuple of (filtered_jobs, removal_report) where report contains:
                - total_input: number of jobs before filtering
                - total_output: number of jobs after filtering
                - total_removed: number of jobs removed
                - per_filter: dict mapping filter name to count removed
                - reasons: list of all removal reason strings
        """
        if not self.filters:
            return jobs, {
                "total_input": len(jobs),
                "total_output": len(jobs),
                "total_removed": 0,
                "per_filter": {},
                "reasons": [],
            }

        current_jobs = list(jobs)
        all_reasons = []
        per_filter: Dict[str, int] = {}

        logger.info(f"FilterPipeline: starting with {len(current_jobs)} jobs")

        for filt in self.filters:
            before_count = len(current_jobs)
            current_jobs, reasons = filt.apply(current_jobs, profile)
            removed_count = before_count - len(current_jobs)

            if removed_count > 0:
                per_filter[filt.get_name()] = removed_count
                all_reasons.extend(reasons)
                logger.info(
                    f"  {filt.get_name()}: {before_count} -> {len(current_jobs)} "
                    f"({removed_count} removed)"
                )

        total_removed = len(jobs) - len(current_jobs)
        logger.info(
            f"FilterPipeline: {len(jobs)} -> {len(current_jobs)} "
            f"({total_removed} removed total)"
        )

        report = {
            "total_input": len(jobs),
            "total_output": len(current_jobs),
            "total_removed": total_removed,
            "per_filter": per_filter,
            "reasons": all_reasons,
        }

        return current_jobs, report
