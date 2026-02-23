"""
Resume and profile parsing module.

Extracts structured data from resumes, CVs, and profile documents.
Supports PDF, JSON (UserProfile, JSON Resume, LinkedIn export), and plain text formats.
PDF and text parsing use LLM-based extraction via any LLMProvider implementation.
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from models.schemas import (
    UserProfile, Location, Salary, WorkExperience, Education, JobLevel
)
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants for LLM-based resume extraction
# ---------------------------------------------------------------------------

RESUME_EXTRACTION_SCHEMA = {
    "full_name": "string - the person's full name",
    "email": "string - email address",
    "phone": "string or null - phone number",
    "summary": "string - professional summary or objective",
    "location": {
        "city": "string",
        "state": "string",
        "country": "string"
    },
    "skills": ["string - list of technical and professional skills"],
    "work_experience": [
        {
            "company": "string",
            "position": "string",
            "start_date": "string - ISO format YYYY-MM-DD or YYYY-MM-01",
            "end_date": "string or null - ISO format, null if current",
            "description": "string",
            "skills": ["string - skills used in this role"],
            "is_current": "boolean"
        }
    ],
    "education": [
        {
            "institution": "string",
            "degree": "string",
            "field": "string - field of study",
            "graduation_date": "string or null - ISO format",
            "gpa": "float or null",
            "honors": "string"
        }
    ],
    "certifications": ["string - list of certifications"]
}

RESUME_SYSTEM_PROMPT = (
    "You are an expert resume parser. Extract structured data from the following "
    "resume text. Be precise and extract all available information. If a field is "
    "not found in the resume, use null or empty string as appropriate. For dates, "
    "use ISO format (YYYY-MM-DD or YYYY-MM-01 if only month/year is available). "
    "For skills, extract both explicitly listed skills and skills mentioned in "
    "work experience descriptions."
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a date string into a datetime, returning None on failure."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    if date_str.lower() in ("null", "none", "present", "current", ""):
        return None
    from dateutil import parser as date_parser
    try:
        return date_parser.parse(date_str)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date: {date_str}")
        return None


def _parse_linkedin_date(date_dict: Optional[Dict]) -> Optional[datetime]:
    """Convert LinkedIn date format {'year': 2020, 'month': 3} to datetime."""
    if not date_dict or not isinstance(date_dict, dict):
        return None
    year = date_dict.get("year")
    month = date_dict.get("month", 1)
    if year:
        try:
            return datetime(int(year), int(month), 1)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse LinkedIn date: {date_dict}")
            return None
    return None


def _dict_to_user_profile(data: Dict[str, Any]) -> UserProfile:
    """
    Convert a raw dictionary into a UserProfile dataclass.

    Handles type construction for nested objects (Location, WorkExperience, Education).
    Defensive against missing or malformed fields.
    """
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()

    if not full_name:
        raise ValueError("full_name is required but was empty or missing")
    if not email:
        raise ValueError("email is required but was empty or missing")

    # Parse location
    location = None
    loc_data = data.get("location")
    if loc_data and isinstance(loc_data, dict):
        location = Location(
            city=loc_data.get("city", ""),
            state=loc_data.get("state", ""),
            country=loc_data.get("country", ""),
            remote=loc_data.get("remote", False),
        )

    # Parse work experience
    work_experience = []
    for exp_data in data.get("work_experience", []):
        if not isinstance(exp_data, dict):
            continue
        start_date = _parse_date(exp_data.get("start_date"))
        if not start_date:
            logger.warning(
                f"Skipping work experience at {exp_data.get('company', 'unknown')}: "
                f"no valid start_date"
            )
            continue
        work_experience.append(WorkExperience(
            company=exp_data.get("company", ""),
            position=exp_data.get("position", ""),
            start_date=start_date,
            end_date=_parse_date(exp_data.get("end_date")),
            description=exp_data.get("description", ""),
            skills=exp_data.get("skills", []) if isinstance(exp_data.get("skills"), list) else [],
            is_current=bool(exp_data.get("is_current", False)),
        ))

    # Parse education
    education = []
    for edu_data in data.get("education", []):
        if not isinstance(edu_data, dict):
            continue
        education.append(Education(
            institution=edu_data.get("institution", ""),
            degree=edu_data.get("degree", ""),
            field=edu_data.get("field", ""),
            graduation_date=_parse_date(edu_data.get("graduation_date")),
            gpa=_safe_float(edu_data.get("gpa")),
            honors=edu_data.get("honors", ""),
        ))

    # Parse skills (deduplicate)
    raw_skills = data.get("skills", [])
    skills = list(dict.fromkeys(
        s.strip() for s in raw_skills if isinstance(s, str) and s.strip()
    ))

    # Parse certifications
    raw_certs = data.get("certifications", [])
    certifications = [
        c.strip() for c in raw_certs if isinstance(c, str) and c.strip()
    ]

    return UserProfile(
        user_id=data.get("user_id", str(uuid.uuid4())),
        full_name=full_name,
        email=email,
        phone=data.get("phone") if isinstance(data.get("phone"), str) else None,
        summary=data.get("summary", ""),
        location=location,
        skills=skills,
        work_experience=work_experience,
        education=education,
        certifications=certifications,
        preferred_job_levels=_parse_job_levels(data.get("preferred_job_levels", [])),
        preferred_locations=_parse_locations(data.get("preferred_locations", [])),
        preferred_salary_range=_parse_salary(data.get("preferred_salary_range")),
        willing_to_relocate=bool(data.get("willing_to_relocate", False)),
        remote_preference=data.get("remote_preference", "flexible"),
        metadata=data.get("metadata", {}),
    )


def _safe_float(value) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_job_levels(levels: list) -> List[JobLevel]:
    """Parse a list of job level strings into JobLevel enums."""
    if not isinstance(levels, list):
        return []
    result = []
    for level in levels:
        if isinstance(level, str):
            try:
                result.append(JobLevel(level.lower()))
            except ValueError:
                logger.warning(f"Unknown job level: {level}")
    return result


def _parse_locations(locations: list) -> List[Location]:
    """Parse a list of location dicts into Location objects."""
    if not isinstance(locations, list):
        return []
    result = []
    for loc in locations:
        if isinstance(loc, dict):
            result.append(Location(
                city=loc.get("city", ""),
                state=loc.get("state", ""),
                country=loc.get("country", ""),
                remote=loc.get("remote", False),
            ))
    return result


def _parse_salary(salary_data) -> Optional[Salary]:
    """Parse salary dict into Salary object."""
    if not salary_data or not isinstance(salary_data, dict):
        return None
    return Salary(
        min_amount=_safe_float(salary_data.get("min_amount")),
        max_amount=_safe_float(salary_data.get("max_amount")),
        currency=salary_data.get("currency", "USD"),
        period=salary_data.get("period", "yearly"),
    )


def _extract_profile_from_text(raw_text: str, llm_provider: LLMProvider) -> UserProfile:
    """
    Use an LLM provider to extract structured profile data from raw resume text.

    Args:
        raw_text: The raw text content of the resume.
        llm_provider: An LLMProvider instance to use for extraction.

    Returns:
        A UserProfile dataclass populated with extracted data.

    Raises:
        ValueError: If extraction or parsing fails.
        ConnectionError: If the LLM service is unreachable.
    """
    prompt = (
        "Parse the following resume and extract structured information:\n\n"
        "---BEGIN RESUME---\n"
        f"{raw_text}\n"
        "---END RESUME---\n\n"
        "Extract all available fields according to the schema provided."
    )

    data = llm_provider.generate_with_structured_output(
        prompt=prompt,
        output_schema=RESUME_EXTRACTION_SCHEMA,
        system_prompt=RESUME_SYSTEM_PROMPT,
    )

    return _dict_to_user_profile(data)


# ---------------------------------------------------------------------------
# Parser classes
# ---------------------------------------------------------------------------

class ProfileParser(ABC):
    """
    Abstract base class for profile/resume parsers.

    Responsibility: Defines interface for parsing various resume formats
    (PDF, DOCX, TXT, JSON) into structured UserProfile objects.
    Follows the Strategy Pattern for extensibility.
    """

    @abstractmethod
    def parse(self, file_path: str) -> UserProfile:
        """
        Parse a resume/profile file.

        Args:
            file_path: Path to the resume file

        Returns:
            Structured UserProfile object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported or parsing fails
        """
        pass

    @abstractmethod
    def supports_format(self, file_path: str) -> bool:
        """
        Check if parser supports the file format.

        Args:
            file_path: Path to the file

        Returns:
            True if parser can handle this file format
        """
        pass


class PDFProfileParser(ProfileParser):
    """
    Parser for PDF resumes.

    Responsibility: Extracts text from PDF resume documents using pdfplumber,
    then sends the text to an LLM for structured data extraction.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider

    def parse(self, file_path: str) -> UserProfile:
        """
        Parse PDF resume file.

        Args:
            file_path: Path to PDF resume

        Returns:
            Structured UserProfile

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If PDF is invalid or parsing fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        if not self.supports_format(file_path):
            raise ValueError(f"Not a PDF file: {file_path}")
        if self.llm_provider is None:
            raise ValueError(
                "LLM provider required for PDF parsing. "
                "Pass an LLMProvider instance to PDFProfileParser constructor."
            )

        import pdfplumber

        text_content = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {file_path}: {e}")
            raise ValueError(f"Failed to read PDF file: {e}") from e

        if not text_content.strip():
            raise ValueError(f"No text could be extracted from PDF: {file_path}")

        logger.info(f"Extracted {len(text_content)} characters from PDF: {file_path}")

        try:
            profile = _extract_profile_from_text(text_content, self.llm_provider)
            logger.info(f"Successfully parsed PDF profile for: {profile.full_name}")
            return profile
        except (ConnectionError, RuntimeError) as e:
            logger.error(f"LLM extraction failed for PDF {file_path}: {e}")
            raise ValueError(f"Failed to extract profile from PDF: {e}") from e

    def supports_format(self, file_path: str) -> bool:
        """Check if file is PDF format."""
        return Path(file_path).suffix.lower() == ".pdf"


class JSONProfileParser(ProfileParser):
    """
    Parser for JSON profile data.

    Responsibility: Loads and validates user profiles from JSON format.
    Supports three formats: direct UserProfile schema, JSON Resume standard,
    and LinkedIn JSON export.
    """

    def parse(self, file_path: str) -> UserProfile:
        """
        Parse JSON profile file.

        Args:
            file_path: Path to JSON profile file

        Returns:
            Structured UserProfile

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or missing required fields
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        if not self.supports_format(file_path):
            raise ValueError(f"Not a JSON file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to read JSON file: {e}") from e

        format_type = self._detect_json_format(data)
        logger.info(f"Detected JSON format: {format_type} for {file_path}")

        if format_type == "user_profile":
            profile = self._parse_user_profile_format(data)
        elif format_type == "json_resume":
            profile = self._parse_json_resume_format(data)
        elif format_type == "linkedin":
            profile = self._parse_linkedin_format(data)
        else:
            raise ValueError(
                f"Unrecognized JSON format in {file_path}. "
                f"Expected UserProfile, JSON Resume, or LinkedIn export format."
            )

        logger.info(f"Successfully parsed JSON profile for: {profile.full_name}")
        return profile

    def supports_format(self, file_path: str) -> bool:
        """Check if file is JSON format."""
        return Path(file_path).suffix.lower() == ".json"

    def _detect_json_format(self, data: Dict[str, Any]) -> str:
        """Detect the JSON format based on key signatures."""
        if not isinstance(data, dict):
            return "unknown"

        # UserProfile direct schema (has user_id)
        if "user_id" in data and "full_name" in data:
            return "user_profile"

        # JSON Resume standard (has "basics" top-level key)
        if "basics" in data and isinstance(data["basics"], dict):
            return "json_resume"

        # LinkedIn export (has firstName/lastName or positions)
        if ("firstName" in data and "lastName" in data) or \
           ("headline" in data and "positions" in data):
            return "linkedin"

        # Simplified UserProfile (full_name + email but no user_id)
        if "full_name" in data and "email" in data:
            return "user_profile"

        return "unknown"

    def _parse_user_profile_format(self, data: Dict[str, Any]) -> UserProfile:
        """Parse data that matches the UserProfile schema directly."""
        return _dict_to_user_profile(data)

    def _parse_json_resume_format(self, data: Dict[str, Any]) -> UserProfile:
        """
        Parse JSON Resume standard format (jsonresume.org).

        Maps JSON Resume fields to UserProfile schema.
        """
        basics = data.get("basics", {})

        # Parse location
        loc = basics.get("location", {})
        location = None
        if loc and isinstance(loc, dict):
            location = {
                "city": loc.get("city", ""),
                "state": loc.get("region", ""),
                "country": loc.get("countryCode", ""),
            }

        # Parse work experience
        work_experience = []
        for work in data.get("work", []):
            if not isinstance(work, dict):
                continue
            # Combine summary and highlights into description
            description = work.get("summary", "")
            highlights = work.get("highlights", [])
            if highlights and isinstance(highlights, list):
                description += "\n" + "\n".join(f"- {h}" for h in highlights)

            has_end = bool(work.get("endDate"))
            work_experience.append({
                "company": work.get("company") or work.get("name", ""),
                "position": work.get("position", ""),
                "start_date": work.get("startDate"),
                "end_date": work.get("endDate"),
                "description": description.strip(),
                "skills": [],
                "is_current": not has_end,
            })

        # Parse education
        education = []
        for edu in data.get("education", []):
            if not isinstance(edu, dict):
                continue
            education.append({
                "institution": edu.get("institution", ""),
                "degree": edu.get("studyType", ""),
                "field": edu.get("area", ""),
                "graduation_date": edu.get("endDate"),
                "gpa": edu.get("gpa"),
                "honors": ", ".join(edu.get("courses", [])) if edu.get("courses") else "",
            })

        # Parse skills (flatten name + keywords)
        skills = []
        for skill_entry in data.get("skills", []):
            if isinstance(skill_entry, dict):
                name = skill_entry.get("name", "")
                if name:
                    skills.append(name)
                keywords = skill_entry.get("keywords", [])
                if isinstance(keywords, list):
                    skills.extend(k for k in keywords if isinstance(k, str))
            elif isinstance(skill_entry, str):
                skills.append(skill_entry)

        # Parse certifications
        certifications = []
        for cert in data.get("certificates", data.get("certifications", [])):
            if isinstance(cert, dict):
                name = cert.get("name", "")
                if name:
                    certifications.append(name)
            elif isinstance(cert, str):
                certifications.append(cert)

        profile_data = {
            "full_name": basics.get("name", ""),
            "email": basics.get("email", ""),
            "phone": basics.get("phone"),
            "summary": basics.get("summary", ""),
            "location": location,
            "skills": skills,
            "work_experience": work_experience,
            "education": education,
            "certifications": certifications,
        }

        return _dict_to_user_profile(profile_data)

    def _parse_linkedin_format(self, data: Dict[str, Any]) -> UserProfile:
        """
        Parse LinkedIn JSON export format.

        Maps LinkedIn-specific field names and date structures to UserProfile.
        """
        first = data.get("firstName", "")
        last = data.get("lastName", "")
        full_name = f"{first} {last}".strip()

        # Parse location from LinkedIn format
        location = None
        loc_data = data.get("location", {})
        if isinstance(loc_data, dict):
            loc_name = loc_data.get("name", "")
            parts = [p.strip() for p in loc_name.split(",")]
            location = {
                "city": parts[0] if len(parts) > 0 else "",
                "state": parts[1] if len(parts) > 1 else "",
                "country": parts[2] if len(parts) > 2 else "US",
            }
        elif isinstance(loc_data, str):
            parts = [p.strip() for p in loc_data.split(",")]
            location = {
                "city": parts[0] if len(parts) > 0 else "",
                "state": parts[1] if len(parts) > 1 else "",
                "country": parts[2] if len(parts) > 2 else "US",
            }

        # Parse work experience
        work_experience = []
        positions = data.get("positions", {})
        position_values = positions.get("values", []) if isinstance(positions, dict) else []
        for pos in position_values:
            if not isinstance(pos, dict):
                continue
            company_data = pos.get("company", {})
            company_name = company_data.get("name", "") if isinstance(company_data, dict) else str(company_data)

            start = _parse_linkedin_date(pos.get("startDate"))
            end = _parse_linkedin_date(pos.get("endDate"))
            is_current = bool(pos.get("isCurrent", False))

            if not start:
                logger.warning(f"Skipping LinkedIn position at {company_name}: no start date")
                continue

            work_experience.append({
                "company": company_name,
                "position": pos.get("title", ""),
                "start_date": start.isoformat() if start else None,
                "end_date": end.isoformat() if end else None,
                "description": pos.get("summary", ""),
                "skills": [],
                "is_current": is_current,
            })

        # Parse education
        education = []
        educations = data.get("educations", {})
        edu_values = educations.get("values", []) if isinstance(educations, dict) else []
        for edu in edu_values:
            if not isinstance(edu, dict):
                continue
            grad_date = _parse_linkedin_date(edu.get("endDate"))
            education.append({
                "institution": edu.get("schoolName", ""),
                "degree": edu.get("degree", ""),
                "field": edu.get("fieldOfStudy", ""),
                "graduation_date": grad_date.isoformat() if grad_date else None,
                "gpa": edu.get("grade"),
                "honors": edu.get("activities", ""),
            })

        # Parse skills
        skills = []
        skills_data = data.get("skills", {})
        skill_values = skills_data.get("values", []) if isinstance(skills_data, dict) else []
        for skill in skill_values:
            if isinstance(skill, dict):
                skill_inner = skill.get("skill", {})
                name = skill_inner.get("name", "") if isinstance(skill_inner, dict) else str(skill_inner)
                if name:
                    skills.append(name)
            elif isinstance(skill, str):
                skills.append(skill)

        # Parse certifications
        certifications = []
        certs_data = data.get("certifications", {})
        cert_values = certs_data.get("values", []) if isinstance(certs_data, dict) else []
        for cert in cert_values:
            if isinstance(cert, dict):
                name = cert.get("name", "")
                if name:
                    certifications.append(name)

        # Phone
        phone = None
        phone_data = data.get("phoneNumbers", {})
        phone_values = phone_data.get("values", []) if isinstance(phone_data, dict) else []
        if phone_values and isinstance(phone_values[0], dict):
            phone = phone_values[0].get("phoneNumber")

        profile_data = {
            "full_name": full_name,
            "email": data.get("emailAddress", ""),
            "phone": phone,
            "summary": data.get("summary", data.get("headline", "")),
            "location": location,
            "skills": skills,
            "work_experience": work_experience,
            "education": education,
            "certifications": certifications,
        }

        return _dict_to_user_profile(profile_data)


