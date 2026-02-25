"""
Demo job fetcher that generates realistic sample job listings.

Used when real scraping sources (LinkedIn, Indeed) are blocked by anti-bot measures.
Generates query-relevant jobs so the full pipeline (scoring, matching, filtering)
can be demonstrated end-to-end.
"""

import hashlib
import logging
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from models.schemas import Job, Location, Salary, JobLevel, EmploymentType
from jobs.fetchers.base import JobFetcher

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample data pools
# ---------------------------------------------------------------------------

COMPANIES = [
    "Google", "Meta", "Amazon", "Apple", "Microsoft", "Netflix",
    "Stripe", "Shopify", "Airbnb", "Uber", "Lyft", "Spotify",
    "Salesforce", "Adobe", "Oracle", "IBM", "Intel", "Cisco",
    "Twitter", "LinkedIn", "Snap", "Pinterest", "Reddit", "Discord",
    "Databricks", "Snowflake", "Datadog", "HashiCorp", "Confluent",
    "Palantir", "Figma", "Notion", "Canva", "Vercel", "Supabase",
    "Twilio", "Cloudflare", "Elastic", "MongoDB", "Atlassian",
]

CITIES = [
    ("San Francisco", "CA", "US"),
    ("New York", "NY", "US"),
    ("Seattle", "WA", "US"),
    ("Austin", "TX", "US"),
    ("Chicago", "IL", "US"),
    ("Boston", "MA", "US"),
    ("Denver", "CO", "US"),
    ("Los Angeles", "CA", "US"),
    ("Portland", "OR", "US"),
    ("Miami", "FL", "US"),
    ("Atlanta", "GA", "US"),
    ("Toronto", "ON", "CA"),
    ("London", "", "UK"),
    ("Berlin", "", "DE"),
    ("Bangalore", "", "IN"),
]

# Templates keyed by domain keyword → (titles, skills, descriptions)
JOB_TEMPLATES = {
    "python": {
        "titles": [
            "Python Developer", "Senior Python Engineer", "Python Backend Developer",
            "Python Software Engineer", "Python Full Stack Developer",
            "Python Data Engineer", "Python API Developer",
        ],
        "skills": [
            "Python", "Django", "Flask", "FastAPI", "PostgreSQL", "Redis",
            "Docker", "AWS", "REST APIs", "Celery", "SQLAlchemy", "pytest",
            "Git", "CI/CD", "Kubernetes", "Microservices",
        ],
        "description_template": (
            "We are looking for a {title} to join our engineering team. "
            "You will design, build, and maintain scalable {focus} using Python. "
            "The ideal candidate has strong experience with {skill1}, {skill2}, "
            "and {skill3}. You'll work closely with cross-functional teams to "
            "deliver high-quality software solutions."
        ),
        "focus_areas": ["backend services", "APIs", "data pipelines", "microservices"],
    },
    "data": {
        "titles": [
            "Data Scientist", "Senior Data Analyst", "Data Engineer",
            "Machine Learning Engineer", "ML Platform Engineer",
            "Analytics Engineer", "Business Intelligence Developer",
        ],
        "skills": [
            "Python", "SQL", "Pandas", "NumPy", "Scikit-learn", "TensorFlow",
            "PyTorch", "Spark", "Airflow", "dbt", "Snowflake", "Tableau",
            "Statistics", "A/B Testing", "ETL", "Data Modeling",
        ],
        "description_template": (
            "Join our data team as a {title}. You will {focus} to drive "
            "business decisions. Strong skills in {skill1}, {skill2}, and "
            "{skill3} are essential. Experience with large-scale data "
            "processing and analytical tools is a plus."
        ),
        "focus_areas": [
            "build ML models", "analyze large datasets",
            "design data pipelines", "create dashboards and reports",
        ],
    },
    "frontend": {
        "titles": [
            "Frontend Developer", "Senior React Developer", "UI Engineer",
            "Frontend Architect", "React Native Developer",
            "JavaScript Developer", "TypeScript Engineer",
        ],
        "skills": [
            "JavaScript", "TypeScript", "React", "Next.js", "Vue.js",
            "HTML/CSS", "Tailwind CSS", "Redux", "GraphQL", "Webpack",
            "Node.js", "Jest", "Cypress", "Figma", "Responsive Design",
        ],
        "description_template": (
            "We're hiring a {title} to build beautiful, performant user "
            "interfaces. You'll work with {skill1}, {skill2}, and {skill3} "
            "to {focus}. Passion for clean code and great UX is a must."
        ),
        "focus_areas": [
            "create responsive web applications",
            "build component libraries",
            "improve application performance",
            "implement pixel-perfect designs",
        ],
    },
    "devops": {
        "titles": [
            "DevOps Engineer", "Site Reliability Engineer", "Platform Engineer",
            "Cloud Infrastructure Engineer", "Senior SRE",
            "Kubernetes Engineer", "Infrastructure Architect",
        ],
        "skills": [
            "AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform",
            "Ansible", "Jenkins", "GitHub Actions", "Prometheus", "Grafana",
            "Linux", "Bash", "Python", "CI/CD", "Networking",
        ],
        "description_template": (
            "As a {title}, you'll {focus} for our cloud-native platform. "
            "Strong experience with {skill1}, {skill2}, and {skill3} is "
            "required. You'll ensure our systems are reliable, scalable, "
            "and secure."
        ),
        "focus_areas": [
            "manage cloud infrastructure",
            "build CI/CD pipelines",
            "improve system reliability",
            "automate deployment processes",
        ],
    },
    "default": {
        "titles": [
            "Software Engineer", "Senior Software Developer",
            "Full Stack Developer", "Backend Engineer",
            "Software Development Engineer", "Application Developer",
            "Systems Engineer",
        ],
        "skills": [
            "Python", "Java", "JavaScript", "TypeScript", "Go", "SQL",
            "REST APIs", "Docker", "Git", "Agile", "CI/CD", "AWS",
            "Microservices", "PostgreSQL", "Redis", "Linux",
        ],
        "description_template": (
            "We're looking for a {title} to help us {focus}. "
            "The ideal candidate has experience with {skill1}, {skill2}, "
            "and {skill3}. You'll contribute to the design and development "
            "of scalable software systems in a collaborative environment."
        ),
        "focus_areas": [
            "build scalable applications",
            "develop new product features",
            "improve system architecture",
            "modernize legacy systems",
        ],
    },
}

