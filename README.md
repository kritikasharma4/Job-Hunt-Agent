# AI Job Hunting Agent

An intelligent job search and matching platform that fetches real job listings, scores them against your resume, and tracks applications — all through a modern web interface.

## What It Does

1. **Upload your resume** (PDF/JSON/TXT) — auto-parses into a structured profile
2. **Search real jobs** from Google Jobs via JSearch API with filters (experience, type, recency, remote)
3. **AI-powered matching** — scores each job against your skills, experience, and preferences
4. **Track applications** — manage your pipeline from applied to offer

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Tailwind CSS 4, Vite, React Router 7 |
| **Backend** | FastAPI, SQLAlchemy, SQLite |
| **Job Data** | JSearch API (RapidAPI) — real listings from Google Jobs |
| **Matching** | Skill-based + Experience-based hybrid scoring |
| **Resume Parsing** | PDF (pdfplumber), JSON, TXT with optional LLM enhancement |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [RapidAPI key](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) (free tier: 500 requests/month)

### Installation

```bash
# Clone the repo
git clone https://github.com/kritikasharma4/Job-Hunt-Agent.git
cd Job-Hunt-Agent

# Python dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env`:

```
RAPIDAPI_KEY=your_rapidapi_key_here
LLM_PROVIDER=ollama       # optional, for enhanced matching
LLM_MODEL=llama3           # optional
```

### Run

```bash
# Terminal 1: Backend (auto-reloads)
python run_api.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open **http://localhost:5173** in your browser.

### CLI Mode (no UI needed)

```bash
python main.py \
  --profile resume.pdf \
  --query "Python Developer" \
  --location "San Francisco" \
  --output results.json
```

## Features

### Job Search with Filters

- **Experience Level** — Entry, Mid, Senior, Lead
- **Employment Type** — Full-time, Part-time, Contract, Internship
- **Date Posted** — Today, Last 3 Days, Last Week, Last Month
- **Remote Only** toggle
- **Min Score** slider to filter low-relevance results

### Profile Management

- Upload resume (PDF/JSON/TXT) to auto-fill profile
- Edit all fields: skills, work experience, education, certifications
- Set preferences: salary range, job levels, remote preference, locations

### Matching & Scoring

Each job is scored across multiple dimensions:

| Score | What It Measures |
|-------|-----------------|
| **Skills** | Overlap between your skills and job requirements |
| **Experience** | Years of experience vs job expectations |
| **Location** | Match with your preferred locations |
| **Salary** | Alignment with your salary range |
| **Level** | Job seniority vs your preferred levels |

### Application Tracking

- One-click apply from matched jobs
- Status tracking: Pending, Applied, Interview, Offer, Rejected
- Notes and history per application

### Dashboard

- Total searches, jobs found, matches, applications
- Applications breakdown by status
- Average match score
- Recent top matches

## Project Structure

```
job-hunt-agent/
├── api/                         # FastAPI backend
│   ├── app.py                   # App factory (CORS, routers, startup)
│   ├── dependencies.py          # Dependency injection
│   ├── schemas.py               # Pydantic request/response models
│   └── routers/
│       ├── profiles.py          # Profile CRUD + resume upload
│       ├── jobs.py              # Job search (triggers pipeline)
│       ├── matches.py           # Match results listing
│       └── applications.py      # Application tracking
├── core/                        # Agent orchestration
│   ├── agent.py                 # JobHuntingAgent + AgentBuilder
│   └── executor.py              # Application tracking
├── config/settings.py           # Centralized configuration
├── db/                          # Database layer
│   ├── engine.py                # SQLAlchemy engine + sessions
│   ├── models.py                # ORM table models
│   └── repository.py            # CRUD operations
├── models/schemas.py            # Domain dataclasses
├── jobs/fetchers/               # Job source integrations
│   ├── base.py                  # Fetcher interface
│   ├── jsearch.py               # JSearch API (real jobs)
│   └── demo.py                  # Demo data generator
├── relevance/matcher.py         # Matching algorithms
├── filters/job_filters.py       # Job filtering pipeline
├── profile/parser.py            # Resume parsers (PDF, JSON, TXT)
├── llm/                         # Optional LLM integration
│   ├── base.py                  # LLM provider interface
│   └── ollama_provider.py       # Ollama (Llama 3) provider
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── pages/               # Dashboard, Profile, Search, Applications
│   │   ├── components/          # Reusable UI components
│   │   └── api/client.js        # Axios API wrapper
│   ├── package.json
│   └── vite.config.js
├── tests/                       # Test suite
├── main.py                      # CLI entry point
├── run_api.py                   # FastAPI entry point
└── requirements.txt
```

## API Endpoints

### Profiles

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/profiles` | Create profile from JSON |
| POST | `/api/profiles/upload` | Upload resume file and auto-parse |
| GET | `/api/profiles/current` | Get current profile |
| GET | `/api/profiles/{user_id}` | Get profile by ID |
| PUT | `/api/profiles/{user_id}` | Update profile |

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/jobs/search` | Search jobs with full pipeline |
| GET | `/api/jobs` | List saved jobs |
| GET | `/api/jobs/{job_id}` | Get job details |

### Matches

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/matches` | List all matches |
| GET | `/api/matches/{id}` | Match details |
| DELETE | `/api/matches/{id}` | Dismiss match |

### Applications

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/applications` | Create application |
| GET | `/api/applications` | List applications |
| PATCH | `/api/applications/{id}` | Update status |
| DELETE | `/api/applications/{id}` | Delete application |

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard` | Aggregate stats |

Swagger docs available at **http://localhost:8000/docs** when the server is running.

## Architecture

### Design Patterns

- **Strategy** — Swappable matchers, fetchers, filters, LLM providers
- **Builder** — `AgentBuilder` for fluent agent construction
- **Factory** — `ProfileParserFactory` for format detection
- **Pipeline** — `JobFilterPipeline` chains filters sequentially
- **Facade** — `JobHuntingAgent` orchestrates the full workflow
- **Repository** — Database CRUD abstracted from business logic

### Pipeline Flow

```
Resume Upload → ProfileParser → UserProfile (DB)
                                     ↓
Search Query → JSearch API → [Jobs] → RelevanceScorer → [Ranked Matches] → DB
                                          ↑
                                     UserProfile
```

### Extending

**Add a new job source:**

```python
from jobs.fetchers.base import JobFetcher

class MyFetcher(JobFetcher):
    def fetch(self, query, location=None, max_results=50, **filters):
        return [Job(...)]

    def validate_connection(self):
        return True
```

**Add a new matching strategy:**

```python
from relevance.matcher import RelevanceMatcher

class CustomMatcher(RelevanceMatcher):
    def match(self, profile, job):
        return RelevanceScore(overall_score=0.75, ...)

    def get_name(self):
        return "custom"
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RAPIDAPI_KEY` | Yes | — | JSearch API key from RapidAPI |
| `DATABASE_URL` | No | `sqlite:///job_hunt.db` | Database connection URL |
| `LLM_PROVIDER` | No | `ollama` | LLM provider (ollama or none) |
| `LLM_MODEL` | No | `llama3` | LLM model name |
| `DEBUG` | No | `false` | Enable debug logging |

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=.    # with coverage
```

## License

MIT License

---

Built for smarter job hunting.
