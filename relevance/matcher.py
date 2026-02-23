"""
Job and profile relevance matching.

Scores the compatibility between user profiles and job opportunities using
skill overlap, experience alignment, LLM semantic analysis, and hybrid
weighted combinations.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from models.schemas import Job, UserProfile, RelevanceScore, JobLevel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Expected experience ranges per job level
# ---------------------------------------------------------------------------

LEVEL_YEAR_RANGES: Dict[JobLevel, tuple] = {
    JobLevel.ENTRY: (0, 2),
    JobLevel.JUNIOR: (1, 3),
    JobLevel.MID: (3, 6),
    JobLevel.SENIOR: (5, 10),
    JobLevel.LEAD: (8, 15),
    JobLevel.EXECUTIVE: (12, 30),
}


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _extract_skills_from_text(text: str, known_skills: List[str]) -> List[str]:
    """Find which known skills appear in a block of text."""
    text_lower = _normalize(text)
    found = []
    for skill in known_skills:
        skill_lower = _normalize(skill)
        if skill_lower and skill_lower in text_lower:
            found.append(skill)
    return found


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class RelevanceMatcher(ABC):
    """
    Abstract base class for relevance matching algorithms.

    Responsibility: Defines interface for comparing user profiles with job postings
    to produce relevance scores. Implements Strategy Pattern for different matching approaches.
    """

    @abstractmethod
    def match(self, profile: UserProfile, job: Job) -> RelevanceScore:
        """
        Calculate relevance score between profile and job.

        Args:
            profile: User profile to match
            job: Job posting to match against

        Returns:
            RelevanceScore with component breakdowns and matching analysis

        Raises:
            ValueError: If profile or job data is invalid
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get name/identifier for this matcher."""
        pass


# ---------------------------------------------------------------------------
# Skill-based matcher
# ---------------------------------------------------------------------------

class SkillBasedMatcher(RelevanceMatcher):
    """
    Matches profiles and jobs based on skill overlap.

    Responsibility: Compares required/preferred skills against user's skills,
    calculating score based on match percentage and weight.
    """

    def match(self, profile: UserProfile, job: Job) -> RelevanceScore:
        """
        Match based on skill alignment.

        Compares user skills against job requirements and nice-to-haves.
        Requirements matched count fully; nice-to-haves count at 50% weight.
        Also scans the job description for skill mentions.
        """
        user_skills = {_normalize(s) for s in profile.skills if s.strip()}

        # Collect all job-side skills
        required = {_normalize(r) for r in job.requirements if r.strip()}
        nice_to_have = {_normalize(n) for n in job.nice_to_haves if n.strip()}

        # Also look for user skills mentioned in the job description
        desc_skills = {
            _normalize(s)
            for s in _extract_skills_from_text(job.description, profile.skills)
        }
        # Merge description-found skills into required if not already there
        required = required | (desc_skills - nice_to_have)

        all_job_skills = required | nice_to_have

        if not all_job_skills:
            return RelevanceScore(
                overall_score=0.5,
                skills_score=0.5,
                experience_score=0.0,
                location_score=0.0,
                salary_score=0.0,
                level_score=0.0,
                matching_skills=list(user_skills)[:10],
                missing_skills=[],
                reasoning="No specific skills listed in job posting; neutral score assigned.",
                metadata={"matcher": self.get_name()},
            )

        # Matching
        matched_required = user_skills & required
        matched_nice = user_skills & nice_to_have
        missing = (required | nice_to_have) - user_skills

        # Score: required matches count 100%, nice-to-have at 50%
        total_weight = len(required) + len(nice_to_have) * 0.5
        matched_weight = len(matched_required) + len(matched_nice) * 0.5
        skills_score = matched_weight / total_weight if total_weight > 0 else 0.0
        skills_score = min(skills_score, 1.0)

        # Restore original casing for output
        matching_skills_original = [
            s for s in profile.skills if _normalize(s) in (matched_required | matched_nice)
        ]
        missing_skills_original = [
            s for s in (list(job.requirements) + list(job.nice_to_haves))
            if _normalize(s) in missing
        ]

        reasoning = (
            f"Matched {len(matched_required)}/{len(required)} required skills"
            f" and {len(matched_nice)}/{len(nice_to_have)} nice-to-haves."
        )

        return RelevanceScore(
            overall_score=skills_score,
            skills_score=skills_score,
            experience_score=0.0,
            location_score=0.0,
            salary_score=0.0,
            level_score=0.0,
            matching_skills=matching_skills_original,
            missing_skills=missing_skills_original,
            reasoning=reasoning,
            metadata={"matcher": self.get_name()},
        )

    def get_name(self) -> str:
        return "skill_based"


# ---------------------------------------------------------------------------
# Experience matcher
# ---------------------------------------------------------------------------

class ExperienceMatcher(RelevanceMatcher):
    """
    Matches profiles and jobs based on experience level and background.

    Responsibility: Evaluates whether user's experience aligns with job requirements
    in terms of years, job level, location preference, and salary range.
    """

    def match(self, profile: UserProfile, job: Job) -> RelevanceScore:
        """
        Match based on experience, level, location, and salary alignment.
        """
        experience_score = self._score_experience(profile, job)
        level_score = self._score_level(profile, job)
        location_score = self._score_location(profile, job)
        salary_score = self._score_salary(profile, job)

        # Weighted average for overall
        overall = (
            experience_score * 0.35
            + level_score * 0.25
            + location_score * 0.25
            + salary_score * 0.15
        )

        parts = []
        if experience_score > 0:
            parts.append(f"experience={experience_score:.2f}")
        if level_score > 0:
            parts.append(f"level={level_score:.2f}")
        if location_score > 0:
            parts.append(f"location={location_score:.2f}")
        if salary_score > 0:
            parts.append(f"salary={salary_score:.2f}")
        reasoning = f"Experience match: {', '.join(parts) or 'insufficient data'}."

        return RelevanceScore(
            overall_score=round(overall, 3),
            skills_score=0.0,
            experience_score=round(experience_score, 3),
            location_score=round(location_score, 3),
            salary_score=round(salary_score, 3),
            level_score=round(level_score, 3),
            matching_skills=[],
            missing_skills=[],
            reasoning=reasoning,
            metadata={"matcher": self.get_name()},
        )

    def get_name(self) -> str:
        return "experience"

    @staticmethod
    def _score_experience(profile: UserProfile, job: Job) -> float:
        """Score how well user's years of experience fit the job level."""
        years = profile.get_years_of_experience()
        if not job.level:
            return 0.5 if years > 0 else 0.3

        expected = LEVEL_YEAR_RANGES.get(job.level, (0, 30))
        min_y, max_y = expected

        if min_y <= years <= max_y:
            return 1.0
        elif years < min_y:
            gap = min_y - years
            return max(0.0, 1.0 - gap * 0.2)
        else:
            gap = years - max_y
            return max(0.3, 1.0 - gap * 0.1)

    @staticmethod
    def _score_level(profile: UserProfile, job: Job) -> float:
        """Score job level match against user's preferred levels."""
        if not job.level:
            return 0.5
        if not profile.preferred_job_levels:
            return 0.5

        if job.level in profile.preferred_job_levels:
            return 1.0

        all_levels = list(JobLevel)
        job_idx = all_levels.index(job.level)
        for pref in profile.preferred_job_levels:
            pref_idx = all_levels.index(pref)
            distance = abs(job_idx - pref_idx)
            if distance == 1:
                return 0.7
            if distance == 2:
                return 0.4

        return 0.1

    @staticmethod
    def _score_location(profile: UserProfile, job: Job) -> float:
        """Score location compatibility."""
        if not job.location:
            return 0.5

        if job.location.remote:
            if profile.remote_preference in ("required", "preferred"):
                return 1.0
            elif profile.remote_preference == "flexible":
                return 0.8
            else:
                return 0.5

        if not profile.preferred_locations:
            if profile.willing_to_relocate:
                return 0.6
            return 0.4

        job_city = job.location.city.lower().strip()
        job_state = job.location.state.lower().strip()

        for pref_loc in profile.preferred_locations:
            if pref_loc.city.lower().strip() == job_city:
                return 1.0
            if pref_loc.state.lower().strip() == job_state:
                return 0.7

        if profile.willing_to_relocate:
            return 0.4
        return 0.1

    @staticmethod
    def _score_salary(profile: UserProfile, job: Job) -> float:
        """Score salary range compatibility."""
        if not job.salary or not profile.preferred_salary_range:
            return 0.5

        job_sal = job.salary
        pref = profile.preferred_salary_range

        if not job_sal.min_amount and not job_sal.max_amount:
            return 0.5
        if not pref.min_amount and not pref.max_amount:
            return 0.5

        job_min = job_sal.min_amount or 0
        job_max = job_sal.max_amount or float("inf")
        pref_min = pref.min_amount or 0
        pref_max = pref.max_amount or float("inf")

        if job_max < pref_min:
            gap_pct = (pref_min - job_max) / pref_min if pref_min > 0 else 0
            return max(0.0, 1.0 - gap_pct * 2)
        elif job_min > pref_max and pref_max != float("inf"):
            return 0.9
        else:
            return 1.0


