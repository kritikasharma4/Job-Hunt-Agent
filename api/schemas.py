"""
Pydantic request/response models for the FastAPI endpoints.

Separate from domain dataclasses (models/schemas.py) and ORM models (db/models.py).
"""

from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class LocationSchema(BaseModel):
    city: str = ""
    state: str = ""
    country: str = ""
    remote: bool = False


class SalarySchema(BaseModel):
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "USD"
    period: str = "yearly"


class WorkExperienceSchema(BaseModel):
    company: str
    position: str
    start_date: datetime
    end_date: Optional[datetime] = None
    description: str = ""
    skills: List[str] = []
    is_current: bool = False


class EducationSchema(BaseModel):
    institution: str
    degree: str
    field: str = ""
    graduation_date: Optional[datetime] = None
    gpa: Optional[float] = None
    honors: str = ""


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class ProfileCreate(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    summary: str = ""
    location: Optional[LocationSchema] = None
    skills: List[str] = []
    work_experience: List[WorkExperienceSchema] = []
    education: List[EducationSchema] = []
    certifications: List[str] = []
    preferred_job_levels: List[str] = []
    preferred_locations: List[LocationSchema] = []
    preferred_salary_min: Optional[float] = None
    preferred_salary_max: Optional[float] = None
    remote_preference: str = "flexible"
    willing_to_relocate: bool = False


class ProfileResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    summary: str = ""
    location: Optional[LocationSchema] = None
    skills: List[str] = []
    work_experience: List[WorkExperienceSchema] = []
    education: List[EducationSchema] = []
    certifications: List[str] = []
    preferred_job_levels: List[str] = []
    preferred_locations: List[LocationSchema] = []
    preferred_salary_min: Optional[float] = None
    preferred_salary_max: Optional[float] = None
    remote_preference: str = "flexible"
    willing_to_relocate: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobResponse(BaseModel):
    job_id: str
    title: str
    company: str
    description: str = ""
    location: LocationSchema = LocationSchema()
    requirements: List[str] = []
    nice_to_haves: List[str] = []
    level: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[SalarySchema] = None
    url: Optional[str] = None
    source: str = "unknown"
    posted_date: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Score & Match
# ---------------------------------------------------------------------------

class ScoreResponse(BaseModel):
    overall_score: float
    skills_score: float = 0.0
    experience_score: float = 0.0
    location_score: float = 0.0
    salary_score: float = 0.0
    level_score: float = 0.0
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    reasoning: str = ""


class MatchResponse(BaseModel):
    id: int
    job: JobResponse
    score: ScoreResponse
    passed_filters: bool = True
    filter_reasons: List[str] = []
    recommendation_text: str = ""
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    location: Optional[str] = None
    sources: Optional[List[str]] = None
    min_score: float = 0.3
    experience_level: Optional[str] = None       # entry, mid, senior, lead
    employment_type: Optional[str] = None         # fulltime, parttime, contract, intern
    date_posted: Optional[str] = None             # all, today, 3days, week, month
    remote_only: bool = False


class SearchResponse(BaseModel):
    search_id: int
    query: str
    total_fetched: int
    total_matched: int
    matches: List[MatchResponse]


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class ApplicationCreate(BaseModel):
    job_id: str
    notes: str = ""


class ApplicationResponse(BaseModel):
    application_id: str
    job_id: str
    job_title: str
    company: str
    applied_date: Optional[datetime] = None
    status: str = "pending"
    notes: str = ""

    model_config = {"from_attributes": True}


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    total_searches: int = 0
    total_jobs_found: int = 0
    total_matches: int = 0
    total_applications: int = 0
    applications_by_status: Dict[str, int] = {}
    avg_match_score: float = 0.0
    recent_matches: List[MatchResponse] = []
