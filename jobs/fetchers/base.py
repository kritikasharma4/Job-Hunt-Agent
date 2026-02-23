"""
Job fetcher implementations for various sources.

Fetches job postings from LinkedIn and Indeed via web scraping.
Uses requests + BeautifulSoup with anti-detection measures (UA rotation, rate limiting).
"""

import hashlib
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from models.schemas import Job, Location, Salary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared constants and helpers
# ---------------------------------------------------------------------------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def _get_random_headers(referer: Optional[str] = None) -> Dict[str, str]:
    """Return request headers with a random user-agent."""
    headers = dict(DEFAULT_HEADERS)
    headers["User-Agent"] = random.choice(USER_AGENTS)
    if referer:
        headers["Referer"] = referer
    return headers


def _rate_limit_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """Sleep for a random interval to avoid detection."""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def _generate_job_id(source: str, identifier: str) -> str:
    """Create a deterministic job_id from source + identifier."""
    raw = f"{source}:{identifier}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _parse_location_string(location_str: str) -> Location:
    """Parse a location string like 'San Francisco, CA' into a Location object."""
    location_str = location_str.strip()

    is_remote = "remote" in location_str.lower()

    parts = [p.strip() for p in location_str.split(",")]
    city = parts[0] if len(parts) > 0 else ""
    state = parts[1] if len(parts) > 1 else ""
    country = parts[2] if len(parts) > 2 else "US"

    # Clean up common patterns
    if city.lower() in ("remote", "remote in"):
        city = ""
    state = re.sub(r"\s*\(.*\)", "", state)  # remove parenthetical notes

    return Location(city=city, state=state, country=country, remote=is_remote)


