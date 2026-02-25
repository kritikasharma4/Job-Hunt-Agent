"""
SQLAlchemy ORM models for the Job Hunting Agent.

Maps domain entities to SQLite tables. Uses JSON columns for list fields
to keep the schema simple (no many-to-many join tables).
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, JSON,
)
from sqlalchemy.orm import relationship
from db.engine import Base


class UserProfileDB(Base):
    """Persisted user profile."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    summary = Column(Text, default="")
    # Location (flattened)
    location_city = Column(String(100), default="")
    location_state = Column(String(100), default="")
    location_country = Column(String(100), default="")
    location_remote = Column(Boolean, default=False)
    # Preferences
    remote_preference = Column(String(20), default="flexible")
    willing_to_relocate = Column(Boolean, default=False)
    preferred_salary_min = Column(Float, nullable=True)
    preferred_salary_max = Column(Float, nullable=True)
    preferred_salary_currency = Column(String(10), default="USD")
    # List fields as JSON
    skills = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    preferred_job_levels = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    work_experiences = relationship(
        "WorkExperienceDB", back_populates="profile", cascade="all, delete-orphan"
    )
    education_entries = relationship(
        "EducationDB", back_populates="profile", cascade="all, delete-orphan"
    )
    applications = relationship(
        "ApplicationDB", back_populates="profile", cascade="all, delete-orphan"
    )


class WorkExperienceDB(Base):
    """Work experience entry linked to a profile."""
    __tablename__ = "work_experiences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    company = Column(String(200), nullable=False)
    position = Column(String(200), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    description = Column(Text, default="")
    skills = Column(JSON, default=list)
    is_current = Column(Boolean, default=False)

    profile = relationship("UserProfileDB", back_populates="work_experiences")


class EducationDB(Base):
    """Education entry linked to a profile."""
    __tablename__ = "education"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    institution = Column(String(200), nullable=False)
    degree = Column(String(200), nullable=False)
    field = Column(String(200), default="")
    graduation_date = Column(DateTime, nullable=True)
    gpa = Column(Float, nullable=True)
    honors = Column(String(500), default="")

    profile = relationship("UserProfileDB", back_populates="education_entries")


class JobDB(Base):
    """Persisted job posting."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    company = Column(String(200), nullable=False)
    description = Column(Text, default="")
    # Location (flattened)
    location_city = Column(String(100), default="")
    location_state = Column(String(100), default="")
    location_country = Column(String(100), default="")
    location_remote = Column(Boolean, default=False)
    # Job details
    requirements = Column(JSON, default=list)
    nice_to_haves = Column(JSON, default=list)
    level = Column(String(20), nullable=True)
    employment_type = Column(String(20), nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), default="USD")
    salary_period = Column(String(20), default="yearly")
    url = Column(String(500), nullable=True)
    source = Column(String(50), default="unknown")
    posted_date = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    matches = relationship("JobMatchDB", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("ApplicationDB", back_populates="job", cascade="all, delete-orphan")


class JobMatchDB(Base):
    """Match result between a profile and a job."""
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    search_id = Column(Integer, ForeignKey("search_history.id"), nullable=True)
    # Scores
    overall_score = Column(Float, nullable=False)
    skills_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    location_score = Column(Float, default=0.0)
    salary_score = Column(Float, default=0.0)
    level_score = Column(Float, default=0.0)
    matching_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    reasoning = Column(Text, default="")
    # Filter info
    passed_filters = Column(Boolean, default=True)
    filter_reasons = Column(JSON, default=list)
    recommendation_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobDB", back_populates="matches")


class ApplicationDB(Base):
    """Job application record."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String(100), unique=True, nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    job_db_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    job_id = Column(String(100), nullable=False)
    job_title = Column(String(300), nullable=False)
    company = Column(String(200), nullable=False)
    applied_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")
    notes = Column(Text, default="")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("UserProfileDB", back_populates="applications")
    job = relationship("JobDB", back_populates="applications")


class SearchHistoryDB(Base):
    """Tracks past job searches."""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False)
    query = Column(String(300), nullable=False)
    location = Column(String(200), nullable=True)
    sources = Column(JSON, default=list)
    results_count = Column(Integer, default=0)
    matches_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
