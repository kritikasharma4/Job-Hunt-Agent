"""
Data models and schemas for job, profile, and matching results.

Defines the domain models used throughout the application following the
Single Responsibility Principle - each model represents a single concept.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobLevel(Enum):
    """Job seniority levels."""

    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class EmploymentType(Enum):
    """Types of employment."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"


@dataclass
class Location:
    """Represents a geographic location."""

    city: str
    state: str
    country: str
    remote: bool = False

    def __str__(self) -> str:
        if self.remote:
            return "Remote"
        return f"{self.city}, {self.state}, {self.country}"


@dataclass
class Salary:
    """Represents a salary range."""

    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "USD"
    period: str = "yearly"  # yearly, hourly, etc.


@dataclass
class Job:
    """
    Represents a job posting.

    Responsibility: Encapsulates all job-related data from various sources.
    """

    job_id: str
    title: str
    company: str
    description: str
    location: Location
    requirements: List[str]
    nice_to_haves: List[str] = field(default_factory=list)
    level: Optional[JobLevel] = None
    employment_type: Optional[EmploymentType] = None
    salary: Optional[Salary] = None
    url: Optional[str] = None
    source: str = "unknown"  # 'linkedin', 'indeed', 'builtin', etc.
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkExperience:
    """Represents professional work experience."""

    company: str
    position: str
    start_date: datetime
    end_date: Optional[datetime] = None
    description: str = ""
    skills: List[str] = field(default_factory=list)
    is_current: bool = False


@dataclass
class Education:
    """Represents educational background."""

    institution: str
    degree: str
    field: str
    graduation_date: Optional[datetime] = None
    gpa: Optional[float] = None
    honors: str = ""


@dataclass
class UserProfile:
    """
    Represents a user's professional profile.

    Responsibility: Encapsulates all user/candidate profile data.
    """

    user_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    summary: str = ""
    location: Optional[Location] = None
    skills: List[str] = field(default_factory=list)
    work_experience: List[WorkExperience] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    preferred_job_levels: List[JobLevel] = field(default_factory=list)
    preferred_locations: List[Location] = field(default_factory=list)
    preferred_salary_range: Optional[Salary] = None
    willing_to_relocate: bool = False
    remote_preference: str = "flexible"  # 'required', 'preferred', 'flexible', 'not_interested'
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_years_of_experience(self) -> float:
        """Calculate total years of professional experience."""
        if not self.work_experience:
            return 0.0

        total_days = 0
        for exp in self.work_experience:
            end = exp.end_date if exp.end_date and not exp.is_current else datetime.now()
            duration = (end - exp.start_date).days
            if duration > 0:
                total_days += duration

        return round(total_days / 365.25, 1)


@dataclass
class RelevanceScore:
    """
    Represents relevance matching results between a job and profile.

    Responsibility: Encapsulates scoring results with component breakdowns.
    """

    overall_score: float  # 0.0 to 1.0
    skills_score: float
    experience_score: float
    location_score: float
    salary_score: float
    level_score: float
    matching_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobMatch:
    """
    Represents a matched job opportunity with relevance scores.

    Responsibility: Combines job data with relevance analysis.
    """

    job: Job
    relevance_score: RelevanceScore
    passed_filters: bool = True
    filter_reasons: List[str] = field(default_factory=list)
    recommendation_text: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ApplicationRecord:
    """
    Tracks a job application.

    Responsibility: Records application history and status.
    """

    application_id: str
    user_id: str
    job_id: str
    job_title: str
    company: str
    applied_date: datetime
    status: str = "pending"  # pending, accepted, rejected, interview, offer
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
