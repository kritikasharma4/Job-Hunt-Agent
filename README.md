# AI Job Hunting Agent 🤖

A scalable, modular Python agent for intelligent job matching using **Llama 3 8B Q4** (via Ollama).

**Status:** 🏗️ Scaffold Complete - Ready for Implementation

## Features

- ✅ **Modular Architecture** - SOLID principles, pluggable components
- ✅ **Local LLM Support** - Llama 3 8B Q4 via Ollama (no API costs)
- ✅ **Multi-Source Job Fetching** - LinkedIn, Indeed, and extensible to more
- ✅ **Intelligent Matching** - Skill, experience, and LLM-based relevance scoring
- ✅ **Flexible Filtering** - Salary, location, experience, keywords, deduplication
- ✅ **Profile Parsing** - Support for PDF, JSON, and text resumes
- ✅ **Application Tracking** - Track status of submitted applications
- ✅ **Type-Safe** - Full type hints throughout codebase

## Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) with Llama 3 8B Q4 model pulled
- Git

### Installation

```bash
# Clone repository
cd /Users/kritikasharma/Desktop/job-hunt-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull Llama 3 model with Ollama
ollama pull llama3
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your preferences
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3
# DEBUG=false
```

### Usage

```bash
# Basic job search
python main.py \
  --profile resume.pdf \
  --query "Python Developer" \
  --location "San Francisco" \
  --output results.json

# Advanced with multiple sources
python main.py \
  --profile resume.json \
  --query "Machine Learning Engineer" \
  --sources linkedin indeed \
  --min-score 0.7 \
  --debug
```

## Project Structure

```
job-hunt-agent/
├── config/              # Configuration management
├── models/              # Data models and schemas
├── llm/                 # LLM provider abstraction
│   ├── base.py         # LLMProvider interface
│   ├── ollama_provider.py    # Llama 3 via Ollama
│   └── openai_provider.py    # Alternative provider
├── profile/            # Resume/profile parsing
│   └── parser.py       # PDF, JSON, text parsers
├── jobs/fetchers/      # Job source integrations
│   └── base.py         # Fetcher interface & implementations
├── relevance/          # Matching & scoring algorithms
│   └── matcher.py      # Skill, experience, LLM matchers
├── filters/            # Job filtering pipelines
│   └── job_filters.py  # Salary, location, keyword filters
├── core/               # Main agent orchestration
│   ├── agent.py        # JobHuntingAgent orchestrator
│   └── executor.py     # Application tracking
├── tests/              # Test suite
├── main.py             # Entry point
└── requirements.txt    # Dependencies
```

## Architecture Highlights

### SOLID Design Principles

- **Single Responsibility**: Each module has one reason to change
- **Open/Closed**: Extensible without modifying existing code
- **Liskov Substitution**: All implementations are properly substitutable
- **Interface Segregation**: Clients depend only on needed methods
- **Dependency Inversion**: Depend on abstractions, not concrete classes

### Design Patterns

- **Strategy Pattern**: Swappable LLM providers, matchers, filters
- **Factory Pattern**: Create providers and components from config
- **Registry Pattern**: Manage multiple job sources
- **Composite Pattern**: Combine filters with AND/OR logic
- **Builder Pattern**: Construct agents with fluent API
- **Facade Pattern**: JobHuntingAgent simplifies complex workflows

### Key Components

#### `config/settings.py`
Centralized configuration using dataclasses. Load from environment variables:

```python
from config.settings import AppSettings

settings = AppSettings.from_env()
settings.llm.provider = "ollama"
settings.relevance.min_relevance_score = 0.7
```

#### `models/schemas.py`
Domain objects with clear responsibilities:
- `Job` - Job posting data
- `UserProfile` - Candidate profile
- `RelevanceScore` - Matching results
- `JobMatch` - Combined job + relevance
- `ApplicationRecord` - Application tracking

#### `llm/base.py` & `llm/ollama_provider.py`
Pluggable LLM interface:

```python
from llm.base import LLMProviderFactory
from config.settings import LLMConfig

config = LLMConfig(provider="ollama", model="llama3")
provider = LLMProviderFactory.create_provider(config)
response = provider.generate("Analyze these skills...")
```

#### `profile/parser.py`
Parse resumes in multiple formats:

```python
from profile.parser import ProfileParserFactory

parser = ProfileParserFactory.get_parser("resume.pdf")
profile = parser.parse("resume.pdf")
```

#### `jobs/fetchers/base.py`
Fetch jobs from multiple sources:

```python
from jobs.fetchers.base import JobFetcherRegistry, LinkedInJobFetcher

registry = JobFetcherRegistry()
registry.register(LinkedInJobFetcher())
jobs = registry.fetch_from_all("Python Developer", "San Francisco")
```

#### `relevance/matcher.py`
Multiple matching strategies:

```python
from relevance.matcher import HybridMatcher, SkillBasedMatcher, LLMBasedMatcher

matcher = HybridMatcher([
    SkillBasedMatcher(),
    LLMBasedMatcher(llm_provider)
])
scores = matcher.match(profile, job)
```

#### `filters/job_filters.py`
Chainable job filtering:

```python
from filters.job_filters import JobFilterPipeline, SalaryFilter, LocationFilter

pipeline = JobFilterPipeline([
    SalaryFilter(min_salary=50000, max_salary=150000),
    LocationFilter(allowed_locations=["San Francisco"]),
])
filtered_jobs, reasons = pipeline.apply(jobs, profile)
```

