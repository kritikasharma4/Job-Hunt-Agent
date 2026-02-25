"""Profile management endpoints."""

import uuid
import tempfile
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from db.engine import get_db
from db.repository import ProfileRepository
from api.schemas import ProfileCreate, ProfileResponse, LocationSchema, WorkExperienceSchema, EducationSchema
from models.schemas import (
    UserProfile, Location, Salary, WorkExperience, Education, JobLevel,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _domain_to_response(profile: UserProfile) -> ProfileResponse:
    """Convert domain UserProfile to API response."""
    loc = None
    if profile.location:
        loc = LocationSchema(
            city=profile.location.city or "",
            state=profile.location.state or "",
            country=profile.location.country or "",
            remote=profile.location.remote or False,
        )

    work_exp = [
        WorkExperienceSchema(
            company=w.company or "", position=w.position or "",
            start_date=w.start_date, end_date=w.end_date,
            description=w.description or "", skills=w.skills or [],
            is_current=w.is_current or False,
        )
        for w in profile.work_experience
    ]

    edu = [
        EducationSchema(
            institution=e.institution or "", degree=e.degree or "",
            field=e.field or "", graduation_date=e.graduation_date,
            gpa=e.gpa, honors=e.honors or "",
        )
        for e in profile.education
    ]

    pref_locs = [
        LocationSchema(city=l.city or "", state=l.state or "", country=l.country or "", remote=l.remote or False)
        for l in profile.preferred_locations
    ]

    return ProfileResponse(
        user_id=profile.user_id,
        full_name=profile.full_name or "",
        email=profile.email or "",
        phone=profile.phone or "",
        summary=profile.summary or "",
        location=loc,
        skills=profile.skills or [],
        work_experience=work_exp,
        education=edu,
        certifications=profile.certifications or [],
        preferred_job_levels=[lvl.value for lvl in (profile.preferred_job_levels or [])],
        preferred_locations=pref_locs,
        preferred_salary_min=profile.preferred_salary_range.min_amount if profile.preferred_salary_range else None,
        preferred_salary_max=profile.preferred_salary_range.max_amount if profile.preferred_salary_range else None,
        remote_preference=profile.remote_preference or "flexible",
        willing_to_relocate=profile.willing_to_relocate or False,
    )


def _request_to_domain(data: ProfileCreate, user_id: str = None) -> UserProfile:
    """Convert API request to domain UserProfile."""
    location = None
    if data.location:
        location = Location(
            city=data.location.city, state=data.location.state,
            country=data.location.country, remote=data.location.remote,
        )

    salary = None
    if data.preferred_salary_min is not None or data.preferred_salary_max is not None:
        salary = Salary(min_amount=data.preferred_salary_min, max_amount=data.preferred_salary_max)

    pref_levels = []
    for lvl in data.preferred_job_levels:
        try:
            pref_levels.append(JobLevel(lvl))
        except ValueError:
            pass

    pref_locations = [
        Location(city=l.city, state=l.state, country=l.country, remote=l.remote)
        for l in data.preferred_locations
    ]

    work_exp = [
        WorkExperience(
            company=w.company, position=w.position,
            start_date=w.start_date, end_date=w.end_date,
            description=w.description, skills=w.skills,
            is_current=w.is_current,
        )
        for w in data.work_experience
    ]

    edu = [
        Education(
            institution=e.institution, degree=e.degree,
            field=e.field, graduation_date=e.graduation_date,
            gpa=e.gpa, honors=e.honors,
        )
        for e in data.education
    ]

    return UserProfile(
        user_id=user_id or str(uuid.uuid4()),
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        summary=data.summary,
        location=location,
        skills=data.skills,
        work_experience=work_exp,
        education=edu,
        certifications=data.certifications,
        preferred_job_levels=pref_levels,
        preferred_locations=pref_locations,
        preferred_salary_range=salary,
        willing_to_relocate=data.willing_to_relocate,
        remote_preference=data.remote_preference,
    )


@router.post("", response_model=ProfileResponse)
def create_profile(data: ProfileCreate, db: Session = Depends(get_db)):
    """Create a new user profile."""
    profile = _request_to_domain(data)
    ProfileRepository.save_profile(db, profile)
    return _domain_to_response(profile)


@router.post("/upload", response_model=ProfileResponse)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a resume file (PDF/JSON/TXT) and auto-parse into a profile."""
    allowed = {".pdf", ".json", ".txt", ".md", ".rst"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {allowed}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = file.file.read()
            tmp.write(content)
            tmp_path = tmp.name

        from profile.parser import ProfileParserFactory
        from config.settings import LLMConfig

        # Try to set up Ollama for PDF/text parsing
        try:
            from llm.ollama_provider import OllamaProvider
            ollama_config = LLMConfig(provider="ollama", model="llama3", timeout=60)
            provider = OllamaProvider(ollama_config)
            if provider.validate_credentials():
                ProfileParserFactory.create_with_llm(provider)
                logger.info("Ollama connected for resume parsing")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")

        profile = ProfileParserFactory.parse_profile(tmp_path)

        ProfileRepository.save_profile(db, profile)
        return _domain_to_response(profile)

    except Exception as e:
        logger.error(f"Resume upload failed: {e}")
        raise HTTPException(400, f"Failed to parse resume: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/current", response_model=ProfileResponse)
def get_current_profile(db: Session = Depends(get_db)):
    """Get the current (first) profile. For single-user mode."""
    profile = ProfileRepository.get_first_profile(db)
    if not profile:
        raise HTTPException(404, "No profile found. Create one first.")
    return _domain_to_response(profile)


@router.get("/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: str, db: Session = Depends(get_db)):
    """Get a profile by user_id."""
    profile = ProfileRepository.get_profile(db, user_id)
    if not profile:
        raise HTTPException(404, f"Profile not found: {user_id}")
    return _domain_to_response(profile)


@router.put("/{user_id}", response_model=ProfileResponse)
def update_profile(user_id: str, data: ProfileCreate, db: Session = Depends(get_db)):
    """Update an existing profile."""
    existing = ProfileRepository.get_profile(db, user_id)
    if not existing:
        raise HTTPException(404, f"Profile not found: {user_id}")

    updated = _request_to_domain(data, user_id=user_id)
    ProfileRepository.save_profile(db, updated)
    return _domain_to_response(updated)