SALARY_RANGES = {
    "junior": (70000, 110000),
    "mid": (100000, 150000),
    "senior": (140000, 200000),
    "lead": (170000, 250000),
}


def _match_template(query: str) -> dict:
    """Pick the best job template based on the search query."""
    query_lower = query.lower()
    for key, template in JOB_TEMPLATES.items():
        if key == "default":
            continue
        if key in query_lower:
            return template
    # Check title matches
    for key, template in JOB_TEMPLATES.items():
        if key == "default":
            continue
        for title in template["titles"]:
            if any(word in query_lower for word in title.lower().split()):
                return template
    return JOB_TEMPLATES["default"]


class DemoJobFetcher(JobFetcher):
    """
    Demo fetcher that generates realistic job listings for any search query.

    Useful for development/testing when real scraping sources are blocked.
    The generated jobs are realistic enough to demonstrate the full scoring,
    matching, and filtering pipeline.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("demo", config)

    def fetch(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **filters,
    ) -> List[Job]:
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        template = _match_template(query)
        count = min(max_results, random.randint(8, 20))

        logger.info(
            f"Demo: generating {count} jobs for query='{query}', location='{location}'"
        )

        used_companies = set()
        jobs: List[Job] = []

        for i in range(count):
            company = random.choice(COMPANIES)
            while company in used_companies and len(used_companies) < len(COMPANIES):
                company = random.choice(COMPANIES)
            used_companies.add(company)

            title = random.choice(template["titles"])
            # Vary the title with the query keyword if not already present
            query_words = query.strip().split()
            if query_words and query_words[0].lower() not in title.lower():
                if random.random() < 0.3:
                    title = f"{query.strip().title()} — {title}"

            # Location
            if location and "remote" in location.lower():
                loc = Location(city="", state="", country="US", remote=True)
            elif location:
                loc_parts = [p.strip() for p in location.split(",")]
                loc = Location(
                    city=loc_parts[0] if loc_parts else "",
                    state=loc_parts[1] if len(loc_parts) > 1 else "",
                    country=loc_parts[2] if len(loc_parts) > 2 else "US",
                    remote=random.random() < 0.3,
                )
            else:
                city_data = random.choice(CITIES)
                loc = Location(
                    city=city_data[0], state=city_data[1], country=city_data[2],
                    remote=random.random() < 0.4,
                )

            # Skills subset for requirements
            num_skills = random.randint(4, 8)
            required_skills = random.sample(
                template["skills"], min(num_skills, len(template["skills"]))
            )
            nice_to_haves = random.sample(
                [s for s in template["skills"] if s not in required_skills],
                min(3, len(template["skills"]) - len(required_skills)),
            )

            # Description
            sampled = random.sample(required_skills, min(3, len(required_skills)))
            description = template["description_template"].format(
                title=title,
                focus=random.choice(template["focus_areas"]),
                skill1=sampled[0] if len(sampled) > 0 else "relevant technologies",
                skill2=sampled[1] if len(sampled) > 1 else "modern tools",
                skill3=sampled[2] if len(sampled) > 2 else "best practices",
            )

            # Salary
            is_senior = "senior" in title.lower() or "lead" in title.lower()
            if is_senior:
                sal_range = random.choice([SALARY_RANGES["senior"], SALARY_RANGES["lead"]])
            else:
                sal_range = random.choice([SALARY_RANGES["mid"], SALARY_RANGES["senior"]])
            min_sal = random.randint(sal_range[0] // 1000, (sal_range[0] + 20000) // 1000) * 1000
            max_sal = min_sal + random.randint(20, 60) * 1000
            salary = Salary(
                min_amount=float(min_sal),
                max_amount=float(max_sal),
                currency="USD",
                period="yearly",
            )

            # Level
            if "senior" in title.lower():
                level = JobLevel.SENIOR
            elif "lead" in title.lower() or "architect" in title.lower():
                level = JobLevel.LEAD
            elif "junior" in title.lower() or "entry" in title.lower():
                level = JobLevel.ENTRY
            else:
                level = random.choice([JobLevel.MID, JobLevel.SENIOR])

            # Posted date (random within last 14 days)
            posted_date = datetime.now() - timedelta(days=random.randint(0, 14))

            # Job ID
            raw_id = f"demo:{company}:{title}:{i}"
            job_id = hashlib.md5(raw_id.encode()).hexdigest()[:12]

            jobs.append(Job(
                job_id=job_id,
                title=title,
                company=company,
                description=description,
                location=loc,
                requirements=required_skills,
                nice_to_haves=nice_to_haves,
                level=level,
                employment_type=EmploymentType.FULL_TIME,
                salary=salary,
                url=f"https://careers.example.com/{company.lower().replace(' ', '-')}/{job_id}",
                source="demo",
                posted_date=posted_date,
            ))

        logger.info(f"Demo: generated {len(jobs)} jobs")
        return jobs

    def validate_connection(self) -> bool:
        return True
