from __future__ import annotations
"""Connector registry — centralized singleton management for all connectors.

Solves: Module-level connector instantiation without initialization (C-2).

Usage:
    # At server startup (server.py):
    from .connectors.registry import initialize_connectors
    await initialize_connectors()

    # In tool modules:
    from ..connectors.registry import get_sfdc, get_groupsio
    org = await get_sfdc().get_org(org_id)
"""

import logging
from typing import Optional

from .salesforce import SalesforceConnector
from .groupsio import GroupsIOConnector
from .calendar import GoogleCalendarConnector
from .discord import DiscordConnector
from .github_connector import GitHubConnector
from .lfx_platform import LFXPlatformConnector
from .hubspot import HubSpotConnector

logger = logging.getLogger(__name__)

# ── Singleton instances ──────────────────────────────────────────
_sfdc: Optional[SalesforceConnector] = None
_groupsio: Optional[GroupsIOConnector] = None
_calendar: Optional[GoogleCalendarConnector] = None
_discord: Optional[DiscordConnector] = None
_github: Optional[GitHubConnector] = None
_lfx: Optional[LFXPlatformConnector] = None
_hubspot: Optional[HubSpotConnector] = None
_initialized: bool = False


async def initialize_connectors() -> None:
    """Initialize all connector singletons. Call once at server startup.

    Creates each connector, calls its async initialize() method (which
    handles authentication or mock-data setup), and stores the singleton.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _sfdc, _groupsio, _calendar, _discord, _github, _lfx, _hubspot, _initialized

    if _initialized:
        logger.debug("Connector registry already initialized — skipping")
        return

    logger.info("Initializing connector registry (7 connectors)…")

    _sfdc = SalesforceConnector()
    await _sfdc.initialize()

    _groupsio = GroupsIOConnector()
    await _groupsio.initialize()

    _calendar = GoogleCalendarConnector()
    await _calendar.initialize()

    _discord = DiscordConnector()
    await _discord.initialize()

    _github = GitHubConnector()
    await _github.initialize()

    _lfx = LFXPlatformConnector()
    await _lfx.initialize()

    _hubspot = HubSpotConnector()
    await _hubspot.initialize()

    _initialized = True
    logger.info("All 7 connectors initialized successfully")

    # Validate configuration
    from ..config import validate_config
    warnings = validate_config()
    for w in warnings:
        logger.warning(f"Config: {w}")


async def shutdown_connectors() -> None:
    """Gracefully close all connector HTTP clients."""
    global _initialized

    for name, connector in [
        ("salesforce", _sfdc),
        ("groupsio", _groupsio),
        ("calendar", _calendar),
        ("discord", _discord),
        ("github", _github),
        ("lfx_platform", _lfx),
        ("hubspot", _hubspot),
    ]:
        if connector and hasattr(connector, "close"):
            try:
                await connector.close()
                logger.debug(f"Closed {name} connector")
            except Exception as e:
                logger.warning(f"Error closing {name} connector: {e}")

    _initialized = False
    logger.info("Connector registry shut down")


# ── Getter functions ─────────────────────────────────────────────
# Each raises RuntimeError if called before initialize_connectors().


def _check_init() -> None:
    if not _initialized:
        raise RuntimeError(
            "Connector registry not initialized. "
            "Call 'await initialize_connectors()' at server startup."
        )


def get_sfdc() -> SalesforceConnector:
    """Return the Salesforce connector singleton."""
    _check_init()
    return _sfdc  # type: ignore[return-value]


def get_groupsio() -> GroupsIOConnector:
    """Return the Groups.io connector singleton."""
    _check_init()
    return _groupsio  # type: ignore[return-value]


def get_calendar() -> GoogleCalendarConnector:
    """Return the Google Calendar connector singleton."""
    _check_init()
    return _calendar  # type: ignore[return-value]


def get_discord() -> DiscordConnector:
    """Return the Discord connector singleton."""
    _check_init()
    return _discord  # type: ignore[return-value]


def get_github() -> GitHubConnector:
    """Return the GitHub connector singleton."""
    _check_init()
    return _github  # type: ignore[return-value]


def get_lfx() -> LFXPlatformConnector:
    """Return the LFX Platform connector singleton."""
    _check_init()
    return _lfx  # type: ignore[return-value]


def get_hubspot() -> HubSpotConnector:
    """Return the HubSpot connector singleton."""
    _check_init()
    return _hubspot  # type: ignore[return-value]
