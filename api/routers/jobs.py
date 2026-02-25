"""Job search and listing endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.engine import get_db
from db.repository import (
    ProfileRepository, JobRepository, MatchRepository, SearchHistoryRepository,
)
from api.schemas import (
    SearchRequest, SearchResponse, MatchResponse, JobResponse,
    ScoreResponse, LocationSchema, SalarySchema,
)
from api.dependencies import get_settings, build_agent
from models.schemas import Job

logger = logging.getLogger(__name__)
router = APIRouter()


def _job_to_response(job: Job) -> JobResponse:
    """Convert domain Job to API response."""
    loc = LocationSchema(
        city=job.location.city if job.location else "",
        state=job.location.state if job.location else "",
        country=job.location.country if job.location else "",
        remote=job.location.remote if job.location else False,
    )
    salary = None
    if job.salary:
        salary = SalarySchema(
            min_amount=job.salary.min_amount,
            max_amount=job.salary.max_amount,
            currency=job.salary.currency,
            period=job.salary.period,
        )
    return JobResponse(
        job_id=job.job_id,
        title=job.title,
        company=job.company,
        description=job.description,
        location=loc,
        requirements=job.requirements,
        nice_to_haves=job.nice_to_haves,
        level=job.level.value if job.level else None,
        employment_type=job.employment_type.value if job.employment_type else None,
        salary=salary,
        url=job.url,
        source=job.source,
        posted_date=job.posted_date,
    )


def _match_dict_to_response(match_dict: dict) -> MatchResponse:
    """Convert repository match dict to API response."""
    return MatchResponse(
        id=match_dict["id"],
        job=_job_to_response(match_dict["job"]),
        score=ScoreResponse(**match_dict["score"]),
        passed_filters=match_dict["passed_filters"],
        filter_reasons=match_dict["filter_reasons"],
        recommendation_text=match_dict["recommendation_text"],
        created_at=match_dict["created_at"],
    )


@router.post("/search", response_model=SearchResponse)
def search_jobs(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Trigger the full pipeline: fetch jobs → score → filter → rank.
    Persists results to the database.
    """
    # Get the current profile
    profile_db = ProfileRepository.get_first_profile_db(db)
    if not profile_db:
        raise HTTPException(400, "No profile found. Create a profile first.")

    profile = ProfileRepository.get_first_profile(db)

    # Build agent and run pipeline
    settings = get_settings()
    settings.relevance.min_relevance_score = request.min_score
    sources = request.sources or settings.job_fetcher.enabled_sources
    settings.job_fetcher.enabled_sources = sources
    agent = build_agent(settings)

    # Set profile directly (bypass file-based load_profile)
    agent.user_profile = profile

    # Build extra filters for fetchers
    search_filters = {}
    if request.experience_level:
        search_filters["experience_level"] = request.experience_level
    if request.employment_type:
        search_filters["employment_type"] = request.employment_type
    if request.date_posted:
        search_filters["date_posted"] = request.date_posted
    if request.remote_only:
        search_filters["remote_only"] = True

    # Prepend experience level to query for better API results
    search_query = request.query
    if request.experience_level and request.experience_level != "all":
        search_query = f"{request.experience_level} {request.query}"

    # Fetch jobs
    logger.info(f"Searching for: {search_query}, location: {request.location}, filters: {search_filters}")
    try:
        fetched_jobs = agent.fetch_jobs(search_query, request.location, sources, **search_filters)
    except Exception as e:
        logger.error(f"Job fetch failed: {e}")
        raise HTTPException(500, f"Job search failed: {str(e)}")

    if not fetched_jobs:
        # Save search history even if no results
        search_record = SearchHistoryRepository.save_search(
            db, profile_db.id, request.query, request.location,
            sources, 0, 0,
        )
        return SearchResponse(
            search_id=search_record.id, query=request.query,
            total_fetched=0, total_matched=0, matches=[],
        )

    # Score and rank
    try:
        matches = agent.match_and_rank_jobs(fetched_jobs)
    except Exception as e:
        logger.error(f"Matching failed: {e}")
        raise HTTPException(500, f"Matching failed: {str(e)}")

    # Persist jobs
    db_jobs = JobRepository.save_jobs_bulk(db, fetched_jobs)
    job_db_map = {}
    for db_job in db_jobs:
        job_db_map[db_job.job_id] = db_job.id

    # Save search history
    search_record = SearchHistoryRepository.save_search(
        db, profile_db.id, request.query, request.location,
        sources, len(fetched_jobs), len(matches),
    )

    # Persist matches
    MatchRepository.save_matches_bulk(
        db, profile_db.id, job_db_map, matches, search_record.id,
    )

    # Build response
    match_responses = []
    for i, m in enumerate(matches):
        job_resp = _job_to_response(m.job)
        score_resp = ScoreResponse(
            overall_score=m.relevance_score.overall_score,
            skills_score=m.relevance_score.skills_score,
            experience_score=m.relevance_score.experience_score,
            location_score=m.relevance_score.location_score,
            salary_score=m.relevance_score.salary_score,
            level_score=m.relevance_score.level_score,
            matching_skills=m.relevance_score.matching_skills,
            missing_skills=m.relevance_score.missing_skills,
            reasoning=m.relevance_score.reasoning,
        )
        match_responses.append(MatchResponse(
            id=i + 1,
            job=job_resp,
            score=score_resp,
            passed_filters=m.passed_filters,
            filter_reasons=m.filter_reasons,
            recommendation_text=m.recommendation_text,
            created_at=m.created_at,
        ))

    return SearchResponse(
        search_id=search_record.id,
        query=request.query,
        total_fetched=len(fetched_jobs),
        total_matched=len(matches),
        matches=match_responses,
    )


@router.get("", response_model=list)
def list_jobs(skip: int = 0, limit: int = 50,
              source: Optional[str] = None,
              db: Session = Depends(get_db)):
    """List saved jobs with optional filtering."""
    jobs = JobRepository.list_jobs(db, skip=skip, limit=limit, source=source)
    return [_job_to_response(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a single job by job_id."""
    job = JobRepository.get_job(db, job_id)
    if not job:
        raise HTTPException(404, f"Job not found: {job_id}")
    return _job_to_response(job)
