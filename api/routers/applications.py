"""Application tracking endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.engine import get_db
from db.repository import ProfileRepository, ApplicationRepository, JobRepository
from api.schemas import ApplicationCreate, ApplicationResponse, ApplicationStatusUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


def _db_to_response(app_db) -> ApplicationResponse:
    return ApplicationResponse(
        application_id=app_db.application_id,
        job_id=app_db.job_id,
        job_title=app_db.job_title,
        company=app_db.company,
        applied_date=app_db.applied_date,
        status=app_db.status,
        notes=app_db.notes or "",
    )


@router.post("", response_model=ApplicationResponse)
def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    """Create a job application."""
    profile_db = ProfileRepository.get_first_profile_db(db)
    if not profile_db:
        raise HTTPException(400, "No profile found. Create a profile first.")

    # Look up the job
    job_db = JobRepository.get_job_db(db, data.job_id)
    if not job_db:
        raise HTTPException(404, f"Job not found: {data.job_id}")

    app_db = ApplicationRepository.save_application(
        db,
        profile_db_id=profile_db.id,
        job_id_str=data.job_id,
        job_title=job_db.title,
        company=job_db.company,
        job_db_id=job_db.id,
        notes=data.notes,
    )
    return _db_to_response(app_db)


@router.get("", response_model=list)
def list_applications(status: Optional[str] = None, skip: int = 0,
                      limit: int = 50, db: Session = Depends(get_db)):
    """List applications with optional status filter."""
    profile_db = ProfileRepository.get_first_profile_db(db)
    if not profile_db:
        return []

    apps = ApplicationRepository.list_applications(
        db, profile_db.id, status=status, skip=skip, limit=limit
    )
    return [_db_to_response(a) for a in apps]


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: str, db: Session = Depends(get_db)):
    """Get a single application."""
    app_db = ApplicationRepository.get_application(db, application_id)
    if not app_db:
        raise HTTPException(404, f"Application not found: {application_id}")
    return _db_to_response(app_db)


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application_status(application_id: str,
                              data: ApplicationStatusUpdate,
                              db: Session = Depends(get_db)):
    """Update application status."""
    try:
        app_db = ApplicationRepository.update_status(
            db, application_id, data.status, data.notes
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    if not app_db:
        raise HTTPException(404, f"Application not found: {application_id}")
    return _db_to_response(app_db)


@router.delete("/{application_id}")
def delete_application(application_id: str, db: Session = Depends(get_db)):
    """Delete an application."""
    deleted = ApplicationRepository.delete_application(db, application_id)
    if not deleted:
        raise HTTPException(404, f"Application not found: {application_id}")
    return {"status": "deleted", "application_id": application_id}
