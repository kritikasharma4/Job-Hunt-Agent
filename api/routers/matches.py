"""Match results endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.engine import get_db
from db.repository import ProfileRepository, MatchRepository, SearchHistoryRepository
from api.schemas import MatchResponse, DashboardStats
from api.routers.jobs import _match_dict_to_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list)
def list_matches(min_score: float = 0.0, skip: int = 0, limit: int = 50,
                 db: Session = Depends(get_db)):
    """List match results for the current profile."""
    profile_db = ProfileRepository.get_first_profile_db(db)
    if not profile_db:
        raise HTTPException(400, "No profile found.")

    matches = MatchRepository.list_matches(
        db, profile_db.id, min_score=min_score, skip=skip, limit=limit
    )
    return [_match_dict_to_response(m) for m in matches]


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregate dashboard statistics."""
    profile_db = ProfileRepository.get_first_profile_db(db)
    if not profile_db:
        return DashboardStats()

    from db.repository import ApplicationRepository, JobRepository

    total_searches = SearchHistoryRepository.count_searches(db, profile_db.id)
    total_jobs = JobRepository.count_jobs(db)
    total_matches = MatchRepository.count_matches(db, profile_db.id)
    total_apps = ApplicationRepository.count_applications(db, profile_db.id)
    apps_by_status = ApplicationRepository.count_by_status(db, profile_db.id)
    avg_score = MatchRepository.avg_score(db, profile_db.id)

    recent = MatchRepository.list_matches(db, profile_db.id, skip=0, limit=5)
    recent_responses = [_match_dict_to_response(m) for m in recent]

    return DashboardStats(
        total_searches=total_searches,
        total_jobs_found=total_jobs,
        total_matches=total_matches,
        total_applications=total_apps,
        applications_by_status=apps_by_status,
        avg_match_score=avg_score,
        recent_matches=recent_responses,
    )


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, db: Session = Depends(get_db)):
    """Get a single match by ID."""
    match = MatchRepository.get_match(db, match_id)
    if not match:
        raise HTTPException(404, f"Match not found: {match_id}")
    return _match_dict_to_response(match)


@router.delete("/{match_id}")
def delete_match(match_id: int, db: Session = Depends(get_db)):
    """Dismiss/delete a match."""
    deleted = MatchRepository.delete_match(db, match_id)
    if not deleted:
        raise HTTPException(404, f"Match not found: {match_id}")
    return {"status": "deleted", "match_id": match_id}