# ---------------------------------------------------------------------------
# LLM-based matcher
# ---------------------------------------------------------------------------

class LLMBasedMatcher(RelevanceMatcher):
    """
    Uses LLM to intelligently match profiles and jobs.

    Responsibility: Leverages language models for nuanced matching that considers
    context, transferable skills, growth potential, and non-obvious connections.
    """

    SCORING_SCHEMA = {
        "overall_score": "float 0.0-1.0 - overall match quality",
        "skills_score": "float 0.0-1.0 - technical skill alignment",
        "experience_score": "float 0.0-1.0 - experience level fit",
        "location_score": "float 0.0-1.0 - location compatibility",
        "salary_score": "float 0.0-1.0 - compensation alignment",
        "level_score": "float 0.0-1.0 - seniority level fit",
        "matching_skills": ["string - skills the candidate has that match"],
        "missing_skills": ["string - skills the candidate lacks"],
        "reasoning": "string - 2-3 sentence explanation of the match quality",
    }

    SYSTEM_PROMPT = (
        "You are an expert recruiter and job matching specialist. "
        "Evaluate how well a candidate's profile matches a job posting. "
        "Consider direct skill matches, transferable skills, career trajectory, "
        "and growth potential. Be realistic — a 0.8+ score means an excellent match. "
        "All scores must be between 0.0 and 1.0."
    )

    def __init__(self, llm_provider):
        """
        Initialize LLM-based matcher.

        Args:
            llm_provider: LLM provider instance for scoring
        """
        self.llm_provider = llm_provider

    def match(self, profile: UserProfile, job: Job) -> RelevanceScore:
        """
        Match using LLM analysis.

        Sends profile summary and job details to the LLM for nuanced scoring.
        """
        prompt = self._build_prompt(profile, job)

        try:
            data = self.llm_provider.generate_with_structured_output(
                prompt=prompt,
                output_schema=self.SCORING_SCHEMA,
                system_prompt=self.SYSTEM_PROMPT,
            )
            return self._parse_response(data)
        except (ConnectionError, RuntimeError, ValueError) as e:
            logger.error(f"LLM matching failed: {e}")
            return RelevanceScore(
                overall_score=0.5,
                skills_score=0.5,
                experience_score=0.5,
                location_score=0.5,
                salary_score=0.5,
                level_score=0.5,
                reasoning=f"LLM analysis unavailable: {e}",
                metadata={"matcher": self.get_name(), "error": str(e)},
            )

    def get_name(self) -> str:
        return "llm_based"

    def _build_prompt(self, profile: UserProfile, job: Job) -> str:
        """Build the matching prompt for the LLM."""
        skills_str = ", ".join(profile.skills[:20]) if profile.skills else "None listed"
        years = profile.get_years_of_experience()

        exp_lines = []
        for exp in profile.work_experience[:5]:
            exp_lines.append(f"- {exp.position} at {exp.company}")
        exp_str = "\n".join(exp_lines) if exp_lines else "No work experience listed"

        edu_lines = []
        for edu in profile.education[:3]:
            edu_lines.append(f"- {edu.degree} in {edu.field} from {edu.institution}")
        edu_str = "\n".join(edu_lines) if edu_lines else "No education listed"

        reqs_str = ", ".join(job.requirements[:15]) if job.requirements else "Not specified"
        location_str = str(job.location) if job.location else "Not specified"
        level_str = job.level.value if job.level else "Not specified"
        salary_str = "Not specified"
        if job.salary:
            parts = []
            if job.salary.min_amount:
                parts.append(f"${job.salary.min_amount:,.0f}")
            if job.salary.max_amount:
                parts.append(f"${job.salary.max_amount:,.0f}")
            if parts:
                salary_str = " - ".join(parts) + f" {job.salary.period}"

        return (
            f"## Candidate Profile\n"
            f"Name: {profile.full_name}\n"
            f"Summary: {profile.summary or 'N/A'}\n"
            f"Skills: {skills_str}\n"
            f"Years of Experience: {years}\n"
            f"Work History:\n{exp_str}\n"
            f"Education:\n{edu_str}\n\n"
            f"## Job Posting\n"
            f"Title: {job.title}\n"
            f"Company: {job.company}\n"
            f"Location: {location_str}\n"
            f"Level: {level_str}\n"
            f"Salary: {salary_str}\n"
            f"Requirements: {reqs_str}\n"
            f"Description: {job.description[:500] if job.description else 'N/A'}\n\n"
            f"Rate how well this candidate matches this job."
        )

    @staticmethod
    def _parse_response(data: Dict[str, Any]) -> RelevanceScore:
        """Parse LLM response dict into RelevanceScore."""

        def _clamp(val, default=0.5) -> float:
            try:
                v = float(val)
                return max(0.0, min(1.0, v))
            except (TypeError, ValueError):
                return default

        matching = data.get("matching_skills", [])
        if not isinstance(matching, list):
            matching = []
        missing = data.get("missing_skills", [])
        if not isinstance(missing, list):
            missing = []

        return RelevanceScore(
            overall_score=_clamp(data.get("overall_score", 0.5)),
            skills_score=_clamp(data.get("skills_score", 0.5)),
            experience_score=_clamp(data.get("experience_score", 0.5)),
            location_score=_clamp(data.get("location_score", 0.5)),
            salary_score=_clamp(data.get("salary_score", 0.5)),
            level_score=_clamp(data.get("level_score", 0.5)),
            matching_skills=[str(s) for s in matching if s],
            missing_skills=[str(s) for s in missing if s],
            reasoning=str(data.get("reasoning", "")),
            metadata={"matcher": "llm_based"},
        )


