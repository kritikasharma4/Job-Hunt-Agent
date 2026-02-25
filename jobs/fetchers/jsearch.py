"""
JSearch API fetcher — real job listings via RapidAPI.

Uses the JSearch API (Google for Jobs aggregator) to fetch real job postings
from LinkedIn, Indeed, Glassdoor, and other sources.

Free tier: 500 requests/month.
Sign up at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
"""

import hashlib
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

import requests

from models.schemas import Job, Location, Salary, JobLevel, EmploymentType
from jobs.fetchers.base import JobFetcher

logger = logging.getLogger(__name__)

API_URL = "https://jsearch.p.rapidapi.com/search"


def _get_api_key() -> Optional[str]:
    """Get RapidAPI key from environment."""
    return os.getenv("RAPIDAPI_KEY")


class JSearchFetcher(JobFetcher):
    """
    Fetcher using JSearch API (RapidAPI) for real job listings.

    Requires RAPIDAPI_KEY environment variable to be set.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("jsearch", config)
        self.api_key = _get_api_key()

    def fetch(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **filters,
    ) -> List[Job]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if not self.api_key:
            logger.error(
                "RAPIDAPI_KEY not set. Get a free key at "
                "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
            )
            return []

        # Build search query — append location if provided
        search_query = query.strip()
        if location:
            search_query += f" in {location.strip()}"

        # Calculate pages needed (10 results per page)
        num_pages = min((max_results + 9) // 10, 5)  # Cap at 5 pages

        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        params = {
            "query": search_query,
            "page": "1",
            "num_pages": str(num_pages),
        }

        # Optional filters from **filters kwargs
        employment_type = filters.get("employment_type")
        if employment_type:
            type_map = {
                "fulltime": "FULLTIME",
                "parttime": "PARTTIME",
                "contract": "CONTRACTOR",
                "intern": "INTERN",
            }
            params["employment_types"] = type_map.get(employment_type.lower(), employment_type.upper())

        date_posted = filters.get("date_posted")
        if date_posted and date_posted != "all":
            params["date_posted"] = date_posted

        remote_only = filters.get("remote_only")
        if remote_only:
            params["remote_jobs_only"] = "true"

        logger.info(
            f"JSearch: fetching jobs for query='{search_query}', "
            f"num_pages={num_pages}"
        )

        try:
            response = requests.get(
                API_URL, headers=headers, params=params, timeout=30
            )

            if response.status_code == 403:
                logger.error("JSearch: invalid or expired API key (403)")
                return []
            if response.status_code == 429:
                logger.error("JSearch: rate limit exceeded (429)")
                return []
            if response.status_code != 200:
                logger.error(f"JSearch: unexpected status {response.status_code}")
                return []

            data = response.json()
            raw_jobs = data.get("data", [])

            logger.info(f"JSearch: received {len(raw_jobs)} raw results")

            jobs = []
            for raw in raw_jobs[:max_results]:
                job = self._parse_job(raw)
                if job:
                    jobs.append(job)

            logger.info(f"JSearch: parsed {len(jobs)} jobs")
            return jobs

        except requests.exceptions.RequestException as e:
            logger.error(f"JSearch: request failed: {e}")
            return []

    def validate_connection(self) -> bool:
        if not self.api_key:
            logger.warning("JSearch: RAPIDAPI_KEY not set")
            return False
        try:
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            }
            response = requests.get(
                API_URL,
                headers=headers,
                params={"query": "test", "page": "1", "num_pages": "1"},
                timeout=10,
            )
            valid = response.status_code == 200
            if valid:
                logger.info("JSearch: connection validated")
            else:
                logger.warning(f"JSearch: returned status {response.status_code}")
            return valid
        except requests.exceptions.RequestException as e:
            logger.warning(f"JSearch: connection validation failed: {e}")
            return False

    @staticmethod
    def _parse_job(raw: dict) -> Optional[Job]:
        """Parse a JSearch API result into a domain Job object."""
        title = raw.get("job_title")
        if not title:
            return None

        company = raw.get("employer_name", "Unknown")

        # Location
        city = raw.get("job_city", "") or ""
        state = raw.get("job_state", "") or ""
        country = raw.get("job_country", "") or ""
        is_remote = raw.get("job_is_remote", False)
        location = Location(
            city=city, state=state, country=country, remote=is_remote
        )

        # Description
        description = raw.get("job_description", "") or ""

        # Requirements from highlights
        requirements = []
        highlights = raw.get("job_highlights", {})
        if highlights:
            qualifications = highlights.get("Qualifications", [])
            requirements = qualifications[:10] if qualifications else []

        # Skills
        required_skills = raw.get("job_required_skills") or []

        # Salary
        salary = None
        min_sal = raw.get("job_min_salary")
        max_sal = raw.get("job_max_salary")
        if min_sal or max_sal:
            salary = Salary(
                min_amount=float(min_sal) if min_sal else None,
                max_amount=float(max_sal) if max_sal else None,
                currency=raw.get("job_salary_currency", "USD") or "USD",
                period=raw.get("job_salary_period", "yearly") or "yearly",
            )

        # Employment type
        emp_type_raw = raw.get("job_employment_type", "")
        employment_type = None
        if emp_type_raw:
            type_map = {
                "FULLTIME": EmploymentType.FULL_TIME,
                "PARTTIME": EmploymentType.PART_TIME,
                "CONTRACTOR": EmploymentType.CONTRACT,
                "INTERN": EmploymentType.INTERNSHIP,
            }
            employment_type = type_map.get(emp_type_raw.upper())

        # Experience level → JobLevel
        level = None
        exp_data = raw.get("job_required_experience", {})
        if exp_data:
            exp_months = exp_data.get("required_experience_in_months")
            if exp_months is not None:
                if exp_months <= 12:
                    level = JobLevel.ENTRY
                elif exp_months <= 48:
                    level = JobLevel.MID
                elif exp_months <= 96:
                    level = JobLevel.SENIOR
                else:
                    level = JobLevel.LEAD

        # URL
        url = raw.get("job_apply_link", "")

        # Posted date
        posted_date = None
        posted_ts = raw.get("job_posted_at_timestamp")
        if posted_ts:
            try:
                posted_date = datetime.fromtimestamp(posted_ts)
            except (ValueError, OSError):
                pass

        # Job ID
        job_id_raw = raw.get("job_id", "")
        if job_id_raw:
            job_id = hashlib.md5(job_id_raw.encode()).hexdigest()[:12]
        else:
            job_id = hashlib.md5(f"{title}:{company}".encode()).hexdigest()[:12]

        return Job(
            job_id=job_id,
            title=title,
            company=company,
            description=description[:2000],  # Cap description length
            location=location,
            requirements=required_skills or requirements,
            level=level,
            employment_type=employment_type,
            salary=salary,
            url=url,
            source="jsearch",
            posted_date=posted_date,
        )