def _parse_relative_date(date_text: str) -> Optional[datetime]:
    """Parse relative date strings like '3 days ago', '1 week ago' into datetime."""
    date_text = date_text.lower().strip()
    now = datetime.now()

    match = re.search(r"(\d+)\s*(second|minute|hour|day|week|month)", date_text)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "second":
            return now - timedelta(seconds=amount)
        elif unit == "minute":
            return now - timedelta(minutes=amount)
        elif unit == "hour":
            return now - timedelta(hours=amount)
        elif unit == "day":
            return now - timedelta(days=amount)
        elif unit == "week":
            return now - timedelta(weeks=amount)
        elif unit == "month":
            return now - timedelta(days=amount * 30)

    if "just" in date_text or "today" in date_text or "now" in date_text:
        return now

    return None


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class JobFetcher(ABC):
    """
    Abstract base class for job fetchers.

    Responsibility: Defines the interface for fetching job postings from various sources
    (LinkedIn, Indeed, etc.). Implements the Strategy Pattern for pluggable job sources.
    """

    def __init__(self, source_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize job fetcher.

        Args:
            source_name: Name of the job source (e.g., 'linkedin', 'indeed')
            config: Optional configuration for this fetcher
        """
        self.source_name = source_name
        self.config = config or {}
        self.session = requests.Session()

    @abstractmethod
    def fetch(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **filters
    ) -> List[Job]:
        """
        Fetch jobs matching criteria.

        Args:
            query: Job search query (title, keywords, etc.)
            location: Optional location filter
            max_results: Maximum number of results to return
            **filters: Additional filters specific to the source

        Returns:
            List of Job objects matching criteria

        Raises:
            ConnectionError: If the source is unreachable
            RuntimeError: If fetching fails
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate connection to job source.

        Returns:
            True if connection is valid and accessible
        """
        pass


# ---------------------------------------------------------------------------
# LinkedIn fetcher
# ---------------------------------------------------------------------------

class LinkedInJobFetcher(JobFetcher):
    """
    Fetcher for LinkedIn job postings.

    Responsibility: Retrieves job listings from LinkedIn's public job search pages
    via web scraping. No login required — uses the publicly accessible search results.
    """

    BASE_URL = "https://www.linkedin.com/jobs/search/"
    RESULTS_PER_PAGE = 25

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize LinkedIn job fetcher.

        Args:
            config: Configuration options:
                - rate_limit_min: min delay between requests (default 1.0)
                - rate_limit_max: max delay between requests (default 3.0)
                - timeout: request timeout in seconds (default 15)
        """
        super().__init__("linkedin", config)

    def fetch(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **filters
    ) -> List[Job]:
        """
        Fetch jobs from LinkedIn public search pages.

        Args:
            query: Job title or keywords
            location: Job location
            max_results: Maximum results
            **filters: Additional filters (not currently used)

        Returns:
            List of Job objects from LinkedIn
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        jobs = []
        offset = 0
        timeout = self.config.get("timeout", 15)
        rate_min = self.config.get("rate_limit_min", 1.0)
        rate_max = self.config.get("rate_limit_max", 3.0)

        logger.info(
            f"LinkedIn: fetching jobs for query='{query}', "
            f"location='{location}', max_results={max_results}"
        )

        while len(jobs) < max_results:
            url = self._build_search_url(query, location, offset)
            headers = _get_random_headers(referer="https://www.linkedin.com/jobs/")

            try:
                response = self.session.get(url, headers=headers, timeout=timeout)

                if response.status_code == 429:
                    logger.warning("LinkedIn: rate limited (429). Stopping pagination.")
                    break
                if response.status_code == 403:
                    logger.warning("LinkedIn: access forbidden (403). Stopping pagination.")
                    break
                if response.status_code != 200:
                    logger.warning(f"LinkedIn: unexpected status {response.status_code}")
                    break

                page_jobs = self._parse_search_results(response.text)

                if not page_jobs:
                    logger.debug(f"LinkedIn: no more results at offset {offset}")
                    break

                jobs.extend(page_jobs)
                logger.debug(f"LinkedIn: fetched {len(page_jobs)} jobs at offset {offset}")

                offset += self.RESULTS_PER_PAGE
                if len(jobs) < max_results:
                    _rate_limit_delay(rate_min, rate_max)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"LinkedIn: connection error: {e}")
                raise ConnectionError(
                    f"Failed to connect to LinkedIn: {e}"
                ) from e
            except requests.exceptions.Timeout as e:
                logger.warning(f"LinkedIn: request timed out at offset {offset}")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"LinkedIn: request error: {e}")
                break

        # Trim to max_results
        jobs = jobs[:max_results]
        logger.info(f"LinkedIn: fetched {len(jobs)} total jobs")
        return jobs

    def validate_connection(self) -> bool:
        """Validate LinkedIn is reachable."""
        try:
            response = self.session.get(
                self.BASE_URL,
                headers=_get_random_headers(),
                timeout=10,
                allow_redirects=True,
            )
            reachable = response.status_code == 200
            if reachable:
                logger.info("LinkedIn: connection validated")
            else:
                logger.warning(f"LinkedIn: returned status {response.status_code}")
            return reachable
        except requests.exceptions.RequestException as e:
            logger.warning(f"LinkedIn: connection validation failed: {e}")
            return False

    def _build_search_url(
        self, query: str, location: Optional[str], offset: int
    ) -> str:
        """Build LinkedIn job search URL with parameters."""
        params = f"keywords={quote_plus(query)}"
        if location:
            params += f"&location={quote_plus(location)}"
        if offset > 0:
            params += f"&start={offset}"
        return f"{self.BASE_URL}?{params}"

    def _parse_search_results(self, html: str) -> List[Job]:
        """Parse LinkedIn search results HTML into Job objects."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # LinkedIn public job search uses base-card or base-search-card divs
        cards = soup.find_all("div", class_=re.compile(r"base-card|base-search-card"))

        if not cards:
            # Fallback: try list items in the job results
            cards = soup.find_all("li", class_=re.compile(r"jobs-search"))

        for card in cards:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"LinkedIn: failed to parse job card: {e}")
                continue

        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a single LinkedIn job card into a Job object."""
        # Title
        title_elem = card.find("h3", class_=re.compile(r"base-search-card__title"))
        if not title_elem:
            title_elem = card.find("h3")
        title = title_elem.get_text(strip=True) if title_elem else None

        if not title:
            return None

        # Company
        company_elem = card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
        if not company_elem:
            company_elem = card.find("h4")
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"

        # Location
        location_elem = card.find("span", class_=re.compile(r"job-search-card__location"))
        location_text = location_elem.get_text(strip=True) if location_elem else ""
        location = _parse_location_string(location_text) if location_text else Location(
            city="", state="", country=""
        )

        # URL
        link_elem = card.find("a", class_=re.compile(r"base-card__full-link"))
        if not link_elem:
            link_elem = card.find("a", href=re.compile(r"/jobs/view/"))
        url = link_elem.get("href", "").split("?")[0] if link_elem else None

        # Posted date
        time_elem = card.find("time")
        posted_date = None
        if time_elem:
            datetime_attr = time_elem.get("datetime")
            if datetime_attr:
                try:
                    posted_date = datetime.fromisoformat(datetime_attr)
                except ValueError:
                    pass
            if not posted_date:
                posted_date = _parse_relative_date(time_elem.get_text())

        # Generate job ID
        job_id = _generate_job_id("linkedin", url or title)

        return Job(
            job_id=job_id,
            title=title,
            company=company,
            description="",  # Not available from search results
            location=location,
            requirements=[],  # Not available from search results
            url=url,
            source="linkedin",
            posted_date=posted_date,
        )


# ---------------------------------------------------------------------------
# Indeed fetcher
# ---------------------------------------------------------------------------

class IndeedJobFetcher(JobFetcher):
    """
    Fetcher for Indeed job postings.

    Responsibility: Retrieves job listings from Indeed's public search pages
    via web scraping.
    """

    BASE_URL = "https://www.indeed.com/jobs"
    RESULTS_PER_PAGE = 10

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Indeed job fetcher.

        Args:
            config: Configuration options:
                - rate_limit_min: min delay between requests (default 1.0)
                - rate_limit_max: max delay between requests (default 3.0)
                - timeout: request timeout in seconds (default 15)
        """
        super().__init__("indeed", config)

    def fetch(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **filters
    ) -> List[Job]:
        """
        Fetch jobs from Indeed public search pages.

        Args:
            query: Job title or keywords
            location: Job location
            max_results: Maximum results
            **filters: Additional filters (not currently used)

        Returns:
            List of Job objects from Indeed
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        jobs = []
        offset = 0
        timeout = self.config.get("timeout", 15)
        rate_min = self.config.get("rate_limit_min", 1.0)
        rate_max = self.config.get("rate_limit_max", 3.0)

        logger.info(
            f"Indeed: fetching jobs for query='{query}', "
            f"location='{location}', max_results={max_results}"
        )

        while len(jobs) < max_results:
            url = self._build_search_url(query, location, offset)
            headers = _get_random_headers(referer="https://www.indeed.com/")

            try:
                response = self.session.get(url, headers=headers, timeout=timeout)

                if response.status_code == 429:
                    logger.warning("Indeed: rate limited (429). Stopping pagination.")
                    break
                if response.status_code == 403:
                    logger.warning("Indeed: access forbidden (403). Stopping pagination.")
                    break
                if response.status_code != 200:
                    logger.warning(f"Indeed: unexpected status {response.status_code}")
                    break

                page_jobs = self._parse_search_results(response.text)

                if not page_jobs:
                    logger.debug(f"Indeed: no more results at offset {offset}")
                    break

                jobs.extend(page_jobs)
                logger.debug(f"Indeed: fetched {len(page_jobs)} jobs at offset {offset}")

                offset += self.RESULTS_PER_PAGE
                if len(jobs) < max_results:
                    _rate_limit_delay(rate_min, rate_max)

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Indeed: connection error: {e}")
                raise ConnectionError(
                    f"Failed to connect to Indeed: {e}"
                ) from e
            except requests.exceptions.Timeout as e:
                logger.warning(f"Indeed: request timed out at offset {offset}")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Indeed: request error: {e}")
                break

        # Trim to max_results
        jobs = jobs[:max_results]
        logger.info(f"Indeed: fetched {len(jobs)} total jobs")
        return jobs

    def validate_connection(self) -> bool:
        """Validate Indeed is reachable."""
        try:
            response = self.session.get(
                self.BASE_URL,
                headers=_get_random_headers(),
                timeout=10,
                allow_redirects=True,
            )
            reachable = response.status_code == 200
            if reachable:
                logger.info("Indeed: connection validated")
            else:
                logger.warning(f"Indeed: returned status {response.status_code}")
            return reachable
        except requests.exceptions.RequestException as e:
            logger.warning(f"Indeed: connection validation failed: {e}")
            return False

    def _build_search_url(
        self, query: str, location: Optional[str], offset: int
    ) -> str:
        """Build Indeed job search URL with parameters."""
        params = f"q={quote_plus(query)}"
        if location:
            params += f"&l={quote_plus(location)}"
        if offset > 0:
            params += f"&start={offset}"
        return f"{self.BASE_URL}?{params}"

    def _parse_search_results(self, html: str) -> List[Job]:
        """Parse Indeed search results HTML into Job objects."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Indeed uses job_seen_beacon divs or cardOutline for job cards
        cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|cardOutline"))

        if not cards:
            # Fallback: try result content divs
            cards = soup.find_all("td", class_="resultContent")

        if not cards:
            # Another fallback: look for tapItem links
            cards = soup.find_all("a", class_=re.compile(r"tapItem|jcs-JobTitle"))

        for card in cards:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Indeed: failed to parse job card: {e}")
                continue

        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a single Indeed job card into a Job object."""
        # Title
        title_elem = (
            card.find("h2", class_=re.compile(r"jobTitle"))
            or card.find("a", class_=re.compile(r"jcs-JobTitle"))
            or card.find("h2")
        )
        if title_elem:
            # Indeed sometimes wraps title in a span
            span = title_elem.find("span", attrs={"title": True})
            title = span["title"] if span else title_elem.get_text(strip=True)
        else:
            title = None

        if not title:
            return None

        # Company
        company_elem = (
            card.find("span", attrs={"data-testid": "company-name"})
            or card.find("span", class_=re.compile(r"company"))
            or card.find("span", class_="companyName")
        )
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"

        # Location
        location_elem = (
            card.find("div", attrs={"data-testid": "text-location"})
            or card.find("div", class_=re.compile(r"company[Ll]ocation"))
            or card.find("span", class_=re.compile(r"location"))
        )
        location_text = location_elem.get_text(strip=True) if location_elem else ""
        location = _parse_location_string(location_text) if location_text else Location(
            city="", state="", country=""
        )

        # URL
        link_elem = (
            card.find("a", class_=re.compile(r"jcs-JobTitle"))
            or card.find("a", href=re.compile(r"/rc/clk|/viewjob"))
            or card.find("a", attrs={"data-jk": True})
        )
        url = None
        if link_elem:
            href = link_elem.get("href", "")
            if href.startswith("http"):
                url = href.split("&")[0]  # Strip tracking params
            elif href:
                url = f"https://www.indeed.com{href}".split("&")[0]

        # Salary
        salary = None
        salary_elem = (
            card.find("div", class_=re.compile(r"salary-snippet"))
            or card.find("span", class_=re.compile(r"salary"))
            or card.find("div", class_=re.compile(r"metadata.*salary"))
        )
        if salary_elem:
            salary = self._parse_salary_text(salary_elem.get_text(strip=True))

        # Posted date
        date_elem = card.find("span", class_=re.compile(r"date"))
        posted_date = None
        if date_elem:
            posted_date = _parse_relative_date(date_elem.get_text())

        # Generate job ID
        job_id = _generate_job_id("indeed", url or title)

        return Job(
            job_id=job_id,
            title=title,
            company=company,
            description="",  # Not available from search results
            location=location,
            requirements=[],  # Not available from search results
            salary=salary,
            url=url,
            source="indeed",
            posted_date=posted_date,
        )

    @staticmethod
    def _parse_salary_text(salary_text: str) -> Optional[Salary]:
        """Parse salary text like '$80,000 - $120,000 a year' into Salary."""
        if not salary_text:
            return None

        # Extract numbers
        amounts = re.findall(r"[\$]?([\d,]+\.?\d*)", salary_text)
        if not amounts:
            return None

        amounts = [float(a.replace(",", "")) for a in amounts]

        # Determine period
        period = "yearly"
        text_lower = salary_text.lower()
        if "hour" in text_lower:
            period = "hourly"
        elif "month" in text_lower:
            period = "monthly"
        elif "week" in text_lower:
            period = "weekly"

        min_amount = amounts[0] if len(amounts) >= 1 else None
        max_amount = amounts[1] if len(amounts) >= 2 else None

        return Salary(
            min_amount=min_amount,
            max_amount=max_amount,
            currency="USD",
            period=period,
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class JobFetcherRegistry:
    """
    Registry for job fetchers.

    Responsibility: Manages fetcher registration and retrieval, enabling
    extensible support for multiple job sources without modifying existing code.
    """

    _fetchers: Dict[str, JobFetcher] = {}

    @classmethod
    def register(cls, fetcher: JobFetcher) -> None:
        """
        Register a job fetcher.

        Args:
            fetcher: JobFetcher instance to register
        """
        cls._fetchers[fetcher.source_name.lower()] = fetcher
        logger.info(f"Registered job fetcher: {fetcher.source_name}")

    @classmethod
    def get_fetcher(cls, source_name: str) -> Optional[JobFetcher]:
        """
        Get a fetcher by source name.

        Args:
            source_name: Name of the job source

        Returns:
            JobFetcher instance or None if not found
        """
        return cls._fetchers.get(source_name.lower())

    @classmethod
    def get_all_fetchers(cls) -> Dict[str, JobFetcher]:
        """Get all registered fetchers."""
        return dict(cls._fetchers)

    @classmethod
    def fetch_from_all(
        cls,
        query: str,
        location: Optional[str] = None,
        max_results_per_source: int = 50
    ) -> List[Job]:
        """
        Fetch jobs from all registered sources.

        Args:
            query: Job search query
            location: Optional location
            max_results_per_source: Max results per source

        Returns:
            Combined list of jobs from all sources
        """
        if not cls._fetchers:
            logger.warning("No fetchers registered. Call register() first.")
            return []

        all_jobs = []

        for source_name, fetcher in cls._fetchers.items():
            try:
                logger.info(f"Fetching from {source_name}...")
                source_jobs = fetcher.fetch(
                    query=query,
                    location=location,
                    max_results=max_results_per_source,
                )
                all_jobs.extend(source_jobs)
                logger.info(f"{source_name}: returned {len(source_jobs)} jobs")
            except Exception as e:
                logger.error(f"Failed to fetch from {source_name}: {e}")
                continue

        logger.info(
            f"Total jobs fetched from {len(cls._fetchers)} sources: {len(all_jobs)}"
        )
        return all_jobs

    @classmethod
    def reset(cls) -> None:
        """Clear all registered fetchers. Useful for testing."""
        cls._fetchers = {}