# ---------------------------------------------------------------------------
# Hybrid matcher
# ---------------------------------------------------------------------------

class HybridMatcher(RelevanceMatcher):
    """
    Combines multiple matching strategies for comprehensive scoring.

    Responsibility: Orchestrates multiple matchers and combines their scores
    using configurable weights for balanced relevance assessment.
    """

    def __init__(
        self,
        matchers: Optional[list] = None,
        weights: Optional[dict] = None
    ):
        """
        Initialize hybrid matcher.

        Args:
            matchers: List of RelevanceMatcher instances to combine
            weights: Weights keyed by matcher.get_name(). Defaults to equal weights.
        """
        self.matchers: List[RelevanceMatcher] = matchers or []
        self.weights: Dict[str, float] = weights or {}

    def match(self, profile: UserProfile, job: Job) -> RelevanceScore:
        """
        Match using all child matchers, then combine with weighted average.
        """
        if not self.matchers:
            raise ValueError("HybridMatcher has no matchers. Call add_matcher() first.")

        results: List[tuple] = []  # (weight, RelevanceScore)

        for matcher in self.matchers:
            try:
                score = matcher.match(profile, job)
                weight = self.weights.get(matcher.get_name(), 1.0)
                results.append((weight, score))
                logger.debug(
                    f"  {matcher.get_name()}: overall={score.overall_score:.3f} "
                    f"(weight={weight})"
                )
            except Exception as e:
                logger.warning(f"Matcher {matcher.get_name()} failed: {e}")
                continue

        if not results:
            raise RuntimeError("All matchers failed")

        return self._combine_scores(results)

    def get_name(self) -> str:
        return "hybrid"

    def add_matcher(self, matcher: RelevanceMatcher, weight: float = 1.0) -> None:
        """Add a matcher to the hybrid matcher."""
        self.matchers.append(matcher)
        self.weights[matcher.get_name()] = weight

    @staticmethod
    def _combine_scores(results: List[tuple]) -> RelevanceScore:
        """Combine multiple weighted RelevanceScores into one."""
        total_weight = sum(w for w, _ in results)
        if total_weight == 0:
            total_weight = 1.0

        def _wavg(attr: str) -> float:
            val = sum(w * getattr(s, attr) for w, s in results) / total_weight
            return round(val, 3)

        # Merge skills lists (deduplicated, preserving order)
        matching = []
        seen_m = set()
        missing = []
        seen_x = set()
        reasoning_parts = []

        for _, score in results:
            for s in score.matching_skills:
                if s not in seen_m:
                    matching.append(s)
                    seen_m.add(s)
            for s in score.missing_skills:
                if s not in seen_x:
                    missing.append(s)
                    seen_x.add(s)
            if score.reasoning:
                reasoning_parts.append(score.reasoning)

        # Remove from missing anything that appeared in matching
        missing = [s for s in missing if s not in seen_m]

        return RelevanceScore(
            overall_score=_wavg("overall_score"),
            skills_score=_wavg("skills_score"),
            experience_score=_wavg("experience_score"),
            location_score=_wavg("location_score"),
            salary_score=_wavg("salary_score"),
            level_score=_wavg("level_score"),
            matching_skills=matching,
            missing_skills=missing,
            reasoning=" | ".join(reasoning_parts),
            metadata={
                "matcher": "hybrid",
                "sub_matchers": [
                    score.metadata.get("matcher", "unknown")
                    for _, score in results
                ],
            },
        )


