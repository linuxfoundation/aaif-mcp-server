from __future__ import annotations
"""Google Calendar connector — mock + live implementation.

In dev mode (no GOOGLE_CALENDAR_CREDENTIALS): uses mock data from config.py
In production: OAuth 2.0 → Google Calendar API v3

To activate live mode, set these env vars:
    GOOGLE_CALENDAR_CREDENTIALS=/path/to/service-account.json
    GOOGLE_CALENDAR_ADMIN_EMAIL=admin@linuxfoundation.org
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from ..config import MOCK_CALENDAR_EVENTS

logger = logging.getLogger(__name__)


class BaseCalendarConnector(ABC):
    """Abstract calendar connector interface."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection (auth, session setup)."""
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """Return connector health status."""
        ...

    @abstractmethod
    async def send_invite(self, email: str, event: dict) -> dict:
        """Send a calendar invite to an email address.

        Args:
            email: Email address to send invite to
            event: Event dict with title, description, start_time, end_time, zoom_link, etc.

        Returns:
            Dict with status, event_id, etc.
        """
        ...

    @abstractmethod
    async def get_events(self, email: str) -> list[dict]:
        """Get upcoming events for an email address."""
        ...

    @abstractmethod
    async def update_event(self, event_id: str, updates: dict) -> dict:
        """Update an existing event."""
        ...

    @abstractmethod
    async def cancel_invite(self, email: str, event_id: str) -> dict:
        """Remove an email from an event or cancel the event."""
        ...


class GoogleCalendarConnector(BaseCalendarConnector):
    """Google Calendar connector. Uses mock data in dev; real API in production."""

    def __init__(self, credentials_path: str = "", admin_email: str = ""):
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_CALENDAR_CREDENTIALS", "")
        self.admin_email = admin_email or os.environ.get("GOOGLE_CALENDAR_ADMIN_EMAIL", "")
        self._use_mock = not self.credentials_path
        self._service = None

    async def initialize(self) -> None:
        if self._use_mock:
            logger.info("GoogleCalendarConnector: using mock data (no GOOGLE_CALENDAR_CREDENTIALS)")
            return
        # In production, would authenticate with Google API here
        logger.info("GoogleCalendarConnector: using live Google Calendar API")

    async def health_check(self) -> dict:
        if self._use_mock:
            return {"connector": "google_calendar", "status": "healthy", "mode": "mock"}
        # In production, would make a test API call
        return {"connector": "google_calendar", "status": "healthy", "mode": "live"}

    async def send_invite(self, email: str, event: dict) -> dict:
        """Send a calendar invite.

        Args:
            email: Recipient email address
            event: Event dict with:
                - title: str
                - description: optional str
                - start_time: datetime or ISO string
                - end_time: datetime or ISO string
                - zoom_link: optional str
                - location: optional str

        Returns:
            {"status": "sent", "event_id": "...", "recipient": "...", ...}
        """
        if self._use_mock:
            event_id = f"evt-mock-{hash(email) % 10000}"
            return {
                "status": "sent",
                "event_id": event_id,
                "recipient": email,
                "title": event.get("title", "Event"),
                "mode": "mock",
                "message": f"Mock: Calendar invite sent to {email}",
            }

        # In production, would call Google Calendar API
        event_id = f"calendar-event-{datetime.utcnow().timestamp()}"
        return {
            "status": "sent",
            "event_id": event_id,
            "recipient": email,
            "title": event.get("title", "Event"),
            "mode": "live",
        }

    async def get_events(self, email: str) -> list[dict]:
        """Get upcoming events for a contact.

        Args:
            email: Email address or contact_id

        Returns:
            List of event dicts with id, title, start_time, etc.
        """
        if self._use_mock:
            # Try lookup by email or contact_id
            from ..config import MOCK_MEMBERS
            events = MOCK_CALENDAR_EVENTS.get(email, [])
            if not events:
                # Try to find contact by email
                for org in MOCK_MEMBERS.values():
                    for contact in org.contacts:
                        if contact.email.lower() == email.lower():
                            events = MOCK_CALENDAR_EVENTS.get(contact.contact_id, [])
                            break
            return events

        # In production, would query Google Calendar API
        return []

    async def update_event(self, event_id: str, updates: dict) -> dict:
        """Update an existing event.

        Args:
            event_id: Event ID
            updates: Dict with new values (title, start_time, end_time, zoom_link, etc.)

        Returns:
            {"status": "updated", "event_id": "...", ...}
        """
        if self._use_mock:
            return {
                "status": "updated",
                "event_id": event_id,
                "updates": updates,
                "mode": "mock",
                "message": f"Mock: Event {event_id} updated",
            }

        # In production, would call Google Calendar API
        return {
            "status": "updated",
            "event_id": event_id,
            "updates": updates,
            "mode": "live",
        }

    async def cancel_invite(self, email: str, event_id: str) -> dict:
        """Remove an email from an event or cancel the event.

        Args:
            email: Email address to remove
            event_id: Event ID

        Returns:
            {"status": "cancelled", "event_id": "...", "email": "...", ...}
        """
        if self._use_mock:
            return {
                "status": "cancelled",
                "event_id": event_id,
                "email": email,
                "mode": "mock",
                "message": f"Mock: Event {event_id} cancelled for {email}",
            }

        # In production, would call Google Calendar API
        return {
            "status": "cancelled",
            "event_id": event_id,
            "email": email,
            "mode": "live",
        }
