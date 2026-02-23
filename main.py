"""
Main entry point for the AI Job Hunting Agent.

Example usage:
    python main.py --profile resume.pdf --query "Python Developer" --location "San Francisco"
    python main.py --profile profile.json --query "Data Scientist" --sources linkedin indeed
"""

import argparse
import sys
import logging
from typing import Optional
from config.settings import AppSettings, LLMConfig
from core.agent import JobHuntingAgent, AgentBuilder
from jobs.fetchers.base import LinkedInJobFetcher, IndeedJobFetcher
from filters.job_filters import (
    SalaryFilter, LocationFilter, ExperienceLevelFilter,
    KeywordFilter, DuplicateFilter,
)


def setup_logging(debug: bool = False, log_level: str = "INFO") -> None:
    """
    Configure logging for the application.

    Args:
        debug: Enable debug mode
        log_level: Logging level
    """
    level = logging.DEBUG if debug else getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def build_agent(settings: AppSettings, args: argparse.Namespace) -> JobHuntingAgent:
    """
    Build the job hunting agent with configured components.

    Args:
        settings: Application settings
        args: Parsed CLI arguments

    Returns:
        Configured JobHuntingAgent
    """
    builder = AgentBuilder(settings)

    # Try to set up LLM provider (optional — needed for PDF/text parsing and LLM matching)
    llm_provider = _try_setup_llm(settings)
    if llm_provider:
        builder.with_llm(llm_provider)

    # Add fetchers
    sources = args.sources or settings.job_fetcher.enabled_sources
    builder.with_fetchers(sources)

    # Add filters
    builder.with_filter(DuplicateFilter())
    builder.with_filter(SalaryFilter())
    builder.with_filter(ExperienceLevelFilter())

    if settings.filter.excluded_keywords:
        builder.with_filter(KeywordFilter(settings.filter.excluded_keywords))

    return builder.build()


def _try_setup_llm(settings: AppSettings):
    """Try to initialize the LLM provider. Returns None if unavailable."""
    logger = logging.getLogger(__name__)

    if settings.llm.provider.lower() == "ollama":
        try:
            from llm.ollama_provider import OllamaProvider
            provider = OllamaProvider(settings.llm)
            if provider.validate_credentials():
                logger.info("Ollama LLM provider connected")
                return provider
            else:
                logger.warning("Ollama not available — running without LLM")
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama: {e}")
            return None

    return None


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI Job Hunting Agent - Intelligent job matching and application"
    )

    parser.add_argument(
        "--profile",
        required=True,
        type=str,
        help="Path to resume/profile file (PDF, JSON, or TXT)"
    )

    parser.add_argument(
        "--query",
        required=True,
        type=str,
        help="Job search query (title, keywords, etc.)"
    )

    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Job location filter (optional)"
    )

    parser.add_argument(
        "--sources",
        type=str,
        nargs="+",
        default=None,
        help="Job sources to search (linkedin, indeed, etc.)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="results.json",
        help="Output file for results (default: results.json)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=0.6,
        help="Minimum relevance score filter (0-1, default: 0.6)"
    )

    return parser.parse_args()


def main() -> int:
    """
    Main application entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Parse arguments
        args = parse_arguments()

        # Setup logging
        setup_logging(debug=args.debug)
        logger = logging.getLogger(__name__)

        logger.info("Initializing AI Job Hunting Agent...")

        # Load settings from environment
        settings = AppSettings.from_env()
        settings.debug = args.debug
        settings.relevance.min_relevance_score = args.min_score

        # Build agent
        logger.info("Building agent with configured components...")
        agent = build_agent(settings, args)

        # Run pipeline
        logger.info(f"Loading profile from {args.profile}...")
        logger.info(f"Searching for: {args.query}")

        matches = agent.run_pipeline(
            profile_path=args.profile,
            query=args.query,
            location=args.location,
            sources=args.sources
        )

        # Save results
        logger.info(f"Saving results to {args.output}...")
        agent.save_results(matches, args.output)

        # Print summary
        logger.info(f"Complete! Found {len(matches)} relevant job matches.")
        if matches:
            print(f"\nTop {min(5, len(matches))} matches:")
            for i, m in enumerate(matches[:5], 1):
                print(
                    f"  {i}. {m.job.title} at {m.job.company} "
                    f"(score: {m.relevance_score.overall_score:.2f})"
                )
            print(f"\nFull results saved to: {args.output}")
        else:
            print("\nNo matching jobs found. Try broadening your search.")

        return 0

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return 130
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