# ---------------------------------------------------------------------------
# Scorer facade
# ---------------------------------------------------------------------------

class RelevanceScorer:
    """
    Orchestrates relevance matching process.

    Responsibility: Manages matcher selection, execution, and result processing.
    Acts as facade for the relevance matching subsystem.
    """

    def __init__(self, matcher: RelevanceMatcher):
        """
        Initialize scorer with a matcher.

        Args:
            matcher: RelevanceMatcher to use for scoring
        """
        self.matcher = matcher

    def score_job(self, profile: UserProfile, job: Job) -> RelevanceScore:
        """
        Score a job for a profile.

        Args:
            profile: User profile
            job: Job posting

        Returns:
            RelevanceScore
        """
        try:
            score = self.matcher.match(profile, job)
            logger.info(
                f"Scored '{job.title}' at {job.company}: "
                f"overall={score.overall_score:.3f}"
            )
            return score
        except Exception as e:
            logger.error(f"Failed to score job '{job.title}': {e}")
            raise

    def score_jobs(self, profile: UserProfile, jobs: List[Job]) -> List[RelevanceScore]:
        """
        Score multiple jobs and return results in the same order.

        Args:
            profile: User profile
            jobs: List of jobs to score

        Returns:
            List of RelevanceScores (one per job)
        """
        scores = []
        for job in jobs:
            try:
                scores.append(self.score_job(profile, job))
            except Exception as e:
                logger.warning(f"Skipping job '{job.title}': {e}")
                scores.append(RelevanceScore(
                    overall_score=0.0,
                    skills_score=0.0,
                    experience_score=0.0,
                    location_score=0.0,
                    salary_score=0.0,
                    level_score=0.0,
                    reasoning=f"Scoring failed: {e}",
                ))
        return scores

    def set_matcher(self, matcher: RelevanceMatcher) -> None:
        """Change the matcher strategy."""
        self.matcher = matcher
        logger.info(f"Switched matcher to: {matcher.get_name()}")