#### `core/agent.py`
Main orchestrator:

```python
from core.agent import JobHuntingAgent

# Construct with dependencies
agent = JobHuntingAgent(
    profile_parser=pdf_parser,
    job_fetchers=[linkedin_fetcher],
    relevance_scorer=hybrid_scorer,
    filter_pipeline=filter_pipeline,
    settings=settings
)

# Run complete pipeline
matches = agent.run_pipeline(
    profile_path="resume.pdf",
    query="Python Developer",
    location="San Francisco"
)
```

## Workflow

```
1. Load Profile
   resume.pdf → [ProfileParser] → UserProfile

2. Fetch Jobs
   "Python Developer" → [JobFetchers] → [Job, Job, ...]

3. Match & Score
   UserProfile + Jobs → [RelevanceMatcher] → [RelevanceScore, ...]

4. Filter
   [RelevanceScore, ...] → [FilterPipeline] → [JobMatch, ...]

5. Rank & Output
   [JobMatch, ...] → Results (JSON/CSV/Database)
```

## Configuration Examples

### Environment Variables
```bash
# Use Ollama with Llama 3
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3
export LLM_TEMPERATURE=0.7

# Relevance thresholds
export MIN_RELEVANCE_SCORE=0.6
export WEIGHT_SKILLS=0.3
export WEIGHT_EXPERIENCE=0.3

# Salary filter
export MIN_SALARY=50000
export MAX_SALARY=150000
```

### Settings in Code
```python
from config.settings import AppSettings, LLMConfig, FilterConfig

settings = AppSettings()
settings.llm = LLMConfig(provider="ollama", model="llama3")
settings.filter = FilterConfig(
    min_salary=50000,
    max_salary=150000,
    excluded_keywords=["relocation required"]
)
```

## Extending the Agent

### Add a New Job Source
```python
from jobs.fetchers.base import JobFetcher
from models.schemas import Job

class MyJobSourceFetcher(JobFetcher):
    def fetch(self, query, location=None, max_results=50, **filters):
        # Implementation
        return [Job(...), Job(...)]

    def validate_connection(self):
        return True
```

### Add a New Matching Strategy
```python
from relevance.matcher import RelevanceMatcher
from models.schemas import RelevanceScore

class CustomMatcher(RelevanceMatcher):
    def match(self, profile, job):
        # Implementation
        return RelevanceScore(overall_score=0.75, ...)

    def get_name(self):
        return "custom"
```

### Add a New Filter
```python
from filters.job_filters import JobFilter
from models.schemas import Job

class CustomFilter(JobFilter):
    def apply(self, jobs, profile):
        filtered = [j for j in jobs if ...]
        reasons = ["reason1", "reason2"]
        return filtered, reasons

    def get_name(self):
        return "custom"
```

## Dependencies

Key dependencies:
- **ollama** (0.1.45) - Local LLM integration
- **pydantic** (2.5.3) - Data validation
- **pdfplumber** (0.10.4) - PDF parsing
- **scikit-learn** (1.3.2) - ML algorithms
- **requests** (2.31.0) - HTTP requests
- **pandas** (2.1.4) - Data processing

See `requirements.txt` for complete list.

## Testing

Run tests:
```bash
pytest tests/ -v
pytest tests/ --cov=.  # With coverage
```

## Development

Code quality:
```bash
black .              # Format code
flake8 .             # Lint
mypy .               # Type checking
isort .              # Sort imports
```

## Roadmap

### Phase 1: ✅ Scaffold (Complete)
- Project structure
- Base classes and interfaces
- Configuration system
- Data models

### Phase 2: 🚧 Implementation (Next)
- LLM provider implementations
- Profile parsers
- Job fetchers
- Relevance matchers
- Filter implementations

### Phase 3: 🔮 Integration
- End-to-end testing
- Database persistence
- Web UI (optional)
- Cloud deployment

### Phase 4: 🎯 Enhancement
- Advanced NLP matching
- Learning from feedback
- Application automation
- Analytics dashboard

## Environment

- Python 3.10+
- macOS, Linux, Windows
- 8GB RAM minimum (for Llama 3)
- Internet connection for job fetching

## Troubleshooting

**Ollama not connecting?**
```bash
# Start Ollama
ollama serve

# In another terminal, pull model
ollama pull llama3

# Test connection
curl http://localhost:11434/api/tags
```

**Profile parsing fails?**
- Ensure PDF is not scanned image (need OCR)
- Validate JSON format matches expected schema
- Text files should have clear section headers

**Low relevance scores?**
- Adjust weights in config: `WEIGHT_SKILLS`, `WEIGHT_EXPERIENCE`
- Lower threshold: `MIN_RELEVANCE_SCORE=0.5`
- Use `HybridMatcher` combining multiple strategies

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Areas for help:
- [ ] Implement job fetchers (LinkedIn, Indeed, etc.)
- [ ] Add more profile parsers (DOCX, LinkedIn profile)
- [ ] Implement matching algorithms
- [ ] Write tests
- [ ] Create web UI

## Support

- 📚 See `PROJECT_STRUCTURE.md` for detailed architecture
- 💬 Check docstrings in source files
- 🐛 Open issues for bugs
- 📧 Questions? Check examples in main.py

---

**Built with ❤️ for intelligent job hunting using local LLMs**