class TextProfileParser(ProfileParser):
    """
    Parser for plain text resumes.

    Responsibility: Reads text resume files and uses an LLM to extract
    structured profile data.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider

    def parse(self, file_path: str) -> UserProfile:
        """
        Parse text resume file.

        Args:
            file_path: Path to text resume

        Returns:
            Structured UserProfile

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If parsing fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")
        if not self.supports_format(file_path):
            raise ValueError(f"Not a text file: {file_path}")
        if self.llm_provider is None:
            raise ValueError(
                "LLM provider required for text parsing. "
                "Pass an LLMProvider instance to TextProfileParser constructor."
            )

        try:
            text_content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text_content = path.read_text(encoding="latin-1")
        except Exception as e:
            logger.error(f"Failed to read text file {file_path}: {e}")
            raise ValueError(f"Failed to read text file: {e}") from e

        if not text_content.strip():
            raise ValueError(f"Text file is empty: {file_path}")

        logger.info(f"Read {len(text_content)} characters from text file: {file_path}")

        try:
            profile = _extract_profile_from_text(text_content, self.llm_provider)
            logger.info(f"Successfully parsed text profile for: {profile.full_name}")
            return profile
        except (ConnectionError, RuntimeError) as e:
            logger.error(f"LLM extraction failed for text file {file_path}: {e}")
            raise ValueError(f"Failed to extract profile from text: {e}") from e

    def supports_format(self, file_path: str) -> bool:
        """Check if file is text format."""
        return Path(file_path).suffix.lower() in (".txt", ".text", ".md", ".rst")


