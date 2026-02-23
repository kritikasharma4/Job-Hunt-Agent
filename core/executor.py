"""
Job application executor and tracking.

Manages job applications and tracks their status.
"""

import logging
import uuid
from typing import List, Optional
from datetime import datetime

from models.schemas import ApplicationRecord, Job

logger = logging.getLogger(__name__)

VALID_STATUSES = {"pending", "accepted", "rejected", "interview", "offer", "withdrawn"}


class ApplicationExecutor:
    """
    Manages job applications and execution tracking.

    Responsibility: Tracks job applications, manages state, and maintains
    application history for analysis and reporting.
    """

    def __init__(self):
        """Initialize application executor."""
        self.applications: dict = {}

    def submit_application(
        self,
        user_id: str,
        job: Job,
        notes: Optional[str] = None
    ) -> ApplicationRecord:
        """
        Submit a job application.

        Args:
            user_id: User identifier
            job: Job to apply for
            notes: Optional notes about the application

        Returns:
            ApplicationRecord tracking the submission

        Raises:
            ValueError: If user_id is empty or job is invalid
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")
        if not job or not job.job_id:
            raise ValueError("Valid job with job_id is required")

        # Check for duplicate application
        for app in self.applications.values():
            if app.user_id == user_id and app.job_id == job.job_id:
                logger.warning(
                    f"Duplicate application: user '{user_id}' already applied "
                    f"to '{job.title}' at {job.company}"
                )
                return app

        app_id = str(uuid.uuid4())[:8]

        record = ApplicationRecord(
            application_id=app_id,
            user_id=user_id,
            job_id=job.job_id,
            job_title=job.title,
            company=job.company,
            applied_date=datetime.now(),
            status="pending",
            notes=notes or "",
        )

        self.applications[app_id] = record
        logger.info(
            f"Application submitted: {record.job_title} at {record.company} "
            f"(id={app_id})"
        )

        return record

    def get_application(self, application_id: str) -> Optional[ApplicationRecord]:
        """Get application by ID."""
        return self.applications.get(application_id)

    def update_application_status(
        self,
        application_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> ApplicationRecord:
        """
        Update application status.

        Args:
            application_id: Application to update
            status: New status (pending, accepted, rejected, interview, offer, withdrawn)
            notes: Optional status notes

        Returns:
            Updated ApplicationRecord

        Raises:
            ValueError: If application not found or invalid status
        """
        record = self.applications.get(application_id)
        if not record:
            raise ValueError(f"Application not found: {application_id}")

        status_lower = status.lower().strip()
        if status_lower not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}"
            )

        old_status = record.status
        record.status = status_lower
        if notes:
            record.notes = notes

        logger.info(
            f"Application {application_id} updated: "
            f"{old_status} -> {status_lower} ({record.job_title})"
        )

        return record

    def get_user_applications(self, user_id: str) -> List[ApplicationRecord]:
        """Get all applications for a user."""
        return [
            app for app in self.applications.values()
            if app.user_id == user_id
        ]

    def get_applications_by_status(
        self,
        user_id: str,
        status: str
    ) -> List[ApplicationRecord]:
        """Get applications filtered by status."""
        status_lower = status.lower().strip()
        return [
            app for app in self.applications.values()
            if app.user_id == user_id and app.status == status_lower
        ]
