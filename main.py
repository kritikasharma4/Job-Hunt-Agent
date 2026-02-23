"""
Main entry point for the AI Job Hunting Agent.

Example usage:
    python main.py --profile resume.pdf --query "Python Developer" --location "San Francisco"
"""

import argparse
import sys
import logging
from typing import Optional
from config.settings import AppSettings
from core.agent import JobHuntingAgent, AgentBuilder


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


def build_agent(settings: AppSettings) -> JobHuntingAgent:
    """
    Build the job hunting agent with configured components.

    Args:
        settings: Application settings

    Returns:
        Configured JobHuntingAgent

    TODO: Implement with actual component initialization
    """
    builder = AgentBuilder(settings)
    # TODO: Add profile parser
    # TODO: Add job fetchers
    # TODO: Add relevance scorer
    # TODO: Add filter pipeline
    # return builder.build()
    pass


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
        agent = build_agent(settings)

        if agent is None:
            logger.error("Failed to build agent - components not yet implemented")
            return 1

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

        logger.info(f"Complete! Found {len(matches)} relevant job matches.")
        return 0

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