class ProfileParserFactory:
    """
    Factory for creating appropriate profile parsers.

    Responsibility: Instantiates the correct parser based on file format,
    following the Factory Pattern for extensibility.
    """

    _parsers: list = []

    @classmethod
    def register_parser(cls, parser: ProfileParser) -> None:
        """Register a profile parser."""
        cls._parsers.append(parser)

    @classmethod
    def create_with_llm(cls, llm_provider: LLMProvider) -> None:
        """
        Register all default parsers with an LLM provider.

        This sets up PDF and Text parsers with LLM-based extraction
        and a JSON parser (which doesn't need LLM).

        Args:
            llm_provider: The LLM provider for PDF/text extraction.
        """
        cls._parsers = [
            JSONProfileParser(),
            PDFProfileParser(llm_provider=llm_provider),
            TextProfileParser(llm_provider=llm_provider),
        ]
        logger.info("Registered all parsers with LLM provider")

    @classmethod
    def parse_profile(cls, file_path: str) -> UserProfile:
        """
        Parse profile file using appropriate parser.

        Args:
            file_path: Path to profile file

        Returns:
            Structured UserProfile

        Raises:
            ValueError: If no suitable parser found
        """
        if not cls._parsers:
            cls._register_defaults()

        parser = cls.get_parser(file_path)
        if parser is None:
            supported = [type(p).__name__ for p in cls._parsers]
            raise ValueError(
                f"No parser found for file: {file_path}. "
                f"Registered parsers: {supported}"
            )

        logger.info(f"Using {type(parser).__name__} for {file_path}")
        return parser.parse(file_path)

    @classmethod
    def get_parser(cls, file_path: str) -> Optional[ProfileParser]:
        """Get appropriate parser for file."""
        for parser in cls._parsers:
            if parser.supports_format(file_path):
                return parser
        return None

    @classmethod
    def _register_defaults(cls) -> None:
        """Register default parsers (PDF/Text without LLM — will error if used)."""
        cls._parsers = [
            JSONProfileParser(),
            PDFProfileParser(),
            TextProfileParser(),
        ]

    @classmethod
    def reset(cls) -> None:
        """Clear all registered parsers. Useful for testing."""
        cls._parsers = []


