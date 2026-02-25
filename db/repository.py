"""
Repository layer providing CRUD operations and domain ↔ ORM conversions.

Bridges between the domain dataclasses (models/schemas.py) and the
SQLAlchemy ORM models (db/models.py).
"""

import logging
import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import (
    UserProfileDB, WorkExperienceDB, EducationDB,
    JobDB, JobMatchDB, ApplicationDB, SearchHistoryDB,
)
from models.schemas import (
    UserProfile, WorkExperience, Education, Location, Salary,
    Job, JobLevel, EmploymentType, RelevanceScore, JobMatch,
    ApplicationRecord,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profile Repository
# ---------------------------------------------------------------------------

class ProfileRepository:

    @staticmethod
    def save_profile(session: Session, profile: UserProfile) -> UserProfileDB:
        existing = session.query(UserProfileDB).filter_by(user_id=profile.user_id).first()
        if existing:
            return ProfileRepository._update_existing(session, existing, profile)

        db_profile = ProfileRepository._from_domain(profile)
        session.add(db_profile)
        session.commit()
        session.refresh(db_profile)
        return db_profile

    @staticmethod
    def get_profile(session: Session, user_id: str) -> Optional[UserProfile]:
        db_obj = session.query(UserProfileDB).filter_by(user_id=user_id).first()
        if not db_obj:
            return None
        return ProfileRepository._to_domain(db_obj)

    @staticmethod
    def get_profile_db(session: Session, user_id: str) -> Optional[UserProfileDB]:
        return session.query(UserProfileDB).filter_by(user_id=user_id).first()

    @staticmethod
    def get_first_profile(session: Session) -> Optional[UserProfile]:
        db_obj = session.query(UserProfileDB).first()
        if not db_obj:
            return None
        return ProfileRepository._to_domain(db_obj)

    @staticmethod
    def get_first_profile_db(session: Session) -> Optional[UserProfileDB]:
        return session.query(UserProfileDB).first()

    @staticmethod
    def list_profiles(session: Session) -> List[UserProfile]:
        rows = session.query(UserProfileDB).all()
        return [ProfileRepository._to_domain(r) for r in rows]

    @staticmethod
    def update_profile(session: Session, user_id: str, data: dict) -> Optional[UserProfile]:
        db_obj = session.query(UserProfileDB).filter_by(user_id=user_id).first()
        if not db_obj:
            return None
        for key, value in data.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        db_obj.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(db_obj)
        return ProfileRepository._to_domain(db_obj)

    @staticmethod
    def delete_profile(session: Session, user_id: str) -> bool:
        db_obj = session.query(UserProfileDB).filter_by(user_id=user_id).first()
        if not db_obj:
            return False
        session.delete(db_obj)
        session.commit()
        return True

    # --- Converters ---

    @staticmethod
    def _to_domain(db_obj: UserProfileDB) -> UserProfile:
        location = None
        if db_obj.location_city or db_obj.location_state or db_obj.location_country:
            location = Location(
                city=db_obj.location_city or "",
                state=db_obj.location_state or "",
                country=db_obj.location_country or "",
                remote=db_obj.location_remote or False,
            )

        salary = None
        if db_obj.preferred_salary_min is not None or db_obj.preferred_salary_max is not None:
            salary = Salary(
                min_amount=db_obj.preferred_salary_min,
                max_amount=db_obj.preferred_salary_max,
                currency=db_obj.preferred_salary_currency or "USD",
            )

        work_exp = [
            WorkExperience(
                company=w.company,
                position=w.position,
                start_date=w.start_date,
                end_date=w.end_date,
                description=w.description or "",
                skills=w.skills or [],
                is_current=w.is_current or False,
            )
            for w in db_obj.work_experiences
        ]

        edu = [
            Education(
                institution=e.institution,
                degree=e.degree,
                field=e.field or "",
                graduation_date=e.graduation_date,
                gpa=e.gpa,
                honors=e.honors or "",
            )
            for e in db_obj.education_entries
        ]

        pref_levels = []
        for lvl in (db_obj.preferred_job_levels or []):
            try:
                pref_levels.append(JobLevel(lvl))
            except ValueError:
                pass

        pref_locations = []
        for loc_dict in (db_obj.preferred_locations or []):
            if isinstance(loc_dict, dict):
                pref_locations.append(Location(
                    city=loc_dict.get("city", ""),
                    state=loc_dict.get("state", ""),
                    country=loc_dict.get("country", ""),
                    remote=loc_dict.get("remote", False),
                ))

        return UserProfile(
            user_id=db_obj.user_id,
            full_name=db_obj.full_name,
            email=db_obj.email,
            phone=db_obj.phone,
            summary=db_obj.summary or "",
            location=location,
            skills=db_obj.skills or [],
            work_experience=work_exp,
            education=edu,
            certifications=db_obj.certifications or [],
            preferred_job_levels=pref_levels,
            preferred_locations=pref_locations,
            preferred_salary_range=salary,
            willing_to_relocate=db_obj.willing_to_relocate or False,
            remote_preference=db_obj.remote_preference or "flexible",
            metadata=db_obj.metadata_json or {},
        )

    @staticmethod
    def _from_domain(profile: UserProfile) -> UserProfileDB:
        db_obj = UserProfileDB(
            user_id=profile.user_id,
            full_name=profile.full_name,
            email=profile.email,
            phone=profile.phone,
            summary=profile.summary,
            location_city=profile.location.city if profile.location else "",
            location_state=profile.location.state if profile.location else "",
            location_country=profile.location.country if profile.location else "",
            location_remote=profile.location.remote if profile.location else False,
            remote_preference=profile.remote_preference,
            willing_to_relocate=profile.willing_to_relocate,
            preferred_salary_min=profile.preferred_salary_range.min_amount if profile.preferred_salary_range else None,
            preferred_salary_max=profile.preferred_salary_range.max_amount if profile.preferred_salary_range else None,
            preferred_salary_currency=profile.preferred_salary_range.currency if profile.preferred_salary_range else "USD",
            skills=profile.skills,
            certifications=profile.certifications,
            preferred_job_levels=[lvl.value for lvl in profile.preferred_job_levels],
            preferred_locations=[
                {"city": loc.city, "state": loc.state, "country": loc.country, "remote": loc.remote}
                for loc in profile.preferred_locations
            ],
            metadata_json=profile.metadata,
        )

        for exp in profile.work_experience:
            db_obj.work_experiences.append(WorkExperienceDB(
                company=exp.company,
                position=exp.position,
                start_date=exp.start_date,
                end_date=exp.end_date,
                description=exp.description,
                skills=exp.skills,
                is_current=exp.is_current,
            ))

        for edu in profile.education:
            db_obj.education_entries.append(EducationDB(
                institution=edu.institution,
                degree=edu.degree,
                field=edu.field,
                graduation_date=edu.graduation_date,
                gpa=edu.gpa,
                honors=edu.honors,
            ))

        return db_obj

    @staticmethod
    def _update_existing(session: Session, db_obj: UserProfileDB, profile: UserProfile) -> UserProfileDB:
        db_obj.full_name = profile.full_name
        db_obj.email = profile.email
        db_obj.phone = profile.phone
        db_obj.summary = profile.summary
        db_obj.location_city = profile.location.city if profile.location else ""
        db_obj.location_state = profile.location.state if profile.location else ""
        db_obj.location_country = profile.location.country if profile.location else ""
        db_obj.location_remote = profile.location.remote if profile.location else False
        db_obj.remote_preference = profile.remote_preference
        db_obj.willing_to_relocate = profile.willing_to_relocate
        db_obj.skills = profile.skills
        db_obj.certifications = profile.certifications
        db_obj.preferred_job_levels = [lvl.value for lvl in profile.preferred_job_levels]
        db_obj.preferred_locations = [
            {"city": loc.city, "state": loc.state, "country": loc.country, "remote": loc.remote}
            for loc in profile.preferred_locations
        ]
        if profile.preferred_salary_range:
            db_obj.preferred_salary_min = profile.preferred_salary_range.min_amount
            db_obj.preferred_salary_max = profile.preferred_salary_range.max_amount
            db_obj.preferred_salary_currency = profile.preferred_salary_range.currency
        db_obj.metadata_json = profile.metadata
        db_obj.updated_at = datetime.utcnow()

        # Replace work experiences
        db_obj.work_experiences.clear()
        for exp in profile.work_experience:
            db_obj.work_experiences.append(WorkExperienceDB(
                company=exp.company, position=exp.position,
                start_date=exp.start_date, end_date=exp.end_date,
                description=exp.description, skills=exp.skills,
                is_current=exp.is_current,
            ))

        # Replace education
        db_obj.education_entries.clear()
        for edu in profile.education:
            db_obj.education_entries.append(EducationDB(
                institution=edu.institution, degree=edu.degree,
                field=edu.field, graduation_date=edu.graduation_date,
                gpa=edu.gpa, honors=edu.honors,
            ))

        session.commit()
        session.refresh(db_obj)
        return db_obj


# ---------------------------------------------------------------------------
# Job Repository
# ---------------------------------------------------------------------------

class JobRepository:

    @staticmethod
    def save_job(session: Session, job: Job) -> JobDB:
        existing = session.query(JobDB).filter_by(job_id=job.job_id).first()
        if existing:
            return existing

        db_job = JobRepository._from_domain(job)
        session.add(db_job)
        session.commit()
        session.refresh(db_job)
        return db_job

    @staticmethod
    def save_jobs_bulk(session: Session, jobs: List[Job]) -> List[JobDB]:
        db_jobs = []
        for job in jobs:
            existing = session.query(JobDB).filter_by(job_id=job.job_id).first()
            if existing:
                db_jobs.append(existing)
            else:
                db_job = JobRepository._from_domain(job)
                session.add(db_job)
                db_jobs.append(db_job)
        session.commit()
        return db_jobs

    @staticmethod
    def get_job(session: Session, job_id: str) -> Optional[Job]:
        db_obj = session.query(JobDB).filter_by(job_id=job_id).first()
        if not db_obj:
            return None
        return JobRepository._to_domain(db_obj)

    @staticmethod
    def get_job_db(session: Session, job_id: str) -> Optional[JobDB]:
        return session.query(JobDB).filter_by(job_id=job_id).first()

    @staticmethod
    def list_jobs(session: Session, skip: int = 0, limit: int = 50,
                  source: Optional[str] = None) -> List[Job]:
        query = session.query(JobDB)
        if source:
            query = query.filter_by(source=source)
        query = query.order_by(JobDB.created_at.desc())
        rows = query.offset(skip).limit(limit).all()
        return [JobRepository._to_domain(r) for r in rows]

    @staticmethod
    def count_jobs(session: Session) -> int:
        return session.query(func.count(JobDB.id)).scalar() or 0

    # --- Converters ---

    @staticmethod
    def _to_domain(db_obj: JobDB) -> Job:
        location = Location(
            city=db_obj.location_city or "",
            state=db_obj.location_state or "",
            country=db_obj.location_country or "",
            remote=db_obj.location_remote or False,
        )

        salary = None
        if db_obj.salary_min is not None or db_obj.salary_max is not None:
            salary = Salary(
                min_amount=db_obj.salary_min,
                max_amount=db_obj.salary_max,
                currency=db_obj.salary_currency or "USD",
                period=db_obj.salary_period or "yearly",
            )

        level = None
        if db_obj.level:
            try:
                level = JobLevel(db_obj.level)
            except ValueError:
                pass

        emp_type = None
        if db_obj.employment_type:
            try:
                emp_type = EmploymentType(db_obj.employment_type)
            except ValueError:
                pass

        return Job(
            job_id=db_obj.job_id,
            title=db_obj.title,
            company=db_obj.company,
            description=db_obj.description or "",
            location=location,
            requirements=db_obj.requirements or [],
            nice_to_haves=db_obj.nice_to_haves or [],
            level=level,
            employment_type=emp_type,
            salary=salary,
            url=db_obj.url,
            source=db_obj.source or "unknown",
            posted_date=db_obj.posted_date,
            metadata=db_obj.metadata_json or {},
        )

    @staticmethod
    def _from_domain(job: Job) -> JobDB:
        return JobDB(
            job_id=job.job_id,
            title=job.title,
            company=job.company,
            description=job.description,
            location_city=job.location.city if job.location else "",
            location_state=job.location.state if job.location else "",
            location_country=job.location.country if job.location else "",
            location_remote=job.location.remote if job.location else False,
            requirements=job.requirements,
            nice_to_haves=job.nice_to_haves,
            level=job.level.value if job.level else None,
            employment_type=job.employment_type.value if job.employment_type else None,
            salary_min=job.salary.min_amount if job.salary else None,
            salary_max=job.salary.max_amount if job.salary else None,
            salary_currency=job.salary.currency if job.salary else "USD",
            salary_period=job.salary.period if job.salary else "yearly",
            url=job.url,
            source=job.source,
            posted_date=job.posted_date,
            metadata_json=job.metadata,
        )


# ---------------------------------------------------------------------------
# Match Repository
# ---------------------------------------------------------------------------

class MatchRepository:

    @staticmethod
    def save_match(session: Session, profile_db_id: int, job_db_id: int,
                   match: JobMatch, search_id: Optional[int] = None) -> JobMatchDB:
        db_match = JobMatchDB(
            profile_id=profile_db_id,
            job_id=job_db_id,
            search_id=search_id,
            overall_score=match.relevance_score.overall_score,
            skills_score=match.relevance_score.skills_score,
            experience_score=match.relevance_score.experience_score,
            location_score=match.relevance_score.location_score,
            salary_score=match.relevance_score.salary_score,
            level_score=match.relevance_score.level_score,
            matching_skills=match.relevance_score.matching_skills,
            missing_skills=match.relevance_score.missing_skills,
            reasoning=match.relevance_score.reasoning,
            passed_filters=match.passed_filters,
            filter_reasons=match.filter_reasons,
            recommendation_text=match.recommendation_text,
        )
        session.add(db_match)
        return db_match

    @staticmethod
    def save_matches_bulk(session: Session, profile_db_id: int,
                          job_db_map: dict, matches: List[JobMatch],
                          search_id: Optional[int] = None) -> List[JobMatchDB]:
        db_matches = []
        for match in matches:
            job_db_id = job_db_map.get(match.job.job_id)
            if job_db_id is None:
                continue
            db_match = MatchRepository.save_match(
                session, profile_db_id, job_db_id, match, search_id
            )
            db_matches.append(db_match)
        session.commit()
        return db_matches

    @staticmethod
    def list_matches(session: Session, profile_id: int,
                     min_score: float = 0.0, skip: int = 0,
                     limit: int = 50) -> List[dict]:
        query = (
            session.query(JobMatchDB, JobDB)
            .join(JobDB, JobMatchDB.job_id == JobDB.id)
            .filter(JobMatchDB.profile_id == profile_id)
            .filter(JobMatchDB.overall_score >= min_score)
            .order_by(JobMatchDB.overall_score.desc())
        )
        rows = query.offset(skip).limit(limit).all()
        results = []
        for match_db, job_db in rows:
            results.append({
                "id": match_db.id,
                "job": JobRepository._to_domain(job_db),
                "score": {
                    "overall_score": match_db.overall_score,
                    "skills_score": match_db.skills_score,
                    "experience_score": match_db.experience_score,
                    "location_score": match_db.location_score,
                    "salary_score": match_db.salary_score,
                    "level_score": match_db.level_score,
                    "matching_skills": match_db.matching_skills or [],
                    "missing_skills": match_db.missing_skills or [],
                    "reasoning": match_db.reasoning or "",
                },
                "passed_filters": match_db.passed_filters,
                "filter_reasons": match_db.filter_reasons or [],
                "recommendation_text": match_db.recommendation_text or "",
                "created_at": match_db.created_at,
            })
        return results

    @staticmethod
    def get_match(session: Session, match_id: int) -> Optional[dict]:
        row = (
            session.query(JobMatchDB, JobDB)
            .join(JobDB, JobMatchDB.job_id == JobDB.id)
            .filter(JobMatchDB.id == match_id)
            .first()
        )
        if not row:
            return None
        match_db, job_db = row
        return {
            "id": match_db.id,
            "job": JobRepository._to_domain(job_db),
            "score": {
                "overall_score": match_db.overall_score,
                "skills_score": match_db.skills_score,
                "experience_score": match_db.experience_score,
                "location_score": match_db.location_score,
                "salary_score": match_db.salary_score,
                "level_score": match_db.level_score,
                "matching_skills": match_db.matching_skills or [],
                "missing_skills": match_db.missing_skills or [],
                "reasoning": match_db.reasoning or "",
            },
            "passed_filters": match_db.passed_filters,
            "filter_reasons": match_db.filter_reasons or [],
            "recommendation_text": match_db.recommendation_text or "",
            "created_at": match_db.created_at,
        }

    @staticmethod
    def delete_match(session: Session, match_id: int) -> bool:
        db_obj = session.query(JobMatchDB).filter_by(id=match_id).first()
        if not db_obj:
            return False
        session.delete(db_obj)
        session.commit()
        return True

    @staticmethod
    def count_matches(session: Session, profile_id: int) -> int:
        return (
            session.query(func.count(JobMatchDB.id))
            .filter(JobMatchDB.profile_id == profile_id)
            .scalar() or 0
        )

    @staticmethod
    def avg_score(session: Session, profile_id: int) -> float:
        result = (
            session.query(func.avg(JobMatchDB.overall_score))
            .filter(JobMatchDB.profile_id == profile_id)
            .scalar()
        )
        return round(result, 2) if result else 0.0


# ---------------------------------------------------------------------------
# Application Repository
# ---------------------------------------------------------------------------

class ApplicationRepository:

    @staticmethod
    def save_application(session: Session, profile_db_id: int,
                         job_id_str: str, job_title: str, company: str,
                         job_db_id: Optional[int] = None,
                         notes: str = "") -> ApplicationDB:
        # Check for duplicate
        existing = (
            session.query(ApplicationDB)
            .filter_by(profile_id=profile_db_id, job_id=job_id_str)
            .first()
        )
        if existing:
            return existing

        app = ApplicationDB(
            application_id=str(uuid.uuid4()),
            profile_id=profile_db_id,
            job_db_id=job_db_id,
            job_id=job_id_str,
            job_title=job_title,
            company=company,
            notes=notes,
        )
        session.add(app)
        session.commit()
        session.refresh(app)
        return app

    @staticmethod
    def get_application(session: Session, application_id: str) -> Optional[ApplicationDB]:
        return session.query(ApplicationDB).filter_by(application_id=application_id).first()

    @staticmethod
    def update_status(session: Session, application_id: str,
                      status: str, notes: Optional[str] = None) -> Optional[ApplicationDB]:
        valid = {"pending", "accepted", "rejected", "interview", "offer", "withdrawn"}
        if status not in valid:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid}")

        app = session.query(ApplicationDB).filter_by(application_id=application_id).first()
        if not app:
            return None
        app.status = status
        if notes is not None:
            app.notes = notes
        app.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(app)
        return app

    @staticmethod
    def list_applications(session: Session, profile_id: int,
                          status: Optional[str] = None,
                          skip: int = 0, limit: int = 50) -> List[ApplicationDB]:
        query = session.query(ApplicationDB).filter_by(profile_id=profile_id)
        if status:
            query = query.filter_by(status=status)
        query = query.order_by(ApplicationDB.applied_date.desc())
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def delete_application(session: Session, application_id: str) -> bool:
        app = session.query(ApplicationDB).filter_by(application_id=application_id).first()
        if not app:
            return False
        session.delete(app)
        session.commit()
        return True

    @staticmethod
    def count_applications(session: Session, profile_id: int) -> int:
        return (
            session.query(func.count(ApplicationDB.id))
            .filter(ApplicationDB.profile_id == profile_id)
            .scalar() or 0
        )

    @staticmethod
    def count_by_status(session: Session, profile_id: int) -> dict:
        rows = (
            session.query(ApplicationDB.status, func.count(ApplicationDB.id))
            .filter(ApplicationDB.profile_id == profile_id)
            .group_by(ApplicationDB.status)
            .all()
        )
        return {status: count for status, count in rows}


# ---------------------------------------------------------------------------
# Search History Repository
# ---------------------------------------------------------------------------

class SearchHistoryRepository:

    @staticmethod
    def save_search(session: Session, profile_id: int, query: str,
                    location: Optional[str], sources: List[str],
                    results_count: int, matches_count: int) -> SearchHistoryDB:
        record = SearchHistoryDB(
            profile_id=profile_id,
            query=query,
            location=location,
            sources=sources,
            results_count=results_count,
            matches_count=matches_count,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @staticmethod
    def get_history(session: Session, profile_id: int,
                    limit: int = 20) -> List[SearchHistoryDB]:
        return (
            session.query(SearchHistoryDB)
            .filter_by(profile_id=profile_id)
            .order_by(SearchHistoryDB.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_searches(session: Session, profile_id: int) -> int:
        return (
            session.query(func.count(SearchHistoryDB.id))
            .filter(SearchHistoryDB.profile_id == profile_id)
            .scalar() or 0
        )