class ProfileValidator:
    """
    Validates UserProfile completeness and accuracy.

    Responsibility: Ensures parsed profiles meet quality standards
    and have required fields.
    """

    @staticmethod
    def validate(profile: UserProfile) -> bool:
        """
        Validate a UserProfile.

        Args:
            profile: UserProfile to validate

        Returns:
            True if valid

        Raises:
            ValueError: If profile is invalid with details
        """
        errors = []

        if not profile.user_id or not profile.user_id.strip():
            errors.append("user_id is required")
        if not profile.full_name or not profile.full_name.strip():
            errors.append("full_name is required")
        if not profile.email or not profile.email.strip():
            errors.append("email is required")

        if profile.email and "@" not in profile.email:
            errors.append(f"Invalid email format: {profile.email}")

        for i, exp in enumerate(profile.work_experience):
            if not exp.company:
                errors.append(f"work_experience[{i}].company is required")
            if not exp.position:
                errors.append(f"work_experience[{i}].position is required")
            if exp.end_date and exp.start_date and exp.end_date < exp.start_date:
                errors.append(
                    f"work_experience[{i}]: end_date before start_date "
                    f"at {exp.company}"
                )

        for i, edu in enumerate(profile.education):
            if not edu.institution:
                errors.append(f"education[{i}].institution is required")
            if not edu.degree:
                errors.append(f"education[{i}].degree is required")

        if errors:
            error_msg = "Profile validation failed: " + "; ".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Profile validated successfully for: {profile.full_name}")
        return True

    @staticmethod
    def validate_completeness(profile: UserProfile) -> dict:
        """
        Check profile completeness and return missing fields.

        Args:
            profile: UserProfile to check

        Returns:
            Dictionary with completeness score and missing fields
        """
        checks = [
            ("full_name", bool(profile.full_name and profile.full_name.strip())),
            ("email", bool(profile.email and profile.email.strip())),
            ("phone", bool(profile.phone and profile.phone.strip())),
            ("summary", bool(profile.summary and profile.summary.strip())),
            ("location", profile.location is not None),
            ("skills", len(profile.skills) > 0),
            ("work_experience", len(profile.work_experience) > 0),
            ("education", len(profile.education) > 0),
            ("certifications", len(profile.certifications) > 0),
            ("preferred_job_levels", len(profile.preferred_job_levels) > 0),
        ]

        missing_fields = []
        filled_fields = 0
        total_fields = len(checks)

        for field_name, is_present in checks:
            if is_present:
                filled_fields += 1
            else:
                missing_fields.append(field_name)

        score = filled_fields / total_fields if total_fields > 0 else 0.0

        result = {
            "completeness_score": round(score, 2),
            "filled_fields": filled_fields,
            "total_fields": total_fields,
            "missing_fields": missing_fields,
            "is_complete": len(missing_fields) == 0,
        }

        logger.debug(
            f"Profile completeness: {result['completeness_score']:.0%} "
            f"({filled_fields}/{total_fields}), "
            f"missing: {missing_fields}"
        )

        return result
